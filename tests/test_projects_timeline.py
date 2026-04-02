import os
import unittest
from datetime import datetime
from unittest import mock

from flask import Flask

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

from apps.projects import project_app
from gabru.auth import PermissionManager
from model.project import Project, ProjectState


class ProjectTimelineTests(unittest.TestCase):
    def _build_client(self):
        flask_app = Flask(__name__)
        flask_app.secret_key = "test-secret"
        flask_app.register_blueprint(project_app.blueprint, url_prefix="/projects")
        return flask_app.test_client()

    def test_blog_timeline_entry_creates_real_blog_link(self):
        client = self._build_client()
        project = Project(
            id=3,
            user_id=1,
            name="Rasbhari",
            project_type="Code",
            focus_tags=["python"],
            ticket_prefix="RSB",
            start_date=datetime(2026, 4, 2, 9, 0, 0),
            state=ProjectState.ACTIVE,
            progress_count=0,
        )

        with mock.patch.object(PermissionManager, "is_authenticated", return_value=True), \
             mock.patch.object(PermissionManager, "can_write", return_value=True), \
             mock.patch.object(PermissionManager, "can_access_route", return_value=True), \
             mock.patch.object(project_app.service, "get_by_id", return_value=project), \
             mock.patch("apps.projects.blog_service.build_unique_slug", return_value="ship-project-narrative"), \
             mock.patch("apps.projects.blog_service.create", return_value=21) as create_blog_mock, \
             mock.patch("apps.projects.timeline_service.create", return_value=8) as create_timeline_mock, \
             mock.patch.object(project_app.service, "update", return_value=True) as update_project_mock, \
             mock.patch("apps.projects.event_service.create", return_value=55):
            response = client.post(
                "/projects/3/timeline",
                json={
                    "title": "Ship project narrative",
                    "content": "# Heading\n\nLonger markdown body.",
                    "item_type": "Blog",
                    "status": "published",
                },
            )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["blog_post_id"], 21)
        self.assertEqual(payload["blog_slug"], "ship-project-narrative")

        created_blog = create_blog_mock.call_args.args[0]
        self.assertEqual(created_blog.title, "Ship project narrative")
        self.assertEqual(created_blog.slug, "ship-project-narrative")
        self.assertEqual(created_blog.status, "published")

        created_timeline = create_timeline_mock.call_args.args[0]
        self.assertEqual(created_timeline.item_type, "Blog")
        self.assertEqual(created_timeline.blog_post_id, 21)
        self.assertEqual(created_timeline.blog_slug, "ship-project-narrative")
        self.assertEqual(created_timeline.title, "Ship project narrative")

        self.assertTrue(update_project_mock.called)


if __name__ == "__main__":
    unittest.main()
