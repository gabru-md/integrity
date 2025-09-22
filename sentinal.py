from contract_db import ContractService
from gabru.log import Logger
import time


class Sentinal:
    def __init__(self):
        self.log = Logger.get_log(self.__class__.__name__)
        self.contract_service = ContractService()

    def run(self):
        self.log.info("Sentinel service is running")

        last_event_count = self.get_total_event_count()

        while True:
            current_event_count = self.get_total_event_count()
            if current_event_count > last_event_count:
                self.log.info("New event(s) detected. Processing...")
                new_events = self.get_new_events(current_event_count - last_event_count)
                for event in new_events:
                    self.validate_event(event)
                last_event_count = current_event_count

                # Wait for a short period before checking again
            time.sleep(5)  # Poll every 5 seconds

    def get_total_event_count(self) -> int:
        if not self.events_db.conn:
            self.log.error("Failed to connect to events database.")
            return -1
        with self.events_db.conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM events")
            return cursor.fetchone()[0]

    def get_total_event_count(self):
        pass
