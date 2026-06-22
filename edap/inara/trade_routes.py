from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
import re
import urllib.parse
from pathlib import Path
from typing import Any, Mapping


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PROFILE_DIR = _REPO_ROOT / "artifacts" / "playwright" / "inara-profile"
_BASE_TRADE_ROUTES_URL = "https://inara.cz/elite/market-traderoutes/"

# These parameters are the operator-supplied starting defaults from the initial
# Praea Euq AK-A d25 experiment. The `pi14`/`pi15` passthrough defaults remain
# pinned until the remaining Powerplay mapping is confirmed live.
DEFAULT_TRADE_ROUTE_QUERY_PARAMS: dict[str, str] = {
    "pi14": "0",
    "pi15": "0",
}

DEFAULT_TRADE_ROUTE_SEARCH_PARAMS: dict[str, str] = {
    "cargo_capacity": "460",
    "max_route_distance_ly": "60",
    "max_price_age_hours": "8",
    "min_landing_pad": "large",
    "max_station_distance_ls": "500",
    "use_surface_stations": "no",
    "min_supply": "5000",
    "min_demand": "5000",
    "include_round_trips": "true",
    "order_by": "best_profit_per_hour_estimate",
}

_LANDING_PAD_TO_QUERY = {
    "small": "1",
    "medium": "2",
    "large": "3",
}
_LANDING_PAD_FROM_QUERY = {value: key for key, value in _LANDING_PAD_TO_QUERY.items()}

_SURFACE_STATIONS_TO_QUERY = {
    "yes_with_odyssey": "0",
    "no": "1",
    "yes_exclude_odyssey": "2",
}
_SURFACE_STATIONS_FROM_QUERY = {
    value: key for key, value in _SURFACE_STATIONS_TO_QUERY.items()
}

_ORDER_BY_TO_QUERY = {
    "best_profit": "0",
    "last_update": "1",
    "route_distance": "2",
    "distance": "3",
    "best_profit_per_hour_estimate": "4",
}
_ORDER_BY_FROM_QUERY = {value: key for key, value in _ORDER_BY_TO_QUERY.items()}

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


def trade_route_search_defaults() -> dict[str, str]:
    return dict(DEFAULT_TRADE_ROUTE_SEARCH_PARAMS)


def _as_bool_string(value: str) -> str:
    return "true" if value.strip().lower() in {"1", "true", "y", "yes"} else "false"


def _clean_search_params(params: Mapping[str, str] | None) -> dict[str, str]:
    cleaned = trade_route_search_defaults()
    if params is None:
        return cleaned
    for key, value in params.items():
        if value is None:
            continue
        cleaned[str(key)] = str(value).strip()
    cleaned["include_round_trips"] = _as_bool_string(cleaned.get("include_round_trips", "true"))
    return cleaned


def build_trade_route_query_params(search_params: Mapping[str, str] | None = None) -> dict[str, str]:
    params = _clean_search_params(search_params)
    query_params = dict(DEFAULT_TRADE_ROUTE_QUERY_PARAMS)
    query_params["pi10"] = params["cargo_capacity"]
    query_params["pi2"] = params["max_route_distance_ly"]
    query_params["pi5"] = params["max_price_age_hours"]
    query_params["pi3"] = _LANDING_PAD_TO_QUERY.get(params["min_landing_pad"], "3")
    query_params["pi9"] = params["max_station_distance_ls"]
    query_params["pi4"] = _SURFACE_STATIONS_TO_QUERY.get(params["use_surface_stations"], "1")
    query_params["pi7"] = params["min_supply"]
    query_params["pi12"] = params["min_demand"]
    query_params["pi1"] = _ORDER_BY_TO_QUERY.get(params["order_by"], "4")
    if params["include_round_trips"] == "true":
        query_params["pi8"] = "1"
    else:
        query_params.pop("pi8", None)
    return query_params


def parse_trade_routes_url(query_url: str) -> tuple[str, dict[str, str]]:
    parsed = urllib.parse.urlparse(query_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Inara trade-route URL must start with http:// or https://.")
    if parsed.netloc.lower() != "inara.cz":
        raise ValueError("Only inara.cz trade-route URLs are supported.")
    if not parsed.path.rstrip("/").endswith("/elite/market-traderoutes"):
        raise ValueError("URL must point to Inara's /elite/market-traderoutes page.")

    query = urllib.parse.parse_qs(parsed.query)
    system_name = (query.get("ps1", [""])[0] or "").strip()
    if not system_name:
        raise ValueError("Inara trade-route URL is missing the ps1 source-system parameter.")

    return system_name, {
        "cargo_capacity": (query.get("pi10", [""])[0] or DEFAULT_TRADE_ROUTE_SEARCH_PARAMS["cargo_capacity"]).strip(),
        "max_route_distance_ly": (query.get("pi2", [""])[0] or DEFAULT_TRADE_ROUTE_SEARCH_PARAMS["max_route_distance_ly"]).strip(),
        "max_price_age_hours": (query.get("pi5", [""])[0] or DEFAULT_TRADE_ROUTE_SEARCH_PARAMS["max_price_age_hours"]).strip(),
        "min_landing_pad": _LANDING_PAD_FROM_QUERY.get(
            (query.get("pi3", [""])[0] or "").strip(),
            DEFAULT_TRADE_ROUTE_SEARCH_PARAMS["min_landing_pad"],
        ),
        "max_station_distance_ls": (query.get("pi9", [""])[0] or DEFAULT_TRADE_ROUTE_SEARCH_PARAMS["max_station_distance_ls"]).strip(),
        "use_surface_stations": _SURFACE_STATIONS_FROM_QUERY.get(
            (query.get("pi4", [""])[0] or "").strip(),
            DEFAULT_TRADE_ROUTE_SEARCH_PARAMS["use_surface_stations"],
        ),
        "min_supply": (query.get("pi7", [""])[0] or DEFAULT_TRADE_ROUTE_SEARCH_PARAMS["min_supply"]).strip(),
        "min_demand": (query.get("pi12", [""])[0] or DEFAULT_TRADE_ROUTE_SEARCH_PARAMS["min_demand"]).strip(),
        "include_round_trips": "true" if (query.get("pi8", [""])[0] or "").strip() == "1" else "false",
        "order_by": _ORDER_BY_FROM_QUERY.get(
            (query.get("pi1", [""])[0] or "").strip(),
            DEFAULT_TRADE_ROUTE_SEARCH_PARAMS["order_by"],
        ),
    }


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
    params = build_trade_route_query_params(query_params)
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
