from backend.db.db_manager import DatabaseConnection


class BaseManager:
    """
    Base Data Access Layer (DAL) class providing managed database connections
    and unified execution handling for both OLTP and OLAP operations.
    """

    def __init__(self, db_connection: DatabaseConnection = None):
        self.db = db_connection or DatabaseConnection()

    def execute_query(self, query: str, params: tuple = None, db_key: str = "oltp", fetch: str = "all"):
        """Execute a parameterized query safely preventing SQL injection."""
        with self.db.get_cursor(db_key=db_key, dictionary=True) as cursor:
            cursor.execute(query, params or ())
            if fetch == "all":
                return cursor.fetchall()
            elif fetch == "one":
                return cursor.fetchone()
            elif fetch == "none":
                return cursor.rowcount
            return cursor.fetchall()

    def execute_insert(self, query: str, params: tuple = None, db_key: str = "oltp") -> int:
        """Execute an insert query and return the last inserted ID."""
        with self.db.get_cursor(db_key=db_key, dictionary=True) as cursor:
            cursor.execute(query, params or ())
            return cursor.lastrowid

