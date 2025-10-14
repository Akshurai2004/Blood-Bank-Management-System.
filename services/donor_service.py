from models.donor import Donor, DonorCreate, DonorUpdate, DonorEligibility
from config.database import execute_procedure
from config.database import execute_query, execute_update
from utils.exceptions import ResourceNotFoundException, DatabaseException
from typing import List, Optional, Tuple
from mysql.connector import Error as MySQLError



class DonorService:
    
    @staticmethod
    def create_donor(donor: DonorCreate) -> Donor:
        try:
            query = """
                INSERT INTO Donor 
                (DonorName, Age, Gender, BloodGroup, ContactNo, Email, Address, CampID)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            execute_update(query, (
                donor.donor_name, donor.age, donor.gender.value, donor.blood_group,
                donor.contact_no, donor.email, donor.address, donor.camp_id
            ))
            return DonorService.get_donor(donor.donor_name)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_donor(donor_name: str) -> Donor:
        try:
            query = "SELECT * FROM Donor WHERE DonorName = %s"
            result = execute_query(query, (donor_name,), fetch="one")
            if not result:
                raise ResourceNotFoundException("Donor", donor_name)
            return Donor(**{k.lower(): v for k, v in result.items()})
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_all_donors(
        blood_group: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Donor], int]:
        try:
            where_clauses = []
            params = []
            
            if blood_group:
                where_clauses.append("BloodGroup = %s")
                params.append(blood_group)
            if is_active is not None:
                where_clauses.append("IsActive = %s")
                params.append(is_active)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            count_query = f"SELECT COUNT(*) as total FROM Donor {where_sql}"
            total = execute_query(count_query, tuple(params), fetch="one")['total']
            
            query = f"SELECT * FROM Donor {where_sql} ORDER BY DonorName LIMIT %s OFFSET %s"
            params.extend([limit, skip])
            results = execute_query(query, tuple(params))
            
            donors = [Donor(**{k.lower(): v for k, v in row.items()}) for row in results]
            return donors, total
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def update_donor(donor_name: str, update: DonorUpdate) -> Donor:
        try:
            DonorService.get_donor(donor_name)
            
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
                params.append(donor_name)
                query = f"UPDATE Donor SET {', '.join(update_fields)} WHERE DonorName = %s"
                execute_update(query, tuple(params))
            
            return DonorService.get_donor(donor_name)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def delete_donor(donor_name: str) -> dict:
        try:
            DonorService.get_donor(donor_name)
            execute_update("DELETE FROM Donor WHERE DonorName = %s", (donor_name,))
            return {"success": True, "message": f"Donor '{donor_name}' deleted"}
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def deactivate_donor(donor_name: str) -> Donor:
        try:
            execute_update("UPDATE Donor SET IsActive = FALSE WHERE DonorName = %s", (donor_name,))
            return DonorService.get_donor(donor_name)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def check_eligibility(donor_name: str) -> DonorEligibility:
        try:
            results = execute_procedure("CheckDonorEligibility", (donor_name,))
            if not results or len(results) == 0:
                raise ResourceNotFoundException("Donor", donor_name)
            
            result = results[0]
            return DonorEligibility(**{k.lower(): v for k, v in result.items()})
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_donor_statistics(donor_name: str) -> dict:
        try:
            query = "SELECT * FROM DonorStatistics WHERE DonorName = %s"
            result = execute_query(query, (donor_name,), fetch="one")
            if not result:
                raise ResourceNotFoundException("Donor", donor_name)
            return result
        except MySQLError as e:
            raise DatabaseException(str(e))uses else ""
            
            count_query = f"SELECT COUNT(*) as total FROM Staff {where_sql}"
            total = execute_query(count_query, tuple(params), fetch="one")['total']
            
            query = f"SELECT * FROM Staff {where_sql} ORDER BY StaffID LIMIT %s OFFSET %s"
            params.extend([limit, skip])
            results = execute_query(query, tuple(params))
            
            staff_list = [Staff(**{k.lower(): v for k, v in row.items()}) for row in results]
            return staff_list, total
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def update_staff(staff_id: int, staff_update: StaffUpdate) -> Staff:
        try:
            StaffService.get_staff(staff_id)
            
            update_fields = []
            params = []
            
            for field, value in staff_update.dict(exclude_unset=True).items():
                if value is not None:
                    db_field = ''.join(word.capitalize() for word in field.split('_'))
                    if field == "role":
                        value = value.value
                    update_fields.append(f"{db_field} = %s")
                    params.append(value)
            
            if not update_fields:
                return StaffService.get_staff(staff_id)
            
            params.append(staff_id)
            query = f"UPDATE Staff SET {', '.join(update_fields)} WHERE StaffID = %s"
            execute_update(query, tuple(params))
            
            return StaffService.get_staff(staff_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def delete_staff(staff_id: int) -> dict:
        try:
            StaffService.get_staff(staff_id)
            execute_update("DELETE FROM Staff WHERE StaffID = %s", (staff_id,))
            return {"success": True, "message": f"Staff {staff_id} deleted successfully"}
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def deactivate_staff(staff_id: int) -> Staff:
        try:
            execute_update("UPDATE Staff SET IsActive = FALSE WHERE StaffID = %s", (staff_id,))
            return StaffService.get_staff(staff_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
