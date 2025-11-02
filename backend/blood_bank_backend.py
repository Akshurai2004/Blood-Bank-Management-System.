import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple


class BloodBankDB:
    def __init__(self, host='localhost', user='root', password='yourpassword', database='BloodBankDB'):
        """Initialize database connection"""
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self) -> bool:
        """Establish database connection"""
        if self.connection and self.connection.is_connected():
            return True

        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if self.connection.is_connected():
                print("Successfully connected to database")
                return True
        except Error as e:
            print(f"Error connecting to database: {e}")
        return False

    def update_patient(self, patient_id: int, **kwargs) -> bool:
        """Update patient information (soft delete if IsActive is set to False)"""
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
    
    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Database connection closed")
        self.connection = None

    def ensure_connection(self) -> bool:
        """Reconnect automatically if the connection drops"""
        if not self.connection or not self.connection.is_connected():
            return self.connect()
        return True

    def execute_query(self, query: str, params: tuple = None) -> bool:
        """Execute INSERT, UPDATE, DELETE queries"""
        if not self.ensure_connection():
            return False

        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
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

    def has_column(self, table: str, column: str) -> bool:
        """Check INFORMATION_SCHEMA to see if a table has a given column.

        This is used to gracefully handle databases created from older
        schemas that may not have the `IsActive` column (or other optional
        columns) so the code can fallback safely.
        """
        try:
            query = """
            SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
            """
            result = self.fetch_query(query, (self.database, table, column))
            if not result:
                return False
            return int(result[0].get('cnt', 0)) > 0
        except Exception as e:
            print(f"Error checking column existence: {e}")
            return False

    def fetch_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute SELECT queries and return results as list of dictionaries"""
        if not self.ensure_connection():
            return []

        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching data: {e}")
            return []
        finally:
            if cursor:
                cursor.close()

    # DONOR OPERATIONS
    def add_donor(self, name: str, age: int, gender: str, blood_group: str,
                  contact: str, email: str = None, address: str = None) -> Optional[int]:
        """Add a new donor"""
        if not self.ensure_connection():
            return None

        query = """
        INSERT INTO Donor (DonorName, Age, Gender, BloodGroup, ContactNo, Email, Address)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (name, age, gender, blood_group, contact, email, address))
            self.connection.commit()
            return cursor.lastrowid
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
        """Check if donor is eligible to donate"""
        query = "SELECT CheckDonorEligibility(%s) AS eligibility"
        results = self.fetch_query(query, (donor_id,))
        return results[0]['eligibility'] if results else "Error checking eligibility"

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

    # BLOOD BANK OPERATIONS
    def add_blood_bank(self, name: str, location: str, contact: str, capacity: int = 1000) -> Optional[int]:
        """Add a new blood bank"""
        if not self.ensure_connection():
            return None

        query = """
        INSERT INTO BloodBank (BloodBankName, Location, ContactNo, Capacity)
        VALUES (%s, %s, %s, %s)
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (name, location, contact, capacity))
            self.connection.commit()
            return cursor.lastrowid
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
        """Get available blood inventory from view"""
        query = "SELECT * FROM AvailableBloodInventory"
        return self.fetch_query(query)

    def get_inventory_by_blood_bank(self, blood_bank_id: int) -> List[Dict]:
        """Get inventory for specific blood bank"""
        query = """
        SELECT * FROM AvailableBloodInventory 
        WHERE BloodBankID = %s
        """
        return self.fetch_query(query, (blood_bank_id,))

    # BLOOD DONATION OPERATIONS
    def record_donation(self, donor_id: int, blood_bank_id: int,
                        component: str = 'Whole Blood', quantity: int = 1) -> bool:
        """Record a blood donation using stored procedure"""
        if not self.ensure_connection():
            return False

        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.callproc('RecordBloodDonation', (donor_id, blood_bank_id, component, quantity))
            for _ in cursor.stored_results():
                pass
            self.connection.commit()
            return True
        except Error as e:
            print(f"Error recording donation: {e}")
            if self.connection:
                self.connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()

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

    # HOSPITAL OPERATIONS
    def add_hospital(self, name: str, location: str, contact: str, email: str = None) -> Optional[int]:
        """Add a new hospital"""
        if not self.ensure_connection():
            return None

        query = """
        INSERT INTO Hospital (HospitalName, Location, ContactNo, Email)
        VALUES (%s, %s, %s, %s)
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (name, location, contact, email))
            self.connection.commit()
            return cursor.lastrowid
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

    # PATIENT OPERATIONS
    def add_patient(self, name: str, age: int, gender: str, blood_group: str,
                    hospital_id: int, contact: str, condition: str = None) -> Optional[int]:
        """Add a new patient"""
        if not self.ensure_connection():
            return None

        query = """
        INSERT INTO Patient (PatientName, Age, Gender, BloodGroupRequired,
                           HospitalID, ContactNo, MedicalCondition)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (name, age, gender, blood_group, hospital_id, contact, condition))
            self.connection.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"Error adding patient: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def get_all_patients(self) -> List[Dict]:
        """Get all patients.

        If the `Patient` table contains an `IsActive` column (soft-delete
        flag), only return active patients. If the column does not exist
        (older schema), fall back to returning all patients.
        """
        if self.has_column('Patient', 'IsActive'):
            query = """
            SELECT p.*, h.HospitalName 
            FROM Patient p
            JOIN Hospital h ON p.HospitalID = h.HospitalID
            WHERE p.IsActive = TRUE
            ORDER BY p.PatientID DESC
            """
            return self.fetch_query(query)

        # Fallback for older schemas without IsActive
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

    # REQUEST OPERATIONS
    def create_request(self, patient_id: int, blood_bank_id: int, required_units: int = 1) -> Optional[int]:
        """Create a blood request"""
        if not self.ensure_connection():
            return None

        query = """
        INSERT INTO Request (PatientID, BloodBankID, RequiredUnits)
        VALUES (%s, %s, %s)
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (patient_id, blood_bank_id, required_units))
            self.connection.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"Error creating request: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def get_all_requests(self) -> List[Dict]:
        """Get all requests with details"""
        query = """
        SELECT r.*, p.PatientName, p.BloodGroupRequired, 
               bb.BloodBankName, h.HospitalName
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
        SET Status = %s, FulfilledDate = IF(%s = 'Fulfilled', NOW(), NULL)
        WHERE RequestID = %s
        """
        return self.execute_query(query, (status, status, request_id))

    def update_request(self, request_id: int, patient_id: int = None, blood_bank_id: int = None, required_units: int = None) -> bool:
        """Update request fields. Only provided fields will be updated."""
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
        """Delete a request record (hard delete). Returns True on success."""
        query = "DELETE FROM Request WHERE RequestID = %s"
        return self.execute_query(query, (request_id,))

    # ALLOCATION OPERATIONS
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
                """,
                (request_id, unit_id)
            )
            self.connection.commit()
            return cursor.lastrowid
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

    # ANALYTICS & REPORTS
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


# Example usage
if __name__ == "__main__":
    # Initialize database connection
    # Update the password to your MySQL root password
    db = BloodBankDB(host='localhost', user='root', password='root', database='BloodBankDB')

    if db.connect():
        # Example: Add a donor
        donor_id = db.add_donor(
            name="John Doe",
            age=25,
            gender="M",
            blood_group="O+",
            contact="9876543210",
            email="john@example.com",
            address="123 Main St"
        )
        print(f"Added donor with ID: {donor_id}")

        # Example: Check eligibility
        if donor_id:
            eligibility = db.check_donor_eligibility(donor_id)
            print(f"Donor eligibility: {eligibility}")

        # Example: Get all donors
        donors = db.get_all_donors()
        print(f"Total donors: {len(donors)}")

        # Example: Get available inventory
        inventory = db.get_available_inventory()
        print(f"Available inventory items: {len(inventory)}")

        # Example: Get statistics
        stats = db.get_donor_statistics()
        print(f"Donor statistics: {stats}")

        db.disconnect()
