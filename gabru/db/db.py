import atexit
import os
import threading

import psycopg2
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
        self.dbname = os.getenv(self.get_db_env('POSTGRES_DB'))
        self.user = os.getenv(self.get_db_env('POSTGRES_USER'))
        self.password = os.getenv(self.get_db_env('POSTGRES_PASSWORD'))
        self.host = os.getenv(self.get_db_env('POSTGRES_HOST'))
        self.port = os.getenv(self.get_db_env('POSTGRES_PORT'))
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

    def __del__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
