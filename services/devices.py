from typing import List

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.device import Device


class DeviceService(CRUDService[Device]):
    def __init__(self):
        super().__init__(
            "devices", DB("rasbhari")
        )

    def _create_table(self):
        # NOTE: Using TEXT for the new JSON fields to handle long strings
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS devices (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        enabled BOOLEAN NOT NULL,
                        location VARCHAR(255),
                        type VARCHAR(255),
                        vendor VARCHAR(255),
                        model VARCHAR(255),
                        coordinates VARCHAR(255),
                        url VARCHAR(500),
                        config_json TEXT, 
                        status_json TEXT 
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, device: Device) -> tuple:
        return (
            device.name,
            device.enabled,
            device.location,
            device.type,
            device.vendor,
            device.model,
            device.coordinates,
            device.url,
            device.config_json,
            device.status_json
        )

    def _to_object(self, row: tuple) -> Device:
        # Assuming the new fields are at the end of the row tuple
        device_dict = {
            "id": row[0],
            "name": row[1],
            "enabled": row[2],
            "location": row[3],
            "type": row[4],
            "vendor": row[5],
            "model": row[6],
            "coordinates": row[7],
            "url": row[8],
            "config_json": row[9],
            "status_json": row[10]
        }
        return Device(**device_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return [
            "name", "enabled", "location", "type",
            "vendor", "model", "coordinates", "url",
            "config_json", "status_json"
        ]

    def _get_columns_for_update(self) -> List[str]:
        return [
            "name", "enabled", "location", "type",
            "vendor", "model", "coordinates", "url",
            "config_json", "status_json"
        ]

    def _get_columns_for_select(self) -> List[str]:
        return [
            "id", "name", "enabled", "location", "type",
            "vendor", "model", "coordinates", "url",
            "config_json", "status_json"
        ]

    # Add specific methods here, e.g., get_enabled_devices_by_location
    def get_devices_by_type(self, device_type: str) -> List[Device]:
        devices = []
        with self.db.conn.cursor() as cursor:
            query = "SELECT * FROM device WHERE device_type = %s;"
            cursor.execute(query, (device_type,))
            rows = cursor.fetchall()
            devices = [self._to_object(row) for row in rows]
        return devices
