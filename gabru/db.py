import psycopg2
import os
from dotenv import load_dotenv
from gabru.log import Logger
from abc import ABC, abstractmethod

load_dotenv()


class DB(ABC):
    """
    A base class for database operations using psycopg2.
    It handles connection management and provides an abstract method for table creation.
    """

    def __init__(self, dbname_env_var: str, user_env_var: str, password_env_var: str, host_env_var: str,
                 port_env_var: str, default_dbname: str):
        self.dbname = os.environ.get(dbname_env_var, default_dbname)
        self.user = os.environ.get(user_env_var, "manish")
        self.password = os.environ.get(password_env_var, "password")
        self.host = os.environ.get(host_env_var, "localhost")
        self.port = os.environ.get(port_env_var, "5432")

        self.log = Logger.get_log(self.__class__.__name__)
        self.conn = None
        self._connect()
        self._create_table()

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

    @abstractmethod
    def _create_table(self):
        """
        Abstract method to be implemented by subclasses for creating their specific table.
        """
        pass

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
