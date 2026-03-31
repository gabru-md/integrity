import os
import unittest
from unittest import mock

from flask import Flask

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from apps.kanban_tickets import kanban_tickets_app
from gabru.auth import PermissionManager


class KanbanTicketsAppTests(unittest.TestCase):
    def _build_client(self):
        flask_app = Flask(__name__)
        flask_app.secret_key = "test-secret"
        flask_app.register_blueprint(kanban_tickets_app.blueprint, url_prefix="/kanbantickets")
        return flask_app.test_client()

    def test_move_route_uses_explicit_state(self):
        client = self._build_client()
        moved_ticket = {"id": 7, "project_id": 3, "title": "Ship board", "description": "", "state": "completed"}
        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "can_write", return_value=True), \
             mock.patch.object(PermissionManager, "can_access_route", return_value=True), \
             mock.patch.object(kanban_tickets_app.service, "move_ticket", return_value=mock.Mock(dict=lambda: moved_ticket)) as move_mock:
            response = client.post("/kanbantickets/7/move", json={"state": "completed"})

        self.assertEqual(response.status_code, 200)
        move_mock.assert_called_once_with(7, "completed")

    def test_project_listing_route_returns_project_tickets(self):
        client = self._build_client()
        tickets = [mock.Mock(dict=lambda: {"id": 1, "project_id": 2, "title": "Board UI", "state": "backlog", "is_archived": False})]
        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "can_access_route", return_value=True), \
             mock.patch.object(kanban_tickets_app.service, "get_by_project_id", return_value=tickets) as list_mock:
            response = client.get("/kanbantickets/project/2")

        self.assertEqual(response.status_code, 200)
        list_mock.assert_called_once_with(2)

    def test_archive_route_archives_ticket(self):
        client = self._build_client()
        archived_ticket = {"id": 4, "project_id": 2, "title": "Board polish", "state": "shipped", "is_archived": True}
        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "can_write", return_value=True), \
             mock.patch.object(PermissionManager, "can_access_route", return_value=True), \
             mock.patch.object(kanban_tickets_app.service, "archive_ticket", return_value=mock.Mock(dict=lambda: archived_ticket)) as archive_mock:
            response = client.post("/kanbantickets/4/archive", json={})

        self.assertEqual(response.status_code, 200)
        archive_mock.assert_called_once_with(4)


if __name__ == "__main__":
    unittest.main()
