import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from model.activity import Activity
from model.event import Event # Re-import Event model
from gabru.db.service import CRUDService
from gabru.db.db import DB
from services.events import EventService


class ActivityService(CRUDService[Activity]):
    def __init__(self):
        super().__init__(
            "activities", DB("rasbhari")
        )
        self.event_service = EventService() # Instantiate EventService

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                            CREATE TABLE IF NOT EXISTS activities (
                                id SERIAL PRIMARY KEY,
                                name VARCHAR(255) NOT NULL UNIQUE,
                                event_type VARCHAR(255) NOT NULL,
                                description TEXT,
                                default_payload JSONB,
                                tags TEXT[]
                            );
                        """)
                self.db.conn.commit()

    def _to_tuple(self, activity: Activity) -> tuple:
        # Ensure tags are JSON serialized if they are to be stored as TEXT[] in PostgreSQL
        return (
            activity.name, activity.event_type, activity.description, json.dumps(activity.default_payload), activity.tags)

    def _to_object(self, row: tuple) -> Activity:
        activity_dict = {
            "id": row[0],
            "name": row[1],
            "event_type": row[2],
            "description": row[3],
            "default_payload": row[4],
            "tags": row[5] if row[5] else [] # Ensure tags are handled correctly, might need json.loads if stored as string representation of list
        }
        return Activity(**activity_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "event_type", "description", "default_payload", "tags"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "event_type", "description", "default_payload", "tags"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "event_type", "description", "default_payload", "tags"]

    def trigger_activity(self, activity_id: int, override_payload: Optional[Dict[str, Any]] = None) -> Optional[int]:
        activity = self.get_by_id(activity_id)
        if not activity:
            self.log.error(f"Activity with ID {activity_id} not found.")
            return None

        # Prepare payloads and tags
        combined_payload = activity.default_payload.copy() if activity.default_payload else {}
        if override_payload:
            combined_payload.update(override_payload)
        
        # Extract event-specific payload items and tags
        event_description_from_payload = combined_payload.pop("description", None)
        event_tags_from_payload = combined_payload.pop("tags", [])
        # Combine tags: activity tags + payload tags + override payload tags
        # Note: `activity.tags` is already a list of strings
        all_tags = list(set(activity.tags + event_tags_from_payload))

        # Use activity description if not provided in payload, otherwise use payload's description
        event_description = event_description_from_payload or activity.description or ""
        # Add any remaining combined_payload to event_description as JSON string
        if combined_payload:
            event_description = f"{event_description} (Payload: {json.dumps(combined_payload)})"

        # Add a specific tag for tracking the trigger source
        all_tags.append(f"triggered_by:activity:{activity.name}")

        new_event = Event(
            event_type=activity.event_type,
            timestamp=datetime.now(),
            description=event_description,
            tags=all_tags
        )

        self.log.info(f"Triggering activity: {activity.name} (Event Type: {activity.event_type})")
        try:
            created_event_id = self.event_service.create(new_event)
            if created_event_id:
                self.log.info(f"Activity '{activity.name}' event created successfully with ID {created_event_id}.")
                return activity_id
            else:
                self.log.error(f"Failed to create event for activity '{activity.name}'.")
                return None
        except Exception as e:
            self.log.exception(f"Failed to create event for activity '{activity.name}': {e}")
            return None
