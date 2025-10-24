import time
from datetime import datetime
from typing import Dict, Any, List

from gabru.log import Logger
from services.events import EventService


class ContractEvaluator:
    """
    A class to evaluate contracts against a stream of events based on the SCL AST.
    It encapsulates all the logic for checking event-based and clock conditions.
    """

    def __init__(self, service: EventService):
        self.event_service = service
        self.log = Logger.get_log(self.__class__.__name__)

    def evaluate_contract_on_trigger(self, contract_dict: Dict[str, Any], trigger_event: Any) -> bool:
        """Evaluates conditions based on a newly triggered event."""
        trigger_event_type = contract_dict["trigger"]
        if trigger_event.event_type != trigger_event_type:
            self.log.info("Trigger event type mismatch. Skipping evaluation.")
            return False

        self.log.info(
            f"Checking contract for latest trigger at timestamp: {datetime.fromtimestamp(trigger_event.timestamp / 1000)}")

        # Pass the trigger event to evaluation for clock and history checks
        return self._evaluate_conditions(contract_dict["conditions"], trigger_event.timestamp, trigger_event)

    def evaluate_open_contract(self, contract_dict: Dict[str, Any], frequency: str) -> bool:
        """Evaluates an open contract on a current timestamp (no direct trigger event)."""
        current_time_ms = int(time.time())
        self.log.info(
            f"Checking contract for latest trigger at timestamp: {datetime.fromtimestamp(current_time_ms)}")

        # Clock checks are generally not useful for open contracts unless they use the current time
        # We assume they evaluate relative to now for the time window/frequency.
        return self._evaluate_conditions(contract_dict["conditions"], current_time_ms, frequency=frequency)

    def _get_required_event_types(self, condition_dict: Dict[str, Any]) -> List[str]:
        """Recursively finds all event types required for querying the database."""
        required_events = set()

        if condition_dict.get("type") == "event_count":
            required_events.add(condition_dict["event"])

        if condition_dict.get("type") == "history_check":
            required_events.add(condition_dict["event"])
            required_events.add(condition_dict["since_event"])

        if "terms" in condition_dict:
            for term in condition_dict["terms"]:
                required_events.update(self._get_required_event_types(term))

        return list(required_events)

    def _evaluate_conditions(self, condition_dict: Dict[str, Any], trigger_timestamp: int,
                             trigger_event: Any = None, frequency: str = None) -> bool:

        # Handle Clock Check
        if condition_dict.get("type") == "clock_check":
            if not trigger_event:
                self.log.warning(
                    "Clock check condition requires a trigger event but none was provided (Open Contract). Assuming false.")
                return False
            return self._evaluate_clock_condition(condition_dict["time_range"], trigger_event)

        # Handle History Check (SINCE)
        if condition_dict.get("type") == "history_check":
            if not trigger_event:
                self.log.warning(
                    "History check condition requires a trigger event but none was provided. Assuming false.")
                return False
            return self._evaluate_history_check(condition_dict, trigger_event)

        # Handle Event Count (WITHIN)
        if "time_window" in condition_dict:
            # Determine the time window boundary
            if frequency:
                self.log.info(f"Open contract detected. Overriding WITHIN window with contract frequency: {frequency}")
                time_window_ms = self._get_frequency_duration_ms(frequency)
            else:
                time_window_ms = self._convert_to_milliseconds(condition_dict["time_window"], condition_dict["unit"])

            min_timestamp = trigger_timestamp - time_window_ms
            max_timestamp = trigger_timestamp

            inner_condition = {k: v for k, v in condition_dict.items() if k not in ["time_window", "unit"]}
            required_event_types = self._get_required_event_types(inner_condition)

            # Efficiently query the DB for only the required events within the window
            events_to_check = self.event_service.find_by_event_type_and_time_range(
                event_types=required_event_types,
                max_timestamp=max_timestamp,
                min_timestamp=min_timestamp
            )
            return self._evaluate_event_count(inner_condition, events_to_check)

        # Handle Simple Event Count (No WITHIN)
        elif condition_dict.get("type") == "event_count":
            required_event_types = self._get_required_event_types(condition_dict)
            self.log.info(f"{required_event_types}, {trigger_timestamp}")
            events_to_check = self.event_service.find_by_event_type_and_time_range(
                event_types=required_event_types,
                max_timestamp=trigger_timestamp,
                min_timestamp=0  # Check full history
            )
            return self._evaluate_event_count(condition_dict, events_to_check)

        # Handle Logical Operators
        elif condition_dict.get("operator") == "AND":
            for term in condition_dict["terms"]:
                if not self._evaluate_conditions(term, trigger_timestamp, trigger_event, frequency):
                    return False
            return True

        elif condition_dict.get("operator") == "OR":
            for term in condition_dict["terms"]:
                if self._evaluate_conditions(term, trigger_timestamp, trigger_event, frequency):
                    return True
            return False

        elif condition_dict.get("operator") == "NOT":
            term = condition_dict["terms"][0]
            return not self._evaluate_conditions(term, trigger_timestamp, trigger_event, frequency)

        raise ValueError(
            f"Unknown condition type or operator: {condition_dict.get('type') or condition_dict.get('operator')}")

    def _evaluate_history_check(self, condition: Dict[str, Any], trigger_event: Any) -> bool:
        """
        Evaluates EVENT_A SINCE EVENT_B.
        Checks if EVENT_A occurred between the last EVENT_B and the trigger_event.
        """
        event_a = condition["event"]
        event_b = condition["since_event"]
        trigger_timestamp = trigger_event.timestamp

        # Find the last occurrence of EVENT_B before the trigger_event
        # This function should be optimized to return only the latest event efficiently.
        last_event_b = self.event_service.find_latest_event_before(event_type=event_b, max_timestamp=trigger_timestamp)

        # If EVENT_B has never happened, the SINCE condition boundary is the beginning of time (min_timestamp=0).
        min_timestamp = last_event_b.timestamp if last_event_b else 0

        # 2. Check if EVENT_A occurred between min_timestamp and trigger_timestamp
        # We only need to check for existence (min_count: 1)
        events_a_in_range = self.event_service.find_by_event_type_and_time_range(
            event_types=[event_a],
            max_timestamp=trigger_timestamp,
            min_timestamp=min_timestamp
        )

        # Check if any EVENT_A was found in the range (last EVENT_B to trigger_event)
        is_valid = len(events_a_in_range) > 0

        if is_valid:
            self.log.info(f"History check met: {event_a} occurred since last {event_b}.")
        else:
            self.log.info(f"History check failed: {event_a} did NOT occur since last {event_b}.")

        return is_valid

    def _evaluate_clock_condition(self, time_range: Dict[str, Any], trigger_event: Any) -> bool:
        """Evaluates clock(HHMM) [AFTER|BEFORE|BETWEEN] conditions."""
        trigger_time_hhmm = self._get_hhmm_from_timestamp(trigger_event.timestamp)
        op = time_range["op"]
        time1_hhmm = int(time_range["time1"])
        time2_hhmm = int(time_range["time2"]) if time_range["time2"] else None

        is_valid = False

        if op == "AFTER":
            # Valid if trigger time is >= time1
            is_valid = trigger_time_hhmm >= time1_hhmm
        elif op == "BEFORE":
            # Valid if trigger time is < time1 (strictly before)
            is_valid = trigger_time_hhmm < time1_hhmm
        elif op == "BETWEEN":
            # Valid if trigger time is >= time1 AND < time2
            # This handles midnight rollover (e.g., 2200 BETWEEN 0600 is not supported, needs 2 checks)
            # Assuming time1 < time2 for simplicity.
            if time1_hhmm < time2_hhmm:
                is_valid = time1_hhmm <= trigger_time_hhmm < time2_hhmm
            else:
                # Handles rollover (e.g., 2200 BETWEEN 0600)
                is_valid = (trigger_time_hhmm >= time1_hhmm) or (trigger_time_hhmm < time2_hhmm)
        else:
            self.log.error(f"Unknown clock operator: {op}")
            return False

        return is_valid

    @staticmethod
    def _evaluate_event_count(condition: Dict[str, Any], events_to_check: List[Any]) -> bool:
        """Counts events within a list and checks against min_count."""
        target_event = condition["event"]
        min_count = condition["min_count"]

        # Only count the target event, as the list might contain other required events
        actual_count = sum(1 for event in events_to_check if event.event_type == target_event)

        return actual_count >= min_count

    @staticmethod
    def _convert_to_milliseconds(value: int, unit: str) -> int:
        if unit == 's':
            return value * 1000
        elif unit == 'm':
            return value * 60 * 1000
        elif unit == 'h':
            return value * 60 * 60 * 1000
        raise ValueError(f"Unknown time unit: {unit}")

    @staticmethod
    def _get_frequency_duration_ms(frequency: str) -> int:
        """Maps the contract frequency string to a duration in milliseconds."""
        seconds_in_hour = 3600
        seconds_in_day = 86400
        seconds_in_week = 604800
        seconds_in_month = 2592000

        if frequency == "hourly":
            return seconds_in_hour * 1000
        elif frequency == "daily":
            return seconds_in_day * 1000
        elif frequency == "weekly":
            return seconds_in_week * 1000
        elif frequency == "monthly":
            return seconds_in_month * 1000
        raise ValueError(f"Unknown contract frequency: {frequency}")

    @staticmethod
    def _get_hhmm_from_timestamp(timestamp: int) -> int:
        """Converts a Unix timestamp (in milliseconds) to an HHMM integer."""
        if timestamp > 1000000000000:  # Heuristic: Assume > 1 trillion is ms
            timestamp = timestamp // 1000

        dt_object = datetime.fromtimestamp(timestamp)
        return int(dt_object.strftime("%H%M"))
