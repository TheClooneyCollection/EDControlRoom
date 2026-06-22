from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
import re
import urllib.parse
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PROFILE_DIR = _REPO_ROOT / "artifacts" / "playwright" / "inara-profile"
_BASE_TRADE_ROUTES_URL = "https://inara.cz/elite/market-traderoutes/"

# These parameters are the operator-supplied starting defaults from the initial
# Praea Euq AK-A d25 experiment. Only the source system (`ps1`) changes for
# `haul search [system]` right now.
DEFAULT_TRADE_ROUTE_QUERY_PARAMS: dict[str, str] = {
    "pi10": "460",
    "pi2": "60",
    "pi5": "8",
    "pi3": "3",
    "pi9": "500",
    "pi4": "1",
    "pi7": "5000",
    "pi12": "5000",
    "pi8": "1",
    "pi14": "0",
    "pi15": "0",
    "pi1": "4",
}

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


@dataclass(frozen=True)
class TradeRoute:
    index: int
    from_station: str
    from_system: str
    to_station: str
    to_system: str
    route_distance: str | None = None
    profit_per_unit: str | None = None
    profit_per_trip: str | None = None
    profit_per_hour: str | None = None
    updated: str | None = None
    raw_text: str = ""
    url_links: tuple[str, ...] = ()


@dataclass(frozen=True)
class TradeRouteSearchResult:
    system_name: str
    query_url: str
    searched_at: str
    routes: tuple[TradeRoute, ...]


def _load_sync_playwright() -> Any:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError(
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


def _row_to_route(row: dict[str, Any]) -> TradeRoute:
    lines = [_clean_line(line) for line in row.get("lines", []) if _clean_line(line)]
    fields = _extract_key_value_pairs(lines)

    from_station = "?"
    from_system = "?"
    to_station = "?"
    to_system = "?"
    for line in lines:
        match = _ENDPOINT_RE.match(line)
        if not match:
            continue
        side, station, system = match.groups()
        if side == "FROM":
            from_station = _clean_endpoint_part(station)
            from_system = _clean_endpoint_part(system)
        else:
            to_station = _clean_endpoint_part(station)
            to_system = _clean_endpoint_part(system)

    return TradeRoute(
        index=int(row.get("index", 0) or 0),
        from_station=from_station,
        from_system=from_system,
        to_station=to_station,
        to_system=to_system,
        route_distance=fields.get("ROUTE DISTANCE"),
        profit_per_unit=fields.get("PROFIT PER UNIT"),
        profit_per_trip=fields.get("PROFIT PER TRIP"),
        profit_per_hour=fields.get("PROFIT PER HOUR"),
        updated=fields.get("UPDATED"),
        raw_text=str(row.get("text", "")),
        url_links=tuple(str(link) for link in row.get("links", [])),
    )


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
    import time

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
                    "the fetch will keep waiting for route rows."
                )
            else:
                raise RuntimeError(
                    "Inara access check detected in headless mode. Retry with a visible browser "
                    "session to complete the check first."
                )
        page.wait_for_timeout(1000)
    raise RuntimeError("Timed out waiting for Inara trade route rows.")


def build_trade_routes_url(
    system_name: str,
    *,
    query_params: dict[str, str] | None = None,
) -> str:
    params = dict(DEFAULT_TRADE_ROUTE_QUERY_PARAMS)
    if query_params is not None:
        params.update({str(key): str(value) for key, value in query_params.items()})
    params["ps1"] = system_name
    return f"{_BASE_TRADE_ROUTES_URL}?{urllib.parse.urlencode(params)}"


def fetch_trade_routes(
    query_url: str,
    *,
    timeout_seconds: float = 20.0,
    profile_dir: Path | None = None,
    show_browser: bool = False,
    browser_path: str | None = None,
) -> tuple[TradeRoute, ...]:
    sync_playwright = _load_sync_playwright()
    resolved_profile_dir = profile_dir or _DEFAULT_PROFILE_DIR
    resolved_profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(resolved_profile_dir),
            headless=not show_browser,
            executable_path=browser_path,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(query_url, wait_until="domcontentloaded")
            rows = _wait_for_route_rows(page, timeout_seconds, show_browser=show_browser)
            return tuple(_row_to_route(row) for row in rows)
        finally:
            context.close()


def search_trade_routes(
    system_name: str,
    *,
    timeout_seconds: float = 20.0,
    profile_dir: Path | None = None,
    show_browser: bool = False,
    browser_path: str | None = None,
    query_params: dict[str, str] | None = None,
) -> TradeRouteSearchResult:
    query_url = build_trade_routes_url(system_name, query_params=query_params)
    routes = fetch_trade_routes(
        query_url,
        timeout_seconds=timeout_seconds,
        profile_dir=profile_dir,
        show_browser=show_browser,
        browser_path=browser_path,
    )
    return TradeRouteSearchResult(
        system_name=system_name,
        query_url=query_url,
        searched_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        routes=routes,
    )
