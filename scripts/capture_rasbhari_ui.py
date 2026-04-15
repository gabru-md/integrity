#!/usr/bin/env python3
"""Capture Rasbhari UI screenshots for design review.

The script logs in, switches the current user to System mode through the
profile UI, opens the visible Rasbhari navigation surfaces, and saves full-page
screenshots under media/.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from getpass import getpass
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError as exc:
    print(
        "Missing dependency: selenium. Install it with:\n"
        "  python3 -m pip install selenium\n",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


DEFAULT_PATHS = [
    "/",
    "/dashboard",
    "/capture",
    "/thoughts/home",
    "/projects/home",
    "/blogs/home",
    "/promises/home",
    "/reports/home",
    "/activities/home",
    "/skills/home",
    "/connections/home",
    "/events/home",
    "/rtv/home",
    "/automation",
    "/admin",
    "/admin/guide",
    "/apps",
    "/processes",
    "/users/profile",
]


@dataclass(frozen=True)
class PageTarget:
    label: str
    url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Log in to Rasbhari and screenshot all visible System-mode pages.",
    )
    parser.add_argument("--base-url", default=os.getenv("RASBHARI_URL", "http://rasbhari.local"))
    parser.add_argument("--username", default=os.getenv("RASBHARI_USERNAME"))
    parser.add_argument("--password", default=os.getenv("RASBHARI_PASSWORD"))
    parser.add_argument("--out-dir", default=None, help="Defaults to media/rasbhari-ui-<timestamp>.")
    parser.add_argument("--browser", choices=["chrome", "firefox"], default=os.getenv("RASBHARI_SCREENSHOT_BROWSER", "chrome"))
    parser.add_argument("--headed", action="store_true", help="Show the browser while capturing.")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1100)
    parser.add_argument("--wait", type=float, default=1.0, help="Extra seconds to wait after each page load.")
    parser.add_argument("--include-discovered", action="store_true", help="Also screenshot internal links discovered from the System-mode shell.")
    return parser.parse_args()


def build_driver(browser: str, headed: bool, width: int, height: int):
    if browser == "firefox":
        options = FirefoxOptions()
        if not headed:
            options.add_argument("-headless")
        driver = webdriver.Firefox(options=options)
    else:
        options = ChromeOptions()
        if not headed:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)

    driver.set_window_size(width, height)
    return driver


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "page"


def normalize_base_url(base_url: str) -> str:
    if not base_url.startswith(("http://", "https://")):
        base_url = f"http://{base_url}"
    return base_url.rstrip("/")


def same_origin(url: str, base_url: str) -> bool:
    parsed = urlparse(url)
    base = urlparse(base_url)
    return parsed.scheme in {"http", "https"} and parsed.netloc == base.netloc


def wait_for_document(driver, timeout: int = 15) -> None:
    WebDriverWait(driver, timeout).until(lambda browser: browser.execute_script("return document.readyState") == "complete")


def login(driver, base_url: str, username: str, password: str) -> None:
    driver.get(urljoin(base_url, "/login"))
    wait_for_document(driver)

    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait_for_document(driver)

    if "/login" in urlparse(driver.current_url).path:
        raise RuntimeError("Login did not complete. Check username/password.")


def set_system_mode(driver, base_url: str) -> None:
    driver.get(urljoin(base_url, "/users/profile"))
    wait_for_document(driver)

    select = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "experience_mode")))
    if select.get_attribute("value") != "system":
        driver.execute_script(
            """
            const select = arguments[0];
            select.value = 'system';
            select.dispatchEvent(new Event('change', { bubbles: true }));
            document.getElementById('profile-form').requestSubmit();
            """,
            select,
        )
        wait_for_document(driver)


def visible_text(element) -> str:
    text = " ".join((element.text or "").split())
    if text:
        return text
    aria = element.get_attribute("aria-label") or element.get_attribute("title") or ""
    return " ".join(aria.split())


def discover_shell_targets(driver, base_url: str) -> list[PageTarget]:
    targets: list[PageTarget] = []
    seen: set[str] = set()
    for link in driver.find_elements(By.CSS_SELECTOR, "nav a[href], header a[href], .notification-shell a[href]"):
        href = link.get_attribute("href")
        if not href or not same_origin(href, base_url):
            continue
        parsed = urlparse(href)
        if parsed.path in {"", "/logout"} or parsed.path.startswith("/static/"):
            continue
        url = urljoin(base_url, parsed.path)
        if parsed.query:
            url = f"{url}?{parsed.query}"
        if url in seen:
            continue
        seen.add(url)
        label = visible_text(link) or parsed.path.strip("/") or "home"
        targets.append(PageTarget(label=label, url=url))
    return targets


def default_targets(base_url: str) -> list[PageTarget]:
    return [
        PageTarget(label=(path.strip("/") or "home").replace("/", "-"), url=urljoin(base_url, path))
        for path in DEFAULT_PATHS
    ]


def merge_targets(*target_groups: list[PageTarget]) -> list[PageTarget]:
    merged: list[PageTarget] = []
    seen: set[str] = set()
    for group in target_groups:
        for target in group:
            clean_url = target.url.rstrip("/")
            if clean_url in seen:
                continue
            seen.add(clean_url)
            merged.append(target)
    return merged


def prepare_page_for_screenshot(driver) -> None:
    driver.execute_script(
        """
        document.querySelectorAll('details.sidebar-group').forEach((node) => node.setAttribute('open', 'open'));
        document.querySelectorAll('#notification-panel').forEach((node) => node.classList.add('hidden'));
        window.scrollTo(0, 0);
        """
    )


def full_page_screenshot(driver, path: Path, width: int, min_height: int) -> None:
    total_height = driver.execute_script(
        "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, arguments[0]);",
        min_height,
    )
    driver.set_window_size(width, min(int(total_height) + 80, 12000))
    time.sleep(0.2)
    driver.save_screenshot(str(path))


def capture_target(driver, target: PageTarget, out_dir: Path, index: int, width: int, height: int, wait_seconds: float) -> None:
    driver.set_window_size(width, height)
    driver.get(target.url)
    wait_for_document(driver)
    time.sleep(wait_seconds)
    prepare_page_for_screenshot(driver)

    parsed = urlparse(driver.current_url)
    label = slugify(target.label)
    path_label = slugify(parsed.path.strip("/") or "home")
    filename = f"{index:02d}-{label}-{path_label}.png"
    full_page_screenshot(driver, out_dir / filename, width, height)
    print(f"captured {filename}")


def write_index(out_dir: Path, base_url: str, targets: list[PageTarget]) -> None:
    lines = [
        "# Rasbhari UI Screenshots",
        "",
        f"- Base URL: `{base_url}`",
        f"- Captured at: `{datetime.now().isoformat(timespec='seconds')}`",
        "",
        "## Pages",
        "",
    ]
    for index, target in enumerate(targets, start=1):
        lines.append(f"- `{index:02d}` {target.label}: {target.url}")
    (out_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    base_url = normalize_base_url(args.base_url)
    username = args.username or input("Username: ").strip()
    password = args.password or getpass("Password: ")
    if not username or not password:
        print("Username and password are required.", file=sys.stderr)
        return 2

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else Path("media") / f"rasbhari-ui-{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    driver = build_driver(args.browser, args.headed, args.width, args.height)
    try:
        login(driver, base_url, username, password)
        set_system_mode(driver, base_url)
        driver.get(urljoin(base_url, "/dashboard"))
        wait_for_document(driver)

        targets = default_targets(base_url)
        if args.include_discovered:
            targets = merge_targets(targets, discover_shell_targets(driver, base_url))

        write_index(out_dir, base_url, targets)
        for index, target in enumerate(targets, start=1):
            try:
                capture_target(driver, target, out_dir, index, args.width, args.height, args.wait)
            except (TimeoutException, WebDriverException, RuntimeError) as exc:
                print(f"skipped {target.url}: {exc}", file=sys.stderr)
    finally:
        driver.quit()

    print(f"\nScreenshots saved to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
