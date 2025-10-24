from gabru.db.service import CRUDService, T
from model.contract import Contract
from typing import List, Optional
from gabru.db.db import DB


class ContractService(CRUDService[Contract]):
    def __init__(self):
        super().__init__(
            "contracts", DB("contracts")
        )

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS contracts (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        frequency VARCHAR(50),
                        trigger_event VARCHAR(255),
                        conditions TEXT,
                        violation_message TEXT,
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        last_run_date TIMESTAMP,
                        next_run_date TIMESTAMP
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, contract: Contract) -> tuple:
        return (contract.name, contract.description, contract.frequency, contract.trigger_event,
                contract.conditions, contract.violation_message, contract.start_time, contract.end_time,
                contract.last_run_date, contract.next_run_date)

    def _to_object(self, row: tuple) -> Contract:
        contract_dict = {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "frequency": row[3],
            "trigger_event": row[4],
            "conditions": row[5],
            "violation_message": row[6],
            "start_time": row[7],
            "end_time": row[8],
            "last_run_date": row[9],
            "next_run_date": row[10]
        }
        return Contract(**contract_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "description", "frequency", "trigger_event", "conditions",
                "violation_message", "start_time", "end_time", "last_run_date", "next_run_date"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "description", "frequency", "trigger_event", "conditions",
                "violation_message", "start_time", "end_time", "last_run_date", "next_run_date"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "description", "frequency", "trigger_event", "conditions",
                "violation_message", "start_time", "end_time", "last_run_date", "next_run_date"]

    def get_contracts_linked_to_event_type(self, event_type) -> List[Contract]:
        with self.db.conn.cursor() as cursor:
            query = "SELECT * FROM contracts WHERE trigger_event = %s and end_time > now() and start_time <= now()"
            cursor.execute(query, (event_type,))
            rows = cursor.fetchall()
            contracts = [self._to_object(row) for row in rows]
        return contracts

    def get_open_contracts(self) -> List[Contract]:
        """ Get the contracts not associated to trigger_event """
        try:
            with self.db.conn.cursor() as cursor:
                query = "SELECT * FROM contracts WHERE trigger_event is null and end_time > now() and next_run_date <= now()"
                cursor.execute(query)
                rows = cursor.fetchall()
                contracts = [self._to_object(row) for row in rows]
            return contracts
        except Exception as e:
            self.log.exception(e)
            return None

    def create(self, obj: Contract) -> Optional[int]:
        if obj.trigger_event == "":
            obj.trigger_event = None
        obj.last_run_date = obj.next_run_date
        return super().create(obj)

    def update(self, obj: Contract) -> bool:
        if obj.trigger_event == "":
            obj.trigger_event = None
        return super().update(obj)
