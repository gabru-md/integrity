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
                        user_id INTEGER,
                        title VARCHAR(255),
                        notification_type VARCHAR(255) NOT NULL,
                        notification_class VARCHAR(50) NOT NULL DEFAULT 'today',
                        notification_data VARCHAR(500) NOT NULL,
                        href VARCHAR(500),
                        is_read BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMP
                    )
                """)
                cursor.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS user_id INTEGER")
                cursor.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS title VARCHAR(255)")
                cursor.execute(
                    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS notification_class VARCHAR(50) NOT NULL DEFAULT 'today'"
                )
                cursor.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS href VARCHAR(500)")
                cursor.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_read BOOLEAN NOT NULL DEFAULT FALSE")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_id_created_at ON notifications (user_id, created_at DESC)")
                self.db.conn.commit()

    def _to_tuple(self, notification: Notification) -> tuple:
        return (
            notification.user_id,
            notification.title,
            notification.notification_type,
            notification.notification_class,
            notification.notification_data,
            notification.href,
            notification.is_read,
            notification.created_at,
        )

    def _to_object(self, row: tuple) -> Notification:
        notification_dict = {
            "id": row[0],
            "user_id": row[1],
            "title": row[2],
            "notification_type": row[3],
            "notification_class": row[4],
            "notification_data": row[5],
            "href": row[6],
            "is_read": row[7],
            "created_at": row[8],
        }
        return Notification(**notification_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["user_id", "title", "notification_type", "notification_class", "notification_data", "href", "is_read", "created_at"]

    def _get_columns_for_update(self) -> List[str]:
        return ["user_id", "title", "notification_type", "notification_class", "notification_data", "href", "is_read", "created_at"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "user_id", "title", "notification_type", "notification_class", "notification_data", "href", "is_read", "created_at"]

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

    def create_in_app_notification(
        self,
        *,
        user_id: int,
        title: str,
        body: str,
        href: Optional[str] = None,
        notification_class: str = "today",
        created_at: Optional[datetime] = None,
    ) -> Optional[int]:
        notification = Notification(
            user_id=user_id,
            title=title,
            notification_data=body,
            href=href,
            notification_type="in_app",
            notification_class=notification_class,
            is_read=False,
            created_at=created_at or datetime.now(),
        )
        return self.create(notification)

    def get_in_app_notifications(self, user_id: int, limit: int = 6, include_read: bool = False) -> List[Notification]:
        columns = ", ".join(self._get_columns_for_select())
        query = f"""
            SELECT {columns}
            FROM {self.table_name}
            WHERE user_id = %s AND notification_type = %s
        """
        params: list[object] = [user_id, "in_app"]
        if not include_read:
            query += " AND is_read = FALSE"
        query += " ORDER BY created_at DESC, id DESC LIMIT %s"
        params.append(limit)

        def operation(conn):
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                return [self._to_object(row) for row in rows]

        return self._run_with_connection_retry(
            operation,
            fallback=[],
            action_name="get_in_app_notifications on notifications",
        )

    def count_unread_in_app_notifications(self, user_id: int) -> int:
        query = f"""
            SELECT COUNT(*)
            FROM {self.table_name}
            WHERE user_id = %s AND notification_type = %s AND is_read = FALSE
        """

        def operation(conn):
            with conn.cursor() as cursor:
                cursor.execute(query, (user_id, "in_app"))
                row = cursor.fetchone()
                return row[0] if row else 0

        return self._run_with_connection_retry(
            operation,
            fallback=0,
            action_name="count_unread_in_app_notifications on notifications",
        )

    def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        query = f"""
            UPDATE {self.table_name}
            SET is_read = TRUE
            WHERE id = %s AND user_id = %s AND notification_type = %s
        """

        def operation(conn):
            with conn.cursor() as cursor:
                cursor.execute(query, (notification_id, user_id, "in_app"))
                conn.commit()
                return cursor.rowcount > 0

        return self._run_with_connection_retry(
            operation,
            fallback=False,
            action_name="mark_as_read on notifications",
        )

    def mark_all_as_read(self, user_id: int) -> bool:
        query = f"""
            UPDATE {self.table_name}
            SET is_read = TRUE
            WHERE user_id = %s AND notification_type = %s AND is_read = FALSE
        """

        def operation(conn):
            with conn.cursor() as cursor:
                cursor.execute(query, (user_id, "in_app"))
                conn.commit()
                return True

        return self._run_with_connection_retry(
            operation,
            fallback=False,
            action_name="mark_all_as_read on notifications",
        )
