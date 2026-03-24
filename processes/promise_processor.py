import time
from datetime import datetime, timedelta
from typing import List, Optional

from gabru.qprocessor.qprocessor import QueueProcessor
from model.event import Event
from model.promise import Promise
from services.promises import PromiseService
from services.events import EventService

class PromiseProcessor(QueueProcessor[Event]):
    """
    Processes events to check for promise fulfillment and handles
    periodic checks for promise violations.
    """

    def __init__(self, **kwargs):
        self.promise_service = PromiseService()
        self.event_service = EventService()
        super().__init__(service=self.event_service, **kwargs)
        self.sleep_time_sec = 60  # Check every minute for due promises

    def filter_item(self, event: Event) -> Optional[Event]:
        # Process all events to see if they match any active promises
        return event

    def _process_item(self, event: Event) -> bool:
        """Checks if the event fulfills any active promises."""
        active_promises = self.promise_service.get_promises_by_status("active")
        for promise in active_promises:
            if self._event_matches_promise(event, promise):
                self.log.info(f"Event {event.id} matches promise: {promise.name}")
                # We don't immediately fulfill it here because it might be a recurring promise
                # that needs N events. We just log it or we could have a temporary counter.
                # Actually, let's keep it simple: the periodic check will count events.
                pass
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
            # 1. Process queued events (standard QueueProcessor behavior)
            next_item = self.get_next_item()
            if next_item:
                self.process_item(next_item)
            
            # 2. Check for due promises (periodic check)
            self._check_due_promises()
            
            if not next_item:
                time.sleep(self.sleep_time_sec)

    def _check_due_promises(self):
        due_promises = self.promise_service.get_due_promises()
        if not due_promises:
            return

        self.log.info(f"Checking {len(due_promises)} due promises")
        for promise in due_promises:
            self._evaluate_promise(promise)

    def _evaluate_promise(self, promise: Promise):
        # Calculate the window for this promise
        end_time = datetime.now()
        start_time = self._get_start_time(promise, end_time)
        
        # Count events in the window
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
                # We could set status to 'broken' but for recurring ones we might just reset streak
            else:
                promise.status = "broken"
                self.log.info(f"One-time promise broken: {promise.name}")

        promise.total_periods += 1
        promise.last_checked_at = end_time
        promise.next_check_at = self._calculate_next_check(promise, end_time)
        
        self.promise_service.update(promise)

    def _get_start_time(self, promise: Promise, end_time: datetime) -> datetime:
        if promise.last_checked_at:
            return promise.last_checked_at
        
        # Fallback based on frequency
        if promise.frequency == "daily":
            return end_time - timedelta(days=1)
        elif promise.frequency == "weekly":
            return end_time - timedelta(weeks=1)
        elif promise.frequency == "monthly":
            return end_time - timedelta(days=30)
        return promise.created_at

    def _calculate_next_check(self, promise: Promise, last_check: datetime) -> datetime:
        if promise.frequency == "daily":
            return last_check + timedelta(days=1)
        elif promise.frequency == "weekly":
            return last_check + timedelta(weeks=1)
        elif promise.frequency == "monthly":
            return last_check + timedelta(days=30)
        return last_check + timedelta(years=100) # For 'once', effectively never again

    def _count_matching_events(self, promise: Promise, start_time: datetime, end_time: datetime) -> int:
        filters = {
            "timestamp": {"$gt": start_time, "$lt": end_time}
        }
        if promise.target_event_type:
            filters["event_type"] = promise.target_event_type
        
        # Note: CRUDService find_all doesn't directly support array containment for tags easily via the dict filter
        # unless implemented in the service. Let's fetch and filter in memory if tag is used.
        events = self.event_service.find_all(filters=filters)
        
        if promise.target_event_tag:
            return sum(1 for e in events if promise.target_event_tag in e.tags)
        
        return len(events)
