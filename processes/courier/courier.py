import os
import time
import requests
from gabru.qprocessor.qprocessor import QueueProcessor
from model.event import Event
from model.notification import Notification
from services.events import EventService
from services.notifications import NotificationService
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


class Courier(QueueProcessor[Event]):
    """
    Courier class handles notification dispatch.
    Supports:
    - ntfy.sh (Default)
    - Email (via SendGrid if 'email' tag is present)
    """

    def __init__(self, **kwargs):
        super().__init__(service=EventService(), **kwargs)
        self.notification_service = NotificationService()

        # Email Configuration
        self.sender_email = os.getenv("COURIER_SENDER_EMAIL")
        self.receiver_email = os.getenv("COURIER_RECEIVER_EMAIL")
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")

        # ntfy.sh Configuration
        self.ntfy_base_url = os.getenv("NTFY_BASE_URL", "https://ntfy.sh").rstrip("/")
        self.ntfy_topic = os.getenv("NTFY_TOPIC", "rasbhari-alerts")
        self.ntfy_url = f"{self.ntfy_base_url}/{self.ntfy_topic}"
        self.ntfy_retry_attempts = 3
        self.ntfy_retry_delays_sec = [2, 5, 10]

        # Processing Filter
        self.allowed_event_tag_types = ['notification']

    def filter_item(self, event: Event):
        """
        Only process events that have the 'notification' tag.
        """
        if event.tags and 'notification' in event.tags:
            return event
        return None

    def _process_item(self, event: Event) -> bool:
        """
        Dispatch notification based on tags. 
        If 'email' tag exists, send email. Otherwise, default to ntfy.sh.
        """
        success = False
        notification_type = "ntfy"

        if 'email' in (event.tags or []):
            notification_type = "email"
            success = self.create_email_notification(event)
        else:
            success = self.send_ntfy_notification(event)

        if success:
            notification_dict = {
                "notification_type": notification_type,
                "notification_data": event.description,
                "created_at": int(time.time())
            }
            notification = Notification(**notification_dict)
            self.notification_service.create(notification)
            return True
        else:
            self.log.warn(f"Could not send {notification_type} notification for event {event.id}")
            return False

    def create_email_notification(self, event: Event) -> bool:
        """
        Sends email via SendGrid.
        """
        try:
            if not self.sendgrid_api_key:
                self.log.error("SENDGRID_API_KEY not configured")
                return False

            message = Mail(
                from_email=self.sender_email,
                to_emails=self.receiver_email,
                subject=f"Rasbhari Alert: {event.event_type}",
                plain_text_content=event.description
            )

            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)

            if response.status_code in (200, 202):
                self.log.info(f"Email sent via SendGrid for event: {event.id}")
                return True
            else:
                self.log.warn(f"SendGrid failed: {response.status_code} {response.body}")
        except Exception as e:
            self.log.exception(f"Exception during email notification: {e}")
        return False

    def send_ntfy_notification(self, event: Event) -> bool:
        """
        Dispatches a POST request to ntfy.sh
        """
        headers = {
            "Title": f"Rasbhari Alert: {event.event_type}",
            "Priority": "high",
            "Tags": "warning,robot"
        }

        # Add event tags to ntfy tags
        if event.tags:
            other_tags = [t for t in event.tags if t not in ['notification', 'ntfy']]
            if other_tags:
                headers["Tags"] += "," + ",".join(other_tags)

        for attempt in range(1, self.ntfy_retry_attempts + 1):
            try:
                response = requests.post(
                    self.ntfy_url,
                    data=event.description.encode('utf-8'),
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    self.log.info(f"ntfy notification sent for event {event.id} on attempt {attempt}")
                    return True

                self.log.warn(
                    f"ntfy server returned error on attempt {attempt}/{self.ntfy_retry_attempts}: "
                    f"{response.status_code} {response.text}"
                )
            except Exception as e:
                self.log.error(
                    f"Failed to send ntfy notification on attempt {attempt}/{self.ntfy_retry_attempts}: {str(e)}"
                )

            if attempt < self.ntfy_retry_attempts:
                delay = self.ntfy_retry_delays_sec[min(attempt - 1, len(self.ntfy_retry_delays_sec) - 1)]
                self.log.info(f"Retrying ntfy notification for event {event.id} in {delay}s")
                time.sleep(delay)

        return False
