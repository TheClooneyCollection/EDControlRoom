from __future__ import annotations

import re
from typing import Any, Callable, Protocol

from edap.control_room.models import HaulStats, RuntimeUIState, ShipState
from edap.control_room.rendering import fmt_duration
from edap.control_room_state import ControlRoomState
from edap.haul_history import abort_run, close_run, record_event, snapshot_duration, utc_timestamp
from edap.tts import AnnouncementId, format_credits_short

_CREDIT_AMOUNT_RE = re.compile(
    r"(?P<amount>[+-]?\d+(?:[\d,]*\d)?(?:\.\d+)?)\s*"
    r"(?P<suffix>billion|bn|b|million|mil|m|thousand|k)?",
    re.IGNORECASE,
)


class HaulTrackingHost(Protocol):
    _haul_stats: HaulStats
    _ship: ShipState
    _runtime_state: RuntimeUIState
    _saved_state: ControlRoomState
    _time_fn: Callable[[], float]

    def _log(self, msg: str) -> None: ...
    def _laden_jump_range_ly(self) -> float: ...
    def _refresh_haul_stats(self) -> None: ...
    def _save_saved_state(self) -> None: ...
    def _announce_tts(self, message_id: AnnouncementId, /, **values: object) -> None: ...


def ship_record(ship: ShipState, laden_jump_range_ly: float) -> dict[str, Any]:
    """The ship a haul run is flown in, as stored on its history row."""
    return {
        "id": ship.ship_id, "type": ship.ship_type, "name": ship.ship_name, "ident": ship.ship_ident,
        "cargo_capacity": ship.cargo_capacity, "max_jump_range_ly": ship.max_jump_range_ly,
        "laden_jump_range_ly": laden_jump_range_ly,
    }


def start_haul_stats(
    app: HaulTrackingHost,
    *,
    station_1_buying: str,
    station_2_buying: str,
    station_1: str,
    station_2: str,
    expected_profit_per_trip_text: str = "",
) -> None:
    at_station_1 = bool(
        station_1
        and app._ship.status == "in_station"
        and app._ship.station
        and app._ship.station.lower() == station_1.lower()
    )
    previous = app._haul_stats
    if previous.suspended and previous.current_run is not None and _same_haul(
        previous, (station_1_buying, station_2_buying, station_1, station_2)
    ):
        previous.suspended = False
        previous.active = True
        previous.paused = True
        previous.expected_profit_per_trip = parse_credit_amount(expected_profit_per_trip_text)
        previous.expected_profit_per_trip_text = expected_profit_per_trip_text
        app._log("[green]Continuing the haul run left open when the haul ended.[/]")
        resume_haul_stats(app)
        return
    abort_run(app._haul_stats, "new haul started over stale run", utc_timestamp(None), app._time_fn())
    if not previous.session_active or previous.suspended:
        previous = HaulStats(pending_runs=previous.pending_runs)
    started_at = app._time_fn()
    expected_profit_per_trip = parse_credit_amount(expected_profit_per_trip_text)
    app._haul_stats = HaulStats(
        pending_runs=previous.pending_runs,
        station_1_buying=station_1_buying,
        station_2_buying=station_2_buying,
        station_1=station_1,
        station_2=station_2,
        session_started_at=(
            previous.session_started_at
            if previous.session_started_at is not None
            else started_at - previous.session_elapsed_s
        ),
        session_elapsed_s=previous.session_elapsed_s,
        session_active=True,
        active=True,
        current_run_started_at=started_at,
        waiting_for_station_1_departure=at_station_1,
        resumed_mid_run=not at_station_1,
        expected_profit_per_trip=expected_profit_per_trip,
        expected_profit_per_trip_text=expected_profit_per_trip_text,
        accumulated_profit=previous.accumulated_profit,
        cargo_moved_t=previous.cargo_moved_t,
        completed_runs=previous.completed_runs,
        last_run_profit=previous.last_run_profit,
        last_run_profit_delta=previous.last_run_profit_delta,
        last_run_elapsed_s=previous.last_run_elapsed_s,
        total_run_elapsed_s=previous.total_run_elapsed_s,
    )
    app._refresh_haul_stats()
    app._save_saved_state()


def _same_haul(stats: HaulStats, haul: tuple[str, str, str, str]) -> bool:
    current = (stats.station_1_buying, stats.station_2_buying, stats.station_1, stats.station_2)
    return all(a.casefold() == b.casefold() for a, b in zip(current, haul))


def suspend_haul_stats(app: HaulTrackingHost) -> None:
    """End a haul but keep its in-progress run open, so restarting the same haul continues it.

    Timers freeze as for a pause; a different haul, `clear` or a relaunch still aborts the run.
    """
    stats = app._haul_stats
    if stats.current_run is None or not stats.active:
        stop_haul_stats(app)
        return
    pause_haul_stats(app)
    snapshot_duration(stats, app._time_fn())
    stats.paused = False
    stats.active = False
    stats.suspended = True
    app._log("[yellow]Haul run kept open; start the same haul again to continue it.[/]")
    app._refresh_haul_stats()
    app._save_saved_state()


