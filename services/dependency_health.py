import os
from typing import List
from urllib.parse import urljoin

import requests


class DependencyHealthService:
    def __init__(self, timeout_sec: float = 1.5):
        self.timeout_sec = timeout_sec

    def get_checks(self) -> List[dict]:
        return [
            self._check_open_webui(),
            self._check_ntfy(),
            self._check_sendgrid(),
        ]

    def _check_open_webui(self) -> dict:
        base_url = os.getenv("OPEN_WEBUI_URL")
        if not base_url:
            return {
                "name": "OpenWebUI",
                "status": "Paused",
                "summary": "OPEN_WEBUI_URL not configured",
                "detail": "The /chat redirect is configured only when OPEN_WEBUI_URL is set.",
            }

        result = self._probe_http_service(
            name="OpenWebUI",
            base_url=base_url,
            probe_paths=["/health", ""],
            success_detail="OpenWebUI is reachable.",
            failure_detail="OpenWebUI did not respond successfully on the configured URL.",
        )
        if result["status"] == "Healthy":
            result["summary"] = f"Reachable at {base_url}"
        return result

    def _check_ntfy(self) -> dict:
        base_url = os.getenv("NTFY_BASE_URL", "https://ntfy.sh").rstrip("/")
        topic = os.getenv("NTFY_TOPIC", "rasbhari-alerts")
        result = self._probe_http_service(
            name="ntfy",
            base_url=base_url,
            probe_paths=["/v1/health", f"/{topic}"],
            success_detail=f"ntfy is reachable. Courier publishes to topic '{topic}'.",
            failure_detail=f"ntfy did not respond successfully. Courier will fail to send topic '{topic}'.",
        )
        if result["status"] == "Healthy":
            result["summary"] = f"Reachable at {base_url}"
        return result

    def _check_sendgrid(self) -> dict:
        api_key = os.getenv("SENDGRID_API_KEY")
        sender = os.getenv("COURIER_SENDER_EMAIL")
        receiver = os.getenv("COURIER_RECEIVER_EMAIL")

        if not api_key:
            return {
                "name": "SendGrid",
                "status": "Paused",
                "summary": "SENDGRID_API_KEY not configured",
                "detail": "Courier can still send ntfy notifications, but email delivery is disabled.",
            }

        if not sender or not receiver:
            return {
                "name": "SendGrid",
                "status": "Delayed",
                "summary": "API key present, email addresses incomplete",
                "detail": "Set COURIER_SENDER_EMAIL and COURIER_RECEIVER_EMAIL to fully enable email delivery.",
            }

        try:
            response = requests.get(
                "https://api.sendgrid.com/v3/user/profile",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=self.timeout_sec,
            )
            if response.status_code == 200:
                return {
                    "name": "SendGrid",
                    "status": "Healthy",
                    "summary": "API key validated",
                    "detail": f"Email routing is configured from {sender} to {receiver}.",
                }
            if response.status_code in (401, 403):
                return {
                    "name": "SendGrid",
                    "status": "Broken",
                    "summary": f"Authentication failed ({response.status_code})",
                    "detail": "The configured SENDGRID_API_KEY was rejected by SendGrid.",
                }
            return {
                "name": "SendGrid",
                "status": "Delayed",
                "summary": f"Unexpected response ({response.status_code})",
                "detail": "SendGrid responded, but not with a healthy profile lookup.",
            }
        except requests.RequestException as exc:
            return {
                "name": "SendGrid",
                "status": "Broken",
                "summary": "SendGrid probe failed",
                "detail": str(exc),
            }

    def _probe_http_service(self, *, name: str, base_url: str, probe_paths: List[str], success_detail: str, failure_detail: str) -> dict:
        last_error = None
        for path in probe_paths:
            url = base_url if path in ("", "/") else urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
            try:
                response = requests.get(url, timeout=self.timeout_sec, allow_redirects=True)
                if 200 <= response.status_code < 400:
                    return {
                        "name": name,
                        "status": "Healthy",
                        "summary": f"HTTP {response.status_code}",
                        "detail": success_detail,
                    }
                last_error = f"{url} returned HTTP {response.status_code}"
            except requests.RequestException as exc:
                last_error = str(exc)

        return {
            "name": name,
            "status": "Broken",
            "summary": "Probe failed",
            "detail": f"{failure_detail} Last error: {last_error}",
        }
