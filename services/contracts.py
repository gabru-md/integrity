from gabru.service import CRUDService
from model.contract import Contract
from typing import List
import time
from gabru.db import DB


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
                        is_valid BOOLEAN DEFAULT TRUE
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, contract: Contract) -> tuple:
        return (contract.name, contract.description, contract.frequency, contract.trigger_event,
                contract.conditions, contract.violation_message, contract.start_time, contract.end_time,
                contract.is_valid)

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
            "is_valid": row[9]
        }
        return Contract(**contract_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "description", "frequency", "trigger_event", "conditions",
                "violation_message", "start_time", "end_time", "is_valid"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "description", "frequency", "trigger_event", "conditions",
                "violation_message", "start_time", "end_time", "is_valid"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "description", "frequency", "trigger_event", "conditions",
                "violation_message", "start_time", "end_time", "is_valid"]

    def get_associated_valid_contracts(self, event_type) -> List[Contract]:
        current_time = int(time.time())
        with self.db.conn.cursor() as cursor:
            query = "SELECT * FROM contracts WHERE trigger_event = %s and end_time > %s and is_valid"
            cursor.execute(query, (event_type, current_time))
            rows = cursor.fetchall()
            contracts = [self._to_object(row) for row in rows]
        return contracts

    def get_open_contracts(self) -> List[Contract]:
        """ Get the contracts not associated to trigger_event and are valid"""
        current_time = int(time.time())
        with self.db.conn.cursor() as cursor:
            query = "SELECT * FROM contracts WHERE trigger_event = null and end_time > %s and is_valid"
            cursor.execute(query, (current_time,))
            rows = cursor.fetchall()
            contracts = [self._to_object(row) for row in rows]
        return contracts
