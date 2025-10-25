
INSERT INTO Hospital (HospitalName, Location, ContactNo, Email) VALUES
('City Care Hospital', 'Downtown', '1234567890', 'info@citycare.com'),
('Metro Medical Center', 'Uptown', '2345678901', 'contact@metromedical.com'),
('Regional Health Institute', 'Suburbs', '3456789012', 'info@regionalhealth.com');

INSERT INTO BloodBank (BloodBankName, Location, ContactNo, Capacity) VALUES
('Red Cross Blood Center', 'Downtown', '1112223333', 2000),
('Community Blood Services', 'Midtown', '2223334444', 1500),
('National Blood Repository', 'Uptown', '3334445555', 3000);

INSERT INTO Donor (DonorName, Age, Gender, BloodGroup, ContactNo, Email, Address, LastDonationDate, TotalDonations) VALUES
('Alice Johnson', 28, 'F', 'A+', '5551234567', 'alice@email.com', '123 Main St', '2025-08-15', 5),
('Bob Smith', 35, 'M', 'O+', '5552345678', 'bob@email.com', '456 Oak Ave', '2025-07-20', 8),
('Carol White', 42, 'F', 'B+', '5553456789', 'carol@email.com', '789 Pine Rd', '2025-09-01', 3),
('David Brown', 31, 'M', 'AB+', '5554567890', 'david@email.com', '321 Elm St', '2025-09-10', 6),
('Emma Davis', 26, 'F', 'O-', '5555678901', 'emma@email.com', '654 Maple Dr', NULL, 0);

INSERT INTO Patient (PatientName, Age, Gender, BloodGroupRequired, HospitalID, ContactNo, MedicalCondition) VALUES
('John Doe', 45, 'M', 'A+', 1, '6661234567', 'Surgery Required'),
('Jane Smith', 32, 'F', 'O+', 1, '6662345678', 'Accident Victim'),
('Michael Johnson', 58, 'M', 'B+', 2, '6663456789', 'Chronic Anemia'),
('Sarah Williams', 28, 'F', 'O-', 3, '6664567890', 'Pregnancy Complications'),
('Robert Taylor', 55, 'M', 'AB+', 2, '6665678901', 'Cancer Treatment');

INSERT INTO BloodUnit (DonorID, BloodBankID, BloodGroup, Quantity, CollectionDate, ExpirationDate, Status, Component) VALUES
(1, 1, 'A+', 1, '2025-09-15', '2025-10-30', 'Available', 'Whole Blood'),
(2, 1, 'O+', 1, '2025-09-16', '2025-10-31', 'Available', 'RBC'),
(3, 2, 'B+', 1, '2025-09-14', '2025-10-29', 'Available', 'Plasma'),
(4, 1, 'AB+', 1, '2025-09-12', '2025-10-27', 'Available', 'Whole Blood'),
(5, 3, 'O-', 1, '2025-09-10', '2025-10-25', 'Available', 'Platelets');



-- TEST 1: Check initial donor stats before donation
SELECT '========== TEST 1: Initial Donor Stats ==========' AS Test;
SELECT DonorID, DonorName, BloodGroup, LastDonationDate, TotalDonations 
FROM Donor 
WHERE DonorID = 5;

-- TEST 2: Check donor eligibility
SELECT '========== TEST 2: Check Donor Eligibility ==========' AS Test;
SELECT CheckDonorEligibility(5) AS 'Emma Davis Eligibility (First time donor)';
SELECT CheckDonorEligibility(1) AS 'Alice Johnson Eligibility (Last donated 2025-08-15)';
SELECT CheckDonorEligibility(2) AS 'Bob Smith Eligibility (Last donated 2025-07-20)';

-- TEST 3: View initial blood inventory
SELECT '========== TEST 3: Initial Blood Inventory ==========' AS Test;
SELECT * FROM AvailableBloodInventory;

-- TEST 4: Count initial blood units
SELECT '========== TEST 4: Initial Blood Unit Count ==========' AS Test;
SELECT COUNT(*) AS 'Total Blood Units in Database' FROM BloodUnit;
SELECT COUNT(*) AS 'Available Blood Units' FROM BloodUnit WHERE Status = 'Available';

