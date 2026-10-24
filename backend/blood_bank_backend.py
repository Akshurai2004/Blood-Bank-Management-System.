import os
import re
import time
from urllib.parse import urlparse, parse_qs
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple, Any


class BloodBankDB:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        ssl_mode: Optional[str] = None,
        ssl_ca: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize database connection with full support for:
        - DATABASE_URL / POSTGRES_URL connection strings (e.g. from Render)
        - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME environment variables
        - SSL encryption for remote/cloud PostgreSQL servers
        """
        # Parse connection string if available
        database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
        url_config = {}
        if database_url:
            try:
                parsed = urlparse(database_url)
                if parsed.hostname:
                    url_config['host'] = parsed.hostname
                if parsed.port:
                    url_config['port'] = parsed.port
                if parsed.username:
                    url_config['user'] = parsed.username
                if parsed.password:
                    url_config['password'] = parsed.password
                if parsed.path and parsed.path.lstrip('/'):
                    url_config['database'] = parsed.path.lstrip('/')
                query_params = parse_qs(parsed.query)
                if 'ssl-mode' in query_params:
                    url_config['ssl_mode'] = query_params['ssl-mode'][0]
                elif 'ssl' in query_params:
                    url_config['ssl_mode'] = query_params['ssl'][0]
            except Exception as e:
                print(f"[DB CONFIG] Error parsing DATABASE_URL: {e}")

        self.host = host or url_config.get('host') or os.getenv('DB_HOST', 'localhost')

        raw_port = port or url_config.get('port') or os.getenv('DB_PORT', '5432')
        try:
            self.port = int(str(raw_port).strip())
        except (ValueError, TypeError):
            self.port = 5432

        self.user = user or url_config.get('user') or os.getenv('DB_USER', 'root')

        if password is not None:
            self.password = password
        elif 'password' in url_config:
            self.password = url_config['password']
        else:
            self.password = os.getenv('DB_PASSWORD', '')

        self.database = database or url_config.get('database') or os.getenv('DB_NAME', 'BloodBankDB')

        # SSL Configuration
        ssl_env = os.getenv('DB_SSL', '').strip().lower()
        self.ssl_mode = ssl_mode or url_config.get('ssl_mode') or os.getenv('DB_SSL_MODE')
        if not self.ssl_mode and ssl_env in ('true', '1', 'yes', 'required'):
            self.ssl_mode = 'REQUIRED'

        self.ssl_ca = ssl_ca or os.getenv('DB_SSL_CA')
        self.connection_timeout = int(os.getenv('DB_CONNECTION_TIMEOUT', '10'))
        self.connection = None

    @staticmethod
    def _adapt_query(query: str) -> str:
        """Translate the small set of legacy MySQL expressions still used by the API."""
        query = re.sub(r"\bUser\b", '"app_user"', query)
        query = query.replace("CURDATE()", "CURRENT_DATE")
        query = re.sub(
            r"DATE_ADD\(CURRENT_DATE, INTERVAL (\d+) DAY\)",
            r"(CURRENT_DATE + INTERVAL '\1 days')",
            query,
            flags=re.IGNORECASE,
        )
        query = re.sub(
            r"DATEDIFF\(MIN\(([^)]+)\), CURRENT_DATE\)",
            r"(MIN(\1)::date - CURRENT_DATE)",
            query,
            flags=re.IGNORECASE,
        )
        query = re.sub(
            r"IF\(([^,]+), NOW\(\), NULL\)",
            r"CASE WHEN \1 THEN NOW() ELSE NULL END",
            query,
            flags=re.IGNORECASE,
        )
        return query

    @staticmethod
    def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """Keep the API's existing column names while PostgreSQL stores lowercase identifiers."""
        column_names = {
            "hospitalid": "HospitalID", "hospitalname": "HospitalName",
            "location": "Location", "contactno": "ContactNo", "email": "Email",
            "address": "Address", "capacity": "Capacity",
            "bloodbankid": "BloodBankID", "bloodbankname": "BloodBankName",
            "donorid": "DonorID", "donorname": "DonorName",
            "bloodgroup": "BloodGroup", "bloodgrouprequired": "BloodGroupRequired",
            "lastdonationdate": "LastDonationDate",
            "totaldonations": "TotalDonations", "isactive": "IsActive",
            "unitid": "UnitID", "quantity": "Quantity", "collectiondate": "CollectionDate",
            "expirationdate": "ExpirationDate", "status": "Status", "component": "Component",
            "patientid": "PatientID", "patientname": "PatientName", "hospitalid": "HospitalID",
            "medicalcondition": "MedicalCondition", "requestid": "RequestID",
            "requiredunits": "RequiredUnits", "requestdate": "RequestDate",
            "fulfilleddate": "FulfilledDate", "allocationid": "AllocationID",
            "allocationdate": "AllocationDate", "deliverystatus": "DeliveryStatus",
            "userid": "UserID", "fullname": "FullName", "passwordhash": "PasswordHash",
            "role": "Role", "donor_id": "DonorID", "hospital_id": "HospitalID",
            "blood_bank_id": "BloodBankID", "createdat": "CreatedAt", "updatedat": "UpdatedAt",
            "totalunits": "TotalUnits", "totalquantity": "TotalQuantity",
            "nearestexpiry": "NearestExpiry", "daysuntilexpiry": "DaysUntilExpiry",
        }
        return {column_names.get(key, key): value for key, value in row.items()}

    def connect(self) -> bool:
        """Establish database connection to PostgreSQL with retries and SSL support."""
        if self.connection:
            try:
                if self.connection.closed == 0:
                    return True
            except Exception:
                pass

        connect_kwargs = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "connect_timeout": self.connection_timeout,
        }

        if self.ssl_mode or os.getenv('DB_SSL', '').strip().lower() in ('true', '1', 'yes', 'required'):
            connect_kwargs["sslmode"] = "require"
        elif os.getenv('DB_SSL_DISABLED', '').lower() in ('true', '1', 'yes'):
            connect_kwargs["sslmode"] = "disable"

        max_retries = int(os.getenv('DB_CONNECT_RETRIES', '3'))
        retry_delay = 2

        for attempt in range(1, max_retries + 1):
            try:
                self.connection = psycopg2.connect(**connect_kwargs)
                if self.connection.closed == 0:
                    print(f"[DATABASE] Connected to PostgreSQL server at {self.host}:{self.port} (DB: {self.database})")
                    return True
            except Error as e:
                print(f"[DATABASE] Connection attempt {attempt}/{max_retries} failed for {self.host}:{self.port}: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)

        return False

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            try:
                if self.connection.closed == 0:
                    self.connection.close()
                    print("[DATABASE] Connection closed")
            except Exception:
                pass
        self.connection = None

    def ensure_connection(self) -> bool:
        """Reconnect automatically if the connection drops or idles out"""
        if not self.connection or self.connection.closed != 0:
            return self.connect()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return self.connect()

    def execute_query(self, query: str, params: tuple = None) -> bool:
        """Execute INSERT, UPDATE, DELETE queries"""
        if not self.ensure_connection():
            return False

        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(self._adapt_query(query), params or ())
            self.connection.commit()
            return True
        except Error as e:
            print(f"Error executing query: {e}")
            if self.connection:
                self.connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()

    def fetch_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute SELECT queries and return results as list of dictionaries"""
        if not self.ensure_connection():
            return []

        cursor = None
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute(self._adapt_query(query), params or ())
            return [self._normalize_row(dict(row)) for row in cursor.fetchall()]
        except Error as e:
            print(f"Error fetching data: {e}")
            return []
        finally:
            if cursor:
                cursor.close()

    def has_column(self, table: str, column: str) -> bool:
        """Check INFORMATION_SCHEMA to see if a table has a given column"""
        try:
            query = """
            SELECT COUNT(*) as cnt FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
            """
            result = self.fetch_query(query, (table.lower(), column.lower()))
            if not result:
                return False
            return int(result[0].get('cnt', 0)) > 0
        except Exception as e:
            print(f"Error checking column existence: {e}")
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """Return database server connection metadata"""
        is_conn = bool(self.connection and self.connection.closed == 0)
        return {
            "connected": is_conn,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "ssl_enabled": bool(self.ssl_mode or self.ssl_ca),
        }

    def execute_sql_file(self, file_path: str) -> bool:
        """Execute a .sql file (e.g. render.sql) statement-by-statement against the database"""
        if not self.ensure_connection():
            return False

        if not os.path.exists(file_path):
            print(f"[SQL RUNNER] File not found: {file_path}")
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            cursor = self.connection.cursor()
            current_delimiter = ";"
            statement = []

            for line in content.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("--") or stripped.startswith("/*"):
                    continue

                if stripped.upper().startswith("DELIMITER "):
                    parts = stripped.split()
                    if len(parts) > 1:
                        current_delimiter = parts[1]
                    continue

                statement.append(line)
                if stripped.endswith(current_delimiter):
                    sql_cmd = "\n".join(statement)
                    if sql_cmd.endswith(current_delimiter):
                        sql_cmd = sql_cmd[:-len(current_delimiter)].strip()

                    if sql_cmd:
                        try:
                            cursor.execute(sql_cmd)
                        except Error as e:
                            print(f"[SQL WARNING] {e} on: {sql_cmd[:50]}...")
                    statement = []

            self.connection.commit()
            cursor.close()
            print(f"[SQL RUNNER] Successfully executed '{file_path}'")
            return True
        except Exception as e:
            print(f"[SQL RUNNER] Error executing '{file_path}': {e}")
            if self.connection:
                self.connection.rollback()
            return False

    # ==================== SCHEMA INITIALIZATION & SEEDING ====================

    def init_schema(self) -> bool:
        """Initialize tables, views, and seed data if not present on MySQL server"""
        if not self.ensure_connection():
            return False

        # If render.sql exists in project, use it directly
        for candidate in ["render.sql", "database/render.sql", "../render.sql", os.path.join(os.path.dirname(__file__), "..", "render.sql")]:
            if os.path.exists(candidate):
                print(f"[SCHEMA] Initializing database using '{candidate}'...")
                return self.execute_sql_file(candidate)

        print("[SCHEMA ERROR] PostgreSQL schema file 'render.sql' was not found.")
        return False

        tables = [
            """
            CREATE TABLE IF NOT EXISTS Hospital (
                HospitalID INT AUTO_INCREMENT PRIMARY KEY,
                HospitalName VARCHAR(100) NOT NULL UNIQUE,
                Location VARCHAR(100) NOT NULL,
                ContactNo VARCHAR(15) NOT NULL,
                Email VARCHAR(100),
                INDEX idx_location (Location)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            """
            CREATE TABLE IF NOT EXISTS BloodBank (
                BloodBankID INT AUTO_INCREMENT PRIMARY KEY,
                BloodBankName VARCHAR(100) NOT NULL UNIQUE,
                Location VARCHAR(100) NOT NULL,
                ContactNo VARCHAR(15) NOT NULL,
                Capacity INT DEFAULT 1000,
                INDEX idx_location (Location)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            """
            CREATE TABLE IF NOT EXISTS Donor (
                DonorID INT AUTO_INCREMENT PRIMARY KEY,
                DonorName VARCHAR(100) NOT NULL,
                Age INT CHECK (Age >= 18 AND Age <= 65),
                Gender ENUM('M','F','O'),
                BloodGroup VARCHAR(5) NOT NULL,
                ContactNo VARCHAR(15) UNIQUE NOT NULL,
                Email VARCHAR(100),
                Address VARCHAR(255),
                LastDonationDate DATE,
                TotalDonations INT DEFAULT 0,
                RegistrationDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                IsActive BOOLEAN DEFAULT TRUE,
                INDEX idx_blood_group (BloodGroup),
                INDEX idx_contact (ContactNo)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            """
            CREATE TABLE IF NOT EXISTS BloodUnit (
                UnitID INT AUTO_INCREMENT PRIMARY KEY,
                DonorID INT NOT NULL,
                BloodBankID INT NOT NULL,
                BloodGroup VARCHAR(5) NOT NULL,
                Quantity INT DEFAULT 1 CHECK (Quantity > 0),
                CollectionDate DATE NOT NULL,
                ExpirationDate DATE NOT NULL,
                Status ENUM('Available','Reserved','Used','Expired') DEFAULT 'Available',
                Component ENUM('Whole Blood','RBC','Plasma','Platelets') DEFAULT 'Whole Blood', 
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (DonorID) REFERENCES Donor(DonorID) ON DELETE CASCADE,
                FOREIGN KEY (BloodBankID) REFERENCES BloodBank(BloodBankID) ON DELETE RESTRICT,
                INDEX idx_blood_group (BloodGroup),
                INDEX idx_status (Status),
                INDEX idx_expiration (ExpirationDate)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            """
            CREATE TABLE IF NOT EXISTS Patient (
                PatientID INT AUTO_INCREMENT PRIMARY KEY,
                PatientName VARCHAR(100) NOT NULL,
                Age INT CHECK (Age > 0),
                Gender ENUM('M','F','O'),
                BloodGroupRequired VARCHAR(5) NOT NULL,
                HospitalID INT NOT NULL,
                ContactNo VARCHAR(15) NOT NULL,
                MedicalCondition VARCHAR(255),
                RegistrationDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                IsActive BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (HospitalID) REFERENCES Hospital(HospitalID) ON DELETE CASCADE,
                INDEX idx_blood_group (BloodGroupRequired),
                INDEX idx_hospital (HospitalID)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            """
            CREATE TABLE IF NOT EXISTS Request (
                RequestID INT AUTO_INCREMENT PRIMARY KEY,
                PatientID INT NOT NULL,
                BloodBankID INT NOT NULL,
                RequiredUnits INT DEFAULT 1 CHECK (RequiredUnits > 0),
                Status ENUM('Pending','Fulfilled','Denied') DEFAULT 'Pending',
                RequestDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FulfilledDate TIMESTAMP NULL,
                FOREIGN KEY (PatientID) REFERENCES Patient(PatientID) ON DELETE CASCADE,
                FOREIGN KEY (BloodBankID) REFERENCES BloodBank(BloodBankID) ON DELETE RESTRICT,
                INDEX idx_status (Status),
                INDEX idx_request_date (RequestDate)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            """
            CREATE TABLE IF NOT EXISTS Allocation (
                AllocationID INT AUTO_INCREMENT PRIMARY KEY,
                RequestID INT NOT NULL,
                UnitID INT NOT NULL,
                AllocationDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                DeliveryStatus ENUM('Pending','Delivered','Failed') DEFAULT 'Pending',
                FOREIGN KEY (RequestID) REFERENCES Request(RequestID) ON DELETE CASCADE,
                FOREIGN KEY (UnitID) REFERENCES BloodUnit(UnitID) ON DELETE RESTRICT,
                INDEX idx_request (RequestID),
                INDEX idx_unit (UnitID)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            """
            CREATE TABLE IF NOT EXISTS User (
                UserID INT AUTO_INCREMENT PRIMARY KEY,
                FullName VARCHAR(100) NOT NULL,
                Email VARCHAR(100) UNIQUE NOT NULL,
                PasswordHash VARCHAR(255) NOT NULL,
                Role ENUM('Donor','Hospital','Admin','SuperAdmin') NOT NULL DEFAULT 'Donor',
                DonorID INT NULL,
                HospitalID INT NULL,
                BloodBankID INT NULL,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (DonorID) REFERENCES Donor(DonorID) ON DELETE SET NULL,
                FOREIGN KEY (HospitalID) REFERENCES Hospital(HospitalID) ON DELETE SET NULL,
                FOREIGN KEY (BloodBankID) REFERENCES BloodBank(BloodBankID) ON DELETE SET NULL,
                INDEX idx_user_email (Email),
                INDEX idx_user_role (Role)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        ]

        cursor = self.connection.cursor()
        for ddl in tables:
            try:
                cursor.execute(ddl)
            except Error as e:
                print(f"[SCHEMA WARNING] {e}")

        # View creation
        try:
            view_sql = """
            CREATE OR REPLACE VIEW AvailableBloodInventory AS
            SELECT 
                bb.BloodBankID,
                bb.BloodBankName,
                bb.Location,
                bu.BloodGroup,
                COUNT(*) AS TotalUnits,
                SUM(bu.Quantity) AS TotalQuantity,
                MIN(bu.ExpirationDate) AS NearestExpiry,
                DATEDIFF(MIN(bu.ExpirationDate), CURDATE()) AS DaysUntilExpiry
            FROM BloodUnit bu
            JOIN BloodBank bb ON bu.BloodBankID = bb.BloodBankID
            WHERE bu.Status = 'Available' 
              AND bu.ExpirationDate > CURDATE()
            GROUP BY bb.BloodBankID, bb.BloodBankName, bb.Location, bu.BloodGroup;
            """
            cursor.execute(view_sql)
        except Exception as e:
            print(f"[SCHEMA] AvailableBloodInventory view notice: {e}")

        # Stored Procedure, Function, Trigger (wrapped in try/except for cloud restricted MySQL instances)
        try:
            cursor.execute("DROP PROCEDURE IF EXISTS RecordBloodDonation")
            proc_sql = """
            CREATE PROCEDURE RecordBloodDonation(
                IN p_DonorID INT,
                IN p_BloodBankID INT,
                IN p_Component VARCHAR(50),
                IN p_Quantity INT
            )
            BEGIN
                DECLARE v_BloodGroup VARCHAR(5);
                DECLARE v_ExpirationDate DATE;
                SELECT BloodGroup INTO v_BloodGroup FROM Donor WHERE DonorID = p_DonorID;  
                SET v_ExpirationDate = DATE_ADD(CURDATE(), INTERVAL 42 DAY);         
                INSERT INTO BloodUnit (DonorID, BloodBankID, BloodGroup, Quantity, CollectionDate, ExpirationDate, Component, Status)
                VALUES (p_DonorID, p_BloodBankID, v_BloodGroup, p_Quantity, CURDATE(), v_ExpirationDate, p_Component, 'Available');
            END
            """
            cursor.execute(proc_sql)
        except Exception as e:
            print(f"[SCHEMA] Stored procedure note (Python fallback enabled): {e}")

        try:
            cursor.execute("DROP FUNCTION IF EXISTS CheckDonorEligibility")
            func_sql = """
            CREATE FUNCTION CheckDonorEligibility(p_DonorID INT)
            RETURNS VARCHAR(100)
            DETERMINISTIC
            READS SQL DATA
            BEGIN
                DECLARE v_LastDonation DATE;
                DECLARE v_DaysGap INT;
                SELECT LastDonationDate INTO v_LastDonation FROM Donor WHERE DonorID = p_DonorID;
                IF v_LastDonation IS NULL THEN
                    RETURN 'ELIGIBLE - First time donor';
                END IF;
                SET v_DaysGap = DATEDIFF(CURDATE(), v_LastDonation);
                IF v_DaysGap >= 56 THEN
                    RETURN 'ELIGIBLE';
                ELSE
                    RETURN CONCAT('NOT ELIGIBLE - Wait ', 56 - v_DaysGap, ' more days');
                END IF;
            END
            """
            cursor.execute(func_sql)
        except Exception as e:
            print(f"[SCHEMA] Stored function note (Python fallback enabled): {e}")

        try:
            cursor.execute("DROP TRIGGER IF EXISTS UpdateDonorStats")
            trig_sql = """
            CREATE TRIGGER UpdateDonorStats
            AFTER INSERT ON BloodUnit
            FOR EACH ROW
            BEGIN
                UPDATE Donor 
                SET LastDonationDate = NEW.CollectionDate,
                    TotalDonations = TotalDonations + 1
                WHERE DonorID = NEW.DonorID;
            END
            """
            cursor.execute(trig_sql)
        except Exception as e:
            print(f"[SCHEMA] Trigger note (Python fallback enabled): {e}")

        self.connection.commit()
        cursor.close()

        # Seed initial data if empty
        self.seed_initial_data()
        return True

    def seed_initial_data(self) -> None:
        """Seed initial lookup records and demo users if User table is empty"""
        if not self.ensure_connection():
            return

        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("SELECT COUNT(*) as count FROM User")
            user_count = cursor.fetchone().get('count', 0)
            if user_count > 0:
                cursor.close()
                return

            print("[SEED] Seeding initial dataset and demo users...")

            # Hospitals
            cursor.execute("""
            INSERT IGNORE INTO Hospital (HospitalID, HospitalName, Location, ContactNo, Email) VALUES
            (1, 'City Care Hospital', 'Downtown', '9876543210', 'info@citycare.org'),
            (2, 'Metro Medical Center', 'Uptown', '9876543211', 'contact@metromedical.org'),
            (3, 'Regional Health Institute', 'Midtown', '9876543212', 'help@regionalhealth.org');
            """)

            # Blood Banks
            cursor.execute("""
            INSERT IGNORE INTO BloodBank (BloodBankID, BloodBankName, Location, ContactNo, Capacity) VALUES
            (1, 'Red Cross Blood Center', 'Downtown', '9876543220', 1500),
            (2, 'Lifeline Blood Bank', 'Uptown', '9876543221', 1200),
            (3, 'National Blood Repository', 'Midtown', '9876543222', 2000),
            (4, 'Rising Sun Blood Bank', 'Westside', '9876543223', 1000);
            """)

            # Donors
            cursor.execute("""
            INSERT IGNORE INTO Donor (DonorID, DonorName, Age, Gender, BloodGroup, ContactNo, Email, Address, LastDonationDate, TotalDonations, IsActive) VALUES
            (1, 'Alice Johnson', 28, 'F', 'A+', '9876500001', 'alice@example.com', '123 Main St', '2026-01-15', 7, TRUE),
            (2, 'Bob Smith', 35, 'M', 'O+', '9876500002', 'bob@example.com', '456 Oak Ave', '2026-01-20', 9, TRUE),
            (3, 'David Brown', 31, 'M', 'AB+', '9876500003', 'david@example.com', '321 Elm St', '2026-02-01', 7, TRUE),
            (4, 'Emma Davis', 26, 'F', 'O-', '9876500004', 'emma@example.com', '654 Maple Dr', '2026-02-10', 3, TRUE),
            (5, 'Akshat Sharma', 22, 'M', 'B+', '9876500005', 'akshat@example.com', '789 Pine Rd', '2026-01-10', 4, TRUE);
            """)

            # Blood Units
            cursor.execute("""
            INSERT IGNORE INTO BloodUnit (UnitID, DonorID, BloodBankID, BloodGroup, Quantity, CollectionDate, ExpirationDate, Status, Component) VALUES
            (1, 1, 1, 'A+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 35 DAY), 'Available', 'Whole Blood'),
            (2, 1, 1, 'A+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 35 DAY), 'Available', 'RBC'),
            (3, 2, 1, 'O+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 30 DAY), 'Available', 'Whole Blood'),
            (4, 2, 2, 'O+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 40 DAY), 'Available', 'Plasma'),
            (5, 3, 2, 'AB+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 25 DAY), 'Available', 'Platelets'),
            (6, 4, 3, 'O-', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 42 DAY), 'Available', 'Whole Blood'),
            (7, 5, 3, 'B+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 38 DAY), 'Available', 'Whole Blood'),
            (8, 5, 4, 'B+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 32 DAY), 'Available', 'RBC');
            """)

            # Patients
            cursor.execute("""
            INSERT IGNORE INTO Patient (PatientID, PatientName, Age, Gender, BloodGroupRequired, HospitalID, ContactNo, MedicalCondition) VALUES
            (1, 'John Doe', 45, 'M', 'A+', 1, '9123450001', 'Surgery Required'),
            (2, 'Jane Smith', 32, 'F', 'O+', 1, '9123450002', 'Accident Victim'),
            (3, 'Robert Taylor', 55, 'M', 'AB+', 2, '9123450003', 'Cancer Treatment'),
            (4, 'Priya Patel', 29, 'F', 'B+', 3, '9123450004', 'Emergency Anemia');
            """)

            # Requests
            cursor.execute("""
            INSERT IGNORE INTO Request (RequestID, PatientID, BloodBankID, RequiredUnits, Status, RequestDate) VALUES
            (1, 1, 1, 2, 'Pending', NOW()),
            (2, 2, 2, 1, 'Fulfilled', NOW()),
            (3, 3, 3, 2, 'Pending', NOW()),
            (4, 4, 3, 1, 'Pending', NOW());
            """)

            # Seed demo users (passwords: Admin@123, SuperAdmin@123, Donor@123, Hospital@123)
            cursor.execute("""
            INSERT IGNORE INTO User (UserID, FullName, Email, PasswordHash, Role, DonorID, HospitalID, BloodBankID) VALUES
            (1, 'System Administrator', 'admin@bloodbank.org', '$2b$12$5Cb76lEVjXiG6naVUbsqAepaP65XIfubDRymX0qiRaPHRoMIDL0fe', 'Admin', NULL, NULL, 1),
            (2, 'Global Super Admin', 'superadmin@bloodbank.org', '$2b$12$AVBrJUt1xxpnIl76dNkcdOWDB/09ztjr6EQ15UH75i30h4KlkiGv6', 'SuperAdmin', NULL, NULL, NULL),
            (3, 'Alice Johnson (Donor)', 'alice@example.com', '$2b$12$UD7KL5M9O1VIyNObltbBkOuFlYBGspnsSW2w1/4czbYQqQa0lZQ/q', 'Donor', 1, NULL, NULL),
            (4, 'City Care Hospital Staff', 'hospital@citycare.org', '$2b$12$/Dka.TQM54K1jyq0tUQDveXoKezM7v9FXbOvjLuR83qPNWo5An0d2', 'Hospital', NULL, 1, NULL);
            """)

            self.connection.commit()
            print("[SEED] Successfully seeded initial dataset and demo users.")
        except Exception as e:
            print(f"[SEED ERROR] Error seeding initial dataset: {e}")
            if self.connection:
                self.connection.rollback()
        finally:
            cursor.close()

    # ==================== DONOR OPERATIONS ====================

    def add_donor(self, name: str, age: int, gender: str, blood_group: str,
                  contact: str, email: str = None, address: str = None) -> Optional[int]:
        """Add a new donor"""
        if not self.ensure_connection():
            return None

        query = """
        INSERT INTO Donor (DonorName, Age, Gender, BloodGroup, ContactNo, Email, Address)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING DonorID
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(self._adapt_query(query), (name, age, gender, blood_group, contact, email, address))
            self.connection.commit()
            return cursor.fetchone()[0]
        except Error as e:
            print(f"Error adding donor: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def get_all_donors(self) -> List[Dict]:
        """Get all active donors"""
        query = "SELECT * FROM Donor WHERE IsActive = TRUE ORDER BY DonorID DESC"
        return self.fetch_query(query)

    def get_donor_by_id(self, donor_id: int) -> Optional[Dict]:
        """Get donor details by ID"""
        query = "SELECT * FROM Donor WHERE DonorID = %s"
        results = self.fetch_query(query, (donor_id,))
        return results[0] if results else None

    def check_donor_eligibility(self, donor_id: int) -> str:
        """Check if donor is eligible to donate (stored function with Python fallback)"""
        # Try stored function first
        try:
            query = "SELECT CheckDonorEligibility(%s) AS eligibility"
            results = self.fetch_query(query, (donor_id,))
            if results and results[0].get('eligibility'):
                return str(results[0]['eligibility'])
        except Exception:
            pass

        # Python fallback calculation
        donor = self.get_donor_by_id(donor_id)
        if not donor:
            return "Donor not found"
        last_donation = donor.get('LastDonationDate')
        if not last_donation:
            return "ELIGIBLE - First time donor"
        try:
            if isinstance(last_donation, str):
                last_date = datetime.strptime(last_donation, "%Y-%m-%d").date()
            elif isinstance(last_donation, datetime):
                last_date = last_donation.date()
            elif isinstance(last_donation, date):
                last_date = last_donation
            else:
                last_date = date.today()
            days_gap = (date.today() - last_date).days
            if days_gap >= 56:
                return "ELIGIBLE"
            return f"NOT ELIGIBLE - Wait {56 - days_gap} more days"
        except Exception as e:
            print(f"Fallback eligibility error: {e}")
            return "ELIGIBLE"

    def update_donor(self, donor_id: int, **kwargs) -> bool:
        """Update donor information"""
        allowed_fields = ['DonorName', 'Age', 'Gender', 'ContactNo', 'Email', 'Address', 'IsActive']
        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = %s")
                values.append(value)

        if not updates:
            return False

        values.append(donor_id)
        query = f"UPDATE Donor SET {', '.join(updates)} WHERE DonorID = %s"
        return self.execute_query(query, tuple(values))

    # ==================== BLOOD BANK OPERATIONS ====================

    def add_blood_bank(self, name: str, location: str, contact: str, capacity: int = 1000) -> Optional[int]:
        """Add a new blood bank"""
        if not self.ensure_connection():
            return None

        query = """
        INSERT INTO BloodBank (BloodBankName, Location, ContactNo, Capacity)
        VALUES (%s, %s, %s, %s)
        RETURNING BloodBankID
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(self._adapt_query(query), (name, location, contact, capacity))
            self.connection.commit()
            return cursor.fetchone()[0]
        except Error as e:
            print(f"Error adding blood bank: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def get_all_blood_banks(self) -> List[Dict]:
        """Get all blood banks"""
        query = "SELECT * FROM BloodBank ORDER BY BloodBankID"
        return self.fetch_query(query)

    def get_blood_bank_by_id(self, blood_bank_id: int) -> Optional[Dict]:
        """Get blood bank details by ID"""
        query = "SELECT * FROM BloodBank WHERE BloodBankID = %s"
        results = self.fetch_query(query, (blood_bank_id,))
        return results[0] if results else None

    def get_available_inventory(self) -> List[Dict]:
        """Get available blood inventory from view with direct query fallback"""
        try:
            query = "SELECT * FROM AvailableBloodInventory"
            results = self.fetch_query(query)
            if results is not None and len(results) > 0:
                return results
        except Exception:
            pass

        # Fallback direct query if view is missing
        fallback_query = """
        SELECT 
            bb.BloodBankID,
            bb.BloodBankName,
            bb.Location,
            bu.BloodGroup,
            COUNT(*) AS TotalUnits,
            SUM(bu.Quantity) AS TotalQuantity,
            MIN(bu.ExpirationDate) AS NearestExpiry,
            DATEDIFF(MIN(bu.ExpirationDate), CURDATE()) AS DaysUntilExpiry
        FROM BloodUnit bu
        JOIN BloodBank bb ON bu.BloodBankID = bb.BloodBankID
        WHERE bu.Status = 'Available' 
          AND bu.ExpirationDate > CURDATE()
        GROUP BY bb.BloodBankID, bb.BloodBankName, bb.Location, bu.BloodGroup
        ORDER BY bu.BloodGroup, DaysUntilExpiry
        """
        return self.fetch_query(fallback_query)

    def get_inventory_by_blood_bank(self, blood_bank_id: int) -> List[Dict]:
        """Get inventory for specific blood bank"""
        try:
            query = "SELECT * FROM AvailableBloodInventory WHERE BloodBankID = %s"
            results = self.fetch_query(query, (blood_bank_id,))
            if results is not None:
                return results
        except Exception:
            pass

        fallback_query = """
        SELECT 
            bb.BloodBankID,
            bb.BloodBankName,
            bb.Location,
            bu.BloodGroup,
            COUNT(*) AS TotalUnits,
            SUM(bu.Quantity) AS TotalQuantity,
            MIN(bu.ExpirationDate) AS NearestExpiry,
            DATEDIFF(MIN(bu.ExpirationDate), CURDATE()) AS DaysUntilExpiry
        FROM BloodUnit bu
        JOIN BloodBank bb ON bu.BloodBankID = bb.BloodBankID
        WHERE bu.Status = 'Available' 
          AND bu.ExpirationDate > CURDATE()
          AND bb.BloodBankID = %s
        GROUP BY bb.BloodBankID, bb.BloodBankName, bb.Location, bu.BloodGroup
        """
        return self.fetch_query(fallback_query, (blood_bank_id,))

    # ==================== BLOOD DONATION OPERATIONS ====================

    def record_donation(self, donor_id: int, blood_bank_id: int,
                        component: str = 'Whole Blood', quantity: int = 1) -> bool:
        """Record a blood donation using stored procedure with direct SQL fallback"""
        if not self.ensure_connection():
            return False

        # Attempt stored procedure first
        try:
            cursor = self.connection.cursor()
            cursor.callproc('RecordBloodDonation', (donor_id, blood_bank_id, component, quantity))
            for _ in cursor.stored_results():
                pass
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"[DONATION] Stored procedure unavailable ({e}), using direct SQL insert.")
            if self.connection:
                self.connection.rollback()

        # Fallback to direct SQL
        try:
            donor = self.get_donor_by_id(donor_id)
            if not donor:
                return False
            blood_group = donor.get('BloodGroup')

            cursor = self.connection.cursor()
            insert_query = """
            INSERT INTO BloodUnit (DonorID, BloodBankID, BloodGroup, Quantity, CollectionDate, ExpirationDate, Component, Status)
            VALUES (%s, %s, %s, %s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 42 DAY), %s, 'Available')
            """
            cursor.execute(self._adapt_query(insert_query), (donor_id, blood_bank_id, blood_group, quantity, component))

            # Update donor stats directly
            update_query = """
            UPDATE Donor 
            SET LastDonationDate = CURDATE(), TotalDonations = TotalDonations + 1
            WHERE DonorID = %s
            """
            cursor.execute(self._adapt_query(update_query), (donor_id,))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e2:
            print(f"Fallback donation record error: {e2}")
            if self.connection:
                self.connection.rollback()
            return False

    def get_blood_units(self, status: str = None, blood_group: str = None) -> List[Dict]:
        """Get blood units with optional filters"""
        query = "SELECT * FROM BloodUnit WHERE 1=1"
        params: List = []

        if status:
            query += " AND Status = %s"
            params.append(status)

        if blood_group:
            query += " AND BloodGroup = %s"
            params.append(blood_group)

        query += " ORDER BY ExpirationDate"
        return self.fetch_query(query, tuple(params) if params else None)

    # ==================== HOSPITAL OPERATIONS ====================

    def add_hospital(self, name: str, location: str, contact: str, email: str = None) -> Optional[int]:
        """Add a new hospital"""
        if not self.ensure_connection():
            return None

        query = """
        INSERT INTO Hospital (HospitalName, Location, ContactNo, Email)
        VALUES (%s, %s, %s, %s)
        RETURNING HospitalID
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(self._adapt_query(query), (name, location, contact, email))
            self.connection.commit()
            return cursor.fetchone()[0]
        except Error as e:
            print(f"Error adding hospital: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def get_all_hospitals(self) -> List[Dict]:
        """Get all hospitals"""
        query = "SELECT * FROM Hospital ORDER BY HospitalID"
        return self.fetch_query(query)

    def get_hospital_by_id(self, hospital_id: int) -> Optional[Dict]:
        """Get hospital details by ID"""
        query = "SELECT * FROM Hospital WHERE HospitalID = %s"
        results = self.fetch_query(query, (hospital_id,))
        return results[0] if results else None

    # ==================== PATIENT OPERATIONS ====================

    def add_patient(self, name: str, age: int, gender: str, blood_group: str,
                    hospital_id: int, contact: str, condition: str = None) -> Optional[int]:
        """Add a new patient"""
        if not self.ensure_connection():
            return None

        query = """
        INSERT INTO Patient (PatientName, Age, Gender, BloodGroupRequired,
                           HospitalID, ContactNo, MedicalCondition)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING PatientID
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(self._adapt_query(query), (name, age, gender, blood_group, hospital_id, contact, condition))
            self.connection.commit()
            return cursor.fetchone()[0]
        except Error as e:
            print(f"Error adding patient: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def get_all_patients(self) -> List[Dict]:
        """Get all active patients"""
        if self.has_column('Patient', 'IsActive'):
            query = """
            SELECT p.*, h.HospitalName 
            FROM Patient p
            JOIN Hospital h ON p.HospitalID = h.HospitalID
            WHERE p.IsActive = TRUE
            ORDER BY p.PatientID DESC
            """
            return self.fetch_query(query)

        query = """
        SELECT p.*, h.HospitalName 
        FROM Patient p
        JOIN Hospital h ON p.HospitalID = h.HospitalID
        ORDER BY p.PatientID DESC
        """
        return self.fetch_query(query)

    def get_patient_by_id(self, patient_id: int) -> Optional[Dict]:
        """Get patient details by ID"""
        query = "SELECT * FROM Patient WHERE PatientID = %s"
        results = self.fetch_query(query, (patient_id,))
        return results[0] if results else None

    def update_patient(self, patient_id: int, **kwargs) -> bool:
        """Update patient information"""
        allowed_fields = ['PatientName', 'Age', 'Gender', 'BloodGroupRequired', 'HospitalID', 'ContactNo', 'MedicalCondition', 'IsActive']
        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = %s")
                values.append(value)

        if not updates:
            return False

        values.append(patient_id)
        query = f"UPDATE Patient SET {', '.join(updates)} WHERE PatientID = %s"
        return self.execute_query(query, tuple(values))

    # ==================== REQUEST OPERATIONS ====================

    def create_request(self, patient_id: int, blood_bank_id: int, required_units: int = 1) -> Optional[int]:
        """Create a blood request"""
        if not self.ensure_connection():
            return None

        query = """
        INSERT INTO Request (PatientID, BloodBankID, RequiredUnits)
        VALUES (%s, %s, %s)
        RETURNING RequestID
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(self._adapt_query(query), (patient_id, blood_bank_id, required_units))
            self.connection.commit()
            return cursor.fetchone()[0]
        except Error as e:
            print(f"Error creating request: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def get_all_requests(self) -> List[Dict]:
        """Get all requests with patient, hospital, and blood bank details"""
        query = """
        SELECT r.*, p.PatientName, p.BloodGroupRequired, p.ContactNo AS PatientContact,
               bb.BloodBankName, bb.Location AS BloodBankLocation,
               h.HospitalName, h.Location AS HospitalLocation, h.ContactNo AS HospitalContact
        FROM Request r
        JOIN Patient p ON r.PatientID = p.PatientID
        JOIN BloodBank bb ON r.BloodBankID = bb.BloodBankID
        JOIN Hospital h ON p.HospitalID = h.HospitalID
        ORDER BY r.RequestDate DESC
        """
        return self.fetch_query(query)

    def update_request_status(self, request_id: int, status: str) -> bool:
        """Update request status"""
        query = """
        UPDATE Request 
        SET Status = %s, FulfilledDate = CASE WHEN %s = 'Fulfilled' THEN NOW() ELSE NULL END
        WHERE RequestID = %s
        """
        return self.execute_query(query, (status, status, request_id))

    def update_request(self, request_id: int, patient_id: int = None, blood_bank_id: int = None, required_units: int = None) -> bool:
        """Update request fields"""
        updates = []
        values = []

        if patient_id is not None:
            updates.append("PatientID = %s")
            values.append(patient_id)
        if blood_bank_id is not None:
            updates.append("BloodBankID = %s")
            values.append(blood_bank_id)
        if required_units is not None:
            updates.append("RequiredUnits = %s")
            values.append(required_units)

        if not updates:
            return False

        values.append(request_id)
        query = f"UPDATE Request SET {', '.join(updates)} WHERE RequestID = %s"
        return self.execute_query(query, tuple(values))

    def delete_request(self, request_id: int) -> bool:
        """Delete a request record"""
        query = "DELETE FROM Request WHERE RequestID = %s"
        return self.execute_query(query, (request_id,))

    # ==================== ALLOCATION OPERATIONS ====================

    def allocate_blood_unit(self, request_id: int, unit_id: int) -> Optional[int]:
        """Allocate a blood unit to a request"""
        if not self.ensure_connection():
            return None

        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE BloodUnit SET Status = 'Reserved' WHERE UnitID = %s", (unit_id,))
            if cursor.rowcount == 0:
                self.connection.rollback()
                print(f"No available blood unit found for UnitID {unit_id}")
                return None

            cursor.execute(
                """
                INSERT INTO Allocation (RequestID, UnitID)
                VALUES (%s, %s)
                RETURNING AllocationID
                """,
                (request_id, unit_id)
            )
            self.connection.commit()
            return cursor.fetchone()[0]
        except Error as e:
            print(f"Error allocating blood unit: {e}")
            if self.connection:
                self.connection.rollback()
            return None
        finally:
            if cursor:
                cursor.close()

    def get_allocations(self) -> List[Dict]:
        """Get all allocations"""
        query = """
        SELECT a.*, r.RequiredUnits, bu.BloodGroup, bu.Component,
               p.PatientName, bb.BloodBankName
        FROM Allocation a
        JOIN Request r ON a.RequestID = r.RequestID
        JOIN BloodUnit bu ON a.UnitID = bu.UnitID
        JOIN Patient p ON r.PatientID = p.PatientID
        JOIN BloodBank bb ON bu.BloodBankID = bb.BloodBankID
        ORDER BY a.AllocationDate DESC
        """
        return self.fetch_query(query)

    # ==================== ANALYTICS & REPORTS ====================

    def get_donor_statistics(self) -> Dict:
        """Get donor statistics"""
        stats: Dict[str, object] = {}

        # Total donors
        query = "SELECT COUNT(*) as total FROM Donor WHERE IsActive = TRUE"
        result = self.fetch_query(query)
        stats['total_donors'] = result[0]['total'] if result else 0

        # Donors by blood group
        query = """
        SELECT BloodGroup, COUNT(*) as count 
        FROM Donor WHERE IsActive = TRUE
        GROUP BY BloodGroup
        """
        stats['by_blood_group'] = self.fetch_query(query)

        # Total donations
        query = "SELECT SUM(TotalDonations) as total FROM Donor WHERE IsActive = TRUE"
        result = self.fetch_query(query)
        stats['total_donations'] = result[0]['total'] if result and result[0]['total'] else 0

        return stats

    def get_blood_bank_statistics(self) -> Dict:
        """Get blood bank statistics"""
        stats: Dict[str, object] = {}

        # Total blood banks
        query = "SELECT COUNT(*) as total FROM BloodBank"
        result = self.fetch_query(query)
        stats['total_banks'] = result[0]['total'] if result else 0

        # Total available units
        query = "SELECT COUNT(*) as total FROM BloodUnit WHERE Status = 'Available'"
        result = self.fetch_query(query)
        stats['available_units'] = result[0]['total'] if result else 0

        # Units expiring soon (within 7 days)
        query = """
        SELECT COUNT(*) as total FROM BloodUnit 
        WHERE Status = 'Available' 
        AND ExpirationDate BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
        """
        result = self.fetch_query(query)
        stats['expiring_soon'] = result[0]['total'] if result else 0

        return stats

    def get_request_statistics(self) -> Dict:
        """Get request statistics"""
        stats: Dict[str, object] = {}

        # Requests by status
        query = """
        SELECT Status, COUNT(*) as count 
        FROM Request 
        GROUP BY Status
        """
        stats['by_status'] = self.fetch_query(query)

        # Pending requests
        query = "SELECT COUNT(*) as total FROM Request WHERE Status = 'Pending'"
        result = self.fetch_query(query)
        stats['pending_requests'] = result[0]['total'] if result else 0

        return stats

    def get_donor_by_email(self, email: str) -> Optional[Dict]:
        """Fetch donor by email"""
        query = "SELECT * FROM Donor WHERE Email = %s LIMIT 1"
        result = self.fetch_query(query, (email,))
        return result[0] if result else None

    def get_donor_by_contact(self, contact: str) -> Optional[Dict]:
        """Fetch donor by contact number"""
        query = "SELECT * FROM Donor WHERE ContactNo = %s LIMIT 1"
        result = self.fetch_query(query, (contact,))
        return result[0] if result else None

    # ==================== AUTHENTICATION & USER MANAGEMENT ====================

    def create_user(self, full_name: str, email: str, password_hash: str, role: str = 'Donor',
                    donor_id: Optional[int] = None, hospital_id: Optional[int] = None, blood_bank_id: Optional[int] = None) -> Optional[int]:
        """Create a new user for authentication"""
        if not self.ensure_connection():
            return None

        query = """
        INSERT INTO User (FullName, Email, PasswordHash, Role, DonorID, HospitalID, BloodBankID)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING UserID
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(self._adapt_query(query), (full_name, email, password_hash, role, donor_id, hospital_id, blood_bank_id))
            self.connection.commit()
            return cursor.fetchone()[0]
        except Error as e:
            print(f"Error creating user: {e}")
            if self.connection:
                self.connection.rollback()
            return None
        finally:
            if cursor:
                cursor.close()

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Fetch user by email"""
        query = "SELECT * FROM User WHERE Email = %s LIMIT 1"
        result = self.fetch_query(query, (email,))
        return result[0] if result else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Fetch user by ID"""
        query = "SELECT * FROM User WHERE UserID = %s LIMIT 1"
        result = self.fetch_query(query, (user_id,))
        return result[0] if result else None


if __name__ == "__main__":
    db = BloodBankDB()
    print("Testing connection with config:", db.get_connection_info())
    if db.connect():
        print("Connected successfully!")
        db.init_schema()
        db.disconnect()
    else:
        print("Could not connect with current settings.")
