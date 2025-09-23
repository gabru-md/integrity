import threading
import time

from gabru.log import Logger
from model.contract import Contract
from model.event import Event
from services.contracts import ContractService
from services.events import EventService


class Sentinel(threading.Thread):
    def __init__(self):
        super().__init__()
        self.log = Logger.get_log(self.__class__.name)
        self.event_service = EventService()
        self.contract_service = ContractService()
        self.sleep_duration_sec = 5

    def run(self):
        self.log.info("Sentinel service is running")
        try:
            last_event_id = self.get_most_recent_event_id()
            while True:
                most_recent_event_id = self.get_most_recent_event_id()
                if most_recent_event_id > last_event_id:
                    self.log.info("New event detected. Processing...")
                    new_events = self.get_new_events_after(last_event_id)
                    for event in new_events:
                        self.validate_event(event)
                    last_event_id = most_recent_event_id

                self.sleep()
        except Exception as e:
            self.log.exception(e)
        finally:
            self.log.info("Sentinel service is stopped")

    def sleep(self):
        self.log.info(f"Sleeping for {self.sleep_duration_sec}s")
        time.sleep(self.sleep_duration_sec)

    def get_most_recent_event_id(self):
        return self.event_service.get_most_recent_item_id()

    def get_new_events_after(self, last_event_id):
        return self.event_service.get_all_items_after(last_event_id)

    def validate_event(self, event: Event):
        contracts_to_invalidate = []
        # 1. try to validate associated contracts
        associated_contracts = self.contract_service.get_associated_valid_contracts(event.event_type)
        if associated_contracts:
            for contract in associated_contracts:
                is_valid = self.run_contract_validation(contract)
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
                is_valid = self.run_contract_validation(contract)
                if is_valid:
                    self.log.info(f"Contract {contract.name} remains valid")
                else:
                    self.log.info(f"Contract {contract.name} was invalidated")
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

    def run_contract_validation(self, contract: Contract) -> bool:
        # need to figure out how to build the contract conditions and how to validate them
        return False

    def queue_contract_invalidated_event(self, contract):
        event_dict = {
            "event_type": "contract:invalidation",
            "timestamp": int(time.time()),
            "description": f"Contract: {contract.name} rendered invalid",
            "tags": ["contracts"]
        }
        contract_invalidated_event = Event(**event_dict)
        self.event_service.create(contract_invalidated_event)