def stop_haul_stats(app: HaulTrackingHost) -> None:
    stats = app._haul_stats
    stats.suspended = False
    now = app._time_fn()
    if stats.session_started_at is not None:
        stats.session_elapsed_s = max(0.0, now - stats.session_started_at)
        stats.session_started_at = None
    if stats.current_run_started_at is not None and not stats.docked_back_at_station_1:
        stats.current_run_elapsed_s = max(0.0, now - stats.current_run_started_at)
    stats.current_run_started_at = None
    abort_run(stats, "stats stopped", utc_timestamp(None), now)
    if not (app._haul_stats.station_1 or app._haul_stats.station_1_buying):
        return
    if app._haul_stats.completed_runs > 0:
        app._announce_tts(
            AnnouncementId.SESSION_COMPLETE,
            cycle_count=app._haul_stats.completed_runs,
            total_profit_short=format_credits_short(app._haul_stats.accumulated_profit),
        )
    app._haul_stats.active = False
    app._haul_stats.paused = False
    # The numbers stay on screen until the next haul, which starts them from zero.
    app._haul_stats.session_active = False
    app._log(f"[dim]{session_summary(app._haul_stats)}.[/]")
    app._refresh_haul_stats()
    app._save_saved_state()


def session_summary(stats: HaulStats) -> str:
    runs = stats.completed_runs
    average = fmt_duration(stats.total_run_elapsed_s / runs) if runs else "—"
    return (
        f"Haul session: {runs} run{'' if runs == 1 else 's'}, {stats.accumulated_profit:,} Cr "
        f"in {fmt_duration(stats.session_elapsed_s)}, average run {average}"
    )


def pause_haul_stats(app: HaulTrackingHost) -> None:
    stats = app._haul_stats
    if not stats.active or stats.paused:
        return
    now = app._time_fn()
    if stats.session_started_at is not None:
        stats.session_elapsed_s = max(0.0, now - stats.session_started_at)
        stats.session_started_at = None
    if stats.current_run_started_at is not None and not stats.docked_back_at_station_1:
        stats.current_run_elapsed_s = max(0.0, now - stats.current_run_started_at)
        stats.current_run_started_at = None
    stats.paused = True
    app._refresh_haul_stats()
    app._save_saved_state()


def resume_haul_stats(app: HaulTrackingHost) -> None:
    stats = app._haul_stats
    if not stats.active or not stats.paused:
        return
    now = app._time_fn()
    if stats.session_active:
        stats.session_started_at = max(0.0, now - stats.session_elapsed_s)
    if stats.current_run_elapsed_s is not None and not stats.docked_back_at_station_1:
        stats.current_run_started_at = max(0.0, now - stats.current_run_elapsed_s)
    stats.paused = False
    app._refresh_haul_stats()
    app._save_saved_state()


def finalize_completed_haul_run(app: HaulTrackingHost) -> None:
    stats = app._haul_stats
    if not stats.clean_run_active:
        return
    elapsed = stats.current_run_elapsed_s
    if elapsed is None and stats.current_run_started_at is not None:
        elapsed = app._time_fn() - stats.current_run_started_at
    if elapsed is None:
        return
    close_run(stats, "completed", "", None, app._time_fn())
    stats.completed_runs += 1
    stats.last_run_elapsed_s = elapsed
    stats.last_run_profit = stats.current_run_profit
    _compare_completed_run_to_expected_route(app, stats)
    stats.total_run_elapsed_s += elapsed
    stats.accumulated_profit += stats.current_run_profit
    stats.clean_run_active = False
    stats.current_run_profit = 0
    stats.current_run_started_at = None
    stats.current_run_elapsed_s = elapsed
    stats.docked_back_at_station_1 = False
    stats.waiting_for_station_1_departure = True
    stats.resumed_mid_run = False
    app._announce_tts(
        AnnouncementId.ROUTE_COMPLETE,
        cycle_count=stats.completed_runs,
        total_profit_short=format_credits_short(stats.accumulated_profit),
    )
    app._save_saved_state()


def parse_credit_amount(value: str | None) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    match = _CREDIT_AMOUNT_RE.search(text.replace(",", ""))
    if match is None:
        return None
    try:
        amount = float(match.group("amount"))
    except (TypeError, ValueError):
        return None
    suffix = (match.group("suffix") or "").lower()
    multiplier = 1
    if suffix in {"billion", "bn", "b"}:
        multiplier = 1_000_000_000
    elif suffix in {"million", "mil", "m"}:
        multiplier = 1_000_000
    elif suffix in {"thousand", "k"}:
        multiplier = 1_000
    return int(round(amount * multiplier))


