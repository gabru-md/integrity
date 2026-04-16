#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request_json(server: str, path: str, api_key: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {
        "Accept": "application/json",
        "X-API-Key": api_key,
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(f"{server.rstrip('/')}{path}", data=data, method=method, headers=headers)
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
    summary = "\n".join([
        "Dry-run worker received the ticket.",
        f"Workspace: {run.get('workspace_key')}",
        f"Local path: {workspace_path}",
        f"Prompt characters: {len(prompt)}",
        "No code was changed. Switch the worker executor to codex or gemini after this queue loop is verified.",
    ])
    return summary, []


def append_result_contract(prompt: str) -> str:
    return "\n".join([
        prompt.rstrip(),
        "",
        "Rasbhari reporting contract:",
        "- Do not use your raw execution log as the final result.",
        "- At the very end, emit exactly one JSON block between these markers:",
        "RASBHARI_RESULT_BEGIN",
        "{\"summary\":\"One or two sentences explaining what feature or bug behavior changed. No file list, no code, no command output.\"}",
        "RASBHARI_RESULT_END",
    ])


def parse_rasbhari_result(output: str) -> str:
    match = re.search(r"RASBHARI_RESULT_BEGIN\s*(\{.*?\})\s*RASBHARI_RESULT_END", output or "", re.DOTALL)
    if match:
        try:
            payload = json.loads(match.group(1))
            summary = str(payload.get("summary") or "").strip()
            if summary:
                return normalize_summary(summary)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return fallback_summary(output)


def normalize_summary(summary: str) -> str:
    compact = " ".join(line.strip() for line in summary.splitlines() if line.strip())
    if len(compact) > 500:
        compact = compact[:497].rstrip() + "..."
    return compact or "The requested ticket work was completed."


def fallback_summary(output: str) -> str:
    if not output:
        return "The requested ticket work was completed."
    lower_output = output.lower()
    if "no changes" in lower_output or "nothing to change" in lower_output:
        return "The agent reviewed the ticket and did not find a code change to apply."
    return "The requested ticket work was completed. The agent did not provide a structured Rasbhari summary."


def run_codex(run: dict[str, Any], workspace_path: Path) -> tuple[str, list[str]]:
    prompt = append_result_contract(run.get("prompt") or "")
    command = ["codex", "exec", "--cd", str(workspace_path), prompt]
    completed = subprocess.run(command, cwd=str(workspace_path), text=True, capture_output=True, check=False)
    output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part).strip()
    if completed.returncode != 0:
        raise RuntimeError(output or f"codex exec failed with exit code {completed.returncode}")
    changed_files = git_changed_files(workspace_path)
    return parse_rasbhari_result(output), changed_files


def run_gemini(run: dict[str, Any], workspace_path: Path) -> tuple[str, list[str]]:
    prompt = append_result_contract(run.get("prompt") or "")
    command = ["gemini", prompt]
    completed = subprocess.run(command, cwd=str(workspace_path), text=True, capture_output=True, check=False)
    output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part).strip()
    if completed.returncode != 0:
        raise RuntimeError(output or f"gemini failed with exit code {completed.returncode}")
    changed_files = git_changed_files(workspace_path)
    return parse_rasbhari_result(output), changed_files


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
    return files


def execute_run(run: dict[str, Any], executor: str, workspace_path: Path) -> tuple[str, list[str]]:
    if executor == "dry-run":
        return run_dry_run(run, workspace_path)
    if executor == "codex":
        return run_codex(run, workspace_path)
    if executor == "gemini":
        return run_gemini(run, workspace_path)
    raise ValueError(f"Unsupported executor: {executor}")


def poll_once(args, workspaces: dict[str, Path]) -> bool:
    query = urlencode({
        "workspace_key": args.workspace_key,
        "agent_kind": args.agent_kind,
    })
    data = request_json(args.server, f"/agent-runs/next?{query}", args.api_key)
    run = data.get("run")
    if not run:
        return False

    run_id = int(run["id"])
    workspace_key = run.get("workspace_key") or args.workspace_key
    workspace_path = workspaces.get(workspace_key)
    if not workspace_path:
        request_json(args.server, f"/agent-runs/{run_id}/fail", args.api_key, method="POST", payload={
            "error_message": f"Worker has no local path for workspace {workspace_key!r}.",
        })
        return True

    claimed = request_json(args.server, f"/agent-runs/{run_id}/claim", args.api_key, method="POST", payload={
        "worker_name": args.worker,
    })
    run = claimed
    request_json(args.server, f"/agent-runs/{run_id}/start", args.api_key, method="POST", payload={})

    try:
        summary, changed_files = execute_run(run, args.executor, workspace_path)
    except Exception as exc:
        request_json(args.server, f"/agent-runs/{run_id}/fail", args.api_key, method="POST", payload={
            "error_message": str(exc),
        })
        return True

    request_json(args.server, f"/agent-runs/{run_id}/complete", args.api_key, method="POST", payload={
        "result_summary": summary,
        "changed_files": changed_files,
    })
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll Rasbhari for local agent runs and execute them on this machine.")
    parser.add_argument("--server", required=True, help="Rasbhari base URL, for example http://rasbhari.local")
    parser.add_argument("--api-key", required=True, help="Rasbhari API key")
    parser.add_argument("--worker", default="local-agent-worker", help="Worker name reported to Rasbhari")
    parser.add_argument("--workspace", action="append", type=parse_workspace, required=True, help="Workspace mapping KEY=/absolute/path")
    parser.add_argument("--workspace-key", default="integrity", help="Workspace key to poll")
    parser.add_argument("--agent-kind", default="dry-run", help="Agent kind to poll from Rasbhari")
    parser.add_argument("--executor", choices=["dry-run", "codex", "gemini"], default="dry-run", help="Local executor")
    parser.add_argument("--poll-interval", type=float, default=8.0, help="Seconds between idle polls")
    parser.add_argument("--once", action="store_true", help="Poll once and exit")
    args = parser.parse_args()

    workspaces = dict(args.workspace)
    while True:
        try:
            did_work = poll_once(args, workspaces)
        except HTTPError as exc:
            print(f"rasbhari-agent-worker: HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}", file=sys.stderr)
            did_work = False
        except URLError as exc:
            print(f"rasbhari-agent-worker: connection failed: {exc}", file=sys.stderr)
            did_work = False

        if args.once:
            return 0
        if not did_work:
            time.sleep(args.poll_interval)


if __name__ == "__main__":
    raise SystemExit(main())
