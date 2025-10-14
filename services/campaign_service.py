from models.campaign import Campaign, CampaignCreate, CampaignUpdate, CampaignStatus
from config.database import execute_query, execute_update
from utils.exceptions import ResourceNotFoundException, DatabaseException
from typing import List, Optional, Tuple
from mysql.connector import Error as MySQLError


class CampaignService:
    
    @staticmethod
    def create_campaign(campaign: CampaignCreate) -> Campaign:
        try:
            query = """
                INSERT INTO Campaign 
                (CampaignName, Location, Date, StartTime, EndTime, OrganizedBy, 
                 TargetDonors, BloodBankName)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            camp_id = execute_update(query, (
                campaign.campaign_name, campaign.location, campaign.date,
                campaign.start_time, campaign.end_time, campaign.organized_by,
                campaign.target_donors, campaign.bloodbank_name
            ))
            return CampaignService.get_campaign(camp_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_campaign(camp_id: int) -> Campaign:
        try:
            query = "SELECT * FROM Campaign WHERE CampID = %s"
            result = execute_query(query, (camp_id,), fetch="one")
            if not result:
                raise ResourceNotFoundException("Campaign", camp_id)
            return Campaign(**{k.lower(): v for k, v in result.items()})
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_all_campaigns(
        status: Optional[CampaignStatus] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Campaign], int]:
        try:
            where_clauses = []
            params = []
            
            if status:
                where_clauses.append("Status = %s")
                params.append(status.value)
            if start_date:
                where_clauses.append("Date >= %s")
                params.append(start_date)
            if end_date:
                where_clauses.append("Date <= %s")
                params.append(end_date)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            count_query = f"SELECT COUNT(*) as total FROM Campaign {where_sql}"
            total = execute_query(count_query, tuple(params), fetch="one")['total']
            
            query = f"SELECT * FROM Campaign {where_sql} ORDER BY Date DESC LIMIT %s OFFSET %s"
            params.extend([limit, skip])
            results = execute_query(query, tuple(params))
            
            campaigns = [Campaign(**{k.lower(): v for k, v in row.items()}) for row in results]
            return campaigns, total
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def update_campaign(camp_id: int, update: CampaignUpdate) -> Campaign:
        try:
            CampaignService.get_campaign(camp_id)
            
            update_fields = []
            params = []
            
            for field, value in update.dict(exclude_unset=True).items():
                if value is not None:
                    db_field = ''.join(word.capitalize() for word in field.split('_'))
                    if field == "status":
                        value = value.value
                    update_fields.append(f"{db_field} = %s")
                    params.append(value)
            
            if update_fields:
                params.append(camp_id)
                query = f"UPDATE Campaign SET {', '.join(update_fields)} WHERE CampID = %s"
                execute_update(query, tuple(params))
            
            return CampaignService.get_campaign(camp_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def delete_campaign(camp_id: int) -> dict:
        try:
            CampaignService.get_campaign(camp_id)
            execute_update("DELETE FROM Campaign WHERE CampID = %s", (camp_id,))
            return {"success": True, "message": f"Campaign {camp_id} deleted"}
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_campaign_performance(camp_id: int) -> dict:
        try:
            query = "CALL GetCampaignReport(%s)"
            result = execute_query(query, (camp_id,), fetch="one")
            if not result:
                raise ResourceNotFoundException("Campaign", camp_id)
            return result
        except MySQLError as e:
            raise DatabaseException(str(e))
