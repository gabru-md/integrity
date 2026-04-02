from datetime import datetime
import secrets
import string
from typing import List, Optional

from werkzeug.security import check_password_hash, generate_password_hash

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.user import User


class UserService(CRUDService[User]):
    API_KEY_ALPHABET = string.ascii_letters + string.digits
    API_KEY_LENGTH = 5

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
                        api_key VARCHAR(5),
                        is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        is_approved BOOLEAN NOT NULL DEFAULT FALSE,
                        onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
                        ntfy_topic TEXT,
                        recommendations_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        recommendation_limit INTEGER NOT NULL DEFAULT 2,
                        encrypted_data_key TEXT,
                        key_version INTEGER NOT NULL DEFAULT 1,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS api_key VARCHAR(5)")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS recommendations_enabled BOOLEAN NOT NULL DEFAULT TRUE")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS recommendation_limit INTEGER NOT NULL DEFAULT 2")
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_api_key ON users (api_key) WHERE api_key IS NOT NULL")
                self.db.conn.commit()

    def _generate_api_key(self) -> str:
        return "".join(secrets.choice(self.API_KEY_ALPHABET) for _ in range(self.API_KEY_LENGTH))

    def _generate_unique_api_key(self) -> str:
        while True:
            api_key = self._generate_api_key()
            if not self.get_by_api_key(api_key):
                return api_key

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
            api_key=row[3],
            is_admin=row[4],
            is_active=row[5],
            is_approved=row[6],
            onboarding_completed=row[7],
            ntfy_topic=row[8],
            recommendations_enabled=row[9],
            recommendation_limit=row[10] if row[10] is not None else 2,
            encrypted_data_key=row[11],
            key_version=row[12],
            created_at=row[13],
            updated_at=row[14],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return [
            "username",
            "display_name",
            "password_hash",
            "api_key",
            "is_admin",
            "is_active",
            "is_approved",
            "onboarding_completed",
            "ntfy_topic",
            "recommendations_enabled",
            "recommendation_limit",
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
            "api_key",
            "is_admin",
            "is_active",
            "is_approved",
            "onboarding_completed",
            "ntfy_topic",
            "recommendations_enabled",
            "recommendation_limit",
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
        api_key = obj.api_key or self._generate_unique_api_key()
        query = """
            INSERT INTO users (
                username, display_name, password_hash, api_key, is_admin, is_active, is_approved,
                onboarding_completed, ntfy_topic, recommendations_enabled, recommendation_limit, encrypted_data_key, key_version, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            obj.username.strip().lower(),
            obj.display_name.strip() or obj.username.strip(),
            password_hash,
            api_key,
            obj.is_admin,
            obj.is_active,
            obj.is_approved,
            obj.onboarding_completed,
            obj.ntfy_topic,
            obj.recommendations_enabled,
            max(0, int(obj.recommendation_limit if obj.recommendation_limit is not None else 2)),
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
                api_key=%s,
                is_admin=%s,
                is_active=%s,
                is_approved=%s,
                onboarding_completed=%s,
                ntfy_topic=%s,
                recommendations_enabled=%s,
                recommendation_limit=%s,
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
            obj.api_key or existing["api_key"] or self._generate_unique_api_key(),
            obj.is_admin,
            obj.is_active,
            obj.is_approved,
            obj.onboarding_completed,
            obj.ntfy_topic,
            obj.recommendations_enabled,
            max(0, int(obj.recommendation_limit if obj.recommendation_limit is not None else 2)),
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

    def get_by_api_key(self, api_key: str) -> Optional[User]:
        return self.find_one_by_field("api_key", (api_key or "").strip())

    def ensure_api_key(self, user_id: int) -> Optional[str]:
        existing = self.get_user_with_password_hash(user_id)
        if not existing:
            return None
        if existing.get("api_key"):
            return existing["api_key"]
        return self.regenerate_api_key(user_id)

    def get_user_with_password_hash(self, user_id: int) -> Optional[dict]:
        if not self.db.get_conn():
            return None
        query = """
            SELECT id, username, display_name, password_hash, api_key, is_admin, is_active, is_approved, onboarding_completed,
                   ntfy_topic, recommendations_enabled, recommendation_limit, encrypted_data_key, key_version, created_at, updated_at
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
                "api_key": row[4],
                "is_admin": row[5],
                "is_active": row[6],
                "is_approved": row[7],
                "onboarding_completed": row[8],
                "ntfy_topic": row[9],
                "recommendations_enabled": row[10],
                "recommendation_limit": row[11] if row[11] is not None else 2,
                "encrypted_data_key": row[12],
                "key_version": row[13],
                "created_at": row[14],
                "updated_at": row[15],
            }

    def authenticate(self, username: str, password: str) -> Optional[User]:
        if not self.db.get_conn():
            return None
        query = """
            SELECT id, username, display_name, password_hash, api_key, is_admin, is_active, is_approved, onboarding_completed,
                   ntfy_topic, recommendations_enabled, recommendation_limit, encrypted_data_key, key_version, created_at, updated_at
            FROM users
            WHERE username = %s
        """
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, (username.strip().lower(),))
            row = cursor.fetchone()
            if not row:
                return None
            if not row[6]: # is_active
                return None
            if not row[7]: # is_approved
                return None
            if not check_password_hash(row[3], password):
                return None
            api_key = row[4] or self.ensure_api_key(row[0])
            return User(
                id=row[0],
                username=row[1],
                display_name=row[2],
                api_key=api_key,
                is_admin=row[5],
                is_active=row[6],
                is_approved=row[7],
                onboarding_completed=row[8],
                ntfy_topic=row[9],
                recommendations_enabled=row[10],
                recommendation_limit=row[11] if row[11] is not None else 2,
                encrypted_data_key=row[12],
                key_version=row[13],
                created_at=row[14],
                updated_at=row[15],
            )

    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        if not self.db.get_conn():
            return None
        safe_api_key = (api_key or "").strip()
        if not safe_api_key:
            return None
        query = """
            SELECT id, username, display_name, api_key, is_admin, is_active, is_approved, onboarding_completed,
                   ntfy_topic, recommendations_enabled, recommendation_limit, encrypted_data_key, key_version, created_at, updated_at
            FROM users
            WHERE api_key = %s
        """
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(query, (safe_api_key,))
            row = cursor.fetchone()
            if not row:
                return None
            if not row[5] or not row[6]:
                return None
            return User(
                id=row[0],
                username=row[1],
                display_name=row[2],
                api_key=row[3],
                is_admin=row[4],
                is_active=row[5],
                is_approved=row[6],
                onboarding_completed=row[7],
                ntfy_topic=row[8],
                recommendations_enabled=row[9],
                recommendation_limit=row[10] if row[10] is not None else 2,
                encrypted_data_key=row[11],
                key_version=row[12],
                created_at=row[13],
                updated_at=row[14],
            )

    def regenerate_api_key(self, user_id: int) -> Optional[str]:
        if not self.db.get_conn():
            return None
        new_api_key = self._generate_unique_api_key()
        with self.db.get_conn().cursor() as cursor:
            cursor.execute(
                """
                    UPDATE users
                    SET api_key = %s,
                        updated_at = %s
                    WHERE id = %s
                """,
                (new_api_key, datetime.now(), user_id),
            )
            self.db.get_conn().commit()
            if cursor.rowcount <= 0:
                return None
        return new_api_key
