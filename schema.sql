-- ============================================
-- SMART BLOOD MATCHING ENGINE - COMPLETE OFFICIAL SCHEMA
-- Based on Blood_Bank_Schema.docx
-- Day 1: Database Foundation with Intelligence
-- ============================================

-- Create Database
DROP DATABASE IF EXISTS SmartBloodDB;
CREATE DATABASE SmartBloodDB;
USE SmartBloodDB;

-- ============================================
-- CORE TABLES (FROM OFFICIAL SCHEMA)
-- ============================================

-- 1. Hospital Table
CREATE TABLE Hospital (
    HospitalName VARCHAR(100) PRIMARY KEY,
    Location VARCHAR(100) NOT NULL,
    ContactNo VARCHAR(15) NOT NULL,
    Email VARCHAR(100),
    INDEX idx_location (Location)
) ENGINE=InnoDB;

-- 2. Staff Table
CREATE TABLE Staff (
    StaffID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Role ENUM('Doctor','Nurse','Lab_Technician','Administrator','Coordinator') NOT NULL,
    SkillSet TEXT,
    ContactNo VARCHAR(15) NOT NULL,
    Email VARCHAR(100),
    JoiningDate DATE DEFAULT (CURDATE()),
    IsActive BOOLEAN DEFAULT TRUE,
    INDEX idx_staff_name (Name),
    INDEX idx_role (Role)
) ENGINE=InnoDB;

-- 3. ASSIGNED TO (Staff-Hospital Relationship)
CREATE TABLE AssignedTo (
    StaffID INT NOT NULL,
    HospitalName VARCHAR(100) NOT NULL,
    AssignmentDate DATE DEFAULT (CURDATE()),
    Status ENUM('Active','Transferred','Resigned') DEFAULT 'Active',
    PRIMARY KEY (StaffID, HospitalName),
    FOREIGN KEY (StaffID) REFERENCES Staff(StaffID) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (HospitalName) REFERENCES Hospital(HospitalName) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_hospital (HospitalName),
    INDEX idx_status (Status)
) ENGINE=InnoDB;

-- 4. BloodBank Table
CREATE TABLE BloodBank (
    BloodBankName VARCHAR(100) PRIMARY KEY,
    Location VARCHAR(100) NOT NULL,
    ContactNo VARCHAR(15) NOT NULL,
    EstablishedYear YEAR NOT NULL,
    Email VARCHAR(100),
    LicenseNumber VARCHAR(50) UNIQUE,
    Capacity INT DEFAULT 1000,
    INDEX idx_location (Location)
) ENGINE=InnoDB;

-- 5. Campaign Table
CREATE TABLE Campaign (
    CampID INT AUTO_INCREMENT PRIMARY KEY,
    CampaignName VARCHAR(150) NOT NULL,
    Location VARCHAR(100) NOT NULL,
    Date DATE NOT NULL,
    StartTime TIME,
    EndTime TIME,
    OrganizedBy VARCHAR(100),
    TargetDonors INT DEFAULT 50,
    ActualDonors INT DEFAULT 0,
    BloodBankName VARCHAR(100),
    Status ENUM('Scheduled','Ongoing','Completed','Cancelled') DEFAULT 'Scheduled',
    FOREIGN KEY (BloodBankName) REFERENCES BloodBank(BloodBankName)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_campaign_date (Date),
    INDEX idx_location (Location),
    INDEX idx_status (Status)
) ENGINE=InnoDB;

-- 6. Donor Table
CREATE TABLE Donor (
    DonorName VARCHAR(100) PRIMARY KEY,
    Age INT CHECK (Age >= 18 AND Age <= 65),
    Gender ENUM('M','F','O') NOT NULL,
    BloodGroup VARCHAR(5) NOT NULL,
    ContactNo VARCHAR(15) UNIQUE NOT NULL,
    Email VARCHAR(100),
    Address VARCHAR(255),
    CampID INT,
    LastDonationDate DATE,
    TotalDonations INT DEFAULT 0,
    RegistrationDate DATE DEFAULT (CURDATE()),
    IsActive BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (CampID) REFERENCES Campaign(CampID)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_blood_group (BloodGroup),
    INDEX idx_contact (ContactNo),
    INDEX idx_camp (CampID),
    INDEX idx_last_donation (LastDonationDate)
) ENGINE=InnoDB;

