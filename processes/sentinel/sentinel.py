import datetime
import time

from gabru.log import Logger
from gabru.qprocessor.qprocessor import QueueProcessor, T
from model.contract import Contract
from model.event import Event
from processes.sentinel.condition.evaluator import ContractEvaluator
from services.contracts import ContractService
from processes.sentinel.condition.parser import parse_contract_as_dict
from services.events import EventService


class Sentinel(QueueProcessor[Event]):

    def __init__(self):
        self.event_service = EventService()

        super().__init__(name=self.__class__.__name__, service=self.event_service)

        self.log = Logger.get_log(self.__class__.__name__)
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

        # 3. invalidate the contracts
        for contract in contracts_to_invalidate:
            if contract.frequency == "ad-hoc":
                contract.is_valid = False
                self.contract_service.update(contract)
            else:
                # do not invalidate any other contract
                self.log.info(f"{contract.name} [{contract.frequency}] remains valid")

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
