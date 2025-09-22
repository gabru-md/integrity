from abc import abstractmethod
from typing import Optional, List, TypeVar, Generic
from db import DB

T = TypeVar('T')


class CrudDB(DB, Generic[T]):
    """
    A base class for common CRUD (Create, Read, Update, Delete) operations.
    It extends DB to handle database connections.
    """

    def __init__(self, table_name: str, dbname_env_var: str, user_env_var: str, password_env_var: str,
                 host_env_var: str, port_env_var: str, default_dbname: str):
        super().__init__(dbname_env_var, user_env_var, password_env_var, host_env_var, port_env_var, default_dbname)
        self.table_name = table_name

    @abstractmethod
    def _create_table(self):
        """
        Abstract method to create the specific table for the subclass.
        """
        pass

    @abstractmethod
    def _to_tuple(self, obj: T) -> tuple:
        """
        Abstract method to convert a model object into a tuple for SQL insertion/update.
        """
        pass

    @abstractmethod
    def _to_object(self, row: tuple) -> T:
        """
        Abstract method to convert a database row tuple back into a model object.
        """
        pass

    def create(self, obj: T) -> Optional[int]:
        """Creates a new object in the database."""
        if not self.conn:
            return None
        columns = ", ".join(self._get_columns_for_insert())
        placeholders = ", ".join(["%s"] * len(self._get_columns_for_insert()))
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) RETURNING id"

        with self.conn.cursor() as cursor:
            cursor.execute(query, self._to_tuple(obj))
            self.conn.commit()
            return cursor.fetchone()[0]

    def get_by_id(self, obj_id: int) -> Optional[T]:
        """Retrieves an object by its ID."""
        if not self.conn:
            return None
        columns = ", ".join(self._get_columns_for_select())
        query = f"SELECT {columns} FROM {self.table_name} WHERE id = %s"

        with self.conn.cursor() as cursor:
            cursor.execute(query, (obj_id,))
            row = cursor.fetchone()
            if row:
                return self._to_object(row)
        return None

    def get_all(self) -> List[T]:
        """Retrieves all objects from the database."""
        if not self.conn:
            return []
        columns = ", ".join(self._get_columns_for_select())
        query = f"SELECT {columns} FROM {self.table_name}"

        with self.conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [self._to_object(row) for row in rows]

    def update(self, obj: T) -> bool:
        """Updates an existing object."""
        if not self.conn or obj.id is None:
            return False

        columns_and_placeholders = [f"{col}=%s" for col in self._get_columns_for_update()]
        set_clause = ", ".join(columns_and_placeholders)
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id=%s"

        values = self._to_tuple(obj) + (obj.id,)
        with self.conn.cursor() as cursor:
            cursor.execute(query, values)
            self.conn.commit()
            return cursor.rowcount > 0

    def delete(self, obj_id: int) -> bool:
        """Deletes an object by its ID."""
        if not self.conn:
            return False
        query = f"DELETE FROM {self.table_name} WHERE id=%s"
        with self.conn.cursor() as cursor:
            cursor.execute(query, (obj_id,))
            self.conn.commit()
            return cursor.rowcount > 0

    @abstractmethod
    def _get_columns_for_insert(self) -> List[str]:
        """Returns the list of columns for an INSERT statement."""
        pass

    @abstractmethod
    def _get_columns_for_update(self) -> List[str]:
        """Returns the list of columns for an UPDATE statement."""
        pass

    @abstractmethod
    def _get_columns_for_select(self) -> List[str]:
        """Returns the list of columns for a SELECT statement."""
        pass
