USE BloodBankDB;

-- Insert Hospitals
INSERT IGNORE INTO Hospital (HospitalID, HospitalName, Location, ContactNo, Email) VALUES
(1, 'City Care Hospital', 'Downtown', '9876543210', 'info@citycare.org'),
(2, 'Metro Medical Center', 'Uptown', '9876543211', 'contact@metromedical.org'),
(3, 'Regional Health Institute', 'Midtown', '9876543212', 'help@regionalhealth.org');

-- Insert Blood Banks
INSERT IGNORE INTO BloodBank (BloodBankID, BloodBankName, Location, ContactNo, Capacity) VALUES
(1, 'Red Cross Blood Center', 'Downtown', '9876543220', 1500),
(2, 'Lifeline Blood Bank', 'Uptown', '9876543221', 1200),
(3, 'National Blood Repository', 'Midtown', '9876543222', 2000),
(4, 'Rising Sun Blood Bank', 'Westside', '9876543223', 1000);

-- Insert Donors
INSERT IGNORE INTO Donor (DonorID, DonorName, Age, Gender, BloodGroup, ContactNo, Email, Address, LastDonationDate, TotalDonations, IsActive) VALUES
(1, 'Alice Johnson', 28, 'F', 'A+', '9876500001', 'alice@example.com', '123 Main St', '2026-01-15', 7, TRUE),
(2, 'Bob Smith', 35, 'M', 'O+', '9876500002', 'bob@example.com', '456 Oak Ave', '2026-01-20', 9, TRUE),
(3, 'David Brown', 31, 'M', 'AB+', '9876500003', 'david@example.com', '321 Elm St', '2026-02-01', 7, TRUE),
(4, 'Emma Davis', 26, 'F', 'O-', '9876500004', 'emma@example.com', '654 Maple Dr', '2026-02-10', 3, TRUE),
(5, 'Akshat Sharma', 22, 'M', 'B+', '9876500005', 'akshat@example.com', '789 Pine Rd', '2026-01-10', 4, TRUE);

-- Insert Blood Units (Expiration dates in the future)
INSERT IGNORE INTO BloodUnit (UnitID, DonorID, BloodBankID, BloodGroup, Quantity, CollectionDate, ExpirationDate, Status, Component) VALUES
(1, 1, 1, 'A+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 35 DAY), 'Available', 'Whole Blood'),
(2, 1, 1, 'A+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 35 DAY), 'Available', 'RBC'),
(3, 2, 1, 'O+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 30 DAY), 'Available', 'Whole Blood'),
(4, 2, 2, 'O+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 40 DAY), 'Available', 'Plasma'),
(5, 3, 2, 'AB+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 25 DAY), 'Available', 'Platelets'),
(6, 4, 3, 'O-', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 42 DAY), 'Available', 'Whole Blood'),
(7, 5, 3, 'B+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 38 DAY), 'Available', 'Whole Blood'),
(8, 5, 4, 'B+', 1, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 32 DAY), 'Available', 'RBC');

-- Insert Patients
INSERT IGNORE INTO Patient (PatientID, PatientName, Age, Gender, BloodGroupRequired, HospitalID, ContactNo, MedicalCondition) VALUES
(1, 'John Doe', 45, 'M', 'A+', 1, '9123450001', 'Surgery Required'),
(2, 'Jane Smith', 32, 'F', 'O+', 1, '9123450002', 'Accident Victim'),
(3, 'Robert Taylor', 55, 'M', 'AB+', 2, '9123450003', 'Cancer Treatment'),
(4, 'Priya Patel', 29, 'F', 'B+', 3, '9123450004', 'Emergency Anemia');

-- Insert Requests
INSERT IGNORE INTO Request (RequestID, PatientID, BloodBankID, RequiredUnits, Status, RequestDate) VALUES
(1, 1, 1, 2, 'Pending', NOW()),
(2, 2, 2, 1, 'Fulfilled', NOW()),
(3, 3, 3, 2, 'Pending', NOW()),
(4, 4, 3, 1, 'Pending', NOW());

-- Insert Seed Users
INSERT IGNORE INTO User (UserID, FullName, Email, PasswordHash, Role, DonorID, HospitalID, BloodBankID) VALUES
(1, 'System Administrator', 'admin@bloodbank.org', '$2b$12$5Cb76lEVjXiG6naVUbsqAepaP65XIfubDRymX0qiRaPHRoMIDL0fe', 'Admin', NULL, NULL, 1),
(2, 'Global Super Admin', 'superadmin@bloodbank.org', '$2b$12$AVBrJUt1xxpnIl76dNkcdOWDB/09ztjr6EQ15UH75i30h4KlkiGv6', 'SuperAdmin', NULL, NULL, NULL),
(3, 'Alice Johnson (Donor)', 'alice@example.com', '$2b$12$UD7KL5M9O1VIyNObltbBkOuFlYBGspnsSW2w1/4czbYQqQa0lZQ/q', 'Donor', 1, NULL, NULL),
(4, 'City Care Hospital Staff', 'hospital@citycare.org', '$2b$12$/Dka.TQM54K1jyq0tUQDveXoKezM7v9FXbOvjLuR83qPNWo5An0d2', 'Hospital', NULL, 1, NULL);
