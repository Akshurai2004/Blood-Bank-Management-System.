from typing import List, Optional
from mysql.connector import Error as MySQLError

from config.database import execute_query, execute_update
from models.hospital import Hospital, HospitalCreate, HospitalUpdate
from utils.exceptions import (
    ResourceNotFoundException, 
    ResourceAlreadyExistsException,
    DatabaseException
)


class HospitalService:
    """Service class for Hospital operations"""
    
    @staticmethod
    def create_hospital(hospital: HospitalCreate) -> Hospital:
        """Create a new hospital"""
        try:
            # Check if hospital already exists
            existing = execute_query(
                "SELECT HospitalName FROM Hospital WHERE HospitalName = %s",
                (hospital.hospital_name,),
                fetch="one"
            )
            
            if existing:
                raise ResourceAlreadyExistsException("Hospital", hospital.hospital_name)
            
            # Insert hospital
            query = """
                INSERT INTO Hospital (HospitalName, Location, ContactNo, Email)
                VALUES (%s, %s, %s, %s)
            """
            execute_update(query, (
                hospital.hospital_name,
                hospital.location,
                hospital.contact_no,
                hospital.email
            ))
            
            return HospitalService.get_hospital(hospital.hospital_name)
            
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    
    @staticmethod
    def get_hospital(hospital_name: str) -> Hospital:
        """Get hospital by name"""
        try:
            query = "SELECT * FROM Hospital WHERE HospitalName = %s"
            result = execute_query(query, (hospital_name,), fetch="one")
            
            if not result:
                raise ResourceNotFoundException("Hospital", hospital_name)
            
            return Hospital(
                hospital_name=result['HospitalName'],
                location=result['Location'],
                contact_no=result['ContactNo'],
                email=result.get('Email')
            )
            
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    
    @staticmethod
    def get_all_hospitals(
        location: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Hospital], int]:
        """Get all hospitals with optional filters"""
        try:
            # Build query
            where_clauses = []
            params = []
            
            if location:
                where_clauses.append("Location LIKE %s")
                params.append(f"%{location}%")
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM Hospital {where_sql}"
            count_result = execute_query(count_query, tuple(params), fetch="one")
            total = count_result['total']
            
            # Get paginated results
            query = f"""
                SELECT * FROM Hospital 
                {where_sql}
                ORDER BY HospitalName
                LIMIT %s OFFSET %s
            """
            params.extend([limit, skip])
            results = execute_query(query, tuple(params))
            
            hospitals = [
                Hospital(
                    hospital_name=row['HospitalName'],
                    location=row['Location'],
                    contact_no=row['ContactNo'],
                    email=row.get('Email')
                )
                for row in results
            ]
            
            return hospitals, total
            
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    
    @staticmethod
    def update_hospital(hospital_name: str, hospital_update: HospitalUpdate) -> Hospital:
        """Update hospital details"""
        try:
            # Check if hospital exists
            HospitalService.get_hospital(hospital_name)
            
            # Build update query dynamically
            update_fields = []
            params = []
            
            if hospital_update.location is not None:
                update_fields.append("Location = %s")
                params.append(hospital_update.location)
            
            if hospital_update.contact_no is not None:
                update_fields.append("ContactNo = %s")
                params.append(hospital_update.contact_no)
            
            if hospital_update.email is not None:
                update_fields.append("Email = %s")
                params.append(hospital_update.email)
            
            if not update_fields:
                return HospitalService.get_hospital(hospital_name)
            
            params.append(hospital_name)
            query = f"""
                UPDATE Hospital 
                SET {', '.join(update_fields)}
                WHERE HospitalName = %s
            """
            
            execute_update(query, tuple(params))
            
            return HospitalService.get_hospital(hospital_name)
            
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    
    @staticmethod
    def delete_hospital(hospital_name: str) -> dict:
        """Delete a hospital"""
        try:
            # Check if hospital exists
            HospitalService.get_hospital(hospital_name)
            
            # Delete hospital (will fail if there are foreign key constraints)
            query = "DELETE FROM Hospital WHERE HospitalName = %s"
            affected_rows = execute_update(query, (hospital_name,))
            
            if affected_rows == 0:
                raise DatabaseException("Hospital could not be deleted. It may have associated records.")
            
            return {
                "success": True,
                "message": f"Hospital '{hospital_name}' deleted successfully"
            }
            
        except MySQLError as e:
            if "foreign key constraint" in str(e).lower():
                raise DatabaseException(
                    f"Cannot delete hospital '{hospital_name}'. "
                    "It has associated patients, staff, or other records."
                )
            raise DatabaseException(str(e))
    
    
    @staticmethod
    def get_hospital_stats(hospital_name: str) -> dict:
        """Get statistics for a hospital"""
        try:
            # Check if hospital exists
            HospitalService.get_hospital(hospital_name)
            
            query = """
                SELECT 
                    h.HospitalName,
                    h.Location,
                    COUNT(DISTINCT p.PatientID) as TotalPatients,
                    COUNT(DISTINCT r.RequestID) as TotalRequests,
                    COUNT(DISTINCT a.StaffID) as TotalStaff,
                    SUM(CASE WHEN req.Status = 'Fulfilled' THEN 1 ELSE 0 END) as FulfilledRequests,
                    SUM(CASE WHEN req.Status = 'Pending' THEN 1 ELSE 0 END) as PendingRequests
                FROM Hospital h
                LEFT JOIN Patient p ON h.HospitalName = p.HospitalName
                LEFT JOIN Request req ON p.Name = req.PatientName
                LEFT JOIN AssignedTo a ON h.HospitalName = a.HospitalName AND a.Status = 'Active'
                WHERE h.HospitalName = %s
                GROUP BY h.HospitalName, h.Location
            """
            
            result = execute_query(query, (hospital_name,), fetch="one")
            
            return {
                "hospital_name": result['HospitalName'],
                "location": result['Location'],
                "total_patients": result['TotalPatients'] or 0,
                "total_requests": result['TotalRequests'] or 0,
                "total_staff": result['TotalStaff'] or 0,
                "fulfilled_requests": result['FulfilledRequests'] or 0,
                "pending_requests": result['PendingRequests'] or 0
            }
            
        except MySQLError as e:
            raise DatabaseException(str(e))