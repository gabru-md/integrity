from datetime import datetime
from typing import List, Optional

from werkzeug.security import check_password_hash, generate_password_hash

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.user import User


class UserService(CRUDService[User]):
    def __init__(self):
        super().__init__("users", DB("rasbhari"))

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(100) NOT NULL UNIQUE,
                        display_name VARCHAR(150) NOT NULL,
                        password_hash TEXT NOT NULL,
                        is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        is_approved BOOLEAN NOT NULL DEFAULT FALSE,
                        ntfy_topic TEXT,
                        encrypted_data_key TEXT,
                        key_version INTEGER NOT NULL DEFAULT 1,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self.db.conn.commit()

    def _hash_password(self, password: Optional[str]) -> str:
        if not password:
            raise ValueError("password is required")
        return generate_password_hash(password, method="pbkdf2:sha256")

    def _to_tuple(self, user: User) -> tuple:
        raise NotImplementedError("UserService manages tuples in create/update overrides")

    def _to_object(self, row: tuple) -> User:
        return User(
            id=row[0],
            username=row[1],
            display_name=row[2],
            is_admin=row[3],
            is_active=row[4],
            is_approved=row[5],
            ntfy_topic=row[6],
            encrypted_data_key=row[7],
            key_version=row[8],
            created_at=row[9],
            updated_at=row[10],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return [
            "username",
            "display_name",
            "password_hash",
            "is_admin",
            "is_active",
            "is_approved",
            "ntfy_topic",
            "encrypted_data_key",
            "key_version",
            "created_at",
            "updated_at",
        ]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return [
            "id",
            "username",
            "display_name",
            "is_admin",
            "is_active",
            "is_approved",
            "ntfy_topic",
            "encrypted_data_key",
            "key_version",
            "created_at",
            "updated_at",
        ]

    def create(self, obj: User) -> Optional[int]:
        if not self.db.get_conn():
            return None

        now = datetime.now()
        password_hash = self._hash_password(obj.password)
        query = """
            INSERT INTO users (
                username, display_name, password_hash, is_admin, is_active, is_approved,
                ntfy_topic, encrypted_data_key, key_version, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            obj.username.strip().lower(),
            obj.display_name.strip() or obj.username.strip(),
            password_hash,
            obj.is_admin,
            obj.is_active,
            obj.is_approved,
            obj.ntfy_topic,
            obj.encrypted_data_key,
            obj.key_version,
            obj.created_at or now,
            now,
        )

        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, params)
            self.db.get_conn().commit()
            return cursor.fetchone()[0]

    def update(self, obj: User) -> bool:
        if not self.db.get_conn() or obj.id is None:
            return False

        existing = self.get_user_with_password_hash(obj.id)
        if not existing:
            return False

        password_hash = existing["password_hash"]
        if obj.password:
            password_hash = self._hash_password(obj.password)

        query = """
            UPDATE users
            SET username=%s,
                display_name=%s,
                password_hash=%s,
                is_admin=%s,
                is_active=%s,
                is_approved=%s,
                ntfy_topic=%s,
                encrypted_data_key=%s,
                key_version=%s,
                created_at=%s,
                updated_at=%s
            WHERE id=%s
        """
        params = (
            obj.username.strip().lower(),
            obj.display_name.strip() or obj.username.strip(),
            password_hash,
            obj.is_admin,
            obj.is_active,
            obj.is_approved,
            obj.ntfy_topic,
            obj.encrypted_data_key,
            obj.key_version,
            obj.created_at or existing["created_at"],
            datetime.now(),
            obj.id,
        )
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, params)
            self.db.get_conn().commit()
            return cursor.rowcount > 0

    def get_by_username(self, username: str) -> Optional[User]:
        return self.find_one_by_field("username", username.strip().lower())

    def get_user_with_password_hash(self, user_id: int) -> Optional[dict]:
        if not self.db.get_conn():
            return None
        query = """
            SELECT id, username, display_name, password_hash, is_admin, is_active, is_approved,
                   ntfy_topic, encrypted_data_key, key_version, created_at, updated_at
            FROM users
            WHERE id = %s
        """
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "username": row[1],
                "display_name": row[2],
                "password_hash": row[3],
                "is_admin": row[4],
                "is_active": row[5],
                "is_approved": row[6],
                "ntfy_topic": row[7],
                "encrypted_data_key": row[8],
                "key_version": row[9],
                "created_at": row[10],
                "updated_at": row[11],
            }

    def authenticate(self, username: str, password: str) -> Optional[User]:
        if not self.db.get_conn():
            return None
        query = """
            SELECT id, username, display_name, password_hash, is_admin, is_active, is_approved,
                   ntfy_topic, encrypted_data_key, key_version, created_at, updated_at
            FROM users
            WHERE username = %s
        """
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, (username.strip().lower(),))
            row = cursor.fetchone()
            if not row:
                return None
            if not row[5]: # is_active
                return None
            if not row[6]: # is_approved
                return None
            if not check_password_hash(row[3], password):
                return None
            return User(
                id=row[0],
                username=row[1],
                display_name=row[2],
                is_admin=row[4],
                is_active=row[5],
                is_approved=row[6],
                ntfy_topic=row[7],
                encrypted_data_key=row[8],
                key_version=row[9],
                created_at=row[10],
                updated_at=row[11],
            )
