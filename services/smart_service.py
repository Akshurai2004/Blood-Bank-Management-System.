from typing import List
from mysql.connector import Error as MySQLError
from config.database import execute_procedure, execute_query
from utils.exceptions import DatabaseException, ResourceNotFoundException


class SmartService:
    
    @staticmethod
    def allocate_blood_smart(request_id: int) -> dict:
        """
        Smart blood allocation using stored procedure
        Returns allocation status and number of units allocated
        """
        try:
            results = execute_procedure("AllocateBloodSmart", (request_id, None, None))
            
            # The procedure sets OUT parameters, we need to fetch them
            query = """
                SELECT 
                    @p_status AS status,
                    @p_allocated_units AS allocated_units
            """
            result = execute_query(query, fetch="one")
            
            return {
                "request_id": request_id,
                "status": result.get('status', 'Unknown'),
                "allocated_units": result.get('allocated_units', 0),
                "message": f"Request {request_id} processed with status: {result.get('status', 'Unknown')}"
            }
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def process_pending_requests() -> dict:
        """
        Process all pending blood requests automatically
        """
        try:
            results = execute_procedure("ProcessPendingRequests", ())
            if results and len(results) > 0:
                return {
                    "success": True,
                    "message": results[0].get('Status', 'Requests processed')
                }
            return {"success": True, "message": "All pending requests processed"}
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_availability_report(blood_group: str = None) -> List[dict]:
        """
        Get blood availability report across all blood banks
        """
        try:
            results = execute_procedure("GetAvailabilityReport", (blood_group,))
            return results if results else []
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def find_compatible_blood(blood_type: str, required_units: int) -> List[dict]:
        """
        Find compatible blood sources for a specific blood type
        """
        try:
            results = execute_procedure("FindCompatibleBlood", (blood_type, required_units))
            return results if results else []
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def forecast_demand(days_back: int = 30) -> List[dict]:
        """
        Forecast blood demand based on historical data
        """
        try:
            results = execute_procedure("ForecastDemand", (days_back,))
            return results if results else []
        except MySQLError as e:
            raise DatabaseException(str(e))