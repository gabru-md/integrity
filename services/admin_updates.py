from __future__ import annotations

import json
import os
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class AdminUpdateService:
    def __init__(
        self,
        repo_dir: Optional[str] = None,
        script_path: Optional[str] = None,
        remote_name: Optional[str] = None,
        branch_name: Optional[str] = None,
        service_name: Optional[str] = None,
        healthcheck_url: Optional[str] = None,
        status_file: Optional[str] = None,
    ):
        self.repo_dir = os.path.expanduser(repo_dir or os.getenv("RASBHARI_UPDATE_REPO_DIR", "")).strip()
        self.script_path = os.path.expanduser(script_path or os.getenv("RASBHARI_UPDATE_SCRIPT", "")).strip()
        self.remote_name = (remote_name or os.getenv("RASBHARI_UPDATE_REMOTE", "origin")).strip() or "origin"
        self.branch_name = (branch_name or os.getenv("RASBHARI_UPDATE_BRANCH", "main")).strip() or "main"
        self.service_name = (service_name or os.getenv("RASBHARI_UPDATE_SERVICE_NAME", "rasbhari")).strip() or "rasbhari"
        self.healthcheck_url = (healthcheck_url or os.getenv("RASBHARI_UPDATE_HEALTHCHECK_URL", "http://127.0.0.1:5000/login")).strip()
        default_status_file = Path(os.getenv("SERVER_FILES_FOLDER", "/tmp")) / "rasbhari-update-status.json"
        self.status_file = Path(os.path.expanduser(status_file or os.getenv("RASBHARI_UPDATE_STATUS_FILE", str(default_status_file))))
        self._lock = threading.Lock()

    def get_update_status(self) -> dict[str, Any]:
        base_status = self._read_status_file()
        config = self._get_configuration_state()

        current_commit = self._get_current_commit() if config["configured"] else None
        latest_commit = self._get_latest_remote_commit() if config["configured"] else None
        dirty_worktree = self._is_worktree_dirty() if config["configured"] else None
        update_available = bool(current_commit and latest_commit and current_commit != latest_commit)

        return {
            "configured": config["configured"],
            "configuration_error": config["configuration_error"],
            "repo_dir": self.repo_dir or None,
            "service_name": self.service_name,
            "script_path": self.script_path or None,
            "branch_name": self.branch_name,
            "remote_name": self.remote_name,
            "healthcheck_url": self.healthcheck_url,
            "current_commit": current_commit,
            "latest_remote_commit": latest_commit,
            "update_available": update_available,
            "dirty_worktree": dirty_worktree,
            "state": base_status.get("state", "idle"),
            "message": base_status.get("message", ""),
            "started_at": base_status.get("started_at"),
            "finished_at": base_status.get("finished_at"),
            "actor_username": base_status.get("actor_username"),
            "output_lines": base_status.get("output_lines", []),
            "last_result": base_status.get("last_result"),
        }

    def trigger_update(self, actor_username: Optional[str] = None) -> dict[str, Any]:
        with self._lock:
            status = self.get_update_status()
            if not status["configured"]:
                return {
                    "started": False,
                    "status": status,
                    "error": status["configuration_error"] or "Update configuration is incomplete.",
                }

            if status["state"] == "running":
                return {
                    "started": False,
                    "status": status,
                    "error": "An update is already in progress.",
                }

            self._write_status_file(
                {
                    "state": "running",
                    "message": "Starting update script.",
                    "started_at": self._now_iso(),
                    "finished_at": None,
                    "actor_username": actor_username,
                    "output_lines": [],
                    "last_result": None,
                }
            )

            worker = threading.Thread(
                target=self._run_update_script,
                kwargs={"actor_username": actor_username},
                daemon=True,
            )
            worker.start()

        return {
            "started": True,
            "status": self.get_update_status(),
        }

    def _run_update_script(self, actor_username: Optional[str] = None) -> None:
        env = os.environ.copy()
        env.update(
            {
                "RASBHARI_UPDATE_REPO_DIR": self.repo_dir,
                "RASBHARI_UPDATE_REMOTE": self.remote_name,
                "RASBHARI_UPDATE_BRANCH": self.branch_name,
                "RASBHARI_UPDATE_SERVICE_NAME": self.service_name,
                "RASBHARI_UPDATE_HEALTHCHECK_URL": self.healthcheck_url,
            }
        )

        try:
            completed = subprocess.run(
                ["bash", self.script_path],
                capture_output=True,
                text=True,
                env=env,
                timeout=600,
            )
            output_lines = self._tail_output(completed.stdout, completed.stderr)
            if completed.returncode == 0:
                self._write_status_file(
                    {
                        "state": "succeeded",
                        "message": "Update completed successfully.",
                        "started_at": self._read_status_file().get("started_at"),
                        "finished_at": self._now_iso(),
                        "actor_username": actor_username,
                        "output_lines": output_lines,
                        "last_result": "success",
                    }
                )
                return

            self._write_status_file(
                {
                    "state": "failed",
                    "message": f"Update failed with exit code {completed.returncode}.",
                    "started_at": self._read_status_file().get("started_at"),
                    "finished_at": self._now_iso(),
                    "actor_username": actor_username,
                    "output_lines": output_lines,
                    "last_result": "failure",
                }
            )
        except Exception as exc:
            self._write_status_file(
                {
                    "state": "failed",
                    "message": f"Update orchestration failed: {exc}",
                    "started_at": self._read_status_file().get("started_at"),
                    "finished_at": self._now_iso(),
                    "actor_username": actor_username,
                    "output_lines": [],
                    "last_result": "failure",
                }
            )

    def _get_configuration_state(self) -> dict[str, Any]:
        if not self.repo_dir:
            return {"configured": False, "configuration_error": "RASBHARI_UPDATE_REPO_DIR is not set."}
        if not self.script_path:
            return {"configured": False, "configuration_error": "RASBHARI_UPDATE_SCRIPT is not set."}
        if not Path(self.script_path).exists():
            return {"configured": False, "configuration_error": f"Update script not found: {self.script_path}"}
        if not Path(self.repo_dir).exists():
            return {"configured": False, "configuration_error": f"Update repo not found: {self.repo_dir}"}
        return {"configured": True, "configuration_error": None}

    def _git_output(self, *args: str) -> Optional[str]:
        try:
            completed = subprocess.run(
                ["git", "-C", self.repo_dir, *args],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except Exception:
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout.strip() or None

    def _get_current_commit(self) -> Optional[str]:
        full_commit = self._git_output("rev-parse", "HEAD")
        if not full_commit:
            return None
        return full_commit[:12]

    def _get_latest_remote_commit(self) -> Optional[str]:
        remote_output = self._git_output("ls-remote", self.remote_name, f"refs/heads/{self.branch_name}")
        if not remote_output:
            return None
        latest_commit = remote_output.split()[0]
        return latest_commit[:12] if latest_commit else None

    def _is_worktree_dirty(self) -> Optional[bool]:
        status_output = self._git_output("status", "--porcelain")
        if status_output is None:
            return None
        lines = [line for line in status_output.splitlines() if line.strip()]
        if not lines:
            return False
        for line in lines:
            if self._status_line_requires_block(line):
                return True
        return False

    def _status_line_requires_block(self, line: str) -> bool:
        if line.startswith("?? "):
            return True

        path = line[3:]
        if not path:
            return True

        unstaged_mode_only = self._is_mode_only_change(path, cached=False)
        staged_mode_only = self._is_mode_only_change(path, cached=True)
        if unstaged_mode_only and staged_mode_only:
            return False
        return True

    def _is_mode_only_change(self, path: str, *, cached: bool) -> bool:
        args = ["diff"]
        if cached:
            args.append("--cached")
        args.extend(["--summary", "--", path])
        summary = self._git_output(*args)
        if summary is None:
            return False
        lines = [line.strip() for line in summary.splitlines() if line.strip()]
        if not lines:
            return False
        return all(line.startswith("mode change ") for line in lines)

    def _read_status_file(self) -> dict[str, Any]:
        if not self.status_file.exists():
            return {}
        try:
            return json.loads(self.status_file.read_text())
        except Exception:
            return {}

    def _write_status_file(self, payload: dict[str, Any]) -> None:
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.write_text(json.dumps(payload, indent=2))

    def _tail_output(self, stdout: str, stderr: str, line_limit: int = 40) -> list[str]:
        combined = []
        if stdout:
            combined.extend([line for line in stdout.splitlines() if line.strip()])
        if stderr:
            combined.extend([line for line in stderr.splitlines() if line.strip()])
        return combined[-line_limit:]

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
