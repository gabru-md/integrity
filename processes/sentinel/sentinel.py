import time
from datetime import datetime

from gabru.qprocessor.qprocessor import QueueProcessor
from model.contract import Contract
from model.event import Event
from processes.sentinel.condition.evaluator import ContractEvaluator
from services.contracts import ContractService
from processes.sentinel.condition.parser import parse_contract_as_dict
from services.events import EventService


class Sentinel(QueueProcessor[Event]):

    def __init__(self, **kwargs):
        self.event_service = EventService()

        super().__init__(name=self.__class__.__name__, service=self.event_service, **kwargs)

        self.excluded_event_types = []
        self.contract_service = ContractService()
        self.evaluator = ContractEvaluator(self.event_service)

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
        contracts_to_invalidate = []
        # 1. try to validate associated contracts
        associated_contracts = self.contract_service.get_associated_valid_contracts(event.event_type)
        if associated_contracts:
            for contract in associated_contracts:
                is_valid = self.run_contract_validation(contract, event)
                if is_valid:
                    self.log.info(f"Contract {contract.name} remains valid")
                else:
                    self.log.info(f"Contract {contract.name} was invalidated")
                    self.queue_contract_invalidated_event(contract)
                    # add to contracts to invalidate later
                    contracts_to_invalidate.append(contract)

        self.invalidate_trigger_based_contracts(contracts_to_invalidate)

        contracts_to_invalidate = []
        # 2. try to validate the open contracts
        open_contracts = self.contract_service.get_open_contracts()
        if open_contracts:
            for contract in open_contracts:
                is_valid = self.run_contract_validation(contract, event)
                if is_valid:
                    self.log.info(f"Open Contract {contract.name} remains valid")
                else:
                    self.log.info(f"Open Contract {contract.name} was invalidated")
                    self.queue_contract_invalidated_event(contract)
                    # add to contracts to invalidate later
                    contracts_to_invalidate.append(contract)

        self.invalidate_open_contracts(contracts_to_invalidate)

    def invalidate_trigger_based_contracts(self, contracts_to_invalidate):
        """
            do nothing in this case as these are trigger based contracts
            even if it is invalidated we still want to check them anytime
            the trigger event is produced.
        """
        for contract in contracts_to_invalidate:
            contract: Contract = contract
            contract.last_run_date = int(datetime.now().timestamp())

            # update the last run
            self.contract_service.update(contract)

    def invalidate_open_contracts(self, contracts_to_invalidate):
        """
            here we need to invalidate them, then update the last_run_date
            depending on the frequency we then need to adjust the next run date
        """

        seconds_in_hour = 3600
        seconds_in_day = 86400
        seconds_in_week = 604800
        seconds_in_month = 2592000

        for contract in contracts_to_invalidate:
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
            self.contract_service.update(contract)

    def run_contract_validation(self, contract: Contract, trigger_event: Event) -> bool:
        # need to figure out how to build the contract conditions and how to validate them
        condition_dict = parse_contract_as_dict(contract.conditions)
        if condition_dict:
            return self.evaluator.evaluate_contract_on_trigger(condition_dict, trigger_event)
        return False

    def queue_contract_invalidated_event(self, contract):
        event_dict = {
            "event_type": "contract:invalidation",
            "timestamp": int(time.time()),
            "description": f"Contract: {contract.name} rendered invalid",
            "tags": ["contracts", "notification"]
        }
        contract_invalidated_event = Event(**event_dict)
        self.event_service.create(contract_invalidated_event)
