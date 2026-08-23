USE BloodBankDB;

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
);

-- Seed default users for testing (passwords: Admin@123, SuperAdmin@123, Donor@123, Hospital@123)
INSERT IGNORE INTO User (UserID, FullName, Email, PasswordHash, Role, DonorID, HospitalID, BloodBankID) VALUES
(1, 'System Administrator', 'admin@bloodbank.org', '', 'Admin', NULL, NULL, 1),
(2, 'Global Super Admin', 'superadmin@bloodbank.org', '/09ztjr6EQ15UH75i30h4KlkiGv6', 'SuperAdmin', NULL, NULL, NULL),
(3, 'Alice Johnson (Donor)', 'alice@example.com', '/4czbYQqQa0lZQ/q', 'Donor', 1, NULL, NULL),
(4, 'City Care Hospital Staff', 'hospital@citycare.org', '$/Dka.TQM54K1jyq0tUQDveXoKezM7v9FXbOvjLuR83qPNWo5An0d2', 'Hospital', NULL, 1, NULL);
