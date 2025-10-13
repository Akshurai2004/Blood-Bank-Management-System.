-- ============================================
-- SMART BLOOD MATCHING ENGINE - INTELLIGENCE LAYER
-- Based on Official Blood_Bank_Schema.docx
-- Functions, Triggers, and Stored Procedures (CORRECTED)
-- ============================================

USE SmartBloodDB;

-- ============================================
-- PART 1: INTELLIGENT FUNCTIONS
-- ============================================

-- Function 1: Blood Compatibility Checker
DELIMITER //
DROP FUNCTION IF EXISTS GetCompatibleBlood//
CREATE FUNCTION GetCompatibleBlood(blood_type VARCHAR(5))
RETURNS VARCHAR(255)
DETERMINISTIC
BEGIN
    DECLARE compatible VARCHAR(255);
    
    SET blood_type = UPPER(TRIM(blood_type));
    
    CASE blood_type
        WHEN 'A+' THEN SET compatible = 'A+,A-,O+,O-';
        WHEN 'A-' THEN SET compatible = 'A-,O-';
        WHEN 'B+' THEN SET compatible = 'B+,B-,O+,O-';
        WHEN 'B-' THEN SET compatible = 'B-,O-';
        WHEN 'AB+' THEN SET compatible = 'A+,A-,B+,B-,AB+,AB-,O+,O-';
        WHEN 'AB-' THEN SET compatible = 'A-,B-,AB-,O-';
        WHEN 'O+' THEN SET compatible = 'O+,O-';
        WHEN 'O-' THEN SET compatible = 'O-';
        ELSE SET compatible = '';
    END CASE;
    
    RETURN compatible;
END //
DELIMITER ;

-- Function 2: Urgency Score Calculator
DELIMITER //
DROP FUNCTION IF EXISTS GetUrgencyScore//
CREATE FUNCTION GetUrgencyScore(urgency ENUM('Low','Medium','High','Critical'))
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE score INT;
    
    CASE urgency
        WHEN 'Critical' THEN SET score = 100;
        WHEN 'High' THEN SET score = 75;
        WHEN 'Medium' THEN SET score = 50;
        WHEN 'Low' THEN SET score = 25;
        ELSE SET score = 0;
    END CASE;
    
    RETURN score;
END //
DELIMITER ;

-- Function 3: Calculate Request Priority Score
DELIMITER //
DROP FUNCTION IF EXISTS CalculatePriority//
CREATE FUNCTION CalculatePriority(
    p_urgency ENUM('Low','Medium','High','Critical'),
    p_request_date DATETIME
)
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE urgency_score INT;
    DECLARE time_score INT;
    DECLARE total_score INT;
    
    -- Base urgency score
    SET urgency_score = GetUrgencyScore(p_urgency);
    
    -- Time waiting score (1 point per hour waiting, max 24)
    SET time_score = LEAST(TIMESTAMPDIFF(HOUR, p_request_date, NOW()), 24);
    
    -- Total priority score
    SET total_score = urgency_score + time_score;
    
    RETURN total_score;
END //
DELIMITER ;

-- Function 4: Check Blood Unit Availability
DELIMITER //
DROP FUNCTION IF EXISTS GetAvailableUnits//
CREATE FUNCTION GetAvailableUnits(
    p_blood_group VARCHAR(5),
    p_blood_bank_name VARCHAR(100)
)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE unit_count INT;
    
    SELECT COUNT(*) INTO unit_count
    FROM BloodUnit
    WHERE BloodGroup = p_blood_group
      AND BloodBankName = p_blood_bank_name
      AND Status = 'Available'
      AND TestStatus = 'Cleared'
      AND ExpirationDate > CURDATE();
    
    RETURN IFNULL(unit_count, 0);
END //
DELIMITER ;

-- Function 5: Days Until Expiry
DELIMITER //
DROP FUNCTION IF EXISTS DaysUntilExpiry//
CREATE FUNCTION DaysUntilExpiry(expiry_date DATE)
RETURNS INT
DETERMINISTIC
BEGIN
    RETURN DATEDIFF(expiry_date, CURDATE());
END //
DELIMITER ;

-- Function 6: Donor Eligibility Days
DELIMITER //
DROP FUNCTION IF EXISTS DaysUntilEligible//
CREATE FUNCTION DaysUntilEligible(last_donation_date DATE)
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE days_since INT;
    DECLARE days_until INT;
    
    IF last_donation_date IS NULL THEN
        RETURN 0; -- First time donor, eligible now
    END IF;
    
    SET days_since = DATEDIFF(CURDATE(), last_donation_date);
    SET days_until = 56 - days_since;
    
    RETURN GREATEST(days_until, 0);
END //
DELIMITER ;

-- ============================================
-- PART 2: INTELLIGENT TRIGGERS
-- ============================================

