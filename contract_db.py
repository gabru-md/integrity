from gabru.crud_db import CrudDB
from contract import Contract  # Assuming Contract class is defined
from typing import List


class ContractDB(CrudDB[Contract]):
    def __init__(self):
        super().__init__(
            "contracts",
            "CONTRACTS_POSTGRES_DB", "CONTRACTS_POSTGRES_USER",
            "CONTRACTS_POSTGRES_PASSWORD", "CONTRACTS_POSTGRES_HOST",
            "CONTRACTS_POSTGRES_PORT", "contracts"
        )

    def _create_table(self):
        if self.conn:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS contracts (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        frequency VARCHAR(50),
                        trigger_event VARCHAR(255),
                        conditions TEXT,
                        violation_message TEXT,
                        start_time BIGINT,
                        end_time BIGINT
                    )
                """)
                self.conn.commit()

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
