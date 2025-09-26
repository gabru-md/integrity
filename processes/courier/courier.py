import os
import time
from gabru.qprocessor.qprocessor import QueueProcessor
from model.event import Event
from model.notification import Notification
from services.events import EventService
from services.notifications import NotificationService
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


class Courier(QueueProcessor[Event]):
    """
    Courier class sending emails via SendGrid API
    """

    def __init__(self):
        super().__init__("Courier", EventService())
        self.notification_service = NotificationService()

        self.sender_email = os.getenv("COURIER_SENDER_EMAIL")
        self.receiver_email = os.getenv("COURIER_RECEIVER_EMAIL")
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")

        self.allowed_event_tag_types = ['notification']

    def filter_item(self, event: Event):
        if event.tags:
            for tag in self.allowed_event_tag_types:
                if tag in event.tags:
                    return event
        return None

    def _process_item(self, event: Event) -> bool:
        notification_dict = {
            "notification_type": "email",
            "notification_data": event.description,
            "created_at": int(time.time())
        }
        notification = Notification(**notification_dict)
        if self.create_email_notification(event):
            self.notification_service.create(notification)
        else:
            self.log.warn("Could not send email notification")

    def create_email_notification(self, event: Event) -> bool:
        try:
            message = Mail(
                from_email=self.sender_email,
                to_emails=self.receiver_email,
                subject=f"Courier: {event.id}",
                plain_text_content=event.description
            )

            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)

            if response.status_code in (200, 202):
                self.log.info(f"Email sent via SendGrid: {event.id}")
                return True
            else:
                self.log.warn(f"SendGrid failed: {response.status_code} {response.body}")
        except Exception as e:
            self.log.exception(e)
        return False