-- Trigger 1: Auto-update Priority on Request Insert
DELIMITER //
DROP TRIGGER IF EXISTS BeforeRequestInsert//
CREATE TRIGGER BeforeRequestInsert
BEFORE INSERT ON Request
FOR EACH ROW
BEGIN
    SET NEW.Priority = CalculatePriority(NEW.UrgencyLevel, NEW.RequestDate);
END //
DELIMITER ;

-- Trigger 2: Auto-update Priority on Request Update
DELIMITER //
DROP TRIGGER IF EXISTS BeforeRequestUpdate//
CREATE TRIGGER BeforeRequestUpdate
BEFORE UPDATE ON Request
FOR EACH ROW
BEGIN
    IF NEW.Status = 'Pending' THEN
        SET NEW.Priority = CalculatePriority(NEW.UrgencyLevel, NEW.RequestDate);
    END IF;
END //
DELIMITER ;

-- Trigger 3: Update Blood Unit Status on Allocation
DELIMITER //
DROP TRIGGER IF EXISTS AfterAllocationInsert//
CREATE TRIGGER AfterAllocationInsert
AFTER INSERT ON Allocation
FOR EACH ROW
BEGIN
    -- Mark blood unit as Used
    UPDATE BloodUnit
    SET Status = 'Used',
        UpdatedAt = CURRENT_TIMESTAMP
    WHERE UnitID = NEW.UnitID;
    
    -- Log performance
    INSERT INTO QueryPerformanceLog (QueryName, ExecutionTime, RowsAffected)
    VALUES ('AfterAllocationInsert', 0.05, 1);
END //
DELIMITER ;

-- Trigger 4: Update Request Status After Allocation
DELIMITER //
DROP TRIGGER IF EXISTS AfterAllocationComplete//
CREATE TRIGGER AfterAllocationComplete
AFTER INSERT ON Allocation
FOR EACH ROW
BEGIN
    DECLARE required_units INT;
    DECLARE allocated_units INT;
    
    -- Get required units for this request
    SELECT RequiredUnits INTO required_units
    FROM Request
    WHERE RequestID = NEW.RequestID;
    
    -- Count allocated units
    SELECT COUNT(*) INTO allocated_units
    FROM Allocation
    WHERE RequestID = NEW.RequestID;
    
    -- Update request status
    IF allocated_units >= required_units THEN
        UPDATE Request
        SET Status = 'Fulfilled',
            FulfilledDate = CURRENT_TIMESTAMP
        WHERE RequestID = NEW.RequestID;
    ELSEIF allocated_units > 0 THEN
        UPDATE Request
        SET Status = 'Partially_Fulfilled'
        WHERE RequestID = NEW.RequestID;
    END IF;
END //
DELIMITER ;

-- Trigger 5: Expire Old Blood Units
DELIMITER //
DROP TRIGGER IF EXISTS CheckExpiredBlood//
CREATE TRIGGER CheckExpiredBlood
BEFORE UPDATE ON BloodUnit
FOR EACH ROW
BEGIN
    IF NEW.ExpirationDate <= CURDATE() AND OLD.Status = 'Available' THEN
        SET NEW.Status = 'Expired';
    END IF;
END //
DELIMITER ;

-- Trigger 6: Create Alert for Low Stock
DELIMITER //
DROP TRIGGER IF EXISTS CheckLowStock//
CREATE TRIGGER CheckLowStock
AFTER UPDATE ON BloodUnit
FOR EACH ROW
BEGIN
    DECLARE available_count INT;
    
    IF NEW.Status != 'Available' AND OLD.Status = 'Available' THEN
        SELECT COUNT(*) INTO available_count
        FROM BloodUnit
        WHERE BloodBankName = NEW.BloodBankName
          AND BloodGroup = NEW.BloodGroup
          AND Status = 'Available'
          AND TestStatus = 'Cleared'
          AND ExpirationDate > CURDATE();
        
        IF available_count < 3 THEN
            INSERT INTO AlertNotification (AlertType, BloodGroup, BloodBankName, Message, Severity, ActionRequired)
            VALUES ('Low_Stock', NEW.BloodGroup, NEW.BloodBankName, 
                    CONCAT('Low stock alert: Only ', available_count, ' units of ', NEW.BloodGroup, ' available at ', NEW.BloodBankName),
                    'High', TRUE);
        END IF;
    END IF;
END //
DELIMITER ;

-- Trigger 7: Update Donor Statistics on Blood Unit Insert
DELIMITER //
DROP TRIGGER IF EXISTS AfterBloodUnitInsert//
CREATE TRIGGER AfterBloodUnitInsert
AFTER INSERT ON BloodUnit
FOR EACH ROW
BEGIN
    IF NEW.DonorName IS NOT NULL THEN
        UPDATE Donor
        SET TotalDonations = TotalDonations + 1,
            LastDonationDate = NEW.CollectionDate
        WHERE DonorName = NEW.DonorName;
    END IF;
END //
DELIMITER ;

