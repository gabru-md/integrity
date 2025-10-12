import time
from datetime import datetime

from gabru.process import Process
from gabru.qprocessor.qprocessor import QueueProcessor
from model.contract import Contract
from model.event import Event
from processes.sentinel.condition.evaluator import ContractEvaluator
from services.contracts import ContractService
from processes.sentinel.condition.parser import parse_contract_as_dict
from services.events import EventService

event_service = EventService()
contract_service = ContractService()
evaluator = ContractEvaluator(event_service)


class SentinelOC(Process):
    def __init__(self, **kwargs):
        super().__init__('SentinelOC', daemon=True)
        self.sleep_time_min = 15
        self.sleep_time_sec = 60 * self.sleep_time_min

    def process(self):
        while self.running:
            try:
                self.validate_open_contracts()
            except Exception as e:
                self.log.exception(e)

            self.sleep()

    def validate_open_contracts(self):
        open_contracts = contract_service.get_open_contracts()
        if open_contracts:
            for contract in open_contracts:
                is_valid = run_contract_validation(contract)
                if is_valid:
                    self.log.info(f"Open Contract {contract.name} remains valid")
                else:
                    self.log.info(f"Open Contract {contract.name} was invalidated")
                    queue_contract_invalidated_event(contract)

            self.update_last_run_next_run(open_contracts)

    @staticmethod
    def update_last_run_next_run(open_contracts):
        """
            here we need to invalidate them, then update the last_run_date
            depending on the frequency we then need to adjust the next run date
        """

        seconds_in_hour = 3600
        seconds_in_day = 86400
        seconds_in_week = 604800
        seconds_in_month = 2592000

        for contract in open_contracts:
            contract: Contract = contract
            current_timestamp = int(datetime.now().timestamp())
            contract.last_run_date = current_timestamp

            if contract.frequency == "daily":
                contract.next_run_date = current_timestamp + seconds_in_day
            elif contract.frequency == "hourly":
                contract.next_run_date = current_timestamp + seconds_in_hour
            elif contract.frequency == "weekly":
                contract.next_run_date = current_timestamp + seconds_in_week
            elif contract.frequency == "monthly":
                contract.next_run_date = current_timestamp + seconds_in_month

            # update the last run and next run date in db
            contract_service.update(contract)

    def sleep(self):
        self.log.info(f"Nothing to do, waiting for {self.sleep_time_sec}s")
        time.sleep(self.sleep_time_sec)


class Sentinel(QueueProcessor[Event]):

    def __init__(self, **kwargs):
        super().__init__(service=event_service, **kwargs)
        self.excluded_event_types = []

    def filter_item(self, event: Event):
        if event.event_type in self.excluded_event_types:
            return None
        return event

    def _process_item(self, event: Event) -> bool:
        try:
            self.validate_event(event=event)
        except Exception as e:
            self.log.exception(e)
            return False
        return True

    def validate_event(self, event: Event):
        # 1. try to validate associated contracts
        associated_contracts = contract_service.get_contracts_linked_to_event_type(event.event_type)
        if associated_contracts:
            for contract in associated_contracts:
                is_valid = run_contract_validation(contract, event)
                if is_valid:
                    self.log.info(f"Contract {contract.name} remains valid")
                else:
                    self.log.info(f"Contract {contract.name} was invalidated")
                    queue_contract_invalidated_event(contract)

            self.update_last_run(associated_contracts)

    @staticmethod
    def update_last_run(triggered_contracts):
        """
            do nothing in this case as these are trigger based contracts
            even if it is invalidated we still want to check them anytime
            the trigger event is produced.
        """
        for contract in triggered_contracts:
            contract: Contract = contract
            contract.last_run_date = int(datetime.now().timestamp())

            # update the last run
            contract_service.update(contract)


def run_contract_validation(contract: Contract, trigger_event: Event = None) -> bool:
    # need to figure out how to build the contract conditions and how to validate them
    condition_dict = parse_contract_as_dict(contract.conditions)
    if condition_dict:
        if trigger_event:
            return evaluator.evaluate_contract_on_trigger(condition_dict, trigger_event)
        return evaluator.evaluate_open_contract(condition_dict)
    return False


def queue_contract_invalidated_event(contract):
    event_dict = {
        "event_type": "contract:invalidation",
        "timestamp": int(time.time()),
        "description": f"Contract: {contract.name} rendered invalid",
        "tags": ["contracts", "notification"]
    }
    contract_invalidated_event = Event(**event_dict)
    event_service.create(contract_invalidated_event)
