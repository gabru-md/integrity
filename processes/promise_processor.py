import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from gabru.qprocessor.qprocessor import QueueProcessor
from model.event import Event
from model.promise import Promise
from services.promises import PromiseService
from services.events import EventService

class PromiseProcessor(QueueProcessor[Event]):
    def __init__(self, **kwargs):
        self.promise_service = PromiseService()
        self.event_service = EventService()
        super().__init__(service=self.event_service, **kwargs)
        self.sleep_time_sec = 60

    def filter_item(self, event: Event) -> Optional[Event]:
        return event

    def _process_item(self, event: Event) -> bool:
        """Checks if the event fulfills any active promises."""
        active_promises = self.promise_service.get_promises_by_status("active")
        
        # Ensure event.timestamp is timezone-aware (UTC) for comparison
        event_ts_aware = self._make_datetime_utc_aware(event.timestamp)
        if not event_ts_aware:
            self.log.warning(f"Event {event.id} has no valid timestamp, skipping.")
            return True

        for promise in active_promises:
            if self._event_matches_promise(event, promise):
                # Get the start_time for the period ending now (or relevant time)
                # Use datetime.now(timezone.utc) to ensure it's aware.
                current_time_utc = datetime.now(timezone.utc)
                start_time = self._get_start_time(promise, current_time_utc)

                # Compare the event's timestamp (made UTC aware) with the start_time (made UTC aware)
                if event_ts_aware > start_time:
                    # The event falls within the current period. Increment count.
                    promise.current_count += 1
                    self.promise_service.update(promise)
                    self.log.info(f"Event {event.id} incremented current_count for promise: {promise.name}")
        return True

    def _event_matches_promise(self, event: Event, promise: Promise) -> bool:
        if promise.target_event_type and event.event_type == promise.target_event_type:
            return True
        if promise.target_event_tag and promise.target_event_tag in event.tags:
            return True
        return False

    def process(self):
        """Override process to include periodic checks for due promises."""
        while self.running:
            next_item = self.get_next_item()
            if next_item:
                self.process_item(next_item)
            
            self._check_due_promises() # This will use datetime.now(timezone.utc) internally
            
            if not next_item:
                time.sleep(self.sleep_time_sec)

    def _check_due_promises(self):
        """Periodically checks for promises that need evaluation."""
        current_time_utc = datetime.now(timezone.utc)
        due_promises = self.promise_service.get_due_promises()
        if not due_promises:
            return

        self.log.info(f"Checking {len(due_promises)} due promises")
        for promise in due_promises:
            # Pass the current UTC time to _evaluate_promise
            self._evaluate_promise(promise, current_time_utc)

    def _evaluate_promise(self, promise: Promise, current_time_utc: datetime):
        """Evaluates a promise based on event counts within its defined period."""
        end_time = current_time_utc # This is already UTC aware
        start_time = self._get_start_time(promise, end_time)
        
        event_count = self._count_matching_events(promise, start_time, end_time)
        
        fulfilled = event_count >= promise.required_count
        
        if fulfilled:
            promise.status = "fulfilled" if promise.frequency == "once" else "active"
            promise.streak += 1
            promise.total_completions += 1
            if promise.streak > promise.best_streak:
                promise.best_streak = promise.streak
            self.log.info(f"Promise fulfilled: {promise.name} (Count: {event_count})")
        else:
            if promise.frequency != "once":
                promise.streak = 0
                self.log.info(f"Promise broken: {promise.name} (Count: {event_count})")
            else:
                promise.status = "broken"
                self.log.info(f"One-time promise broken: {promise.name}")

        promise.total_periods += 1
        promise.current_count = 0
        promise.last_checked_at = end_time # Store UTC aware time
        promise.next_check_at = self._calculate_next_check(promise, end_time)
        
        self.promise_service.update(promise)

    def _get_start_time(self, promise: Promise, end_time: datetime) -> datetime:
        """Calculates the start time of the period for the promise, ensuring it's UTC aware."""
        # end_time is expected to be UTC aware.
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        last_checked = promise.last_checked_at
        if last_checked:
            # Ensure last_checked is also UTC aware. If loaded naive from DB, assume UTC.
            if last_checked.tzinfo is None:
                last_checked = last_checked.replace(tzinfo=timezone.utc)
            return last_checked
        
        # Fallback based on frequency using end_time (which is UTC aware)
        if promise.frequency == "daily":
            return end_time - timedelta(days=1)
        elif promise.frequency == "weekly":
            return end_time - timedelta(weeks=1)
        elif promise.frequency == "monthly":
            return end_time - timedelta(days=30) # Approximation
        
        # Handle created_at similarly. It might be naive if loaded from DB.
        created_at = promise.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        # Fallback to end_time if created_at is missing or invalid
        return created_at if created_at else end_time

    def _calculate_next_check(self, promise: Promise, last_check: datetime) -> datetime:
        """Calculates the next check time, ensuring it's UTC aware."""
        # last_check is expected to be UTC aware.
        if promise.frequency == "daily":
            return last_check + timedelta(days=1)
        elif promise.frequency == "weekly":
            return last_check + timedelta(weeks=1)
        elif promise.frequency == "monthly":
            return last_check + timedelta(days=30)
        return last_check + timedelta(days=36500) # For 'once', effectively never again

    def _count_matching_events(self, promise: Promise, start_time: datetime, end_time: datetime) -> int:
        """Counts events within the specified UTC aware time window."""
        # start_time and end_time are expected to be UTC aware from the caller.

        filters = {
            "timestamp": {"$gt": start_time, "$lt": end_time}
        }
        if promise.target_event_type:
            filters["event_type"] = promise.target_event_type
        
        # Fetch events. `event.timestamp` needs to be made consistent.
        events = self.event_service.find_all(filters=filters)
        
        count = 0
        for e in events:
            # Ensure event.timestamp is UTC aware for comparison.
            event_ts_aware = self._make_datetime_utc_aware(e.timestamp)
            
            # Compare UTC aware datetimes.
            if event_ts_aware and event_ts_aware > start_time and event_ts_aware < end_time:
                if promise.target_event_tag:
                    if promise.target_event_tag in e.tags:
                        count += 1
                else:
                    count += 1
        return count

    def _make_datetime_utc_aware(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Helper to convert a datetime object to UTC aware. If naive, assumes UTC and makes it aware."""
        if dt is None:
            return None
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            # If naive, assume it's UTC and make it aware
            return dt.replace(tzinfo=timezone.utc)
        else:
            # If already aware, convert to UTC
            return dt.astimezone(timezone.utc)
