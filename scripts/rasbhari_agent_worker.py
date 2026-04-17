#!/usr/bin/env python3
"""
Rasbhari Agent Worker
Polls a Rasbhari server for tasks and executes them using local LLM tools.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def request_json(
    server: str,
    path: str,
    api_key: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    headers = {
        "Accept": "application/json",
        "X-API-Key": api_key,
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(
        f"{server.rstrip('/')}{path}", data=data, method=method, headers=headers
    )
    with urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def parse_workspace(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("Workspace must be KEY=/absolute/path")
    key, path = value.split("=", 1)
    key = key.strip()
    resolved = Path(path).expanduser().resolve()
    if not key:
        raise argparse.ArgumentTypeError("Workspace key cannot be empty")
    if not resolved.exists():
        raise argparse.ArgumentTypeError(f"Workspace path does not exist: {resolved}")
    return key, resolved


def run_dry_run(run: dict[str, Any], workspace_path: Path) -> tuple[str, list[str]]:
    prompt = run.get("prompt") or ""
    summary = "\n".join(
        [
            "Dry-run worker received the ticket.",
            f"Workspace: {run.get('workspace_key')}",
            f"Local path: {workspace_path}",
            f"Prompt characters: {len(prompt)}",
            "No code was changed. Verify the loop before switching executors.",
        ]
    )
    return summary, []


def append_result_contract(prompt: str) -> str:
    return "\n".join(
        [
            prompt.rstrip(),
            "",
            "Rasbhari reporting contract:",
            "- Do not use your raw execution log as the final result.",
            "- At the very end, emit exactly one JSON block between these markers:",
            "RASBHARI_RESULT_BEGIN",
            '{"summary":"One or two sentences explaining what changed. No file lists."}',
            "RASBHARI_RESULT_END",
        ]
    )


def fallback_summary(output: str) -> str:
    if not output:
        return "The requested ticket work was completed."
    lower_output = output.lower()
    if "no changes" in lower_output or "nothing to change" in lower_output:
        return "The agent reviewed the ticket and did not find a code change to apply."
    return "The requested ticket work was completed."


def run_codex(run: dict[str, Any], workspace_path: Path) -> tuple[str, list[str]]:
    prompt = append_result_contract(run.get("prompt") or "")
    command = ["codex", "exec", "--cd", str(workspace_path), prompt]
    log(f"Executing Codex in {workspace_path}...")
    completed = subprocess.run(
        command, cwd=str(workspace_path), text=True, capture_output=True, check=False
    )
    output = "\n".join(
        p for p in [completed.stdout.strip(), completed.stderr.strip()] if p
    ).strip()
    if completed.returncode != 0:
        log(f"Codex failed with code {completed.returncode}")
        raise RuntimeError(output or f"Codex failed with code {completed.returncode}")
    changed_files = git_changed_files(workspace_path)
    # Note: Using fallback here as parsing logic is removed for brevity
    return fallback_summary(output), changed_files


def run_gemini(run: dict[str, Any], workspace_path: Path) -> tuple[str, list[str]]:
    # We skip the contract because we aren't capturing output to parse it
    prompt = run.get("prompt") or ""
    command = ["gemini", "exec", "--yolo", prompt]
    
    log("Running Gemini CLI in interactive mode...")
    
    # We REMOVE capture_output=True so Gemini has a real TTY to work with.
    # This ensures it actually writes the files instead of just talking about it.
    completed = subprocess.run(
        command, 
        cwd=str(workspace_path), 
        check=False
    )
    
    if completed.returncode != 0:
        log(f"Gemini CLI failed with code {completed.returncode}")
        raise RuntimeError(f"Gemini failed with exit code {completed.returncode}")
    
    changed_files = git_changed_files(workspace_path)
    
    if not changed_files:
        summary = "The agent finished its task, but no files were modified in the workspace."
    else:
        summary = f"Task completed successfully. Modified {len(changed_files)} files."
        
    return summary, changed_files


def git_changed_files(workspace_path: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(workspace_path),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    files = []
    for line in completed.stdout.splitlines():
        path = line[3:].strip()
        if path:
            files.append(path)
    if files:
        log(f"Git detected changes in: {', '.join(files)}")
    else:
        log("No files were changed in the workspace.")
    return files


def execute_run(
    run: dict[str, Any], executor: str, workspace_path: Path
) -> tuple[str, list[str]]:
    log(f"Starting execution via executor: {executor}")
    if executor == "dry-run":
        return run_dry_run(run, workspace_path)
    if executor == "codex":
        return run_codex(run, workspace_path)
    if executor == "gemini":
        return run_gemini(run, workspace_path)
    raise ValueError(f"Unsupported executor: {executor}")


def poll_once(args, workspaces: dict[str, Path]) -> bool:
    query = urlencode(
        {
            "workspace_key": args.workspace_key,
            "agent_kind": args.agent_kind,
        }
    )

    data = request_json(args.server, f"/agent-runs/next?{query}", args.api_key)
    run = data.get("run")
    if not run:
        return False

    run_id = int(run["id"])
    workspace_key = run.get("workspace_key") or args.workspace_key
    log(f"*** Found Task! ID: {run_id} for Workspace: {workspace_key} ***")

    workspace_path = workspaces.get(workspace_key)
    if not workspace_path:
        error_msg = f"Worker has no local path for workspace {workspace_key!r}."
        log(f"Error: {error_msg}")
        request_json(
            args.server,
            f"/agent-runs/{run_id}/fail",
            args.api_key,
            method="POST",
            payload={"error_message": error_msg},
        )
        return True

    log(f"Claiming run {run_id}...")
    claimed = request_json(
        args.server,
        f"/agent-runs/{run_id}/claim",
        args.api_key,
        method="POST",
        payload={"worker_name": args.worker},
    )
    run = claimed

    log(f"Marking run {run_id} as started.")
    request_json(
        args.server, f"/agent-runs/{run_id}/start", args.api_key, method="POST", payload={}
    )

    try:
        summary, changed_files = execute_run(run, args.executor, workspace_path)
    except Exception as exc:
        log(f"Execution failed: {exc}")
        request_json(
            args.server,
            f"/agent-runs/{run_id}/fail",
            args.api_key,
            method="POST",
            payload={"error_message": str(exc)},
        )
        return True

    log(f"Run {run_id} completed successfully. Sending results.")
    request_json(
        args.server,
        f"/agent-runs/{run_id}/complete",
        args.api_key,
        method="POST",
        payload={
            "result_summary": summary,
            "changed_files": changed_files,
        },
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll Rasbhari for local agent runs.")
    parser.add_argument("--server", required=True, help="Rasbhari base URL")
    parser.add_argument("--api-key", required=True, help="Rasbhari API key")
    parser.add_argument("--worker", default="local-agent-worker", help="Worker name")
    parser.add_argument(
        "--workspace",
        action="append",
        type=parse_workspace,
        required=True,
        help="Workspace mapping KEY=/path",
    )
    parser.add_argument("--workspace-key", default="integrity", help="Workspace to poll")
    parser.add_argument("--agent-kind", help="Agent kind to poll. Defaults to executor.")
    parser.add_argument(
        "--executor", choices=["dry-run", "codex", "gemini"], default="dry-run"
    )
    parser.add_argument("--poll-interval", type=float, default=8.0)
    parser.add_argument("--once", action="store_true", help="Poll once and exit")
    args = parser.parse_args()

    if not args.agent_kind:
        args.agent_kind = args.executor

    workspaces = dict(args.workspace)
    log(f"Worker '{args.worker}' started. Interval: {args.poll_interval}s")
    log(f"Workspaces: {list(workspaces.keys())}")

    while True:
        try:
            did_work = poll_once(args, workspaces)
        except HTTPError as exc:
            log(f"HTTP Error {exc.code}")
            did_work = False
        except URLError as exc:
            log(f"Connection failed: {exc}")
            did_work = False

        if args.once:
            log("Exiting (--once).")
            return 0

        if not did_work:
            time.sleep(args.poll_interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("Worker stopped by user.")
        sys.exit(0)
