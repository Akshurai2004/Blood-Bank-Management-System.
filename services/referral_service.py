from models.referral import Referral, ReferralCreate, ReferralUpdate
from config.database import execute_query, execute_update
from utils.exceptions import ResourceNotFoundException, DatabaseException
from typing import List
from mysql.connector import Error as MySQLError

class ReferralService:
    
    @staticmethod
    def create_referral(referral: ReferralCreate) -> Referral:
        try:
            query = """
                INSERT INTO Refers (DonorName, ReferredDonorName)
                VALUES (%s, %s)
            """
            execute_update(query, (referral.donor_name, referral.referred_donor_name))
            return ReferralService.get_referral(referral.donor_name, referral.referred_donor_name)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_referral(donor_name: str, referred_donor_name: str) -> Referral:
        try:
            query = "SELECT * FROM Refers WHERE DonorName = %s AND ReferredDonorName = %s"
            result = execute_query(query, (donor_name, referred_donor_name), fetch="one")
            if not result:
                raise ResourceNotFoundException("Referral", f"{donor_name} -> {referred_donor_name}")
            return Referral(**{k.lower(): v for k, v in result.items()})
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_donor_referrals(donor_name: str) -> List[Referral]:
        try:
            query = "SELECT * FROM Refers WHERE DonorName = %s ORDER BY ReferralDate DESC"
            results = execute_query(query, (donor_name,))
            return [Referral(**{k.lower(): v for k, v in row.items()}) for row in results]
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def update_referral(
        donor_name: str, 
        referred_donor_name: str, 
        update: ReferralUpdate
    ) -> Referral:
        try:
            query = "UPDATE Refers SET Status = %s WHERE DonorName = %s AND ReferredDonorName = %s"
            execute_update(query, (update.status.value, donor_name, referred_donor_name))
            return ReferralService.get_referral(donor_name, referred_donor_name)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def delete_referral(donor_name: str, referred_donor_name: str) -> dict:
        try:
            ReferralService.get_referral(donor_name, referred_donor_name)
            execute_update(
                "DELETE FROM Refers WHERE DonorName = %s AND ReferredDonorName = %s",
                (donor_name, referred_donor_name)
            )
            return {"success": True, "message": "Referral deleted"}
        except MySQLError as e:
            raise DatabaseException(str(e))
