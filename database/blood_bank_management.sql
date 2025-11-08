DROP DATABASE IF EXISTS BloodBankDB;
CREATE DATABASE BloodBankDB;
USE BloodBankDB;

CREATE TABLE Hospital (
    HospitalID INT AUTO_INCREMENT PRIMARY KEY,
    HospitalName VARCHAR(100) NOT NULL UNIQUE,
    Location VARCHAR(100) NOT NULL,
    ContactNo VARCHAR(15) NOT NULL,
    Email VARCHAR(100),
    INDEX idx_location (Location)
)  ;

CREATE TABLE BloodBank (
    BloodBankID INT AUTO_INCREMENT PRIMARY KEY,
    BloodBankName VARCHAR(100) NOT NULL UNIQUE,
    Location VARCHAR(100) NOT NULL,
    ContactNo VARCHAR(15) NOT NULL,
    Capacity INT DEFAULT 1000,
    INDEX idx_location (Location)
);
CREATE TABLE Donor (
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
);
CREATE TABLE BloodUnit (
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
    INDEX idx_expiration (ExpirationDate), 
    CHECK (ExpirationDate > CollectionDate)
);
CREATE TABLE Patient (
    PatientID INT AUTO_INCREMENT PRIMARY KEY,
    PatientName VARCHAR(100) NOT NULL,
    Age INT CHECK (Age > 0),
    Gender ENUM('M','F','O'),
    BloodGroupRequired VARCHAR(5) NOT NULL,
    HospitalID INT NOT NULL,
    ContactNo VARCHAR(15) NOT NULL,
    MedicalCondition VARCHAR(255),
    RegistrationDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (HospitalID) REFERENCES Hospital(HospitalID) ON DELETE CASCADE,
    INDEX idx_blood_group (BloodGroupRequired),
    INDEX idx_hospital (HospitalID)
) ;
CREATE TABLE Request (
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
) ;
CREATE TABLE Allocation (
    AllocationID INT AUTO_INCREMENT PRIMARY KEY,
    RequestID INT NOT NULL,
    UnitID INT NOT NULL,
    AllocationDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    DeliveryStatus ENUM('Pending','Delivered','Failed') DEFAULT 'Pending',
    FOREIGN KEY (RequestID) REFERENCES Request(RequestID) ON DELETE CASCADE,
    FOREIGN KEY (UnitID) REFERENCES BloodUnit(UnitID) ON DELETE RESTRICT,
    INDEX idx_request (RequestID),
    INDEX idx_unit (UnitID)
);  


-- View 1: Available Blood Inventory by Blood Bank
 -- MAINLY USED TO SEE THE AVAILABLE BLOOD BANK AND BLOOD GROUP IMMEDIATELY
CREATE VIEW AvailableBloodInventory AS
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
ORDER BY bu.BloodGroup, DaysUntilExpiry;



-- PROCEDURE 
-- new blood donations are recorded here
DELIMITER //
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
    SELECT 'Donation recorded successfully!' AS Message; 
END //
DELIMITER ;


-- FUNCTION: Check Donor Eligibility like the interval between the donating is min 56 days + (age we can add, )
DELIMITER //
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
END //
DELIMITER ;

-- TRIGGER: Update Donor Stats After Donation  (RECORD_BLOOD_DONATION) both are working together 
-- updates donor's LastDonationDate and TotalDonations when a new blood unit is inserted,
DELIMITER //
CREATE TRIGGER UpdateDonorStats
AFTER INSERT ON BloodUnit
FOR EACH ROW
BEGIN
    UPDATE Donor 
    SET LastDonationDate = NEW.CollectionDate,
        TotalDonations = TotalDonations + 1
    WHERE DonorID = NEW.DonorID;
END //
DELIMITER ;