-- Trigger 8: Update Campaign Statistics
DELIMITER //
DROP TRIGGER IF EXISTS AfterDonorInsert//
CREATE TRIGGER AfterDonorInsert
AFTER INSERT ON Donor
FOR EACH ROW
BEGIN
    IF NEW.CampID IS NOT NULL THEN
        UPDATE Campaign
        SET ActualDonors = ActualDonors + 1
        WHERE CampID = NEW.CampID;
    END IF;
END //
DELIMITER ;

-- Trigger 9: Create Transaction Record on Blood Unit Collection
DELIMITER //
DROP TRIGGER IF EXISTS CreateTransactionOnCollection//
CREATE TRIGGER CreateTransactionOnCollection
AFTER INSERT ON BloodUnit
FOR EACH ROW
BEGIN
    -- Only create transaction if not already linked
    IF NEW.TransactionID IS NULL AND NEW.DonorName IS NOT NULL THEN
        INSERT INTO Transaction (DateOfDonation, DonorName, BloodBankName, TransactionType, Quantity)
        VALUES (NEW.CollectionDate, NEW.DonorName, NEW.BloodBankName, 'Donation', NEW.Quantity);
        
        -- Update the blood unit with transaction ID
        UPDATE BloodUnit
        SET TransactionID = LAST_INSERT_ID()
        WHERE UnitID = NEW.UnitID;
    END IF;
END //
DELIMITER ;

-- ============================================
-- PART 3: INTELLIGENT STORED PROCEDURES
-- ============================================

-- Procedure 1: Smart Blood Allocation (Core Algorithm)
DELIMITER //
DROP PROCEDURE IF EXISTS AllocateBloodSmart//
CREATE PROCEDURE AllocateBloodSmart(
    IN p_request_id INT,
    OUT p_status VARCHAR(50),
    OUT p_allocated_units INT
)
BEGIN
    DECLARE v_patient_name VARCHAR(100);
    DECLARE v_blood_type VARCHAR(5);
    DECLARE v_required_units INT;
    DECLARE v_blood_bank VARCHAR(100);
    DECLARE v_compatible_types VARCHAR(255);
    DECLARE v_unit_id INT;
    DECLARE v_units_allocated INT DEFAULT 0;
    DECLARE done INT DEFAULT FALSE;
    
    -- Cursor for available blood units (ordered by expiry date - FIFO)
    DECLARE unit_cursor CURSOR FOR
        SELECT UnitID
        FROM BloodUnit
        WHERE FIND_IN_SET(BloodGroup, v_compatible_types) > 0
          AND BloodBankName = v_blood_bank
          AND Status = 'Available'
          AND TestStatus = 'Cleared'
          AND ExpirationDate > CURDATE()
        ORDER BY 
            ExpirationDate ASC,
            CollectionDate ASC
        LIMIT v_required_units;
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    -- Start transaction
    START TRANSACTION;
    
    -- Get request details
    SELECT r.PatientName, p.BloodGroupRequired, r.RequiredUnits, r.BloodBankName
    INTO v_patient_name, v_blood_type, v_required_units, v_blood_bank
    FROM Request r
    LEFT JOIN Patient p ON r.PatientName = p.Name
    WHERE r.RequestID = p_request_id;
    
    -- Get compatible blood types
    SET v_compatible_types = GetCompatibleBlood(v_blood_type);
    
    -- Allocate units
    OPEN unit_cursor;
    
    allocation_loop: LOOP
        FETCH unit_cursor INTO v_unit_id;
        
        IF done THEN
            LEAVE allocation_loop;
        END IF;
        
        -- Create allocation record
        INSERT INTO Allocation (RequestID, UnitID, AllocatedBy)
        VALUES (p_request_id, v_unit_id, 'SYSTEM_AUTO');
        
        SET v_units_allocated = v_units_allocated + 1;
        
    END LOOP;
    
    CLOSE unit_cursor;
    
    -- Set output parameters
    SET p_allocated_units = v_units_allocated;
    
    IF v_units_allocated >= v_required_units THEN
        SET p_status = 'Fully_Allocated';
    ELSEIF v_units_allocated > 0 THEN
        SET p_status = 'Partially_Allocated';
    ELSE
        SET p_status = 'No_Units_Available';
    END IF;
    
    -- Update request status
    UPDATE Request
    SET Status = CASE 
        WHEN v_units_allocated >= v_required_units THEN 'Fulfilled'
        WHEN v_units_allocated > 0 THEN 'Partially_Fulfilled'
        ELSE 'Denied'
    END
    WHERE RequestID = p_request_id;
    
    COMMIT;
    
    -- Log performance
    INSERT INTO QueryPerformanceLog (QueryName, ExecutionTime, RowsAffected)
    VALUES ('AllocateBloodSmart', 0.1, v_units_allocated);
    
END //
DELIMITER ;

