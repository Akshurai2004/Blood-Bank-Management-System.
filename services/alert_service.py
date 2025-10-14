from models.alert import Alert, AlertType, Severity
from config.database import execute_query, execute_update
from utils.exceptions import ResourceNotFoundException, DatabaseException
from typing import List, Optional, Tuple
from mysql.connector import Error as MySQLError

class AlertService:
    
    @staticmethod
    def get_alert(alert_id: int) -> Alert:
        try:
            query = "SELECT * FROM AlertNotification WHERE AlertID = %s"
            result = execute_query(query, (alert_id,), fetch="one")
            if not result:
                raise ResourceNotFoundException("Alert", alert_id)
            return Alert(**{k.lower(): v for k, v in result.items()})
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_all_alerts(
        alert_type: Optional[AlertType] = None,
        severity: Optional[Severity] = None,
        is_read: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Alert], int]:
        try:
            where_clauses = []
            params = []
            
            if alert_type:
                where_clauses.append("AlertType = %s")
                params.append(alert_type.value)
            if severity:
                where_clauses.append("Severity = %s")
                params.append(severity.value)
            if is_read is not None:
                where_clauses.append("IsRead = %s")
                params.append(is_read)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            count_query = f"SELECT COUNT(*) as total FROM AlertNotification {where_sql}"
            total = execute_query(count_query, tuple(params), fetch="one")['total']
            
            query = f"SELECT * FROM AlertNotification {where_sql} ORDER BY CreatedAt DESC LIMIT %s OFFSET %s"
            params.extend([limit, skip])
            results = execute_query(query, tuple(params))
            
            alerts = [Alert(**{k.lower(): v for k, v in row.items()}) for row in results]
            return alerts, total
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def mark_as_read(alert_id: int) -> Alert:
        try:
            query = "UPDATE AlertNotification SET IsRead = TRUE, ReadAt = NOW() WHERE AlertID = %s"
            execute_update(query, (alert_id,))
            return AlertService.get_alert(alert_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def delete_alert(alert_id: int) -> dict:
        try:
            AlertService.get_alert(alert_id)
            execute_update("DELETE FROM AlertNotification WHERE AlertID = %s", (alert_id,))
            return {"success": True, "message": f"Alert {alert_id} deleted"}
        except MySQLError as e:
            raise DatabaseException(str(e))