-- TEST 5: Record a new donation (Trigger will auto-update donor stats)
SELECT '========== TEST 5: Record Blood Donation ==========' AS Test;
CALL RecordBloodDonation(5, 3, 'Whole Blood', 1);

-- TEST 6: Verify trigger updated donor stats
SELECT '========== TEST 6: Verify Donor Stats After Donation ==========' AS Test;
SELECT DonorID, DonorName, BloodGroup, LastDonationDate, TotalDonations 
FROM Donor 
WHERE DonorID = 5;

-- TEST 7: Verify new blood unit was created
SELECT '========== TEST 7: Verify New Blood Unit Created ==========' AS Test;
SELECT UnitID, DonorID, BloodBankID, BloodGroup, Component, CollectionDate, ExpirationDate, Status
FROM BloodUnit
WHERE DonorID = 5
ORDER BY UnitID DESC
LIMIT 2;

-- TEST 8: Check updated blood inventory
SELECT '========== TEST 8: Updated Blood Inventory ==========' AS Test;
SELECT * FROM AvailableBloodInventory
WHERE BloodGroup = 'O-';

-- TEST 9: Check blood availability by blood group using VIEW
SELECT '========== TEST 9: Blood Availability by Blood Group ==========' AS Test;
SELECT * FROM AvailableBloodInventory
WHERE BloodGroup IN ('A+', 'O-')
ORDER BY BloodGroup;

-- TEST 10: Record another donation from a different donor
SELECT '========== TEST 10: Record Another Donation ==========' AS Test;
CALL RecordBloodDonation(1, 1, 'RBC', 1);

-- TEST 11: Verify Alice's updated stats
SELECT '========== TEST 11: Verify Alice Stats After Donation ==========' AS Test;
SELECT DonorID, DonorName, TotalDonations, LastDonationDate 
FROM Donor 
WHERE DonorID = 1;

-- TEST 12: Final inventory summary
SELECT '========== TEST 12: Final Inventory Summary ==========' AS Test;
SELECT 
    BloodGroup,
    COUNT(*) AS TotalUnits,
    SUM(CASE WHEN Status = 'Available' THEN 1 ELSE 0 END) AS Available,
    SUM(CASE WHEN Status = 'Reserved' THEN 1 ELSE 0 END) AS Reserved,
    SUM(CASE WHEN Status = 'Expired' THEN 1 ELSE 0 END) AS Expired
FROM BloodUnit
GROUP BY BloodGroup
ORDER BY BloodGroup;

-- PROCEDURE (1) used: Tests 5, 10
-- FUNCTION (1) used: Test 2
-- VIEW (1) used: Tests 3, 8, 9
-- TRIGGER (1) fired: Tests 5, 10 (automatically)

-- 📋 Test Cases (12 comprehensive tests):
-- TEST 1: Initial Donor Stats
-- Simple SELECT query on Donor table
-- TEST 2: Check Donor Eligibility
-- Calls FUNCTION CheckDonorEligibility three times
-- TEST 3: Initial Blood Inventory
-- Queries VIEW AvailableBloodInventory
-- TEST 4: Initial Blood Unit Count
-- Simple SELECT queries with COUNT on BloodUnit table
-- TEST 5: Record Blood Donation
-- Calls PROCEDURE RecordBloodDonation which automatically fires TRIGGER UpdateDonorStats
-- TEST 6: Verify Donor Stats After Donation
-- Simple SELECT query to verify TRIGGER worked correctly
-- TEST 7: Verify New Blood Unit Created
-- Simple SELECT query to verify PROCEDURE inserted the blood unit
-- TEST 8: Updated Blood Inventory
-- Queries VIEW AvailableBloodInventory with filter
-- TEST 9: Blood Availability by Blood Group
-- Queries VIEW AvailableBloodInventory for specific blood groups
-- TEST 10: Record Another Donation
-- Calls PROCEDURE RecordBloodDonation again, firing TRIGGER again
-- TEST 11: Verify Alice Stats After Donation
-- Simple SELECT query to verify TRIGGER updated Alice's stats
-- TEST 12: Final Inventory Summary
-- Simple SELECT query with GROUP BY on BloodUnit table