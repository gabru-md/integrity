from __future__ import annotations

import argparse
import os
import sys
import unittest


os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")


TEST_GROUPS = {
    "unit": [
        "tests.test_assistant_command_service",
        "tests.test_db_reconnect",
        "tests.test_eventing",
        "tests.test_import_pipeline",
        "tests.test_notification_policy",
        "tests.test_promise_processor",
        "tests.test_project_work_linking",
        "tests.test_recommendation_followups",
        "tests.test_session_inference_processor",
        "tests.test_skill_service",
    ],
    "integration": [
        "tests.test_cleanup_regressions",
        "tests.test_events_app",
        "tests.test_kanban_tickets_app",
        "tests.test_promises_app",
    ],
}
TEST_GROUPS["all"] = TEST_GROUPS["unit"] + TEST_GROUPS["integration"]


def build_suite(group: str) -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for module_name in TEST_GROUPS[group]:
        suite.addTests(loader.loadTestsFromName(module_name))
    return suite


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Rasbhari test suite by group.")
    parser.add_argument(
        "group",
        nargs="?",
        default="all",
        choices=["unit", "integration", "all", "list"],
        help="Which test group to run.",
    )
    args = parser.parse_args()

    if args.group == "list":
        for group_name, modules in TEST_GROUPS.items():
            print(f"{group_name}:")
            for module in modules:
                print(f"  - {module}")
        return 0

    result = unittest.TextTestRunner(verbosity=2).run(build_suite(args.group))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
