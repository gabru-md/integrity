import atexit
import os
import threading
from urllib.parse import urlparse

import psycopg2
from psycopg2 import InterfaceError, OperationalError
from dotenv import load_dotenv

from gabru.log import Logger

load_dotenv()


class DB:
    """
    A base class for database operations using psycopg2.
    It now shares one live connection per logical database config instead of
    opening a dedicated connection for every service instance.
    """

    _shared_connections = {}
    _shared_lock = threading.Lock()
    _atexit_registered = False

    def __init__(self, default_dbname: str):
        self.db = default_dbname
        shared_config = self._get_shared_database_config()
        self.dbname = os.getenv(self.get_db_env('POSTGRES_DB')) or shared_config.get('dbname')
        self.user = os.getenv(self.get_db_env('POSTGRES_USER')) or shared_config.get('user')
        self.password = os.getenv(self.get_db_env('POSTGRES_PASSWORD')) or shared_config.get('password')
        self.host = os.getenv(self.get_db_env('POSTGRES_HOST')) or shared_config.get('host')
        self.port = os.getenv(self.get_db_env('POSTGRES_PORT')) or shared_config.get('port')
        self.log = Logger.get_log(f"{self.db.capitalize()}DB")
        self._connection_key = (
            self.db,
            self.dbname,
            self.user,
            self.host,
            self.port,
        )
        self._register_atexit_once()

    def get_db_env(self, key):
        return f"{self.db.upper()}_{key}"

    def _get_shared_database_config(self) -> dict:
        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url:
            return {}

        parsed = urlparse(database_url)
        return {
            "dbname": parsed.path.lstrip("/") or None,
            "user": parsed.username,
            "password": parsed.password,
            "host": parsed.hostname,
            "port": str(parsed.port) if parsed.port else None,
        }

    def _register_atexit_once(self):
        if DB._atexit_registered:
            return
        atexit.register(self._close_all_shared_connections)
        DB._atexit_registered = True

    @classmethod
    def _close_all_shared_connections(cls):
        with cls._shared_lock:
            for conn in cls._shared_connections.values():
                try:
                    conn.close()
                except Exception:
                    pass
            cls._shared_connections.clear()

    def _is_connection_usable(self, conn) -> bool:
        return bool(conn) and getattr(conn, "closed", 1) == 0

    @staticmethod
    def is_connection_error(exc: Exception) -> bool:
        return isinstance(exc, (OperationalError, InterfaceError))

    def _connect(self):
        try:
            conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
            )
            self.log.info("Connected to PostgreSQL database.")
            return conn
        except psycopg2.Error as e:
            self.log.error(f"Error connecting to the database: {e}")
            return None

    def get_conn(self):
        with DB._shared_lock:
            conn = DB._shared_connections.get(self._connection_key)
            if self._is_connection_usable(conn):
                return conn

            conn = self._connect()
            if conn:
                DB._shared_connections[self._connection_key] = conn
            return conn

    @property
    def conn(self):
        return self.get_conn()

    def close(self):
        """Closes the shared connection for this logical DB, if requested explicitly."""
        with DB._shared_lock:
            conn = DB._shared_connections.pop(self._connection_key, None)
            if self._is_connection_usable(conn):
                conn.close()

    def invalidate_connection(self):
        with DB._shared_lock:
            conn = DB._shared_connections.pop(self._connection_key, None)
        if self._is_connection_usable(conn):
            try:
                conn.close()
            except Exception:
                pass

    def rollback_quietly(self):
        conn = self.get_conn()
        if not self._is_connection_usable(conn):
            return
        try:
            conn.rollback()
        except Exception:
            pass

    def __del__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