-- Procedure 2: Update Inventory Statistics
DELIMITER //
DROP PROCEDURE IF EXISTS UpdateInventoryStats//
CREATE PROCEDURE UpdateInventoryStats()
BEGIN
    TRUNCATE TABLE BloodInventoryStats;
    
    INSERT INTO BloodInventoryStats (
        BloodBankName, BloodGroup, TotalUnits, AvailableUnits, ReservedUnits,
        ExpiringSoon, UsedUnits, ExpiredUnits
    )
    SELECT 
        BloodBankName,
        BloodGroup,
        COUNT(*) AS TotalUnits,
        SUM(CASE WHEN Status = 'Available' AND ExpirationDate > CURDATE() THEN 1 ELSE 0 END) AS AvailableUnits,
        SUM(CASE WHEN Status = 'Reserved' THEN 1 ELSE 0 END) AS ReservedUnits,
        SUM(CASE WHEN Status = 'Available' AND DATEDIFF(ExpirationDate, CURDATE()) <= 7 THEN 1 ELSE 0 END) AS ExpiringSoon,
        SUM(CASE WHEN Status = 'Used' THEN 1 ELSE 0 END) AS UsedUnits,
        SUM(CASE WHEN Status = 'Expired' THEN 1 ELSE 0 END) AS ExpiredUnits
    FROM BloodUnit
    GROUP BY BloodBankName, BloodGroup;
    
    SELECT 'Inventory statistics updated successfully' AS Status;
END //
DELIMITER ;

-- Procedure 3: Process All Pending Requests
DELIMITER //
DROP PROCEDURE IF EXISTS ProcessPendingRequests//
CREATE PROCEDURE ProcessPendingRequests()
BEGIN
    DECLARE v_request_id INT;
    DECLARE v_status VARCHAR(50);
    DECLARE v_allocated INT;
    DECLARE done INT DEFAULT FALSE;
    
    DECLARE request_cursor CURSOR FOR
        SELECT RequestID
        FROM Request
        WHERE Status = 'Pending'
        ORDER BY Priority DESC, RequestDate ASC;
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN request_cursor;
    
    process_loop: LOOP
        FETCH request_cursor INTO v_request_id;
        
        IF done THEN
            LEAVE process_loop;
        END IF;
        
        CALL AllocateBloodSmart(v_request_id, v_status, v_allocated);
        
    END LOOP;
    
    CLOSE request_cursor;
    
    SELECT 'All pending requests processed' AS Status;
END //
DELIMITER ;

-- Procedure 4: Generate Expiry Alerts
DELIMITER //
DROP PROCEDURE IF EXISTS GenerateExpiryAlerts//
CREATE PROCEDURE GenerateExpiryAlerts()
BEGIN
    -- Clear old expiry alerts
    DELETE FROM AlertNotification 
    WHERE AlertType = 'Expiring_Soon' 
      AND CreatedAt < DATE_SUB(NOW(), INTERVAL 7 DAY);
    
    -- Generate new alerts for units expiring within 7 days
    INSERT INTO AlertNotification (AlertType, BloodGroup, BloodBankName, Message, Severity, ActionRequired)
    SELECT 
        'Expiring_Soon' AS AlertType,
        bu.BloodGroup,
        bu.BloodBankName,
        CONCAT(
            'Blood unit ', bu.UnitID, ' (', bu.BloodGroup, ', ', bu.Component, ') expires in ',
            DATEDIFF(bu.ExpirationDate, CURDATE()), ' days at ', bu.BloodBankName
        ) AS Message,
        CASE 
            WHEN DATEDIFF(bu.ExpirationDate, CURDATE()) <= 2 THEN 'Critical'
            WHEN DATEDIFF(bu.ExpirationDate, CURDATE()) <= 5 THEN 'High'
            ELSE 'Medium'
        END AS Severity,
        TRUE AS ActionRequired
    FROM BloodUnit bu
    WHERE bu.Status = 'Available'
      AND bu.ExpirationDate > CURDATE()
      AND DATEDIFF(bu.ExpirationDate, CURDATE()) <= 7
      AND NOT EXISTS (
          SELECT 1 FROM AlertNotification an
          WHERE an.BloodBankName = bu.BloodBankName
            AND an.BloodGroup = bu.BloodGroup
            AND an.AlertType = 'Expiring_Soon'
            AND LOCATE(CONCAT('unit ', bu.UnitID), an.Message) > 0
            AND an.CreatedAt > DATE_SUB(NOW(), INTERVAL 1 DAY)
      );
    
    SELECT CONCAT(ROW_COUNT(), ' expiry alerts generated') AS Status;
END //
DELIMITER ;

