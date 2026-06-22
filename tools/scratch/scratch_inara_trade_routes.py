"""
Browser-backed Inara trade-route probe.

This scratch script uses Playwright to open an Inara trade-routes results page
in a real browser context, wait for route rows to appear, and print a compact
summary of the live DOM. It is intentionally a developer probe, not part of the
main runtime surface.

Typical usage:
    uv run python3 tools/scratch/scratch_inara_trade_routes.py "<url>"
    uv run python3 tools/scratch/scratch_inara_trade_routes.py "<url>" --save-html /tmp/inara.html
    uv run python3 tools/scratch/scratch_inara_trade_routes.py "<url>" --show-browser

Before first use on a machine:
    uv sync --extra browsing
    uv run playwright install chromium
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_DEFAULT_PROFILE_DIR = _REPO_ROOT / "artifacts" / "playwright" / "inara-profile"
_ENDPOINT_RE = re.compile(r"^(FROM|TO)\s+(.+?)\s+\|\s+(.+)$")
_FIELD_LABEL_RE = re.compile(r"^[A-Z][A-Z0-9 %/+.-]*(?: [A-Z0-9 %/+.-]+)*$")
_FIELD_LABELS = (
    "PROFIT PER HOUR",
    "PROFIT PER TRIP",
    "PROFIT PER UNIT",
    "ROUTE DISTANCE",
    "STATION DISTANCE",
    "SELL PRICE",
    "BUY PRICE",
    "UPDATED",
    "DISTANCE",
    "SUPPLY",
    "DEMAND",
    "MARGIN",
    "SELL",
    "BUY",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open an Inara trade-routes page in Playwright and print live route summaries."
    )
    parser.add_argument("url", help="full Inara trade-routes results URL")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=90.0,
        help="maximum time to wait for route rows before failing (default: 90)",
    )
    parser.add_argument(
        "--profile-dir",
        default=str(_DEFAULT_PROFILE_DIR),
        help="persistent Playwright user-data directory (default: artifacts/playwright/inara-profile)",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="show the browser window for manual login or challenge confirmation",
    )
    parser.add_argument(
        "--browser-path",
        help="optional browser executable path; default uses Playwright-managed Chromium",
    )
    parser.add_argument(
        "--save-html",
        metavar="PATH",
        help="write the final page HTML to PATH after routes load",
    )
    parser.add_argument(
        "--save-json",
        metavar="PATH",
        help="write extracted route rows as JSON to PATH",
    )
    parser.add_argument(
        "--screenshot",
        metavar="PATH",
        help="save a screenshot after route extraction or on failure",
    )
    parser.add_argument(
        "--max-routes",
        type=int,
        default=5,
        help="how many route summaries to print (default: 5)",
    )
    return parser


def _load_sync_playwright() -> Any:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Playwright is not installed. Run `uv sync --extra browsing` and "
            "`uv run playwright install chromium` first."
        ) from exc
    return sync_playwright


def _clean_line(line: str) -> str:
    line = line.replace("\xa0", " ").replace("\u200b", "").strip()
    return re.sub(r"\s+", " ", line)


def _clean_endpoint_part(value: str) -> str:
    value = _clean_line(value)
    value = re.sub(r"[\ue000-\uf8ff\ufe0e\ufe0f]", "", value)
    value = re.sub(r"^[^\w]+", "", value)
    value = re.sub(r"\s+[^\w]+$", "", value)
    return value.strip()


def _extract_key_value_pairs(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    idx = 0
    while idx + 1 < len(lines):
        label = lines[idx]
        if _FIELD_LABEL_RE.fullmatch(label):
            fields[label] = lines[idx + 1]
            idx += 2
            continue
        idx += 1
    for line in lines:
        for label in _FIELD_LABELS:
            prefix = f"{label} "
            if line.startswith(prefix):
                fields[label] = line[len(prefix):].strip()
                break
    return fields


def _route_summary(row: dict[str, Any]) -> dict[str, Any]:
    lines = [_clean_line(line) for line in row.get("lines", []) if _clean_line(line)]
    fields = _extract_key_value_pairs(lines)
    route: dict[str, Any] = {
        "index": row.get("index"),
        "raw_text": row.get("text", ""),
        "lines": lines,
        "fields": fields,
        "links": list(row.get("links", [])),
    }

    for line in lines:
        match = _ENDPOINT_RE.match(line)
        if not match:
            continue
        side, station, system = match.groups()
        route[f"{side.lower()}_station"] = _clean_endpoint_part(station)
        route[f"{side.lower()}_system"] = _clean_endpoint_part(system)

    route["route_distance"] = fields.get("ROUTE DISTANCE")
    route["updated"] = fields.get("UPDATED")
    route["profit_per_unit"] = fields.get("PROFIT PER UNIT")
    route["profit_per_trip"] = fields.get("PROFIT PER TRIP")
    route["profit_per_hour"] = fields.get("PROFIT PER HOUR")
    return route


def _print_route_summary(route: dict[str, Any]) -> None:
    index = route.get("index", "?")
    from_station = route.get("from_station", "?")
    from_system = route.get("from_system", "?")
    to_station = route.get("to_station", "?")
    to_system = route.get("to_system", "?")
    print(f"[{index}] {from_station} ({from_system}) -> {to_station} ({to_system})")

    details: list[str] = []
    for label, key in (
        ("route", "route_distance"),
        ("ppu", "profit_per_unit"),
        ("trip", "profit_per_trip"),
        ("hour", "profit_per_hour"),
        ("updated", "updated"),
    ):
        value = route.get(key)
        if value:
            details.append(f"{label}={value}")
    if details:
        print(f"    {' | '.join(details)}")
    else:
        preview = " | ".join(route.get("lines", [])[:4])
        if preview:
            print(f"    {preview}")


def _extract_rows(page: Any) -> list[dict[str, Any]]:
    return page.locator("div.mainblock.traderoutebox").evaluate_all(
        """
        (nodes) => nodes.map((node, index) => ({
          index: index + 1,
          text: (node.innerText || "").replace(/\\u00a0/g, " ").trim(),
          lines: (node.innerText || "")
            .replace(/\\u00a0/g, " ")
            .split(/\\n+/)
            .map((line) => line.trim())
            .filter(Boolean),
          links: Array.from(node.querySelectorAll("a[href]"), (anchor) => anchor.href),
        }))
        """
    )


def _challenge_present(page: Any) -> bool:
    text = page.locator("body").inner_text(timeout=1000)
    return "Access check required" in text or "Confirm and continue" in text


def _wait_for_route_rows(page: Any, timeout_seconds: float, *, show_browser: bool) -> list[dict[str, Any]]:
    deadline = time.monotonic() + max(timeout_seconds, 0.0)
    challenge_logged = False
    while time.monotonic() < deadline:
        rows = _extract_rows(page)
        if rows:
            return rows
        if not challenge_logged and _challenge_present(page):
            challenge_logged = True
            if show_browser:
                print(
                    "Inara access check detected. Complete it in the opened browser window; "
                    "the probe will keep waiting for route rows."
                )
            else:
                print(
                    "Inara access check detected in headless mode. "
                    "Retry with `--show-browser` if you need to complete it manually."
                )
        page.wait_for_timeout(1000)
    raise SystemExit(
        "Timed out waiting for `div.mainblock.traderoutebox`. "
        "If Inara presented an access check, retry with `--show-browser`, "
        "complete the check, and rerun."
    )


def main() -> None:
    args = _build_parser().parse_args()
    sync_playwright = _load_sync_playwright()

    profile_dir = Path(args.profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=not args.show_browser,
            executable_path=args.browser_path,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            print(f"Opening {args.url}")
            page.goto(args.url, wait_until="domcontentloaded")
            rows = _wait_for_route_rows(page, args.timeout_seconds, show_browser=args.show_browser)
            summaries = [_route_summary(row) for row in rows]

            print(f"Found {len(summaries)} trade route row(s).")
            for route in summaries[: max(args.max_routes, 0)]:
                _print_route_summary(route)

            if args.save_html:
                html_path = Path(args.save_html)
                html_path.parent.mkdir(parents=True, exist_ok=True)
                html_path.write_text(page.content(), encoding="utf-8")
                print(f"Saved HTML to {html_path}")

            if args.save_json:
                json_path = Path(args.save_json)
                json_path.parent.mkdir(parents=True, exist_ok=True)
                json_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
                print(f"Saved JSON to {json_path}")

            if args.screenshot:
                screenshot_path = Path(args.screenshot)
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"Saved screenshot to {screenshot_path}")
        except BaseException:
            if args.screenshot:
                screenshot_path = Path(args.screenshot)
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    page = context.pages[0] if context.pages else None
                    if page is not None:
                        page.screenshot(path=str(screenshot_path), full_page=True)
                        print(f"Saved screenshot to {screenshot_path}")
                except Exception:
                    pass
            raise
        finally:
            context.close()


if __name__ == "__main__":
    main()