-- 7. REFERS (Donor Referral Relationship)
CREATE TABLE Refers (
    DonorName VARCHAR(100) NOT NULL,
    ReferredDonorName VARCHAR(100) NOT NULL,
    ReferralDate DATE DEFAULT (CURDATE()),
    Status ENUM('Pending','Accepted','Donated','Declined') DEFAULT 'Pending',
    PRIMARY KEY (DonorName, ReferredDonorName),
    FOREIGN KEY (DonorName) REFERENCES Donor(DonorName)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (ReferredDonorName) REFERENCES Donor(DonorName)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_referral_date (ReferralDate),
    INDEX idx_status (Status),
    CHECK (DonorName != ReferredDonorName)
) ENGINE=InnoDB;

-- 8. Transaction Table
CREATE TABLE Transaction (
    TransactionID INT AUTO_INCREMENT PRIMARY KEY,
    DateOfDonation DATETIME DEFAULT CURRENT_TIMESTAMP,
    DonorName VARCHAR(100),
    BloodBankName VARCHAR(100),
    TransactionType ENUM('Donation','Distribution','Transfer') DEFAULT 'Donation',
    Quantity INT DEFAULT 1,
    Notes TEXT,
    FOREIGN KEY (DonorName) REFERENCES Donor(DonorName)
        ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (BloodBankName) REFERENCES BloodBank(BloodBankName)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_date (DateOfDonation),
    INDEX idx_donor (DonorName),
    INDEX idx_bloodbank (BloodBankName),
    INDEX idx_type (TransactionType)
) ENGINE=InnoDB;

-- 9. BloodUnit Table
CREATE TABLE BloodUnit (
    UnitID INT AUTO_INCREMENT PRIMARY KEY,
    DonorName VARCHAR(100),
    BloodBankName VARCHAR(100) NOT NULL,
    BloodGroup VARCHAR(5) NOT NULL,
    Quantity INT DEFAULT 1 CHECK (Quantity > 0),
    CollectionDate DATE NOT NULL,
    ExpirationDate DATE NOT NULL,
    Status ENUM('Available','Reserved','Used','Expired','Quarantine') DEFAULT 'Available',
    Component ENUM('Whole Blood','RBC','Plasma','Platelets','Cryoprecipitate') DEFAULT 'Whole Blood',
    TestStatus ENUM('Pending','Cleared','Rejected') DEFAULT 'Pending',
    StorageLocation VARCHAR(50),
    TransactionID INT,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (DonorName) REFERENCES Donor(DonorName)
        ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (BloodBankName) REFERENCES BloodBank(BloodBankName)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (TransactionID) REFERENCES Transaction(TransactionID)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_blood_group (BloodGroup),
    INDEX idx_status (Status),
    INDEX idx_expiration (ExpirationDate),
    INDEX idx_bloodbank (BloodBankName),
    INDEX idx_collection_date (CollectionDate),
    INDEX idx_donor (DonorName),
    CHECK (ExpirationDate > CollectionDate)
) ENGINE=InnoDB;

-- 10. Patient Table
CREATE TABLE Patient (
    PatientID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Age INT CHECK (Age > 0 AND Age < 150),
    Gender ENUM('M','F','O') NOT NULL,
    Address VARCHAR(255),
    ContactNo VARCHAR(15) NOT NULL,
    BloodGroupRequired VARCHAR(5) NOT NULL,
    HospitalName VARCHAR(100) NOT NULL,
    RegistrationDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    MedicalCondition TEXT,
    EmergencyContact VARCHAR(15),
    FOREIGN KEY (HospitalName) REFERENCES Hospital(HospitalName)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_blood_group (BloodGroupRequired),
    INDEX idx_hospital (HospitalName),
    INDEX idx_name (Name)
) ENGINE=InnoDB;

