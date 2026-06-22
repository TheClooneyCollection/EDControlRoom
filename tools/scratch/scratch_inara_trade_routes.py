"""
Browser-backed Inara trade-route probe.

This scratch script uses the shared Inara Playwright fetcher to open a
trade-routes results page in a real browser context and print a compact summary
of the live DOM. It is intentionally a developer probe, not part of the main
runtime surface.

Typical usage:
    uv run python3 tools/scratch/scratch_inara_trade_routes.py "<url>"
    uv run python3 tools/scratch/scratch_inara_trade_routes.py "<url>" --show-browser

Before first use on a machine:
    uv sync --extra browsing
    uv run playwright install chromium
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from edap.inara.trade_routes import TradeRoute, fetch_trade_routes

_DEFAULT_PROFILE_DIR = _REPO_ROOT / "artifacts" / "playwright" / "inara-profile"


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
        "--save-json",
        metavar="PATH",
        help="write extracted route rows as JSON to PATH",
    )
    parser.add_argument(
        "--max-routes",
        type=int,
        default=5,
        help="how many route summaries to print (default: 5)",
    )
    return parser


def _print_route_summary(route: TradeRoute) -> None:
    print(
        f"[{route.index}] {route.from_station} ({route.from_system}) -> "
        f"{route.to_station} ({route.to_system})"
    )
    details: list[str] = []
    if route.route_distance:
        details.append(f"route={route.route_distance}")
    if route.profit_per_unit:
        details.append(f"ppu={route.profit_per_unit}")
    if route.profit_per_trip:
        details.append(f"trip={route.profit_per_trip}")
    if route.profit_per_hour:
        details.append(f"hour={route.profit_per_hour}")
    if route.updated:
        details.append(f"updated={route.updated}")
    print(f"    {' | '.join(details)}")


def main() -> None:
    args = _build_parser().parse_args()
    print(f"Opening {args.url}")
    routes = fetch_trade_routes(
        args.url,
        timeout_seconds=args.timeout_seconds,
        profile_dir=Path(args.profile_dir),
        show_browser=args.show_browser,
        browser_path=args.browser_path,
    )
    print(f"Found {len(routes)} trade route row(s).")
    for route in routes[: max(args.max_routes, 0)]:
        _print_route_summary(route)
    if args.save_json:
        output_path = Path(args.save_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps([route.__dict__ for route in routes], indent=2), encoding="utf-8")
        print(f"Saved JSON to {output_path}")


if __name__ == "__main__":
    main()
