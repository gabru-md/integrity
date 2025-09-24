from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict
import time

from gabru.log import Logger
from services.events import EventService


class ContractEvaluator:
    """
    A class to evaluate contracts against a stream of events.
    It encapsulates all the logic for checking event-based conditions.
    """

    def __init__(self):
        """
        Initializes the Evaluator with its required dependencies.

        Args:
            event_service: An instance of the EventService to fetch events.
        """
        self.event_service = EventService()
        self.log = Logger.get_log(self.__class__.__name__)

    def evaluate_contract_on_trigger(self, contract_dict: Dict[str, Any], trigger_event: Any) -> bool:
        """
        Evaluates a contract based on a single, newly triggered event.

        Args:
            contract_dict: The contract dictionary to evaluate.
            trigger_event: The single, latest event that triggered this evaluation.

        Returns:
            bool: True if the contract is met, False otherwise.
        """
        trigger_event_type = contract_dict["trigger"]
        if trigger_event.event_type != trigger_event_type:
            self.log.info("Trigger event type mismatch. Skipping evaluation.")
            return False

        self.log.info(
            f"Checking contract for latest trigger at timestamp: {datetime.fromtimestamp(trigger_event.timestamp / 1000)}")

        return self._evaluate_conditions(contract_dict["conditions"], trigger_event.timestamp)

    def _get_required_event_types(self, condition_dict: Dict[str, Any]) -> List[str]:
        """
        Recursively walks the condition tree to find all unique event types required.
        """
        required_events = set()

        if "event" in condition_dict:
            required_events.add(condition_dict["event"])

        if "terms" in condition_dict:
            for term in condition_dict["terms"]:
                required_events.update(self._get_required_event_types(term))

        return list(required_events)

    def _evaluate_conditions(self, condition_dict: Dict[str, Any], trigger_timestamp: int) -> bool:
        """
        Recursively evaluates a condition dictionary.
        This function now handles temporal filtering and fetches only the required data.
        """
        # Determine the min and max timestamps for this specific condition
        max_timestamp = trigger_timestamp
        min_timestamp = 0  # Default to the beginning of time

        # Check if the condition has a time window
        if "time_window" in condition_dict:
            time_window_ms = self._convert_to_milliseconds(condition_dict["time_window"], condition_dict["unit"])
            min_timestamp = trigger_timestamp - time_window_ms

            # Since this is a nested temporal condition, we need to strip the time window
            # keys so the inner condition can be evaluated correctly.
            inner_condition = {k: v for k, v in condition_dict.items() if k not in ["time_window", "unit"]}

            # Find the event types for the inner condition
            required_event_types = self._get_required_event_types(inner_condition)

            # Fetch events from the database only for this specific time window
            events_to_check = self.event_service.find_by_event_type_and_time_range(
                event_types=required_event_types,
                max_timestamp=max_timestamp,
                min_timestamp=min_timestamp
            )

            return self._evaluate_event_count(inner_condition, events_to_check)

        elif condition_dict.get("type") == "event_count":
            # If it's a direct event count without a time window, find the events
            required_event_types = self._get_required_event_types(condition_dict)
            events_to_check = self.event_service.find_by_event_type_and_time_range(
                event_types=required_event_types,
                max_timestamp=max_timestamp,
                min_timestamp=min_timestamp
            )
            return self._evaluate_event_count(condition_dict, events_to_check)

        elif condition_dict.get("operator") == "AND":
            for term in condition_dict["terms"]:
                if not self._evaluate_conditions(term, trigger_timestamp):
                    self.log.info("Contract not met for some trigger event instance.")
                    return False
            self.log.info(
                f"Contract conditions met at timestamp: {datetime.fromtimestamp(trigger_timestamp / 1000)}")
            return True

        elif condition_dict.get("operator") == "OR":
            for term in condition_dict["terms"]:
                if self._evaluate_conditions(term, trigger_timestamp):
                    self.log.info(
                        f"Contract conditions met at timestamp: {datetime.fromtimestamp(trigger_timestamp / 1000)}")
                    return True

            self.log.info("Contract not met for any trigger event instance.")
            return False

        raise ValueError(
            f"Unknown condition type or operator: {condition_dict.get('type') or condition_dict.get('operator')}")

    @staticmethod
    def _evaluate_event_count(condition: Dict[str, Any], events_to_check: List[Any]) -> bool:
        """
        Evaluates a single event_count condition.
        """
        target_event = condition["event"]
        min_count = condition["min_count"]

        event_counts = defaultdict(int)
        for event in events_to_check:
            event_counts[event.event_type] += 1

        actual_count = event_counts[target_event]

        return actual_count >= min_count

    @staticmethod
    def _convert_to_milliseconds(value: int, unit: str) -> int:
        """
        Converts a time value and unit to milliseconds.
        """
        if unit == 's':
            return value * 1000
        elif unit == 'm':
            return value * 60 * 1000
        elif unit == 'h':
            return value * 60 * 60 * 1000
        raise ValueError(f"Unknown time unit: {unit}")


if __name__ == '__main__':
    class MockEvent:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id')
            self.event_type = kwargs.get('event_type')
            self.timestamp = kwargs.get('timestamp')


    class MockEventService:
        def __init__(self):
            # A base timestamp for our mock events (e.g., now)
            self.base_ts = int(time.time() * 1000)

        def find_by_event_type_and_time_range(self, event_types, max_timestamp, min_timestamp):
            events = [
                MockEvent(id=1, event_type='exercise', timestamp=self.base_ts - 3600000),  # 1 hour ago
                MockEvent(id=2, event_type='laundry:loaded', timestamp=self.base_ts - 1800000),  # 30 mins ago
                MockEvent(id=3, event_type='exercise', timestamp=self.base_ts - 1200000),  # 20 mins ago
                MockEvent(id=4, event_type='gaming:league_of_legends', timestamp=self.base_ts)  # Now
            ]

            # Simulate database filtering with both min and max timestamps
            return [e for e in events if e.event_type in event_types and min_timestamp <= e.timestamp < max_timestamp]


    _event_service = MockEventService()
    evaluator = ContractEvaluator(_event_service)

    # Let's get the most recent trigger event to pass to the evaluator
    latest_trigger_event = MockEvent(id=4, event_type='gaming:league_of_legends', timestamp=int(time.time() * 1000))

    # Define the contract with time constraints
    contract = {
        "name": "Generated Contract",
        "trigger": "gaming:league_of_legends",
        "conditions": {
            "operator": "AND",
            "terms": [
                {
                    "type": "event_count",
                    "event": "exercise",
                    "min_count": 2,
                    "time_window": 1,
                    "unit": "h"
                },
                {
                    "type": "event_count",
                    "event": "laundry:loaded",
                    "min_count": 1,
                    "time_window": 30,
                    "unit": "m"
                }
            ]
        }
    }

    # Evaluate the contract using the new optimized method
    result = evaluator.evaluate_contract_on_trigger(contract, latest_trigger_event)
    # print(f"\nFinal contract evaluation result: {result}")
