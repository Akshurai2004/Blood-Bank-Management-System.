from typing import List, Optional, Tuple
from mysql.connector import Error as MySQLError
from config.database import execute_query, execute_update
from models.staff import Staff, StaffCreate, StaffUpdate, StaffRole
from utils.exceptions import ResourceNotFoundException, DatabaseException


class StaffService:
    
    @staticmethod
    def create_staff(staff: StaffCreate) -> Staff:
        try:
            query = """
                INSERT INTO Staff (Name, Role, SkillSet, ContactNo, Email)
                VALUES (%s, %s, %s, %s, %s)
            """
            staff_id = execute_update(query, (
                staff.name, staff.role.value, staff.skill_set,
                staff.contact_no, staff.email
            ))
            return StaffService.get_staff(staff_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_staff(staff_id: int) -> Staff:
        try:
            query = "SELECT * FROM Staff WHERE StaffID = %s"
            result = execute_query(query, (staff_id,), fetch="one")
            if not result:
                raise ResourceNotFoundException("Staff", staff_id)
            return Staff(**{k.lower(): v for k, v in result.items()})
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_all_staff(
        role: Optional[StaffRole] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Staff], int]:
        try:
            where_clauses = []
            params = []
            
            if role:
                where_clauses.append("Role = %s")
                params.append(role.value)
            if is_active is not None:
                where_clauses.append("IsActive = %s")
                params.append(is_active)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
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
