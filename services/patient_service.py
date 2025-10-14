from typing import List, Optional, Tuple
from mysql.connector import Error as MySQLError
from config.database import execute_query, execute_update
from models.patient import Patient, PatientCreate, PatientUpdate
from utils.exceptions import ResourceNotFoundException, DatabaseException


class PatientService:
    
    @staticmethod
    def create_patient(patient: PatientCreate) -> Patient:
        try:
            query = """
                INSERT INTO Patient 
                (Name, Age, Gender, Address, ContactNo, BloodGroupRequired, 
                 HospitalName, MedicalCondition, EmergencyContact)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            patient_id = execute_update(query, (
                patient.name, patient.age, patient.gender.value, patient.address,
                patient.contact_no, patient.blood_group_required, patient.hospital_name,
                patient.medical_condition, patient.emergency_contact
            ))
            return PatientService.get_patient(patient_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_patient(patient_id: int) -> Patient:
        try:
            query = "SELECT * FROM Patient WHERE PatientID = %s"
            result = execute_query(query, (patient_id,), fetch="one")
            if not result:
                raise ResourceNotFoundException("Patient", patient_id)
            return Patient(**{k.lower(): v for k, v in result.items()})
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_all_patients(
        hospital_name: Optional[str] = None,
        blood_group: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Patient], int]:
        try:
            where_clauses = []
            params = []
            
            if hospital_name:
                where_clauses.append("HospitalName = %s")
                params.append(hospital_name)
            if blood_group:
                where_clauses.append("BloodGroupRequired = %s")
                params.append(blood_group)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            count_query = f"SELECT COUNT(*) as total FROM Patient {where_sql}"
            total = execute_query(count_query, tuple(params), fetch="one")['total']
            
            query = f"SELECT * FROM Patient {where_sql} ORDER BY PatientID DESC LIMIT %s OFFSET %s"
            params.extend([limit, skip])
            results = execute_query(query, tuple(params))
            
            patients = [Patient(**{k.lower(): v for k, v in row.items()}) for row in results]
            return patients, total
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def update_patient(patient_id: int, update: PatientUpdate) -> Patient:
        try:
            PatientService.get_patient(patient_id)
            
            update_fields = []
            params = []
            
            for field, value in update.dict(exclude_unset=True).items():
                if value is not None:
                    db_field = ''.join(word.capitalize() for word in field.split('_'))
                    if field == "gender":
                        value = value.value
                    update_fields.append(f"{db_field} = %s")
                    params.append(value)
            
            if update_fields:
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