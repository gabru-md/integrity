from typing import List

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.notification import Notification


class NotificationService(CRUDService[Notification]):
    def __init__(self):
        super().__init__(
            "notifications", DB("notifications")
        )

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id SERIAL PRIMARY KEY,
                        notification_type VARCHAR(255) NOT NULL,
                        notification_data VARCHAR(500) NOT NULL,
                        created_at TIMESTAMP
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, notification: Notification) -> tuple:
        return (
            notification.id, notification.notification_type, notification.notification_data, notification.created_at)

    def _to_object(self, row: tuple) -> Notification:
        notification_dict = {
            "id": row[0],
            "notification_type": row[1],
            "notification_data": row[2],
            "created_at": row[3]
        }
        return Notification(**notification_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["notification_type", "notification_data", "created_at"]

    def _get_columns_for_update(self) -> List[str]:
        return ["notification_type", "notification_data", "created_at"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "notification_type", "notification_data", "created_at"]

    def queue_email_notification(self, notification):
        pass
