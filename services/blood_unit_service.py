from models.blood_unit import BloodUnit, BloodUnitCreate, BloodUnitUpdate, BloodUnitStatus
from config.database import execute_query, execute_update
from utils.exceptions import ResourceNotFoundException, DatabaseException
from typing import List, Optional, Tuple
from mysql.connector import Error as MySQLError


class BloodUnitService:
    
    @staticmethod
    def create_blood_unit(unit: BloodUnitCreate) -> BloodUnit:
        try:
            query = """
                INSERT INTO BloodUnit 
                (DonorName, BloodBankName, BloodGroup, Quantity, CollectionDate, 
                 ExpirationDate, Component, StorageLocation, TransactionID)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            unit_id = execute_update(query, (
                unit.donor_name, unit.bloodbank_name, unit.blood_group, unit.quantity,
                unit.collection_date, unit.expiration_date, unit.component.value,
                unit.storage_location, unit.transaction_id
            ))
            return BloodUnitService.get_blood_unit(unit_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_blood_unit(unit_id: int) -> BloodUnit:
        try:
            query = "SELECT * FROM BloodUnit WHERE UnitID = %s"
            result = execute_query(query, (unit_id,), fetch="one")
            if not result:
                raise ResourceNotFoundException("BloodUnit", unit_id)
            return BloodUnit(**{k.lower(): v for k, v in result.items()})
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_all_blood_units(
        blood_group: Optional[str] = None,
        status: Optional[BloodUnitStatus] = None,
        bloodbank_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[BloodUnit], int]:
        try:
            where_clauses = []
            params = []
            
            if blood_group:
                where_clauses.append("BloodGroup = %s")
                params.append(blood_group)
            if status:
                where_clauses.append("Status = %s")
                params.append(status.value)
            if bloodbank_name:
                where_clauses.append("BloodBankName = %s")
                params.append(bloodbank_name)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            count_query = f"SELECT COUNT(*) as total FROM BloodUnit {where_sql}"
            total = execute_query(count_query, tuple(params), fetch="one")['total']
            
            query = f"SELECT * FROM BloodUnit {where_sql} ORDER BY ExpirationDate ASC LIMIT %s OFFSET %s"
            params.extend([limit, skip])
            results = execute_query(query, tuple(params))
            
            units = [BloodUnit(**{k.lower(): v for k, v in row.items()}) for row in results]
            return units, total
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def update_blood_unit(unit_id: int, update: BloodUnitUpdate) -> BloodUnit:
        try:
            BloodUnitService.get_blood_unit(unit_id)
            
            update_fields = []
            params = []
            
            for field, value in update.dict(exclude_unset=True).items():
                if value is not None:
                    db_field = ''.join(word.capitalize() for word in field.split('_'))
                    if field in ["status", "test_status"]:
                        value = value.value
                    update_fields.append(f"{db_field} = %s")
                    params.append(value)
            
            if update_fields:
                params.append(unit_id)
                query = f"UPDATE BloodUnit SET {', '.join(update_fields)} WHERE UnitID = %s"
                execute_update(query, tuple(params))
            
            return BloodUnitService.get_blood_unit(unit_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def delete_blood_unit(unit_id: int) -> dict:
        try:
            BloodUnitService.get_blood_unit(unit_id)
            execute_update("DELETE FROM BloodUnit WHERE UnitID = %s", (unit_id,))
            return {"success": True, "message": f"Blood unit {unit_id} deleted"}
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_expiring_soon(days: int = 7) -> List[BloodUnit]:
        try:
            query = """
                SELECT * FROM BloodUnit 
                WHERE Status = 'Available' 
                  AND TestStatus = 'Cleared'
                  AND ExpirationDate > CURDATE()
                  AND DATEDIFF(ExpirationDate, CURDATE()) <= %s
                ORDER BY ExpirationDate ASC
            """
            results = execute_query(query, (days,))
            return [BloodUnit(**{k.lower(): v for k, v in row.items()}) for row in results]
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_available_inventory() -> List[dict]:
        try:
            query = "SELECT * FROM AvailableBloodInventory ORDER BY BloodBankName, BloodGroup"
            results = execute_query(query)
            return results
        except MySQLError as e:
            raise DatabaseException(str(e))
