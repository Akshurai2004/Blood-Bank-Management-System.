"""
Database Initialization & Migration CLI Script
Usage:
    python backend/init_db.py [optional_sql_file]
    python -m backend.init_db [optional_sql_file]

Examples:
    python -m backend.init_db
    python -m backend.init_db render.sql

Initializes PostgreSQL schema, views, and seed records on a local or cloud server.
"""

import os
import sys

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from dotenv import load_dotenv
    # Load .env from project root or backend folder
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    load_dotenv(os.path.join(CURRENT_DIR, ".env"))
except ImportError:
    pass

try:
    from backend.blood_bank_backend import BloodBankDB
except ImportError:
    from blood_bank_backend import BloodBankDB


def init_database(sql_file: str = None):
    print("=" * 65)
    print("      BLOOD BANK MANAGEMENT SYSTEM - DATABASE INITIALIZER")
    print("=" * 65)

    db = BloodBankDB()
    info = db.get_connection_info()
    print(f"Target PostgreSQL Host : {info['host']}:{info['port']}")
    print(f"Database Name     : {info['database']}")
    print(f"User              : {info['user']}")
    print(f"SSL Enabled       : {info['ssl_enabled']}")
    print("-" * 65)
    print("Connecting to PostgreSQL server...")

    if not db.connect():
        print("[ERROR] Failed to establish connection to PostgreSQL server.")
        print("Please verify DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME")
        print("or ensure DATABASE_URL is set correctly in your environment.")
        sys.exit(1)

    print("[OK] Connected to PostgreSQL server.")

    # Target specific SQL file if given
    target_file = sql_file or (sys.argv[1] if len(sys.argv) > 1 else None)
    if target_file and os.path.exists(target_file):
        print(f"Executing SQL script: {target_file}...")
        success = db.execute_sql_file(target_file)
    else:
        # Default schema initialization (automatically uses render.sql if found)
        print("Applying schema DDL (tables, views, indexes, triggers)...")
        success = db.init_schema()

    if not success:
        print("[ERROR] Database schema initialization failed.")
        db.disconnect()
        sys.exit(1)

    print("[OK] Schema initialization and seeding complete!\n")

    # Verify counts
    tables_to_check = ["Hospital", "BloodBank", "Donor", "BloodUnit", "Patient", "Request", "User"]
    print("Table Verification Summary:")
    print("-" * 40)
    for tbl in tables_to_check:
        res = db.fetch_query(f"SELECT COUNT(*) as cnt FROM {tbl}")
        count = res[0]["cnt"] if res else 0
        print(f"  - {tbl:<15}: {count} records")

    print("-" * 40)
    print("Default Demo Accounts Ready:")
    print("  * Admin:       admin@bloodbank.org       / Admin@123")
    print("  * SuperAdmin:  superadmin@bloodbank.org  / SuperAdmin@123")
    print("  * Donor:       alice@example.com         / Donor@123")
    print("  * Hospital:    hospital@citycare.org     / Hospital@123")
    print("=" * 65)

    db.disconnect()
    print("[SUCCESS] PostgreSQL database is initialized and ready for deployment!\n")


if __name__ == "__main__":
    init_database()
