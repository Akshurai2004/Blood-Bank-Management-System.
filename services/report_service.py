from config.database import execute_query, execute_procedure
from utils.exceptions import DatabaseException
from typing import List
from mysql.connector import Error as MySQLError

class ReportService:
    
    @staticmethod
    def get_inventory_stats() -> List[dict]:
        """
        Get current inventory statistics for all blood banks
        """
        try:
            query = """
                SELECT * FROM BloodInventoryStats 
                ORDER BY BloodBankName, BloodGroup
            """
            results = execute_query(query)
            return results
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def update_inventory_stats() -> dict:
        """
        Update inventory statistics (usually run as scheduled task)
        """
        try:
            results = execute_procedure("UpdateInventoryStats", ())
            return {
                "success": True,
                "message": results[0].get('Status', 'Statistics updated') if results else 'Updated'
            }
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_hospital_summary() -> List[dict]:
        """
        Get hospital-wise blood request summary
        """
        try:
            results = execute_procedure("GetHospitalRequestSummary", ())
            return results if results else []
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_campaign_performance(camp_id: int = None) -> List[dict]:
        """
        Get campaign performance report
        """
        try:
            results = execute_procedure("GetCampaignReport", (camp_id,))
            return results if results else []
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def analyze_donor_referrals() -> List[dict]:
        """
        Analyze donor referral network
        """
        try:
            results = execute_procedure("AnalyzeDonorReferrals", ())
            return results if results else []
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def analyze_performance() -> List[dict]:
        """
        Analyze system performance metrics
        """
        try:
            results = execute_procedure("AnalyzePerformance", ())
            return results if results else []
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_staff_assignments(hospital_name: str = None) -> List[dict]:
        """
        Get staff assignment report
        """
        try:
            results = execute_procedure("GetStaffAssignments", (hospital_name,))
            return results if results else []
        except MySQLError as e:
            raise DatabaseException(str(e))
