from datetime import datetime
from typing import List, Optional, Union

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
                        title VARCHAR(255),
                        notification_type VARCHAR(255) NOT NULL,
                        notification_class VARCHAR(50) NOT NULL DEFAULT 'today',
                        notification_data VARCHAR(500) NOT NULL,
                        created_at TIMESTAMP
                    )
                """)
                cursor.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS title VARCHAR(255)")
                cursor.execute(
                    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS notification_class VARCHAR(50) NOT NULL DEFAULT 'today'"
                )
                self.db.conn.commit()

    def _to_tuple(self, notification: Notification) -> tuple:
        return (
            notification.title, notification.notification_type, notification.notification_class,
            notification.notification_data, notification.created_at)

    def _to_object(self, row: tuple) -> Notification:
        notification_dict = {
            "id": row[0],
            "title": row[1],
            "notification_type": row[2],
            "notification_class": row[3],
            "notification_data": row[4],
            "created_at": row[5]
        }
        return Notification(**notification_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["title", "notification_type", "notification_class", "notification_data", "created_at"]

    def _get_columns_for_update(self) -> List[str]:
        return ["title", "notification_type", "notification_class", "notification_data", "created_at"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "title", "notification_type", "notification_class", "notification_data", "created_at"]

    def queue_email_notification(self, notification: Union[Notification, str]) -> Optional[int]:
        if isinstance(notification, Notification):
            notification_obj = notification
            notification_obj.notification_type = "email"
            if notification_obj.created_at is None:
                notification_obj.created_at = datetime.now()
        else:
            notification_obj = Notification(
                title="Email notification",
                notification_type="email",
                notification_class="system",
                notification_data=str(notification),
                created_at=datetime.now(),
            )
        return self.create(notification_obj)