-- 11. Request Table
CREATE TABLE Request (
    RequestID INT AUTO_INCREMENT PRIMARY KEY,
    PatientName VARCHAR(100),
    RequestDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    Status ENUM('Pending','Processing','Fulfilled','Partially_Fulfilled','Denied','Cancelled') DEFAULT 'Pending',
    BloodBankName VARCHAR(100),
    RequiredUnits INT DEFAULT 1 CHECK (RequiredUnits > 0),
    UrgencyLevel ENUM('Low','Medium','High','Critical') DEFAULT 'Medium',
    Priority INT DEFAULT 0,
    RequestedBy VARCHAR(100),
    ApprovedBy VARCHAR(100),
    Notes TEXT,
    FulfilledDate DATETIME,
    FOREIGN KEY (BloodBankName) REFERENCES BloodBank(BloodBankName)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_status (Status),
    INDEX idx_urgency (UrgencyLevel),
    INDEX idx_date (RequestDate),
    INDEX idx_patient (PatientName),
    INDEX idx_priority (Priority),
    INDEX idx_bloodbank (BloodBankName)
) ENGINE=InnoDB;

-- 12. Allocation Table (Links Request to BloodUnit)
CREATE TABLE Allocation (
    AllocationID INT AUTO_INCREMENT PRIMARY KEY,
    RequestID INT NOT NULL,
    UnitID INT NOT NULL,
    AllocationDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    AllocatedBy VARCHAR(100),
    DeliveryStatus ENUM('Pending','In_Transit','Delivered','Failed') DEFAULT 'Pending',
    DeliveryDate DATETIME,
    ReceivedBy VARCHAR(100),
    Notes TEXT,
    FOREIGN KEY (RequestID) REFERENCES Request(RequestID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (UnitID) REFERENCES BloodUnit(UnitID)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_request (RequestID),
    INDEX idx_unit (UnitID),
    INDEX idx_allocation_date (AllocationDate),
    INDEX idx_delivery_status (DeliveryStatus)
) ENGINE=InnoDB;

-- ============================================
-- ANALYTICS & MONITORING TABLES
-- ============================================

-- 13. QueryPerformanceLog Table (Self-Optimization)
CREATE TABLE QueryPerformanceLog (
    LogID INT AUTO_INCREMENT PRIMARY KEY,
    QueryName VARCHAR(100) NOT NULL,
    ExecutionTime FLOAT NOT NULL,
    RowsAffected INT DEFAULT 0,
    OptimizationLevel ENUM('Poor','Good','Excellent') DEFAULT 'Good',
    IndexesUsed TEXT,
    RunDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    QueryParameters TEXT,
    INDEX idx_query_name (QueryName),
    INDEX idx_run_date (RunDate),
    INDEX idx_execution_time (ExecutionTime)
) ENGINE=InnoDB;

-- 14. BloodInventoryStats Table
CREATE TABLE BloodInventoryStats (
    StatsID INT AUTO_INCREMENT PRIMARY KEY,
    BloodBankName VARCHAR(100) NOT NULL,
    BloodGroup VARCHAR(5) NOT NULL,
    TotalUnits INT DEFAULT 0,
    AvailableUnits INT DEFAULT 0,
    ReservedUnits INT DEFAULT 0,
    ExpiringSoon INT DEFAULT 0,
    UsedUnits INT DEFAULT 0,
    ExpiredUnits INT DEFAULT 0,
    LastUpdated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (BloodBankName) REFERENCES BloodBank(BloodBankName)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_blood_group (BloodGroup),
    INDEX idx_bloodbank (BloodBankName),
    INDEX idx_last_updated (LastUpdated),
    UNIQUE KEY unique_bloodbank_group (BloodBankName, BloodGroup)
) ENGINE=InnoDB;

-- 15. AlertNotification Table
CREATE TABLE AlertNotification (
    AlertID INT AUTO_INCREMENT PRIMARY KEY,
    AlertType ENUM('Low_Stock','Expiring_Soon','Critical_Request','Campaign_Due','System') NOT NULL,
    BloodGroup VARCHAR(5),
    BloodBankName VARCHAR(100),
    HospitalName VARCHAR(100),
    Message TEXT NOT NULL,
    Severity ENUM('Low','Medium','High','Critical') DEFAULT 'Medium',
    IsRead BOOLEAN DEFAULT FALSE,
    ActionRequired BOOLEAN DEFAULT FALSE,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ReadAt TIMESTAMP NULL,
    FOREIGN KEY (BloodBankName) REFERENCES BloodBank(BloodBankName)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (HospitalName) REFERENCES Hospital(HospitalName)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_alert_type (AlertType),
    INDEX idx_severity (Severity),
    INDEX idx_is_read (IsRead),
    INDEX idx_created_at (CreatedAt)
) ENGINE=InnoDB;

-- ============================================
-- VIEWS FOR QUICK ACCESS
-- ============================================

-- View 1: Available Blood Inventory
CREATE VIEW AvailableBloodInventory AS
SELECT 
    bb.BloodBankName,
    bb.Location,
    bu.BloodGroup,
    COUNT(*) AS TotalUnits,
    SUM(bu.Quantity) AS TotalQuantity,
    MIN(bu.ExpirationDate) AS NearestExpiry,
    MAX(bu.ExpirationDate) AS FarthestExpiry,
    AVG(DATEDIFF(bu.ExpirationDate, CURDATE())) AS AvgDaysToExpiry
FROM BloodUnit bu
JOIN BloodBank bb ON bu.BloodBankName = bb.BloodBankName
WHERE bu.Status = 'Available' 
  AND bu.TestStatus = 'Cleared'
  AND bu.ExpirationDate > CURDATE()
GROUP BY bb.BloodBankName, bb.Location, bu.BloodGroup;

-- View 2: Pending Requests
CREATE VIEW PendingRequests AS
SELECT 
    r.RequestID,
    r.PatientName,
    p.BloodGroupRequired,
    p.HospitalName,
    h.Location AS HospitalLocation,
    r.RequiredUnits,
    r.UrgencyLevel,
    r.Priority,
    r.RequestDate,
    r.BloodBankName,
    TIMESTAMPDIFF(HOUR, r.RequestDate, NOW()) AS HoursWaiting
FROM Request r
LEFT JOIN Patient p ON r.PatientName = p.Name
JOIN Hospital h ON p.HospitalName = h.HospitalName
WHERE r.Status = 'Pending'
ORDER BY r.Priority DESC, r.RequestDate ASC;

-- View 3: Blood Expiry Alerts
CREATE VIEW ExpiryAlerts AS
SELECT 
    bb.BloodBankName,
    bb.Location,
    bu.UnitID,
    bu.BloodGroup,
    bu.Component,
    bu.ExpirationDate,
    DATEDIFF(bu.ExpirationDate, CURDATE()) AS DaysUntilExpiry,
    CASE 
        WHEN DATEDIFF(bu.ExpirationDate, CURDATE()) <= 3 THEN 'Critical'
        WHEN DATEDIFF(bu.ExpirationDate, CURDATE()) <= 7 THEN 'High'
        WHEN DATEDIFF(bu.ExpirationDate, CURDATE()) <= 14 THEN 'Medium'
        ELSE 'Low'
    END AS AlertLevel
FROM BloodUnit bu
JOIN BloodBank bb ON bu.BloodBankName = bb.BloodBankName
WHERE bu.Status = 'Available' 
  AND bu.TestStatus = 'Cleared'
  AND bu.ExpirationDate > CURDATE()
  AND DATEDIFF(bu.ExpirationDate, CURDATE()) <= 14
ORDER BY bu.ExpirationDate ASC;

-- View 4: Donor Statistics
CREATE VIEW DonorStatistics AS
SELECT 
    d.DonorName,
    d.BloodGroup,
    d.TotalDonations,
    d.LastDonationDate,
    DATEDIFF(CURDATE(), d.LastDonationDate) AS DaysSinceLastDonation,
    CASE 
        WHEN d.LastDonationDate IS NULL THEN 'Eligible'
        WHEN DATEDIFF(CURDATE(), d.LastDonationDate) >= 56 THEN 'Eligible'
        ELSE 'Not Eligible'
    END AS EligibilityStatus,
    COUNT(DISTINCT r.ReferredDonorName) AS TotalReferrals,
    c.CampaignName AS LastCampaign
FROM Donor d
LEFT JOIN Refers r ON d.DonorName = r.DonorName
LEFT JOIN Campaign c ON d.CampID = c.CampID
GROUP BY d.DonorName, d.BloodGroup, d.TotalDonations, d.LastDonationDate, c.CampaignName;

-- View 5: Hospital Staff Assignment
CREATE VIEW HospitalStaffView AS
SELECT 
    h.HospitalName,
    h.Location AS HospitalLocation,
    s.StaffID,
    s.Name AS StaffName,
    s.Role,
    s.ContactNo,
    a.AssignmentDate,
    a.Status AS AssignmentStatus
FROM Hospital h
JOIN AssignedTo a ON h.HospitalName = a.HospitalName
JOIN Staff s ON a.StaffID = s.StaffID
WHERE a.Status = 'Active'
ORDER BY h.HospitalName, s.Role;

-- View 6: Campaign Performance
CREATE VIEW CampaignPerformance AS
SELECT 
    c.CampID,
    c.CampaignName,
    c.Location,
    c.Date,
    c.TargetDonors,
    c.ActualDonors,
    COUNT(DISTINCT d.DonorName) AS RegisteredDonors,
    COUNT(DISTINCT bu.UnitID) AS UnitsCollected,
    ROUND((c.ActualDonors * 100.0 / NULLIF(c.TargetDonors, 0)), 2) AS AchievementRate,
    c.Status
FROM Campaign c
LEFT JOIN Donor d ON c.CampID = d.CampID
LEFT JOIN BloodUnit bu ON d.DonorName = bu.DonorName 
    AND DATE(bu.CollectionDate) = c.Date
GROUP BY c.CampID, c.CampaignName, c.Location, c.Date, 
         c.TargetDonors, c.ActualDonors, c.Status;

-- ============================================
-- SAMPLE DATA
-- ============================================

-- Insert Hospitals
INSERT INTO Hospital (HospitalName, Location, ContactNo, Email) VALUES
('City Care Hospital', 'Downtown', '1234567890', 'info@citycare.com'),
('Metro Medical Center', 'Uptown', '2345678901', 'contact@metromedical.com'),
('Regional Health Institute', 'Suburbs', '3456789012', 'info@regionalhealth.com'),
('Central General Hospital', 'Midtown', '4567890123', 'admin@centralgeneral.com');

-- Insert Staff
INSERT INTO Staff (Name, Role, SkillSet, ContactNo, Email) VALUES
('Dr. Sarah Williams', 'Doctor', 'Emergency Medicine, Hematology', '5551111111', 'sarah.w@hospital.com'),
('Dr. James Miller', 'Doctor', 'Surgery, Transfusion Medicine', '5552222222', 'james.m@hospital.com'),
('Nurse Emily Davis', 'Nurse', 'ICU, Blood Bank Operations', '5553333333', 'emily.d@hospital.com'),
('John Anderson', 'Lab_Technician', 'Blood Testing, Quality Control', '5554444444', 'john.a@hospital.com'),
('Mary Johnson', 'Coordinator', 'Donation Campaigns, Donor Relations', '5555555555', 'mary.j@hospital.com');

-- Assign Staff to Hospitals
INSERT INTO AssignedTo (StaffID, HospitalName, AssignmentDate) VALUES
(1, 'City Care Hospital', '2024-01-15'),
(2, 'City Care Hospital', '2024-02-01'),
(3, 'Metro Medical Center', '2024-01-20'),
(4, 'Regional Health Institute', '2024-03-01'),
(5, 'Central General Hospital', '2024-01-10');

-- Insert Blood Banks
INSERT INTO BloodBank (BloodBankName, Location, ContactNo, EstablishedYear, Email, LicenseNumber, Capacity) VALUES
('Red Cross Blood Center', 'Downtown', '1112223333', 2005, 'redcross@blood.org', 'RC-2005-001', 2000),
('Community Blood Services', 'Midtown', '2223334444', 2012, 'info@communityblood.org', 'CBS-2012-002', 1500),
('National Blood Repository', 'Uptown', '3334445555', 2000, 'contact@nationalblood.org', 'NBR-2000-003', 3000);

-- Insert Campaigns
INSERT INTO Campaign (CampaignName, Location, Date, StartTime, EndTime, OrganizedBy, TargetDonors, BloodBankName, Status) VALUES
('Save Lives Blood Drive 2025', 'City Center', '2025-09-15', '09:00:00', '17:00:00', 'Red Cross', 100, 'Red Cross Blood Center', 'Completed'),
('Corporate Donation Day', 'Tech Park', '2025-10-01', '10:00:00', '16:00:00', 'Community Blood', 75, 'Community Blood Services', 'Completed'),
('University Health Fair', 'State University', '2025-10-20', '08:00:00', '14:00:00', 'National Repository', 150, 'National Blood Repository', 'Scheduled'),
('Emergency Response Drive', 'Community Hall', '2025-11-05', '09:00:00', '15:00:00', 'Red Cross', 200, 'Red Cross Blood Center', 'Scheduled');

-- Update campaign actual donors
UPDATE Campaign SET ActualDonors = 95 WHERE CampID = 1;
UPDATE Campaign SET ActualDonors = 68 WHERE CampID = 2;

-- Insert Donors
INSERT INTO Donor (DonorName, Age, Gender, BloodGroup, ContactNo, Email, Address, CampID, LastDonationDate, TotalDonations) VALUES
('Alice Johnson', 28, 'F', 'A+', '5551234567', 'alice@email.com', '123 Main St', 1, '2025-09-15', 5),
('Bob Smith', 35, 'M', 'O+', '5552345678', 'bob@email.com', '456 Oak Ave', 1, '2025-09-15', 8),
('Carol White', 42, 'F', 'B+', '5553456789', 'carol@email.com', '789 Pine Rd', 2, '2025-10-01', 3),
('David Brown', 31, 'M', 'AB+', '5554567890', 'david@email.com', '321 Elm St', 2, '2025-10-01', 6),
('Emma Davis', 26, 'F', 'O-', '5555678901', 'emma@email.com', '654 Maple Dr', 1, '2025-09-15', 4),
('Frank Miller', 45, 'M', 'A-', '5556789012', 'frank@email.com', '987 Cedar Ln', 1, '2025-09-15', 12),
('Grace Wilson', 33, 'F', 'B-', '5557890123', 'grace@email.com', '147 Birch Ct', 2, '2025-10-01', 7);

-- Insert Referrals
INSERT INTO Refers (DonorName, ReferredDonorName, ReferralDate, Status) VALUES
('Alice Johnson', 'Emma Davis', '2025-08-01', 'Donated'),
('Bob Smith', 'David Brown', '2025-09-10', 'Donated'),
('Carol White', 'Grace Wilson', '2025-09-20', 'Donated');

-- Insert Transactions
INSERT INTO Transaction (DateOfDonation, DonorName, BloodBankName, TransactionType, Quantity) VALUES
('2025-09-15 10:30:00', 'Alice Johnson', 'Red Cross Blood Center', 'Donation', 1),
('2025-09-15 11:00:00', 'Bob Smith', 'Red Cross Blood Center', 'Donation', 1),
('2025-09-15 11:30:00', 'Emma Davis', 'Red Cross Blood Center', 'Donation', 1),
('2025-09-15 14:00:00', 'Frank Miller', 'Red Cross Blood Center', 'Donation', 1),
('2025-10-01 10:00:00', 'Carol White', 'Community Blood Services', 'Donation', 1),
('2025-10-01 10:45:00', 'David Brown', 'Community Blood Services', 'Donation', 1),
('2025-10-01 11:15:00', 'Grace Wilson', 'Community Blood Services', 'Donation', 1);

-- Insert Blood Units
INSERT INTO BloodUnit (DonorName, BloodBankName, BloodGroup, Quantity, CollectionDate, ExpirationDate, Status, Component, TestStatus, TransactionID) VALUES
('Alice Johnson', 'Red Cross Blood Center', 'A+', 1, '2025-09-15', '2025-10-30', 'Available', 'Whole Blood', 'Cleared', 1),
('Alice Johnson', 'Red Cross Blood Center', 'A+', 1, '2025-09-15', '2025-10-30', 'Available', 'RBC', 'Cleared', 1),
('Bob Smith', 'Red Cross Blood Center', 'O+', 1, '2025-09-15', '2025-10-30', 'Available', 'Whole Blood', 'Cleared', 2),
('Bob Smith', 'Red Cross Blood Center', 'O+', 1, '2025-09-15', '2025-10-30', 'Available', 'Plasma', 'Cleared', 2),
('Emma Davis', 'Red Cross Blood Center', 'O-', 1, '2025-09-15', '2025-10-30', 'Available', 'Whole Blood', 'Cleared', 3),
('Frank Miller', 'Red Cross Blood Center', 'A-', 1, '2025-09-15', '2025-10-30', 'Available', 'Whole Blood', 'Cleared', 4),
('Carol White', 'Community Blood Services', 'B+', 1, '2025-10-01', '2025-11-15', 'Available', 'Whole Blood', 'Cleared', 5),
('David Brown', 'Community Blood Services', 'AB+', 1, '2025-10-01', '2025-11-15', 'Available', 'Whole Blood', 'Cleared', 6),
('Grace Wilson', 'Community Blood Services', 'B-', 1, '2025-10-01', '2025-11-15', 'Available', 'Whole Blood', 'Cleared', 7),
-- Add some expiring soon units for testing
('Bob Smith', 'Red Cross Blood Center', 'O+', 1, '2025-09-20', '2025-10-15', 'Available', 'Whole Blood', 'Cleared', 2),
('Alice Johnson', 'Red Cross Blood Center', 'A+', 1, '2025-09-25', '2025-10-18', 'Available', 'Platelets', 'Cleared', 1);

-- Insert Patients
INSERT INTO Patient (Name, Age, Gender, Address, ContactNo, BloodGroupRequired, HospitalName, MedicalCondition, EmergencyContact) VALUES
('John Doe', 45, 'M', '111 Patient St', '6661234567', 'A+', 'City Care Hospital', 'Surgery Required - Cardiac Bypass', '6669999999'),
('Jane Smith', 32, 'F', '222 Care Ave', '6662345678', 'O+', 'City Care Hospital', 'Accident Victim - Multiple Trauma', '6668888888'),
('Michael Johnson', 58, 'M', '333 Health Rd', '6663456789', 'B+', 'Metro Medical Center', 'Chronic Anemia - Regular Transfusion', '6667777777'),
('Sarah Williams', 28, 'F', '444 Emergency Ln', '6664567890', 'O-', 'Regional Health Institute', 'Pregnancy Complications', '6666666666'),
('Robert Taylor', 55, 'M', '555 Critical St', '6665678901', 'AB+', 'Central General Hospital', 'Cancer Treatment', '6665555555');

-- Insert Requests
INSERT INTO Request (PatientName, RequestDate, Status, BloodBankName, RequiredUnits, UrgencyLevel, RequestedBy, Notes) VALUES
('John Doe', '2025-10-10 08:30:00', 'Pending', 'Red Cross Blood Center', 2, 'High', 'Dr. Sarah Williams', 'Pre-operative requirement for cardiac surgery'),
('Jane Smith', '2025-10-11 14:45:00', 'Pending', 'Red Cross Blood Center', 3, 'Critical', 'Dr. James Miller', 'Emergency - road accident with severe blood loss'),
('Michael Johnson', '2025-10-11 09:00:00', 'Pending', 'Community Blood Services', 1, 'Medium', 'Dr. Emily Davis', 'Regular scheduled transfusion'),
('Sarah Williams', '2025-10-12 06:15:00', 'Pending', 'National Blood Repository', 2, 'Critical', 'Dr. Sarah Williams', 'Emergency obstetric case'),
('Robert Taylor', '2025-10-11 11:30:00', 'Pending', 'Red Cross Blood Center', 1, 'High', 'Dr. James Miller', 'Chemotherapy support');

-- ============================================
-- COMPLETION MESSAGE
-- ============================================
SELECT 'Smart Blood DB - Official Schema Created Successfully!' AS Status;
SELECT '15 Tables | 6 Views | Sample Data Loaded' AS Summary;