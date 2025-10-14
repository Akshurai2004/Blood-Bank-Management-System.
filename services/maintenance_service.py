from config.database import execute_procedure, execute_query
from utils.exceptions import DatabaseException
from typing import List
from mysql.connector import Error as MySQLError

class MaintenanceService:
    
    @staticmethod
    def run_daily_maintenance() -> dict:
        """
        Run all daily maintenance tasks
        """
        try:
            results = execute_procedure("DailyMaintenance", ())
            if results and len(results) > 0:
                return {
                    "success": True,
                    "message": results[0].get('MaintenanceCompleted', 'Maintenance completed'),
                    "completed_at": results[0].get('CompletedAt')
                }
            return {"success": True, "message": "Daily maintenance completed"}
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def mark_expired_units() -> dict:
        """
        Mark expired blood units
        """
        try:
            results = execute_procedure("MarkExpiredUnits", ())
            if results and len(results) > 0:
                return {
                    "success": True,
                    "message": results[0].get('Status', 'Expired units marked')
                }
            return {"success": True, "message": "Expired units processed"}
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def generate_expiry_alerts() -> dict:
        """
        Generate alerts for expiring blood units
        """
        try:
            results = execute_procedure("GenerateExpiryAlerts", ())
            if results and len(results) > 0:
                return {
                    "success": True,
                    "message": results[0].get('Status', 'Expiry alerts generated')
                }
            return {"success": True, "message": "Expiry alerts generated"}
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def update_inventory_statistics() -> dict:
        """
        Update inventory statistics
        """
        try:
            results = execute_procedure("UpdateInventoryStats", ())
            if results and len(results) > 0:
                return {
                    "success": True,
                    "message": results[0].get('Status', 'Inventory stats updated')
                }
            return {"success": True, "message": "Inventory statistics updated"}
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_expiry_alerts() -> List[dict]:
        """
        Get all expiry alerts from view
        """
        try:
            query = """
                SELECT * FROM ExpiryAlerts 
                ORDER BY DaysUntilExpiry ASC
            """
            results = execute_query(query)
            return results
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def cleanup_old_logs(days: int = 30) -> dict:
        """
        Cleanup old performance logs
        """
        try:
            query = """
                DELETE FROM QueryPerformanceLog 
                WHERE RunDate < DATE_SUB(NOW(), INTERVAL %s DAY)
            """
            from config.database import execute_update
            rows = execute_update(query, (days,))
            return {
                "success": True,
                "message": f"Deleted {rows} old log entries"
            }
        except MySQLError as e:
            raise DatabaseException(str(e))