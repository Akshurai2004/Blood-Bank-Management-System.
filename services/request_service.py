from models.request import Request, RequestCreate, RequestUpdate, RequestStatus, UrgencyLevel
from config.database import execute_query, execute_update
from utils.exceptions import ResourceNotFoundException, DatabaseException
from typing import List, Optional, Tuple
from mysql.connector import Error as MySQLError


class RequestService:
    
    @staticmethod
    def create_request(request: RequestCreate) -> Request:
        try:
            query = """
                INSERT INTO Request 
                (PatientName, BloodBankName, RequiredUnits, UrgencyLevel, RequestedBy, Notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            request_id = execute_update(query, (
                request.patient_name, request.bloodbank_name, request.required_units,
                request.urgency_level.value, request.requested_by, request.notes
            ))
            return RequestService.get_request(request_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_request(request_id: int) -> Request:
        try:
            query = "SELECT * FROM Request WHERE RequestID = %s"
            result = execute_query(query, (request_id,), fetch="one")
            if not result:
                raise ResourceNotFoundException("Request", request_id)
            return Request(**{k.lower(): v for k, v in result.items()})
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_all_requests(
        status: Optional[RequestStatus] = None,
        urgency: Optional[UrgencyLevel] = None,
        bloodbank_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Request], int]:
        try:
            where_clauses = []
            params = []
            
            if status:
                where_clauses.append("Status = %s")
                params.append(status.value)
            if urgency:
                where_clauses.append("UrgencyLevel = %s")
                params.append(urgency.value)
            if bloodbank_name:
                where_clauses.append("BloodBankName = %s")
                params.append(bloodbank_name)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            count_query = f"SELECT COUNT(*) as total FROM Request {where_sql}"
            total = execute_query(count_query, tuple(params), fetch="one")['total']
            
            query = f"""
                SELECT * FROM Request {where_sql} 
                ORDER BY Priority DESC, RequestDate DESC 
                LIMIT %s OFFSET %s
            """
            params.extend([limit, skip])
            results = execute_query(query, tuple(params))
            
            requests = [Request(**{k.lower(): v for k, v in row.items()}) for row in results]
            return requests, total
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def update_request(request_id: int, update: RequestUpdate) -> Request:
        try:
            RequestService.get_request(request_id)
            
            update_fields = []
            params = []
            
            for field, value in update.dict(exclude_unset=True).items():
                if value is not None:
                    db_field = ''.join(word.capitalize() for word in field.split('_'))
                    if field in ["status", "urgency_level"]:
                        value = value.value
                    update_fields.append(f"{db_field} = %s")
                    params.append(value)
            
            if update_fields:
                params.append(request_id)
                query = f"UPDATE Request SET {', '.join(update_fields)} WHERE RequestID = %s"
                execute_update(query, tuple(params))
            
            return RequestService.get_request(request_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def delete_request(request_id: int) -> dict:
        try:
            RequestService.get_request(request_id)
            execute_update("DELETE FROM Request WHERE RequestID = %s", (request_id,))
            return {"success": True, "message": f"Request {request_id} deleted"}
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_pending_requests() -> List[Request]:
        try:
            query = "SELECT * FROM PendingRequests ORDER BY Priority DESC, RequestDate ASC"
            results = execute_query(query)
            return [Request(**{k.lower(): v for k, v in row.items()}) for row in results]
        except MySQLError as e:
            raise DatabaseException(str(e))
