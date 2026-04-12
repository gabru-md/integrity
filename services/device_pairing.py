import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.device_pairing import DevicePairing


class DevicePairingService(CRUDService[DevicePairing]):
    def __init__(self):
        super().__init__("device_pairings", DB("rasbhari"))

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS device_pairings (
                        id SERIAL PRIMARY KEY,
                        token VARCHAR(128) NOT NULL UNIQUE,
                        requested_path VARCHAR(512) NOT NULL DEFAULT '/',
                        user_id INTEGER,
                        status VARCHAR(32) NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMP NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        authorized_at TIMESTAMP,
                        consumed_at TIMESTAMP,
                        requester_ip VARCHAR(64),
                        requester_user_agent VARCHAR(512)
                    )
                    """
                )
                cursor.execute("ALTER TABLE device_pairings ADD COLUMN IF NOT EXISTS requested_path VARCHAR(512) NOT NULL DEFAULT '/'")
                cursor.execute("ALTER TABLE device_pairings ADD COLUMN IF NOT EXISTS authorized_at TIMESTAMP")
                cursor.execute("ALTER TABLE device_pairings ADD COLUMN IF NOT EXISTS consumed_at TIMESTAMP")
                cursor.execute("ALTER TABLE device_pairings ADD COLUMN IF NOT EXISTS requester_ip VARCHAR(64)")
                cursor.execute("ALTER TABLE device_pairings ADD COLUMN IF NOT EXISTS requester_user_agent VARCHAR(512)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_pairings_token ON device_pairings (token)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_pairings_status_expires ON device_pairings (status, expires_at)")
                self.db.conn.commit()

    def _to_tuple(self, pairing: DevicePairing) -> tuple:
        return (
            pairing.token,
            pairing.requested_path or "/",
            pairing.user_id,
            pairing.status,
            pairing.created_at,
            pairing.expires_at,
            pairing.authorized_at,
            pairing.consumed_at,
            pairing.requester_ip,
            pairing.requester_user_agent,
        )

    def _to_object(self, row: tuple) -> DevicePairing:
        return DevicePairing(
            id=row[0],
            token=row[1],
            requested_path=row[2],
            user_id=row[3],
            status=row[4],
            created_at=row[5],
            expires_at=row[6],
            authorized_at=row[7],
            consumed_at=row[8],
            requester_ip=row[9],
            requester_user_agent=row[10],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return [
            "token",
            "requested_path",
            "user_id",
            "status",
            "created_at",
            "expires_at",
            "authorized_at",
            "consumed_at",
            "requester_ip",
            "requester_user_agent",
        ]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return [
            "id",
            "token",
            "requested_path",
            "user_id",
            "status",
            "created_at",
            "expires_at",
            "authorized_at",
            "consumed_at",
            "requester_ip",
            "requester_user_agent",
        ]

    def create_pairing(
        self,
        *,
        requested_path: str = "/",
        ttl_minutes: int = 5,
        requester_ip: Optional[str] = None,
        requester_user_agent: Optional[str] = None,
    ) -> DevicePairing:
        safe_path = requested_path if isinstance(requested_path, str) and requested_path.startswith("/") else "/"
        pairing = DevicePairing(
            token=secrets.token_urlsafe(32),
            requested_path=safe_path,
            status="pending",
            expires_at=datetime.now() + timedelta(minutes=max(1, ttl_minutes)),
            requester_ip=requester_ip,
            requester_user_agent=requester_user_agent,
        )
        pairing_id = self.create(pairing)
        if pairing_id:
            pairing.id = pairing_id
        return pairing

    def get_by_token(self, token: str) -> Optional[DevicePairing]:
        results = self.find_all(filters={"token": token}, sort_by={"id": "DESC"})
        return results[0] if results else None

    def get_valid_pairing(self, token: str) -> Optional[DevicePairing]:
        pairing = self.get_by_token(token)
        if not pairing:
            return None
        if datetime.now() > pairing.expires_at and pairing.status not in {"consumed", "expired"}:
            pairing.status = "expired"
            self.update(pairing)
            return None
        return pairing

    def authorize_pairing(self, token: str, user_id: int) -> bool:
        pairing = self.get_valid_pairing(token)
        if not pairing or pairing.status != "pending":
            return False
        pairing.user_id = user_id
        pairing.status = "authorized"
        pairing.authorized_at = datetime.now()
        return self.update(pairing)

    def consume_pairing(self, token: str) -> Optional[DevicePairing]:
        pairing = self.get_valid_pairing(token)
        if not pairing or pairing.status != "authorized":
            return None
        pairing.status = "consumed"
        pairing.consumed_at = datetime.now()
        if not self.update(pairing):
            return None
        return pairing
