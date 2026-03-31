import unittest
from unittest import mock

from gabru.db.db import DB
from gabru.db.service import ReadOnlyService


class DummyService(ReadOnlyService[dict]):
    def __init__(self, db):
        super().__init__("dummy", db)
        self.log = mock.Mock()

    def _to_object(self, row: tuple) -> dict:
        return {"id": row[0]}

    def _get_columns_for_select(self):
        return ["id"]


class DBReconnectTests(unittest.TestCase):
    def test_run_with_connection_retry_invalidates_and_retries_once(self):
        db = mock.Mock(spec=DB)
        first_error = RuntimeError("connection lost")
        db.is_connection_error.return_value = True
        db.get_conn.side_effect = [object(), object()]

        service = DummyService(db)
        calls = {"count": 0}

        def operation(conn):
            calls["count"] += 1
            if calls["count"] == 1:
                raise first_error
            return "ok"

        result = service._run_with_connection_retry(operation, fallback=None, action_name="test operation")

        self.assertEqual(result, "ok")
        db.invalidate_connection.assert_called_once()
        self.assertEqual(calls["count"], 2)


if __name__ == "__main__":
    unittest.main()