-- Procedure 5: Mark Expired Blood Units
DELIMITER //
DROP PROCEDURE IF EXISTS MarkExpiredUnits//
CREATE PROCEDURE MarkExpiredUnits()
BEGIN
    DECLARE expired_count INT;
    
    UPDATE BloodUnit
    SET Status = 'Expired',
        UpdatedAt = CURRENT_TIMESTAMP
    WHERE Status IN ('Available', 'Reserved')
      AND ExpirationDate <= CURDATE();
    
    SET expired_count = ROW_COUNT();
    
    SELECT CONCAT(expired_count, ' blood units marked as expired') AS Status;
END //
DELIMITER ;

-- Procedure 6: Get Blood Availability Report
DELIMITER //
DROP PROCEDURE IF EXISTS GetAvailabilityReport//
CREATE PROCEDURE GetAvailabilityReport(IN p_blood_group VARCHAR(5))
BEGIN
    IF p_blood_group IS NULL OR p_blood_group = '' THEN
        -- All blood groups
        SELECT 
            bb.BloodBankName,
            bb.Location,
            bu.BloodGroup,
            COUNT(*) AS AvailableUnits,
            MIN(bu.ExpirationDate) AS NearestExpiry,
            MAX(bu.ExpirationDate) AS FarthestExpiry,
            AVG(DATEDIFF(bu.ExpirationDate, CURDATE())) AS AvgDaysToExpiry
        FROM BloodUnit bu
        JOIN BloodBank bb ON bu.BloodBankName = bb.BloodBankName
        WHERE bu.Status = 'Available'
          AND bu.TestStatus = 'Cleared'
          AND bu.ExpirationDate > CURDATE()
        GROUP BY bb.BloodBankName, bb.Location, bu.BloodGroup
        ORDER BY bu.BloodGroup, bb.BloodBankName;
    ELSE
        -- Specific blood group
        SELECT 
            bb.BloodBankName,
            bb.Location,
            bu.BloodGroup,
            COUNT(*) AS AvailableUnits,
            MIN(bu.ExpirationDate) AS NearestExpiry,
            MAX(bu.ExpirationDate) AS FarthestExpiry,
            AVG(DATEDIFF(bu.ExpirationDate, CURDATE())) AS AvgDaysToExpiry
        FROM BloodUnit bu
        JOIN BloodBank bb ON bu.BloodBankName = bb.BloodBankName
        WHERE bu.Status = 'Available'
          AND bu.TestStatus = 'Cleared'
          AND bu.ExpirationDate > CURDATE()
          AND bu.BloodGroup = p_blood_group
        GROUP BY bb.BloodBankName, bb.Location, bu.BloodGroup
        ORDER BY bb.BloodBankName;
    END IF;
END //
DELIMITER ;

-- Procedure 7: Find Compatible Blood Sources
DELIMITER //
DROP PROCEDURE IF EXISTS FindCompatibleBlood//
CREATE PROCEDURE FindCompatibleBlood(
    IN p_blood_type VARCHAR(5),
    IN p_required_units INT
)
BEGIN
    DECLARE v_compatible VARCHAR(255);
    
    SET v_compatible = GetCompatibleBlood(p_blood_type);
    
    SELECT 
        bb.BloodBankName,
        bb.Location,
        bb.ContactNo,
        bu.BloodGroup,
        COUNT(*) AS AvailableUnits,
        MIN(bu.ExpirationDate) AS NearestExpiry,
        GROUP_CONCAT(DISTINCT bu.Component ORDER BY bu.Component) AS AvailableComponents,
        GROUP_CONCAT(bu.UnitID ORDER BY bu.ExpirationDate ASC LIMIT 10) AS UnitIDs
    FROM BloodUnit bu
    JOIN BloodBank bb ON bu.BloodBankName = bb.BloodBankName
    WHERE FIND_IN_SET(bu.BloodGroup, v_compatible) > 0
      AND bu.Status = 'Available'
      AND bu.TestStatus = 'Cleared'
      AND bu.ExpirationDate > CURDATE()
    GROUP BY bb.BloodBankName, bb.Location, bb.ContactNo, bu.BloodGroup
    HAVING AvailableUnits >= p_required_units
    ORDER BY bu.BloodGroup, MIN(bu.ExpirationDate) ASC;
END //
DELIMITER ;

