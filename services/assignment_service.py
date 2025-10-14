from models.assignment import Assignment, AssignmentCreate, AssignmentUpdate
from config.database import execute_query, execute_update
from utils.exceptions import ResourceNotFoundException, DatabaseException
from typing import List
from mysql.connector import Error as MySQLError


class AssignmentService:
    
    @staticmethod
    def create_assignment(assignment: AssignmentCreate) -> Assignment:
        try:
            query = "INSERT INTO AssignedTo (StaffID, HospitalName) VALUES (%s, %s)"
            execute_update(query, (assignment.staff_id, assignment.hospital_name))
            return AssignmentService.get_assignment(assignment.staff_id, assignment.hospital_name)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_assignment(staff_id: int, hospital_name: str) -> Assignment:
        try:
            query = "SELECT * FROM AssignedTo WHERE StaffID = %s AND HospitalName = %s"
            result = execute_query(query, (staff_id, hospital_name), fetch="one")
            if not result:
                raise ResourceNotFoundException("Assignment", f"Staff {staff_id} - {hospital_name}")
            return Assignment(**{k.lower(): v for k, v in result.items()})
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_staff_assignments(staff_id: int) -> List[Assignment]:
        try:
            query = "SELECT * FROM AssignedTo WHERE StaffID = %s ORDER BY AssignmentDate DESC"
            results = execute_query(query, (staff_id,))
            return [Assignment(**{k.lower(): v for k, v in row.items()}) for row in results]
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_hospital_staff(hospital_name: str) -> List[dict]:
        try:
            query = "SELECT * FROM HospitalStaffView WHERE HospitalName = %s"
            results = execute_query(query, (hospital_name,))
            return results
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def update_assignment(
        staff_id: int, 
        hospital_name: str, 
        update: AssignmentUpdate
    ) -> Assignment:
        try:
            query = "UPDATE AssignedTo SET Status = %s WHERE StaffID = %s AND HospitalName = %s"
            execute_update(query, (update.status.value, staff_id, hospital_name))
            return AssignmentService.get_assignment(staff_id, hospital_name)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def delete_assignment(staff_id: int, hospital_name: str) -> dict:
        try:
            AssignmentService.get_assignment(staff_id, hospital_name)
            execute_update(
                "DELETE FROM AssignedTo WHERE StaffID = %s AND HospitalName = %s",
                (staff_id, hospital_name)
            )
            return {"success": True, "message": "Assignment deleted"}
        except MySQLError as e:
            raise DatabaseException(str(e))
                params.append(patient_id)
                query = f"UPDATE Patient SET {', '.join(update_fields)} WHERE PatientID = %s"
                execute_update(query, tuple(params))
            
            return PatientService.get_patient(patient_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def delete_patient(patient_id: int) -> dict:
        try:
            PatientService.get_patient(patient_id)
            execute_update("DELETE FROM Patient WHERE PatientID = %s", (patient_id,))
            return {"success": True, "message": f"Patient {patient_id} deleted"}
        except MySQLError as e:
            raise DatabaseException(str(e))
