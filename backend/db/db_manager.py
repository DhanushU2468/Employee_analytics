import os
import threading
from contextlib import contextmanager
import mysql.connector
from mysql.connector import Error, pooling
from backend.db.config import load_mysql_settings, validate_mysql_settings, _resolve_ssl_ca

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class DatabaseConnection:
    """
    Thread-safe Singleton class managing MySQL-compatible pools for the
    operational tables and analytical warehouse.
    Prevents connection exhaustion and ensures safe pooling across Streamlit sessions.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(DatabaseConnection, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self._load_config()
            self._pools = {}
            self._init_pool("oltp", self.oltp_db)
            if self.olap_db == self.oltp_db:
                self._pools["olap"] = self._pools["oltp"]
            else:
                self._init_pool("olap", self.olap_db)
            self._initialized = True

    def _load_config(self):
        """Dynamically load credentials from Streamlit secrets, environment variables, or fallbacks."""
        st_secrets = {}
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "mysql" in st.secrets:
                st_secrets = st.secrets["mysql"]
        except Exception:
            pass

        settings = load_mysql_settings(st_secrets)
        validate_mysql_settings(settings)
        self.host = settings["host"]
        self.port = settings["port"]
        self.user = settings["user"]
        self.password = settings["password"]
        self.oltp_db = settings["oltp_db"]
        self.olap_db = settings["olap_db"]
        self.pool_size = settings["pool_size"]
        self.ssl_enabled = settings["ssl_enabled"]
        self.ssl_verify_cert = settings["ssl_verify_cert"]
        self.ssl_ca = settings["ssl_ca"]

    def _init_pool(self, key: str, database_name: str):
        """Initialize a named connection pool."""
        pool_name = f"pool_{key}_{os.getpid()}"
        try:
            self._pools[key] = pooling.MySQLConnectionPool(
                pool_name=pool_name,
                pool_size=self.pool_size,
                pool_reset_session=True,
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=database_name,
                **self._ssl_options(),
            )
        except Error:
            self._pools[key] = None

    def _ssl_options(self):
        if not self.ssl_enabled:
            return {"ssl_disabled": True}
        options = {"ssl_disabled": False, "ssl_verify_cert": self.ssl_verify_cert}
        if self.ssl_ca:
            resolved = _resolve_ssl_ca(self.ssl_ca)
            if resolved:
                options["ssl_ca"] = resolved
        return options

    def get_connection(self, db_key="oltp"):
        """Acquire a connection from the designated pool or establish a direct connection."""
        db_name = self.oltp_db if db_key == "oltp" else self.olap_db
        pool = self._pools.get(db_key)

        if pool:
            try:
                return pool.get_connection()
            except Error:
                pass

        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=db_name,
            **self._ssl_options(),
        )

    @contextmanager
    def get_cursor(self, db_key="oltp", dictionary=True):
        """
        Thread-safe context manager that yields a cursor and safely
        commits transactions, rolls back on error, and returns connection to pool.
        """
        conn = self.get_connection(db_key)
        cursor = conn.cursor(dictionary=dictionary)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            if conn.is_connected():
                conn.rollback()
            raise e
        finally:
            try:
                # Consume unread results to prevent connection poisoning in pool
                cursor.fetchall()
            except Exception:
                pass
            cursor.close()
            if conn.is_connected():
                conn.close()

    def check_health(self):
        """Verify database connectivity."""
        status = {}
        for key in ["oltp", "olap"]:
            try:
                with self.get_cursor(key) as cur:
                    cur.execute("SELECT 1 AS health_check;")
                    cur.fetchall()
                    status[key] = "Connected"
            except Exception as e:
                status[key] = f"Error: {e}"
        return status
