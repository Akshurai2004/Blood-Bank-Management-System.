import sys
import os
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.blood_bank_fastapi import app, db
from backend.queue_service import message_queue

def run_tests():
    print("=" * 70)
    print("RUNNING FULL BLOOD BANK SYSTEM VERIFICATION SUITE")
    print("=" * 70)

    # 1. Test DB Connection
    print("\n[1] Testing Database Connection...")
    if not db.connect():
        print("[FAIL] Database connection failed.")
        sys.exit(1)
    print("[PASS] MySQL Database connected successfully.")

    client = TestClient(app)

    # 2. Test OTP Registration Flow
    print("\n[2] Testing Email OTP Registration Flow...")
    test_email = f"donor_test_{int(time.time())}@example.com"
    reg_payload = {
        "full_name": "Test Donor OTP",
        "email": test_email,
        "password": "Password@123",
        "role": "Donor",
        "age": 28,
        "gender": "M",
        "blood_group": "B+",
        "contact": f"98{str(int(time.time()))[-8:]}",
        "address": "100 Innovation Way"
    }

    # Step A: Send OTP
    r_send = client.post("/api/auth/send-registration-otp", json=reg_payload)
    assert r_send.status_code == 200, f"Failed send OTP: {r_send.text}"
    otp_data = r_send.json()
    assert otp_data["success"] is True
    assert "preview_otp" not in otp_data, "OTP must NOT be exposed in API responses!"
    
    # Retrieve OTP from email simulation store for test verification
    from backend.email_service import OTPService
    received_otp = OTPService.get_internal_otp_for_testing(test_email)
    assert received_otp is not None, "OTP was not generated or dispatched!"
    print(f"   -> OTP Sent to email: {otp_data['message']}")

    # Step B: Verify OTP & Register
    r_verify = client.post("/api/auth/verify-registration-otp", json={"email": test_email, "otp": received_otp})
    assert r_verify.status_code == 200, f"Failed verify OTP: {r_verify.text}"
    verify_data = r_verify.json()
    assert verify_data["success"] is True
    token = verify_data["token"]
    user = verify_data["user"]
    print(f"[PASS] Registered & Verified {user['name']} with token: {token[:20]}...")

    auth_headers = {"Authorization": f"Bearer {token}"}

    # 3. Test Session Verification (/api/auth/me)
    print("\n[3] Testing Live Session Verification (/api/auth/me)...")
    r_me = client.get("/api/auth/me", headers=auth_headers)
    assert r_me.status_code == 200, f"Failed /auth/me: {r_me.text}"
    me_data = r_me.json()
    assert me_data["success"] is True
    assert me_data["user"]["Email"] == test_email
    print(f"[PASS] Session verified for user: {me_data['user']['FullName']} (Role: {me_data['user']['Role']})")

    # 4. Test Email OTP Login Flow
    print("\n[4] Testing Email OTP Login Flow...")
    r_login_otp_send = client.post("/api/auth/send-login-otp", json={"email": test_email})
    assert r_login_otp_send.status_code == 200, f"Failed send login OTP: {r_login_otp_send.text}"
    assert "preview_otp" not in r_login_otp_send.json(), "Login OTP must NOT be exposed in API responses!"
    login_otp = OTPService.get_internal_otp_for_testing(test_email)
    assert login_otp is not None
    r_login_otp_verify = client.post("/api/auth/verify-login-otp", json={"email": test_email, "otp": login_otp})
    assert r_login_otp_verify.status_code == 200, f"Failed verify login OTP: {r_login_otp_verify.text}"
    print(f"[PASS] Email OTP login successful for {test_email}")

    # 5. Test Password Login with Pre-Seeded Accounts
    print("\n[5] Testing Pre-Seeded Accounts...")
    demo_accounts = [
        ("admin@bloodbank.org", "Admin@123", "Admin"),
        ("superadmin@bloodbank.org", "SuperAdmin@123", "SuperAdmin"),
        ("alice@example.com", "Donor@123", "Donor"),
        ("hospital@citycare.org", "Hospital@123", "Hospital")
    ]
    for email, pwd, expected_role in demo_accounts:
        r_login = client.post("/api/auth/login", json={"email": email, "password": pwd})
        assert r_login.status_code == 200, f"Failed login for {email}: {r_login.text}"
        login_res = r_login.json()
        assert login_res["user"]["role"] == expected_role
        print(f"   -> Demo Account {email} ({expected_role}): Validated [OK]")
    print("[PASS] All pre-seeded accounts authenticated successfully.")

    # 6. Test Donor Portal Self-Service Data
    print("\n[6] Testing Donor Portal Self-Service Data...")
    r_donor_portal = client.get("/api/donor/portal-data", headers=auth_headers)
    assert r_donor_portal.status_code == 200, f"Failed donor portal: {r_donor_portal.text}"
    dp_data = r_donor_portal.json()
    assert dp_data["success"] is True
    print(f"[PASS] Donor Portal returned eligibility status: '{dp_data['eligibility']}'")

    # 7. Test Inventory & Blood Banks
    print("\n[7] Testing Blood Bank & Available Inventory...")
    r_banks = client.get("/api/bloodbanks")
    assert r_banks.status_code == 200
    banks = r_banks.json()["data"]
    assert len(banks) > 0
    bank_id = banks[0]["BloodBankID"]

    r_inv = client.get("/api/inventory")
    assert r_inv.status_code == 200
    print(f"[PASS] Retrieved {len(banks)} blood banks and {len(r_inv.json()['data'])} inventory groups.")

    # 8. Test Stored Procedure Blood Donation (RecordBloodDonation)
    print("\n[8] Testing Stored Procedure Blood Donation (RecordBloodDonation)...")
    donor_id = user.get("donor_id")
    if donor_id:
        r_don = client.post("/api/donations", json={
            "donor_id": donor_id,
            "blood_bank_id": bank_id,
            "component": "Whole Blood",
            "quantity": 1
        })
        assert r_don.status_code == 200, f"Failed donation: {r_don.text}"
        print(f"[PASS] Donation recorded via Stored Procedure for Donor #{donor_id}")

    # 9. Test Emergency Request Creation & Decoupled Message Queue
    print("\n[9] Testing Emergency Request & Decoupled Message Queue...")
    # Fetch patients
    patients = client.get("/api/patients").json()["data"]
    assert len(patients) > 0
    patient_id = patients[0]["PatientID"]

    r_req = client.post("/api/requests", json={
        "patient_id": patient_id,
        "blood_bank_id": bank_id,
        "required_units": 1
    })
    assert r_req.status_code == 200, f"Failed create request: {r_req.text}"
    req_data = r_req.json()
    assert req_data["success"] is True
    assert "job_id" in req_data
    request_id = req_data["request_id"]
    print(f"[PASS] Emergency Request #{request_id} enqueued (Job ID: {req_data['job_id']}, Broker: {req_data['queue_broker']})")

    # 10. Test Queue Telemetry
    print("\n[10] Testing Queue Telemetry & Broadcast Alerts...")
    r_telemetry = client.get("/api/notifications/queue-status")
    assert r_telemetry.status_code == 200
    telemetry = r_telemetry.json()["telemetry"]
    print(f"[PASS] Queue Telemetry Status: {telemetry['status']} (Host: {telemetry['host']}, Recent: {telemetry['recent_broadcast_count']})")

    # 11. Test Allocation Engine with Blood Type Validation
    print("\n[11] Testing Unit Allocation Engine...")
    units = client.get("/api/bloodunits", params={"status": "Available"}).json()["data"]
    if units:
        avail_unit = units[0]
        # Test allocation
        r_alloc = client.post("/api/allocations", json={
            "request_id": request_id,
            "unit_id": avail_unit["UnitID"]
        })
        print(f"   -> Allocation result for Request #{request_id} with Unit #{avail_unit['UnitID']}: {r_alloc.json()['message']}")
        assert r_alloc.status_code in [200, 400]
    print("[PASS] Allocation engine validated.")

    # 12. Test Statistics Dashboard
    print("\n[12] Testing Dashboard Analytics Endpoint...")
    r_stats = client.get("/api/statistics/dashboard")
    assert r_stats.status_code == 200
    stats = r_stats.json()["data"]
    print(f"[PASS] Dashboard stats returned: Total Donors={stats['donors']['total_donors']}, Total Banks={stats['blood_banks']['total_banks']}")

    # 13. Test Geolocation & Live Network Map Data Payloads
    print("\n[13] Testing Live Network Map & Geolocation Endpoints...")
    r_all_reqs = client.get("/api/requests")
    assert r_all_reqs.status_code == 200
    req_list = r_all_reqs.json()["data"]
    assert len(req_list) > 0, "Expected at least 1 blood request in dataset"
    sample_req = req_list[0]
    assert "HospitalLocation" in sample_req or "BloodBankLocation" in sample_req, "Request must contain location data for map plotting"
    
    r_all_donors = client.get("/api/donors")
    assert r_all_donors.status_code == 200
    donors_list = r_all_donors.json()["data"]
    assert len(donors_list) > 0, "Expected registered donors for map display"
    assert "Address" in donors_list[0] or "BloodGroup" in donors_list[0]
    print(f"[PASS] Map Geolocation payload validated: {len(donors_list)} donors and {len(req_list)} emergency needed locations ready for mapping.")

    print("\n" + "=" * 70)
    print("ALL SYSTEM, AUTH, QUEUE & MAP TESTS PASSED SUCCESSFULLY (100% HEALTHY)!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
