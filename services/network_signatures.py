from model.network_signature import NetworkSignature
from gabru.db.service import CRUDService
from gabru.db.db import DB
from typing import List, Union

class NetworkSignatureService(CRUDService[NetworkSignature]):
    def __init__(self):
        super().__init__(
            "network_signatures", DB("rasbhari"), user_scoped=True
        )

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS network_signatures (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        name VARCHAR(255) NOT NULL,
                        mac_address VARCHAR(17) NOT NULL,
                        domain_pattern TEXT NOT NULL,
                        event_type VARCHAR(255) DEFAULT 'network_activity',
                        tags TEXT[] DEFAULT ARRAY['automated', 'network'],
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """)
                self.db.conn.commit()

    def _parse_tags(self, tags: Union[str, List[str], None]) -> List[str]:
        if not tags:
            return []
        if isinstance(tags, list):
            return tags
        # Handle PostgreSQL array string format: {tag1,tag2}
        if isinstance(tags, str):
            tags = tags.strip()
            if tags.startswith('{') and tags.endswith('}'):
                tags = tags[1:-1]
            if not tags:
                return []
            return [t.strip() for t in tags.split(',') if t.strip()]
        return []

    def _to_tuple(self, sig: NetworkSignature) -> tuple:
        return (
            sig.user_id, sig.name, sig.mac_address, sig.domain_pattern,
            sig.event_type, sig.tags, sig.is_active
        )

    def _to_object(self, row: tuple) -> NetworkSignature:
        return NetworkSignature(
            id=row[0],
            user_id=row[1],
            name=row[2],
            mac_address=row[3],
            domain_pattern=row[4],
            event_type=row[5],
            tags=self._parse_tags(row[6]),
            is_active=row[7]
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "name", "mac_address", "domain_pattern", "event_type", "tags", "is_active"]

    def _get_columns_for_update(self) -> List[str]:
        return ["user_id", "name", "mac_address", "domain_pattern", "event_type", "tags", "is_active"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "name", "mac_address", "domain_pattern", "event_type", "tags", "is_active"]
