#!/usr/bin/env python3
import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional
from uuid import uuid4


CONFIG_DIR = Path.home() / ".config" / "rasbhari-mac-agent"
CONFIG_PATH = CONFIG_DIR / "config.json"
PID_PATH = CONFIG_DIR / "agent.pid"
LOG_PATH = CONFIG_DIR / "agent.log"
DEFAULT_POLL_SECONDS = 3


@dataclass
class AgentRule:
    id: str
    app_name: str
    trigger: str
    event_type: str
    description: str
    tags: List[str]
    cooldown_seconds: int = 300
    enabled: bool = True


def default_config() -> dict:
    return {
        "rasbhari_url": "http://localhost:5000",
        "api_key": "",
        "machine_name": os.uname().nodename,
        "poll_seconds": DEFAULT_POLL_SECONDS,
        "rules": [],
    }


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def pid_path_from_args(args) -> Path:
    return Path(getattr(args, "pid_file", "") or PID_PATH)


def log_path_from_args(args) -> Path:
    return Path(getattr(args, "log_file", "") or LOG_PATH)


def read_pid(pid_path: Path) -> Optional[int]:
    try:
        return int(pid_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def cleanup_stale_pid(pid_path: Path) -> None:
    pid = read_pid(pid_path)
    if pid and not is_process_running(pid):
        try:
            pid_path.unlink()
        except OSError:
            pass


def load_config() -> dict:
    ensure_config_dir()
    if not CONFIG_PATH.exists():
        config = default_config()
        save_config(config)
        return config
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    config = default_config()
    config.update(data)
    config["rules"] = [normalize_rule(rule) for rule in config.get("rules", [])]
    return config


def save_config(config: dict) -> None:
    ensure_config_dir()
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


def normalize_rule(raw: dict) -> dict:
    rule = asdict(
        AgentRule(
            id=raw.get("id") or str(uuid4()),
            app_name=raw.get("app_name") or "",
            trigger=raw.get("trigger") or "opened",
            event_type=raw.get("event_type") or "mac:activity",
            description=raw.get("description") or "{app_name} {trigger}",
            tags=list(raw.get("tags") or []),
            cooldown_seconds=int(raw.get("cooldown_seconds") or 300),
            enabled=bool(raw.get("enabled", True)),
        )
    )
    return rule


def current_apps() -> set[str]:
    script = 'tell application "System Events" to get name of every process whose background only is false'
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    raw = result.stdout.strip()
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def post_event(config: dict, rule: dict, app_name: str) -> None:
    rasbhari_url = config.get("rasbhari_url", "").rstrip("/")
    api_key = config.get("api_key", "").strip()
    if not rasbhari_url or not api_key:
        raise RuntimeError("rasbhari_url and api_key must be configured before running the agent")

    description_template = rule.get("description") or "{app_name} {trigger}"
    tags = list(
        dict.fromkeys(
            [*(rule.get("tags") or []), "source:mac_agent", f"app:{slugify(app_name)}", f"machine:{slugify(config.get('machine_name', 'mac'))}"]
        )
    )
    payload = {
        "event_type": rule["event_type"],
        "description": description_template.format(app_name=app_name, trigger=rule["trigger"]),
        # Rasbhari's current /events/ handler expects tags as a comma-separated string.
        "tags": ", ".join(tags),
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{rasbhari_url}/events/",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status >= 300:
            raise RuntimeError(f"Event post failed with status {response.status}")


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "unknown"


def prompt_text(label: str, default: str = "", required: bool = False) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default
        if not required:
            return ""
        print("This value is required.")


def prompt_int(label: str, default: int) -> int:
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            print("Enter a valid integer.")


def prompt_choice(label: str, choices: list[str], default: str) -> str:
    choice_str = "/".join(choices)
    while True:
        raw = input(f"{label} ({choice_str}) [{default}]: ").strip().lower()
        if not raw:
            return default
        if raw in choices:
            return raw
        print(f"Choose one of: {choice_str}")


def command_init(args) -> int:
    config = load_config()
    interactive = not any([args.url, args.api_key, args.machine_name, args.poll_seconds])
    if interactive:
        print("Rasbhari macOS agent setup")
        config["rasbhari_url"] = prompt_text("Rasbhari URL", config["rasbhari_url"], required=True)
        config["api_key"] = prompt_text("API key", config.get("api_key", ""), required=True)
        config["machine_name"] = prompt_text("Machine name", config["machine_name"], required=True)
        config["poll_seconds"] = prompt_int("Polling interval seconds", int(config["poll_seconds"]))
    else:
        if args.url:
            config["rasbhari_url"] = args.url
        if args.api_key:
            config["api_key"] = args.api_key
        if args.machine_name:
            config["machine_name"] = args.machine_name
        if args.poll_seconds:
            config["poll_seconds"] = args.poll_seconds
    save_config(config)
    print(f"Saved config to {CONFIG_PATH}")
    return 0


def command_rule_add(args) -> int:
    config = load_config()
    interactive = not any([args.app_name, args.trigger, args.event_type, args.description, args.tags])
    if interactive:
        print("Add app rule")
        try:
            apps = sorted(current_apps())
        except Exception:
            apps = []
        if apps:
            print("Detected apps:")
            print(", ".join(apps[:20]))
        app_name = prompt_text("App name", required=True)
        trigger = prompt_choice("Trigger", ["opened", "closed"], "opened")
        event_type = prompt_text("Event type", f"mac:{slugify(app_name)}", required=True)
        description = prompt_text("Description template", "{app_name} {trigger}")
        tags = prompt_text("Tags (comma separated)", slugify(app_name))
        cooldown_seconds = prompt_int("Cooldown seconds", 300)
    else:
        app_name = args.app_name
        trigger = args.trigger
        event_type = args.event_type
        description = args.description or "{app_name} {trigger}"
        tags = args.tags or ""
        cooldown_seconds = args.cooldown_seconds
    rule = normalize_rule(
        {
            "id": str(uuid4()),
            "app_name": app_name,
            "trigger": trigger,
            "event_type": event_type,
            "description": description,
            "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
            "cooldown_seconds": cooldown_seconds,
            "enabled": True,
        }
    )
    config["rules"].append(rule)
    save_config(config)
    print(f"Added rule {rule['id']} for {rule['app_name']} on {rule['trigger']}")
    return 0


def command_rule_list(args) -> int:
    config = load_config()
    if not config["rules"]:
        print("No rules configured.")
        return 0
    for rule in config["rules"]:
        status = "enabled" if rule["enabled"] else "disabled"
        print(f"{rule['id']} | {status} | {rule['app_name']} | {rule['trigger']} -> {rule['event_type']}")
    return 0


def command_rule_remove(args) -> int:
    config = load_config()
    before = len(config["rules"])
    config["rules"] = [rule for rule in config["rules"] if rule["id"] != args.rule_id]
    if len(config["rules"]) == before:
        print("Rule not found.")
        return 1
    save_config(config)
    print(f"Removed rule {args.rule_id}")
    return 0


def command_rule_toggle(args, enabled: bool) -> int:
    config = load_config()
    for rule in config["rules"]:
        if rule["id"] == args.rule_id:
            rule["enabled"] = enabled
            save_config(config)
            print(f"{'Enabled' if enabled else 'Disabled'} rule {args.rule_id}")
            return 0
    print("Rule not found.")
    return 1


def command_doctor(args) -> int:
    config = load_config()
    print(f"Config: {CONFIG_PATH}")
    print(f"Rasbhari URL: {config['rasbhari_url']}")
    print(f"API key configured: {'yes' if config.get('api_key') else 'no'}")
    print(f"Machine name: {config['machine_name']}")
    print(f"Poll seconds: {config['poll_seconds']}")
    try:
        apps = sorted(current_apps())
        print(f"Detected GUI apps: {len(apps)}")
        print(", ".join(apps[:12]) or "none")
    except Exception as exc:
        print(f"Failed to query running apps: {exc}")
        return 1
    return 0


def command_rule_wizard(args) -> int:
    return command_rule_add(args)


def command_run(args) -> int:
    config = load_config()
    rules = [rule for rule in config["rules"] if rule["enabled"]]
    if not rules:
        print("No enabled rules configured.")
        return 1

    cooldowns: dict[tuple[str, str, str], float] = {}
    previous_apps = current_apps()
    print(f"Watching {len(rules)} rules. Press Ctrl+C to stop.")
    while True:
        try:
            time.sleep(config.get("poll_seconds") or DEFAULT_POLL_SECONDS)
            apps = current_apps()
            opened = apps - previous_apps
            closed = previous_apps - apps
            for rule in rules:
                matches = opened if rule["trigger"] == "opened" else closed
                if rule["app_name"] not in matches:
                    continue
                key = (rule["id"], rule["app_name"], rule["trigger"])
                now = time.time()
                cooldown_until = cooldowns.get(key, 0)
                if now < cooldown_until:
                    continue
                post_event(config, rule, rule["app_name"])
                print(f"Emitted {rule['event_type']} for {rule['app_name']} ({rule['trigger']})")
                cooldowns[key] = now + int(rule.get("cooldown_seconds") or 300)
            previous_apps = apps
        except KeyboardInterrupt:
            print("Stopped.")
            return 0
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace").strip()
            except Exception:
                body = ""
            if body:
                print(f"Failed to reach Rasbhari: HTTP Error {exc.code}: {exc.reason} | {body}")
            else:
                print(f"Failed to reach Rasbhari: HTTP Error {exc.code}: {exc.reason}")
        except urllib.error.URLError as exc:
            print(f"Failed to reach Rasbhari: {exc}")
        except Exception as exc:
            print(f"Agent error: {exc}")


def command_daemon_start(args) -> int:
    ensure_config_dir()
    pid_path = pid_path_from_args(args)
    log_path = log_path_from_args(args)
    cleanup_stale_pid(pid_path)
    pid = read_pid(pid_path)
    if pid and is_process_running(pid):
        print(f"Daemon already running with pid {pid}")
        return 0

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "run"],
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    pid_path.write_text(str(process.pid), encoding="utf-8")
    print(f"Started daemon pid {process.pid}")
    print(f"PID file: {pid_path}")
    print(f"Log file: {log_path}")
    return 0


def command_daemon_stop(args) -> int:
    pid_path = pid_path_from_args(args)
    cleanup_stale_pid(pid_path)
    pid = read_pid(pid_path)
    if not pid:
        print("Daemon is not running.")
        return 1
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        try:
            pid_path.unlink()
        except OSError:
            pass
        print("Daemon was not running.")
        return 1

    deadline = time.time() + 5
    while time.time() < deadline:
        if not is_process_running(pid):
            try:
                pid_path.unlink()
            except OSError:
                pass
            print(f"Stopped daemon pid {pid}")
            return 0
        time.sleep(0.1)

    print(f"Sent SIGTERM to daemon pid {pid}")
    return 0


def command_daemon_status(args) -> int:
    pid_path = pid_path_from_args(args)
    cleanup_stale_pid(pid_path)
    pid = read_pid(pid_path)
    if not pid:
        print("Daemon is not running.")
        return 1
    if is_process_running(pid):
        print(f"Daemon running with pid {pid}")
        print(f"PID file: {pid_path}")
        print(f"Log file: {log_path_from_args(args)}")
        return 0
    try:
        pid_path.unlink()
    except OSError:
        pass
    print("Daemon is not running.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rasbhari macOS app activity agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="configure the agent")
    init_parser.add_argument("--url")
    init_parser.add_argument("--api-key")
    init_parser.add_argument("--machine-name")
    init_parser.add_argument("--poll-seconds", type=int)
    init_parser.set_defaults(func=command_init)

    rule_parser = subparsers.add_parser("rule", help="manage rules")
    rule_subparsers = rule_parser.add_subparsers(dest="rule_command", required=True)

    add_parser = rule_subparsers.add_parser("add", help="add an app rule")
    add_parser.add_argument("--app-name")
    add_parser.add_argument("--trigger", choices=["opened", "closed"])
    add_parser.add_argument("--event-type")
    add_parser.add_argument("--description")
    add_parser.add_argument("--tags")
    add_parser.add_argument("--cooldown-seconds", type=int, default=300)
    add_parser.set_defaults(func=command_rule_add)

    wizard_parser = rule_subparsers.add_parser("wizard", help="guided rule setup")
    wizard_parser.add_argument("--app-name")
    wizard_parser.add_argument("--trigger", choices=["opened", "closed"])
    wizard_parser.add_argument("--event-type")
    wizard_parser.add_argument("--description")
    wizard_parser.add_argument("--tags")
    wizard_parser.add_argument("--cooldown-seconds", type=int, default=300)
    wizard_parser.set_defaults(func=command_rule_wizard)

    list_parser = rule_subparsers.add_parser("list", help="list rules")
    list_parser.set_defaults(func=command_rule_list)

    remove_parser = rule_subparsers.add_parser("remove", help="remove a rule")
    remove_parser.add_argument("rule_id")
    remove_parser.set_defaults(func=command_rule_remove)

    enable_parser = rule_subparsers.add_parser("enable", help="enable a rule")
    enable_parser.add_argument("rule_id")
    enable_parser.set_defaults(func=lambda args: command_rule_toggle(args, True))

    disable_parser = rule_subparsers.add_parser("disable", help="disable a rule")
    disable_parser.add_argument("rule_id")
    disable_parser.set_defaults(func=lambda args: command_rule_toggle(args, False))

    doctor_parser = subparsers.add_parser("doctor", help="check local setup")
    doctor_parser.set_defaults(func=command_doctor)

    run_parser = subparsers.add_parser("run", help="run the watcher loop")
    run_parser.set_defaults(func=command_run)

    daemon_parser = subparsers.add_parser("daemon", help="manage background daemon mode")
    daemon_subparsers = daemon_parser.add_subparsers(dest="daemon_command", required=True)

    daemon_start_parser = daemon_subparsers.add_parser("start", help="start the agent in the background")
    daemon_start_parser.add_argument("--pid-file")
    daemon_start_parser.add_argument("--log-file")
    daemon_start_parser.set_defaults(func=command_daemon_start)

    daemon_stop_parser = daemon_subparsers.add_parser("stop", help="stop the background agent")
    daemon_stop_parser.add_argument("--pid-file")
    daemon_stop_parser.set_defaults(func=command_daemon_stop)

    daemon_status_parser = daemon_subparsers.add_parser("status", help="show background agent status")
    daemon_status_parser.add_argument("--pid-file")
    daemon_status_parser.add_argument("--log-file")
    daemon_status_parser.set_defaults(func=command_daemon_status)
    return parser


def main() -> int:
    if sys.platform != "darwin":
        print("This agent currently supports macOS only.")
        return 1
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
