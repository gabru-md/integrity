from abc import abstractmethod
from typing import Optional, List, TypeVar, Generic, Dict, Any

from gabru.db.db import DB

T = TypeVar('T')


class ReadOnlyService(Generic[T]):
    """ ReadOnlyService also useful for queue processor """

    def __init__(self, table_name: str, db: DB):
        self.table_name = table_name
        self.db = db

    @abstractmethod
    def _to_object(self, row: tuple) -> T:
        """
        Abstract method to convert a database row tuple back into a model object.
        """
        pass

    def get_by_id(self, obj_id: int) -> Optional[T]:
        """Retrieves an object by its ID."""
        if not self.db.get_conn():
            return None
        columns = ", ".join(self._get_columns_for_select())
        query = f"SELECT {columns} FROM {self.table_name} WHERE id = %s"

        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, (obj_id,))
            row = cursor.fetchone()
            if row:
                return self._to_object(row)
        return None

    def get_all(self) -> List[T]:
        """Retrieves all objects from the database."""
        if not self.db.get_conn():
            return []
        columns = ", ".join(self._get_columns_for_select())
        query = f"SELECT {columns} FROM {self.table_name}"

        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [self._to_object(row) for row in rows]

    def get_recent_items(self, limit: int = 10) -> List[T]:
        """Retrieves the most recently created items from the database."""
        if not self.db.get_conn():
            return []
        columns = ", ".join(self._get_columns_for_select())
        query = f"SELECT {columns} FROM {self.table_name} ORDER BY id DESC LIMIT %s"
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            return [self._to_object(row) for row in rows]

    def get_all_items_after(self, last_id: int, limit=10) -> List[T]:
        """
        Retrieves all events with an ID greater than the given last_id.
        """
        if not self.db.get_conn():
            return []

        columns = ", ".join(self._get_columns_for_select())
        query = f"SELECT {columns} FROM {self.table_name} WHERE id > %s ORDER BY id ASC LIMIT %s"

        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, (last_id, limit, ))
            rows = cursor.fetchall()
            return [self._to_object(row) for row in rows]

    def find_all(self, filters: Optional[Dict[str, Any]] = None, sort_by: Optional[Dict[str, str]] = None) -> List[T]:
        """
        Retrieves items from the database based on flexible filters and sorting.
        This is a crucial improvement for performance.
        """
        if not self.db.get_conn():
            return []

        columns = ", ".join(self._get_columns_for_select())
        query = f"SELECT {columns} FROM {self.table_name}"
        where_clauses = []
        params = []

        if filters:
            for column, filter_val in filters.items():
                if isinstance(filter_val, dict):
                    # Handle advanced operators like $in and $lt
                    for op, val in filter_val.items():
                        if op == "$in":
                            # For IN clauses, use %s for each item
                            placeholders = ", ".join(["%s"] * len(val))
                            where_clauses.append(f"{column} IN ({placeholders})")
                            params.extend(val)
                        elif op == "$lt":
                            where_clauses.append(f"{column} < %s")
                            params.append(val)
                        elif op == "$gt":
                            where_clauses.append(f"{column} > %s")
                            params.append(val)
                else:
                    where_clauses.append(f"{column} = %s")
                    params.append(filter_val)

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

        if sort_by:
            sort_clauses = [f"{col} {order}" for col, order in sort_by.items()]
            query += " ORDER BY " + ", ".join(sort_clauses)

        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [self._to_object(row) for row in rows]

    @abstractmethod
    def _get_columns_for_select(self) -> List[str]:
        """Returns the list of columns for a SELECT statement."""
        pass


class CRUDService(ReadOnlyService[T]):
    """
    A base class for common CRUD (Create, Read, Update, Delete) operations.
    It extends DB to handle database connections.
    """

    def __init__(self, table_name: str, db: DB):
        super().__init__(table_name, db)
        self._create_table()

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

    def create(self, obj: T) -> Optional[int]:
        """Creates a new object in the database."""
        if not self.db.get_conn():
            return None
        columns = ", ".join(self._get_columns_for_insert())
        placeholders = ", ".join(["%s"] * len(self._get_columns_for_insert()))
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) RETURNING id"

        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, self._to_tuple(obj))
            self.db.get_conn().commit()
            return cursor.fetchone()[0]

    def update(self, obj: T) -> bool:
        """Updates an existing object."""
        if not self.db.get_conn() or obj.id is None:
            return False

        columns_and_placeholders = [f"{col}=%s" for col in self._get_columns_for_update()]
        set_clause = ", ".join(columns_and_placeholders)
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id=%s"

        values = self._to_tuple(obj) + (obj.id,)
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, values)
            self.db.get_conn().commit()
            return cursor.rowcount > 0

    def delete(self, obj_id: int) -> bool:
        """Deletes an object by its ID."""
        if not self.db.get_conn():
            return False
        query = f"DELETE FROM {self.table_name} WHERE id=%s"
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, (obj_id,))
            self.db.get_conn().commit()
            return cursor.rowcount > 0

    @abstractmethod
    def _get_columns_for_insert(self) -> List[str]:
        """Returns the list of columns for an INSERT statement."""
        pass

    @abstractmethod
    def _get_columns_for_update(self) -> List[str]:
        """Returns the list of columns for an UPDATE statement."""
        pass
