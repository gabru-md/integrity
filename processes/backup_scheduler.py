import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from gabru.process import Process


class BackupScheduler(Process):
    def __init__(self, enabled=False, name=None):
        super().__init__(name=name or "BackupScheduler", enabled=enabled, daemon=True)
        self.repo_dir = Path(os.path.dirname(os.path.dirname(__file__)))
        self.script_path = Path(os.path.expanduser(os.getenv("RASBHARI_BACKUP_SCRIPT", str(self.repo_dir / "scripts" / "backup_rasbhari_postgres.sh"))))
        self.interval_seconds = max(3600, int(os.getenv("RASBHARI_BACKUP_INTERVAL_SECONDS", "7200") or 7200))
        self.poll_seconds = max(30, int(os.getenv("RASBHARI_BACKUP_POLL_SECONDS", "60") or 60))
        status_root = Path(os.getenv("SERVER_FILES_FOLDER", "/tmp"))
        self.status_file = Path(os.path.expanduser(os.getenv("RASBHARI_BACKUP_STATUS_FILE", str(status_root / "rasbhari-backup-status.json"))))

    def process(self):
        self.log.info("Backup scheduler started with interval %ss", self.interval_seconds)
        while self.running:
            status = self.read_status()
            if self._backup_due(status):
                self._run_backup()
            self._write_status({
                **status,
                "next_run_at": self._next_run_at_iso(status),
                "interval_seconds": self.interval_seconds,
            })
            time.sleep(self.poll_seconds)

    def get_operator_snapshot(self) -> dict:
        status = self.read_status()
        last_success_at = status.get("last_success_at")
        last_failure_at = status.get("last_failure_at")
        state = status.get("state") or "idle"
        summary = "Backup scheduler is waiting for the next interval."
        if state == "running":
            summary = "Backup is running now."
        elif state == "failed" and last_failure_at:
            summary = f"Last backup failed at {self._display_time(last_failure_at)}."
        elif last_success_at:
            summary = f"Last backup succeeded at {self._display_time(last_success_at)}."

        return {
            "backup_state": state,
            "backup_summary": summary,
            "backup_last_success_at": last_success_at,
            "backup_last_failure_at": last_failure_at,
            "backup_next_run_at": status.get("next_run_at"),
            "backup_last_exit_code": status.get("last_exit_code"),
            "backup_last_output": status.get("last_output", ""),
        }

    def read_status(self) -> dict:
        if not self.status_file.exists():
            return {"state": "idle", "interval_seconds": self.interval_seconds}
        try:
            return json.loads(self.status_file.read_text())
        except Exception:
            return {"state": "unknown", "interval_seconds": self.interval_seconds}

    def _backup_due(self, status: dict) -> bool:
        if status.get("state") == "running":
            return False
        last_started_at = status.get("last_started_at")
        if not last_started_at:
            return True
        try:
            last_started = datetime.fromisoformat(last_started_at)
        except Exception:
            return True
        return datetime.now() >= last_started + timedelta(seconds=self.interval_seconds)

    def _run_backup(self):
        started_at = datetime.now().isoformat()
        self._write_status({
            **self.read_status(),
            "state": "running",
            "last_started_at": started_at,
            "interval_seconds": self.interval_seconds,
        })
        if not self.script_path.exists():
            self._write_status({
                **self.read_status(),
                "state": "failed",
                "last_finished_at": datetime.now().isoformat(),
                "last_failure_at": datetime.now().isoformat(),
                "last_exit_code": 127,
                "last_output": f"Backup script not found: {self.script_path}",
                "next_run_at": self._next_run_at_iso({"last_started_at": started_at}),
            })
            return

        command = ["bash", str(self.script_path)]
        result = subprocess.run(
            command,
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
        finished_at = datetime.now().isoformat()
        combined_output = "\n".join(filter(None, [result.stdout.strip(), result.stderr.strip()])).strip()
        next_run_at = self._next_run_at_iso({"last_started_at": started_at})
        if result.returncode == 0:
            self._write_status({
                **self.read_status(),
                "state": "healthy",
                "last_finished_at": finished_at,
                "last_success_at": finished_at,
                "last_exit_code": result.returncode,
                "last_output": combined_output,
                "next_run_at": next_run_at,
            })
            self.log.info("Backup completed successfully.")
        else:
            self._write_status({
                **self.read_status(),
                "state": "failed",
                "last_finished_at": finished_at,
                "last_failure_at": finished_at,
                "last_exit_code": result.returncode,
                "last_output": combined_output,
                "next_run_at": next_run_at,
            })
            self.log.warning("Backup failed with exit code %s", result.returncode)

    def _write_status(self, payload: dict):
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def _next_run_at_iso(self, status: dict) -> str:
        last_started_at = status.get("last_started_at")
        if last_started_at:
            try:
                last_started = datetime.fromisoformat(last_started_at)
                return (last_started + timedelta(seconds=self.interval_seconds)).isoformat()
            except Exception:
                pass
        return (datetime.now() + timedelta(seconds=self.interval_seconds)).isoformat()

    @staticmethod
    def _display_time(value: str) -> str:
        try:
            return datetime.fromisoformat(value).strftime("%b %d, %Y, %I:%M %p")
        except Exception:
            return value