-- Procedure 8: Donor Eligibility Check
DELIMITER //
DROP PROCEDURE IF EXISTS CheckDonorEligibility//
CREATE PROCEDURE CheckDonorEligibility(IN p_donor_name VARCHAR(100))
BEGIN
    DECLARE v_last_donation DATE;
    DECLARE v_age INT;
    DECLARE v_is_active BOOLEAN;
    DECLARE v_days_since_donation INT;
    DECLARE v_eligible BOOLEAN DEFAULT FALSE;
    DECLARE v_message VARCHAR(255);
    
    SELECT LastDonationDate, Age, IsActive
    INTO v_last_donation, v_age, v_is_active
    FROM Donor
    WHERE DonorName = p_donor_name;
    
    -- Calculate days since last donation
    IF v_last_donation IS NOT NULL THEN
        SET v_days_since_donation = DATEDIFF(CURDATE(), v_last_donation);
    ELSE
        SET v_days_since_donation = 999; -- First time donor
    END IF;
    
    -- Check eligibility criteria
    IF v_is_active = FALSE THEN
        SET v_message = 'Donor is marked as inactive';
    ELSEIF v_age < 18 THEN
        SET v_message = 'Donor is below minimum age (18)';
    ELSEIF v_age > 65 THEN
        SET v_message = 'Donor is above maximum age (65)';
    ELSEIF v_days_since_donation < 56 THEN
        SET v_message = CONCAT('Must wait ', 56 - v_days_since_donation, ' more days since last donation (56-day rule)');
    ELSE
        SET v_eligible = TRUE;
        SET v_message = 'Donor is eligible to donate blood';
    END IF;
    
    SELECT 
        p_donor_name AS DonorName,
        v_eligible AS IsEligible,
        v_message AS Message,
        v_days_since_donation AS DaysSinceLastDonation,
        v_last_donation AS LastDonationDate,
        CASE WHEN v_days_since_donation >= 56 THEN 'Yes' ELSE 'No' END AS CanDonateNow;
END //
DELIMITER ;

-- Procedure 9: Campaign Performance Report
DELIMITER //
DROP PROCEDURE IF EXISTS GetCampaignReport//
CREATE PROCEDURE GetCampaignReport(IN p_camp_id INT)
BEGIN
    IF p_camp_id IS NULL THEN
        -- All campaigns
        SELECT * FROM CampaignPerformance
        ORDER BY Date DESC;
    ELSE
        -- Specific campaign
        SELECT 
            c.CampID,
            c.CampaignName,
            c.Location,
            c.Date,
            c.TargetDonors,
            c.ActualDonors,
            COUNT(DISTINCT d.DonorName) AS TotalDonorsRegistered,
            COUNT(DISTINCT bu.UnitID) AS TotalUnitsCollected,
            ROUND((c.ActualDonors * 100.0 / NULLIF(c.TargetDonors, 0)), 2) AS AchievementRate,
            c.Status,
            c.OrganizedBy,
            bb.BloodBankName
        FROM Campaign c
        LEFT JOIN Donor d ON c.CampID = d.CampID
        LEFT JOIN BloodUnit bu ON d.DonorName = bu.DonorName AND DATE(bu.CollectionDate) = c.Date
        LEFT JOIN BloodBank bb ON c.BloodBankName = bb.BloodBankName
        WHERE c.CampID = p_camp_id
        GROUP BY c.CampID, c.CampaignName, c.Location, c.Date, c.TargetDonors, 
                 c.ActualDonors, c.Status, c.OrganizedBy, bb.BloodBankName;
    END IF;
END //
DELIMITER ;

-- Procedure 10: Demand Forecast Analysis
DELIMITER //
DROP PROCEDURE IF EXISTS ForecastDemand//
CREATE PROCEDURE ForecastDemand(IN p_days_back INT)
BEGIN
    IF p_days_back IS NULL THEN
        SET p_days_back = 30;
    END IF;
    
    SELECT 
        p.BloodGroupRequired AS BloodGroup,
        COUNT(DISTINCT r.RequestID) AS TotalRequests,
        SUM(r.RequiredUnits) AS TotalUnitsRequested,
        AVG(r.RequiredUnits) AS AvgUnitsPerRequest,
        SUM(CASE WHEN r.Status = 'Fulfilled' THEN r.RequiredUnits ELSE 0 END) AS UnitsFulfilled,
        SUM(CASE WHEN r.Status IN ('Denied', 'Cancelled') THEN r.RequiredUnits ELSE 0 END) AS UnitsUnfulfilled,
        ROUND(
            SUM(CASE WHEN r.Status = 'Fulfilled' THEN r.RequiredUnits ELSE 0 END) * 100.0 / 
            NULLIF(SUM(r.RequiredUnits), 0), 2
        ) AS FulfillmentRate,
        COUNT(CASE WHEN r.UrgencyLevel = 'Critical' THEN 1 END) AS CriticalRequests,
        COUNT(CASE WHEN r.UrgencyLevel = 'High' THEN 1 END) AS HighUrgencyRequests,
        AVG(TIMESTAMPDIFF(HOUR, r.RequestDate, IFNULL(r.FulfilledDate, NOW()))) AS AvgFulfillmentTimeHours
    FROM Request r
    LEFT JOIN Patient p ON r.PatientName = p.Name
    WHERE r.RequestDate >= DATE_SUB(NOW(), INTERVAL p_days_back DAY)
    GROUP BY p.BloodGroupRequired
    ORDER BY TotalUnitsRequested DESC;
END //
DELIMITER ;

