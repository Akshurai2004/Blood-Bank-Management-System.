from models.transaction import Transaction, TransactionCreate, TransactionUpdate, TransactionType
from config.database import execute_query, execute_update
from utils.exceptions import ResourceNotFoundException, DatabaseException
from typing import List, Optional, Tuple
from mysql.connector import Error as MySQLError

class TransactionService:
    
    @staticmethod
    def create_transaction(transaction: TransactionCreate) -> Transaction:
        try:
            query = """
                INSERT INTO Transaction 
                (DonorName, BloodBankName, TransactionType, Quantity, Notes)
                VALUES (%s, %s, %s, %s, %s)
            """
            transaction_id = execute_update(query, (
                transaction.donor_name, transaction.bloodbank_name,
                transaction.transaction_type.value, transaction.quantity, transaction.notes
            ))
            return TransactionService.get_transaction(transaction_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_transaction(transaction_id: int) -> Transaction:
        try:
            query = "SELECT * FROM Transaction WHERE TransactionID = %s"
            result = execute_query(query, (transaction_id,), fetch="one")
            if not result:
                raise ResourceNotFoundException("Transaction", transaction_id)
            return Transaction(**{k.lower(): v for k, v in result.items()})
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def get_all_transactions(
        transaction_type: Optional[TransactionType] = None,
        donor_name: Optional[str] = None,
        bloodbank_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Transaction], int]:
        try:
            where_clauses = []
            params = []
            
            if transaction_type:
                where_clauses.append("TransactionType = %s")
                params.append(transaction_type.value)
            if donor_name:
                where_clauses.append("DonorName = %s")
                params.append(donor_name)
            if bloodbank_name:
                where_clauses.append("BloodBankName = %s")
                params.append(bloodbank_name)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            count_query = f"SELECT COUNT(*) as total FROM Transaction {where_sql}"
            total = execute_query(count_query, tuple(params), fetch="one")['total']
            
            query = f"SELECT * FROM Transaction {where_sql} ORDER BY DateOfDonation DESC LIMIT %s OFFSET %s"
            params.extend([limit, skip])
            results = execute_query(query, tuple(params))
            
            transactions = [Transaction(**{k.lower(): v for k, v in row.items()}) for row in results]
            return transactions, total
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def update_transaction(transaction_id: int, update: TransactionUpdate) -> Transaction:
        try:
            TransactionService.get_transaction(transaction_id)
            
            update_fields = []
            params = []
            
            for field, value in update.dict(exclude_unset=True).items():
                if value is not None:
                    db_field = ''.join(word.capitalize() for word in field.split('_'))
                    if field == "transaction_type":
                        value = value.value
                    update_fields.append(f"{db_field} = %s")
                    params.append(value)
            
            if update_fields:
                params.append(transaction_id)
                query = f"UPDATE Transaction SET {', '.join(update_fields)} WHERE TransactionID = %s"
                execute_update(query, tuple(params))
            
            return TransactionService.get_transaction(transaction_id)
        except MySQLError as e:
            raise DatabaseException(str(e))
    
    @staticmethod
    def delete_transaction(transaction_id: int) -> dict:
        try:
            TransactionService.get_transaction(transaction_id)
            execute_update("DELETE FROM Transaction WHERE TransactionID = %s", (transaction_id,))
            return {"success": True, "message": f"Transaction {transaction_id} deleted"}
        except MySQLError as e:
            raise DatabaseException(str(e))