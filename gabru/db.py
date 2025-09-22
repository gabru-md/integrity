import os

import psycopg2
from dotenv import load_dotenv
from gabru.log import Logger

load_dotenv()


class DB:
    """
    A base class for database operations using psycopg2.
    It handles connection management and provides an abstract method for table creation.
    """

    def __init__(self, default_dbname: str):

        self.db = default_dbname

        self.dbname = os.getenv(self.get_db_env('POSTGRES_DB'))
        self.user = os.getenv(self.get_db_env('POSTGRES_USER'))
        self.password = os.getenv(self.get_db_env('POSTGRES_PASSWORD'))
        self.host = os.getenv(self.get_db_env('POSTGRES_HOST'))
        self.port = os.getenv(self.get_db_env('POSTGRES_PORT'))

        self.log = Logger.get_log(f"{self.db.capitalize()}DB")
        self.conn = None
        self._connect()

    def get_db_env(self, key):
        return f"{self.db.upper()}_{key}"

    def _connect(self):
        """Establishes a connection to the PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            self.log.info("Connected to PostgreSQL database.")
        except psycopg2.Error as e:
            self.log.error(f"Error connecting to the database: {e}")
            self.conn = None

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