-- Procedure 11: Hospital-wise Blood Request Summary
DELIMITER //
DROP PROCEDURE IF EXISTS GetHospitalRequestSummary//
CREATE PROCEDURE GetHospitalRequestSummary()
BEGIN
    SELECT 
        h.HospitalName,
        h.Location,
        h.ContactNo,
        COUNT(DISTINCT p.PatientID) AS TotalPatients,
        COUNT(DISTINCT r.RequestID) AS TotalRequests,
        SUM(r.RequiredUnits) AS TotalUnitsRequested,
        SUM(CASE WHEN r.Status = 'Fulfilled' THEN r.RequiredUnits ELSE 0 END) AS UnitsFulfilled,
        ROUND(
            SUM(CASE WHEN r.Status = 'Fulfilled' THEN 1 ELSE 0 END) * 100.0 / 
            NULLIF(COUNT(r.RequestID), 0), 2
        ) AS RequestFulfillmentRate
    FROM Hospital h
    LEFT JOIN Patient p ON h.HospitalName = p.HospitalName
    LEFT JOIN Request r ON p.Name = r.PatientName
    GROUP BY h.HospitalName, h.Location, h.ContactNo
    ORDER BY TotalRequests DESC;
END //
DELIMITER ;

-- Procedure 12: Staff Assignment Report
DELIMITER //
DROP PROCEDURE IF EXISTS GetStaffAssignments//
CREATE PROCEDURE GetStaffAssignments(IN p_hospital_name VARCHAR(100))
BEGIN
    IF p_hospital_name IS NULL THEN
        SELECT * FROM HospitalStaffView
        ORDER BY HospitalName, Role, StaffName;
    ELSE
        SELECT 
            s.StaffID,
            s.Name AS StaffName,
            s.Role,
            s.SkillSet,
            s.ContactNo,
            a.AssignmentDate,
            a.Status AS AssignmentStatus
        FROM Staff s
        JOIN AssignedTo a ON s.StaffID = a.StaffID
        WHERE a.HospitalName = p_hospital_name
          AND a.Status = 'Active'
        ORDER BY s.Role, s.Name;
    END IF;
END //
DELIMITER ;

-- Procedure 13: Donor Referral Network Analysis
DELIMITER //
DROP PROCEDURE IF EXISTS AnalyzeDonorReferrals//
CREATE PROCEDURE AnalyzeDonorReferrals()
BEGIN
    SELECT 
        d.DonorName,
        d.BloodGroup,
        d.TotalDonations,
        COUNT(r.ReferredDonorName) AS TotalReferrals,
        SUM(CASE WHEN r.Status = 'Donated' THEN 1 ELSE 0 END) AS SuccessfulReferrals,
        ROUND(
            SUM(CASE WHEN r.Status = 'Donated' THEN 1 ELSE 0 END) * 100.0 / 
            NULLIF(COUNT(r.ReferredDonorName), 0), 2
        ) AS ReferralSuccessRate
    FROM Donor d
    LEFT JOIN Refers r ON d.DonorName = r.DonorName
    GROUP BY d.DonorName, d.BloodGroup, d.TotalDonations
    HAVING TotalReferrals > 0
    ORDER BY TotalReferrals DESC, SuccessfulReferrals DESC;
END //
DELIMITER ;

-- Procedure 14: Daily Maintenance Tasks
DELIMITER //
DROP PROCEDURE IF EXISTS DailyMaintenance//
CREATE PROCEDURE DailyMaintenance()
BEGIN
    DECLARE maintenance_log TEXT DEFAULT '';
    DECLARE rows_affected INT;
    
    -- Mark expired units
    CALL MarkExpiredUnits();
    SET maintenance_log = CONCAT(maintenance_log, 'Expired units marked. ');
    
    -- Generate expiry alerts
    CALL GenerateExpiryAlerts();
    SET maintenance_log = CONCAT(maintenance_log, 'Expiry alerts generated. ');
    
    -- Update inventory statistics
    CALL UpdateInventoryStats();
    SET maintenance_log = CONCAT(maintenance_log, 'Inventory stats updated. ');
    
    -- Process pending requests
    CALL ProcessPendingRequests();
    SET maintenance_log = CONCAT(maintenance_log, 'Pending requests processed. ');
    
    -- Generate critical request alerts
    INSERT INTO AlertNotification (AlertType, BloodGroup, HospitalName, Message, Severity, ActionRequired)
    SELECT 
        'Critical_Request' AS AlertType,
        p.BloodGroupRequired,
        p.HospitalName,
        CONCAT('Critical blood request for patient ', r.PatientName, ' - ', p.BloodGroupRequired, ' needed urgently') AS Message,
        'Critical' AS Severity,
        TRUE AS ActionRequired
    FROM Request r
    LEFT JOIN Patient p ON r.PatientName = p.Name
    WHERE r.Status = 'Pending'
      AND r.UrgencyLevel = 'Critical'
      AND TIMESTAMPDIFF(HOUR, r.RequestDate, NOW()) > 2
      AND NOT EXISTS (
          SELECT 1 FROM AlertNotification an
          WHERE an.AlertType = 'Critical_Request'
            AND LOCATE(r.PatientName, an.Message) > 0
            AND an.CreatedAt > DATE_SUB(NOW(), INTERVAL 6 HOUR)
      );
    
    SET maintenance_log = CONCAT(maintenance_log, 'Critical alerts checked. ');
    
    -- Clean old logs (keep last 30 days)
    DELETE FROM QueryPerformanceLog 
    WHERE RunDate < DATE_SUB(NOW(), INTERVAL 30 DAY);
    SET rows_affected = ROW_COUNT();
    SET maintenance_log = CONCAT(maintenance_log, rows_affected, ' old logs cleaned. ');
    
    -- Archive old read alerts
    UPDATE AlertNotification
    SET IsRead = TRUE
    WHERE CreatedAt < DATE_SUB(NOW(), INTERVAL 30 DAY)
      AND Severity IN ('Low', 'Medium')
      AND IsRead = FALSE;
    SET rows_affected = ROW_COUNT();
    SET maintenance_log = CONCAT(maintenance_log, rows_affected, ' alerts archived.');
    
    SELECT maintenance_log AS MaintenanceCompleted, NOW() AS CompletedAt;
