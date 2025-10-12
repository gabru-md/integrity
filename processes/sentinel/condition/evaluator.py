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

    def __init__(self, service: EventService):
        """
        Initializes the Evaluator with its required dependencies.

        Args:
            event_service: An instance of the EventService to fetch events.
        """
        self.event_service = service
        self.log = Logger.get_log(self.__class__.__name__)

    def evaluate_contract_on_trigger(self, contract_dict: Dict[str, Any], trigger_event: Any) -> bool:
        trigger_event_type = contract_dict["trigger"]
        if trigger_event.event_type != trigger_event_type:
            self.log.info("Trigger event type mismatch. Skipping evaluation.")
            return False

        self.log.info(
            f"Checking contract for latest trigger at timestamp: {datetime.fromtimestamp(trigger_event.timestamp)}")

        return self._evaluate_conditions(contract_dict["conditions"], trigger_event.timestamp)

    def evaluate_open_contract(self, contract_dict: Dict[str, Any]) -> bool:
        """ evaluates an open contract without a trigger event on current_timestamp """
        current_time = int(datetime.now().timestamp())
        self.log.info(
            f"Checking contract for latest trigger at timestamp: {datetime.fromtimestamp(current_time)}")

        return self._evaluate_conditions(contract_dict["conditions"], current_time)

    def _get_required_event_types(self, condition_dict: Dict[str, Any]) -> List[str]:
        required_events = set()
        if "event" in condition_dict:
            required_events.add(condition_dict["event"])

        if "terms" in condition_dict:
            for term in condition_dict["terms"]:
                required_events.update(self._get_required_event_types(term))

        return list(required_events)

    def _evaluate_conditions(self, condition_dict: Dict[str, Any], trigger_timestamp: int) -> bool:
        max_timestamp = trigger_timestamp
        min_timestamp = 0

        if "time_window" in condition_dict:
            time_window_ms = self._convert_to_milliseconds(condition_dict["time_window"], condition_dict["unit"])
            min_timestamp = trigger_timestamp - time_window_ms
            inner_condition = {k: v for k, v in condition_dict.items() if k not in ["time_window", "unit"]}
            required_event_types = self._get_required_event_types(inner_condition)
            events_to_check = self.event_service.find_by_event_type_and_time_range(
                event_types=required_event_types,
                max_timestamp=max_timestamp,
                min_timestamp=min_timestamp
            )
            return self._evaluate_event_count(inner_condition, events_to_check)

        elif condition_dict.get("type") == "event_count":
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

        elif condition_dict.get("operator") == "NOT":
            # The NOT operator negates the result of its single child term
            term = condition_dict["terms"][0]
            return not self._evaluate_conditions(term, trigger_timestamp)

        raise ValueError(
            f"Unknown condition type or operator: {condition_dict.get('type') or condition_dict.get('operator')}")

    @staticmethod
    def _evaluate_event_count(condition: Dict[str, Any], events_to_check: List[Any]) -> bool:
        target_event = condition["event"]
        min_count = condition["min_count"]

        event_counts = defaultdict(int)
        for event in events_to_check:
            event_counts[event.event_type] += 1

        actual_count = event_counts[target_event]

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


if __name__ == '__main__':
    # Mock classes to simulate the environment for demonstration
    class MockEvent:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id')
            self.event_type = kwargs.get('event_type')
            self.timestamp = kwargs.get('timestamp')


    class MockEventService:
        def __init__(self):
            self.base_ts = int(time.time() * 1000)

        def find_by_event_type_and_time_range(self, event_types, max_timestamp, min_timestamp):
            events = [
                MockEvent(id=1, event_type='exercise', timestamp=self.base_ts - 3600000),
                MockEvent(id=2, event_type='laundry:loaded', timestamp=self.base_ts - 1800000),
                MockEvent(id=3, event_type='exercise', timestamp=self.base_ts - 1200000),
                MockEvent(id=4, event_type='gaming:league_of_legends', timestamp=self.base_ts),
                MockEvent(id=5, event_type='cooking_dinner', timestamp=self.base_ts - 7200000)
            ]

            return [e for e in events if e.event_type in event_types and min_timestamp <= e.timestamp < max_timestamp]


    _event_service = MockEventService()
    evaluator = ContractEvaluator(_event_service)

    # Example: gaming only after cooking_dinner
    contract_gaming_after_cooking = {
        "name": "Gaming only after cooking",
        "trigger": "gaming:league_of_legends",
        "conditions": {
            "operator": "AND",
            "terms": [
                {
                    "type": "event_count",
                    "event": "cooking_dinner",
                    "min_count": 1
                }
            ]
        }
    }

    # Example: No gaming after 10pm (simplified for this evaluator)
    # The logic "after 10pm" would need to be handled by a separate rule engine or in the application logic
    # Here, we can simulate with "No gaming AFTER hand_wash"
    contract_no_gaming_after_hand_wash = {
        "name": "No gaming after hand_wash",
        "trigger": "gaming:league_of_legends",
        "conditions": {
            "operator": "NOT",
            "terms": [
                {
                    "type": "event_count",
                    "event": "hand_wash",
                    "min_count": 1
                }
            ]
        }
    }

    latest_trigger_event = MockEvent(id=4, event_type='gaming:league_of_legends', timestamp=int(time.time() * 1000))
    print("\nEvaluating 'Gaming only after cooking_dinner' contract...")
    result = evaluator.evaluate_contract_on_trigger(contract_gaming_after_cooking, latest_trigger_event)
    print(f"Result: {result}")

    print("\nEvaluating 'No gaming after hand_wash' contract...")
    # This will be true if 'hand_wash' has not occurred
    result = evaluator.evaluate_contract_on_trigger(contract_no_gaming_after_hand_wash, latest_trigger_event)
    print(f"Result: {result}")
