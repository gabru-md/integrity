from abc import abstractmethod
from typing import Optional, List, TypeVar, Generic, Dict, Any

from flask import has_request_context

from gabru.auth import PermissionManager
from gabru.db.db import DB
from gabru.log import Logger

T = TypeVar('T')

log = Logger.get_log('ReadOnlyService')

class ReadOnlyService(Generic[T]):
    """ ReadOnlyService also useful for queue processor """

    def __init__(self, table_name: str, db: DB, user_scoped: bool = False, user_scope_column: str = "user_id"):
        self.table_name = table_name
        self.db = db
        self.user_scoped = user_scoped
        self.user_scope_column = user_scope_column

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
        params = [obj_id]

        user_scope = self._get_request_user_scope()
        if user_scope is not None:
            query += f" AND {self.user_scope_column} = %s"
            params.append(user_scope)

        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            if row:
                return self._to_object(row)
        return None

    def get_all(self) -> List[T]:
        """Retrieves all objects from the database."""
        return self.find_all()

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Returns the total count of items matching the filters."""
        if not self.db.get_conn():
            return 0
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        where_clauses = []
        params = []
        filters = self._with_request_user_scope(filters)
        if filters:
            for column, filter_val in filters.items():
                where_clauses.append(f"{column} = %s")
                params.append(filter_val)
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_recent_items(self, limit: int = 10) -> List[T]:
        """Retrieves the most recently created items from the database."""
        if not self.db.get_conn():
            return []
        columns = ", ".join(self._get_columns_for_select())
        query = f"SELECT {columns} FROM {self.table_name} ORDER BY id DESC LIMIT %s"
        params = [limit]

        filters = self._with_request_user_scope()
        if filters:
            where_clauses = [f"{column} = %s" for column in filters.keys()]
            filter_params = list(filters.values())
            query = f"SELECT {columns} FROM {self.table_name} WHERE {' AND '.join(where_clauses)} ORDER BY id DESC LIMIT %s"
            params = filter_params + params
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, tuple(params))
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
        params = [last_id, limit]

        user_scope = self._get_request_user_scope()
        if user_scope is not None:
            query = f"SELECT {columns} FROM {self.table_name} WHERE id > %s AND {self.user_scope_column} = %s ORDER BY id ASC LIMIT %s"
            params = [last_id, user_scope, limit]

        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, tuple(params))
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

        filters = self._with_request_user_scope(filters)

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

    def find_one_by_field(self, field_name: str, value: Any) -> Optional[T]:
        """Retrieves a single object by a specific field and value."""
        results = self.find_all(filters={field_name: value})
        return results[0] if results else None

    def _get_request_user_scope(self) -> Optional[int]:
        if not self.user_scoped:
            return None
        if not has_request_context():
            return None
        return PermissionManager.get_current_user_id()

    def _with_request_user_scope(self, filters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        user_scope = self._get_request_user_scope()
        scoped_filters = dict(filters or {})
        if user_scope is not None and self.user_scope_column not in scoped_filters:
            scoped_filters[self.user_scope_column] = user_scope
        return scoped_filters or None

    @abstractmethod
    def _get_columns_for_select(self) -> List[str]:
        """Returns the list of columns for a SELECT statement."""
        pass


class CRUDService(ReadOnlyService[T]):
    """
    A base class for common CRUD (Create, Read, Update, Delete) operations.
    It extends DB to handle database connections.
    """

    def __init__(self, table_name: str, db: DB, user_scoped: bool = False, user_scope_column: str = "user_id"):
        super().__init__(table_name, db, user_scoped=user_scoped, user_scope_column=user_scope_column)
        self.log = Logger.get_log(f"{table_name}:{db.dbname} Service")
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
        self._apply_request_user_scope_to_object(obj)
        columns = ", ".join(self._get_columns_for_insert())
        placeholders = ", ".join(["%s"] * len(self._get_columns_for_insert()))
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) RETURNING id"

        with self.db.get_conn().cursor() as cursor:
            try:
                cursor.execute(query, self._to_tuple(obj))
                self.db.get_conn().commit()
                return cursor.fetchone()[0]
            except Exception as e:
                log.exception(e)
                log.warn(self._to_tuple(obj))


    def update(self, obj: T) -> bool:
        """Updates an existing object."""
        if not self.db.get_conn() or obj.id is None:
            return False
        self._apply_request_user_scope_to_object(obj)
        existing = self.get_by_id(obj.id)
        if self.user_scoped and self._get_request_user_scope() is not None and not existing:
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
        if self.user_scoped and self._get_request_user_scope() is not None and not self.get_by_id(obj_id):
            return False
        query = f"DELETE FROM {self.table_name} WHERE id=%s"
        params = [obj_id]
        user_scope = self._get_request_user_scope()
        if user_scope is not None:
            query += f" AND {self.user_scope_column} = %s"
            params.append(user_scope)
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, tuple(params))
            self.db.get_conn().commit()
            return cursor.rowcount > 0

    def _apply_request_user_scope_to_object(self, obj: T):
        user_scope = self._get_request_user_scope()
        if user_scope is None or not hasattr(obj, self.user_scope_column):
            return
        setattr(obj, self.user_scope_column, user_scope)

    @abstractmethod
    def _get_columns_for_insert(self) -> List[str]:
        """Returns the list of columns for an INSERT statement."""
        pass

    @abstractmethod
    def _get_columns_for_update(self) -> List[str]:
        """Returns the list of columns for an UPDATE statement."""
        pass