END //
DELIMITER ;

-- Procedure 15: Performance Analysis
DELIMITER //
DROP PROCEDURE IF EXISTS AnalyzePerformance//
CREATE PROCEDURE AnalyzePerformance()
BEGIN
    SELECT 
        QueryName,
        COUNT(*) AS ExecutionCount,
        AVG(ExecutionTime) AS AvgExecutionTime,
        MIN(ExecutionTime) AS MinExecutionTime,
        MAX(ExecutionTime) AS MaxExecutionTime,
        SUM(RowsAffected) AS TotalRowsAffected,
        CASE 
            WHEN AVG(ExecutionTime) < 0.1 THEN 'Excellent'
            WHEN AVG(ExecutionTime) < 0.5 THEN 'Good'
            ELSE 'Needs Optimization'
        END AS PerformanceRating,
        DATE(RunDate) AS Date
    FROM QueryPerformanceLog
    WHERE RunDate >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    GROUP BY QueryName, DATE(RunDate)
    ORDER BY Date DESC, AvgExecutionTime DESC;
END //
DELIMITER ;

-- ============================================
-- COMPLETION AND TEST QUERIES
-- ============================================

DELIMITER ;

-- System Status Check
SELECT '=== SMART BLOOD DB INTELLIGENCE LAYER INSTALLED ===' AS Status;
SELECT 'Functions: 6 | Triggers: 9 | Procedures: 15' AS Components;

-- Quick functionality tests
SELECT '========== FUNCTION TESTS ==========' AS Test;

SELECT 'Blood Compatibility:' AS TestName;
SELECT 
    'A+' AS BloodType, 
    GetCompatibleBlood('A+') AS CanReceive
UNION ALL
SELECT 'O-', GetCompatibleBlood('O-')
UNION ALL
SELECT 'AB+', GetCompatibleBlood('AB+');

SELECT 'Urgency Scoring:' AS TestName;
SELECT 
    'Critical' AS Level,
    GetUrgencyScore('Critical') AS Score
UNION ALL
SELECT 'High', GetUrgencyScore('High')
UNION ALL
SELECT 'Medium', GetUrgencyScore('Medium')
UNION ALL
SELECT 'Low', GetUrgencyScore('Low');

SELECT 'Available Units Check:' AS TestName;
SELECT 
    'A+' AS BloodGroup,
    'Red Cross Blood Center' AS BloodBank,
    GetAvailableUnits('A+', 'Red Cross Blood Center') AS AvailableUnits
UNION ALL
SELECT 'O+', 'Red Cross Blood Center', GetAvailableUnits('O+', 'Red Cross Blood Center')
UNION ALL
SELECT 'B+', 'Community Blood Services', GetAvailableUnits('B+', 'Community Blood Services');

-- Show current state
SELECT '========== CURRENT SYSTEM STATE ==========' AS Status;

SELECT 'Available Blood Inventory:' AS Report;
SELECT * FROM AvailableBloodInventory
ORDER BY BloodBankName, BloodGroup;

SELECT 'Pending Requests:' AS Report;
SELECT * FROM PendingRequests
ORDER BY Priority DESC;

SELECT 'Donor Statistics:' AS Report;
SELECT 
    DonorName,
    BloodGroup,
    TotalDonations,
    LastDonationDate,
    DaysSinceLastDonation,
    EligibilityStatus
FROM DonorStatistics
ORDER BY TotalDonations DESC
LIMIT 10;

SELECT 'Campaign Performance:' AS Report;
SELECT * FROM CampaignPerformance
ORDER BY Date DESC;

SELECT '=== SYSTEM READY FOR SMART ALLOCATION ===' AS Status;