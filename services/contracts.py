from gabru.service import CRUDService
from model.contract import Contract
from typing import List

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
                        end_time TIMESTAMP
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, contract: Contract) -> tuple:
        return (contract.name, contract.description, contract.frequency, contract.trigger_event,
                contract.conditions, contract.violation_message, contract.start_time, contract.end_time)

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
            "end_time": row[8]
        }
        return Contract(**contract_dict)

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "description", "frequency", "trigger_event", "conditions",
                "violation_message", "start_time", "end_time"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "description", "frequency", "trigger_event", "conditions",
                "violation_message", "start_time", "end_time"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "description", "frequency", "trigger_event", "conditions",
                "violation_message", "start_time", "end_time"]