def _compare_completed_run_to_expected_route(app: HaulTrackingHost, stats: HaulStats) -> None:
    expected = stats.expected_profit_per_trip
    actual = stats.last_run_profit
    if expected is None or actual is None:
        stats.last_run_profit_delta = None
        return
    delta = actual - expected
    stats.last_run_profit_delta = delta
    actual_text = format_credits_short(actual)
    expected_text = format_credits_short(expected)
    if delta == 0:
        comparison_text = "the expected amount"
        log_comparison = "exactly the expected route profit"
        color = "green"
    elif delta > 0:
        comparison_text = f"{format_credits_short(delta)} more"
        log_comparison = f"{format_credits_short(delta)} more than expected"
        color = "green"
    else:
        comparison_text = f"{format_credits_short(abs(delta))} less"
        log_comparison = f"{format_credits_short(abs(delta))} less than expected"
        color = "yellow"
    app._log(
        f"[{color}]Completed haul run profit "
        f"{actual_text}; {log_comparison} "
        f"(planned route {expected_text}).[/{color}]"
    )
    app._announce_tts(
        AnnouncementId.ROUTE_PROFIT_DELTA,
        comparison_text=comparison_text,
    )


def handle_haul_event(
    app: HaulTrackingHost,
    ev: dict[str, Any],
    *,
    station_before: str | None,
) -> None:
    stats = app._haul_stats
    if not stats.active or not stats.station_1:
        return

    event = ev.get("event", "")
    current_station = ev.get("StationName") or station_before or app._ship.station
    at_station_1 = bool(current_station and current_station.lower() == stats.station_1.lower())
    at_station_2 = bool(
        stats.station_2
        and current_station
        and current_station.lower() == stats.station_2.lower()
    )

    if (at_station_1 and stats.current_run is not None
            and stats.current_run.get("partial_start")
            and (event == "Undocked" or (event == "MarketBuy" and stats.waiting_for_station_1_departure))):
        abort_run(stats, "resumed mid-run, not a clean run", None, app._time_fn())

    if at_station_1 or at_station_2 or event in {"MarketBuy", "MarketSell"}:
        record_event(stats, ev, current_station or "", ev.get("StarSystem") or app._ship.system or "")
        if stats.current_run is not None:
            stats.current_run["phase"] = app._runtime_state.haul_phase
            # A row saved before ship tracking, or begun before the Loadout arrived, gets its ship here.
            if (stats.current_run.get("ship") or {}).get("id") is None:
                stats.current_run["ship"] = ship_record(app._ship, app._laden_jump_range_ly())
            for index in (1, 2):
                key = f"system_{index}"
                if not stats.current_run["route"][key]:
                    stats.current_run["route"][key] = app._saved_state.default_haul.get(f"station_{index}_system") or None

    if event == "Undocked" and at_station_1:
        if stats.current_run_started_at is None:
            stats.current_run_started_at = app._time_fn()
            stats.current_run_elapsed_s = None
        stats.clean_run_active = True
        stats.waiting_for_station_1_departure = False
        stats.resumed_mid_run = False
        stats.docked_back_at_station_1 = False
    elif event == "Docked" and ev.get("StationName", "").lower() == stats.station_1.lower():
        if stats.clean_run_active and stats.current_run_started_at is not None:
            stats.current_run_elapsed_s = app._time_fn() - stats.current_run_started_at
            stats.docked_back_at_station_1 = True
        elif stats.resumed_mid_run:
            if stats.current_run_started_at is not None:
                stats.current_run_elapsed_s = app._time_fn() - stats.current_run_started_at
            stats.resumed_mid_run = False
            stats.waiting_for_station_1_departure = True
    elif event == "MarketBuy" and "TotalCost" in ev:
        total_cost = int(ev["TotalCost"])
        stats.cargo_moved_t += int(ev.get("Count", 0) or 0)
        if stats.clean_run_active and at_station_2:
            stats.current_run_profit -= total_cost
        elif at_station_1 and stats.waiting_for_station_1_departure:
            stats.current_run_started_at = None
            stats.current_run_elapsed_s = None
            stats.current_run_profit -= total_cost
    elif event == "MarketSell" and "TotalSale" in ev:
        total_sale = int(ev["TotalSale"])
        if stats.clean_run_active and at_station_2:
            stats.current_run_profit += total_sale
        elif stats.clean_run_active and at_station_1:
            stats.current_run_profit += total_sale
            if stats.docked_back_at_station_1:
                finalize_completed_haul_run(app)
        elif at_station_1:
            abort_run(stats, "resumed mid-run, not a clean run", None, app._time_fn())
            app._log(
                "[dim]Station 1 sale ends a resumed run: profit counts in the session, "
                "not as a completed run.[/]"
            )

    app._refresh_haul_stats()
    app._save_saved_state()
