"""
Database Configuration Module
Handles MySQL connection pooling and session management
"""

import mysql.connector
from mysql.connector import pooling
from contextlib import contextmanager
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "SmartBloodDB"),
    "pool_name": "blood_bank_pool",
    "pool_size": 10,
    "pool_reset_session": True,
    "autocommit": False
}

# Create connection pool
try:
    connection_pool = pooling.MySQLConnectionPool(**DB_CONFIG)
    print("✅ Database connection pool created successfully")
except mysql.connector.Error as err:
    print(f"❌ Error creating connection pool: {err}")
    raise


@contextmanager
def get_db_connection() -> Generator:
    """
    Context manager for database connections
    Automatically handles connection acquisition and release
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Hospital")
            results = cursor.fetchall()
    """
    connection = None
    try:
        connection = connection_pool.get_connection()
        yield connection
    except mysql.connector.Error as err:
        if connection:
            connection.rollback()
        raise
    finally:
        if connection and connection.is_connected():
            connection.close()


def execute_query(query: str, params: tuple = None, fetch: str = "all") -> any:
    """
    Execute a SELECT query and return results
    
    Args:
        query: SQL query string
        params: Query parameters
        fetch: 'all', 'one', or 'none'
    
    Returns:
        Query results as list of dictionaries or single dictionary
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        if fetch == "all":
            result = cursor.fetchall()
        elif fetch == "one":
            result = cursor.fetchone()
        else:
            result = None
        
        cursor.close()
        return result


def execute_update(query: str, params: tuple = None) -> int:
    """
    Execute an INSERT, UPDATE, or DELETE query
    
    Args:
        query: SQL query string
        params: Query parameters
    
    Returns:
        Number of affected rows or last inserted ID
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        
        # Return last inserted ID for INSERT, row count for UPDATE/DELETE
        result = cursor.lastrowid if cursor.lastrowid > 0 else cursor.rowcount
        cursor.close()
        return result


def execute_procedure(proc_name: str, args: tuple = None) -> any:
    """
    Execute a stored procedure
    
    Args:
        proc_name: Stored procedure name
        args: Procedure arguments
    
    Returns:
        Procedure results
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc(proc_name, args or ())
        
        # Fetch all result sets
        results = []
        for result in cursor.stored_results():
            results.append(result.fetchall())
        
        conn.commit()
        cursor.close()
        return results[0] if len(results) == 1 else results


def test_connection() -> bool:
    """
    Test database connection
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False