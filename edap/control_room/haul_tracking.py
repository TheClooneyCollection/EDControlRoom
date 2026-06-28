from __future__ import annotations

from typing import Any, Callable, Protocol

from edap.control_room.models import HaulStats, ShipState
from edap.tts import AnnouncementId, format_credits_short


class HaulTrackingHost(Protocol):
    _haul_stats: HaulStats
    _ship: ShipState
    _time_fn: Callable[[], float]

    def _log(self, msg: str) -> None: ...
    def _refresh_haul_stats(self) -> None: ...
    def _save_saved_state(self) -> None: ...
    def _announce_tts(self, message_id: AnnouncementId, /, **values: object) -> None: ...


def start_haul_stats(
    app: HaulTrackingHost,
    *,
    station_1_buying: str,
    station_2_buying: str,
    station_1: str,
    station_2: str,
) -> None:
    at_station_1 = bool(
        station_1
        and app._ship.status == "in_station"
        and app._ship.station
        and app._ship.station.lower() == station_1.lower()
    )
    previous = app._haul_stats
    started_at = app._time_fn()
    app._haul_stats = HaulStats(
        station_1_buying=station_1_buying,
        station_2_buying=station_2_buying,
        station_1=station_1,
        station_2=station_2,
        session_started_at=previous.session_started_at or started_at,
        active=True,
        current_run_started_at=started_at,
        waiting_for_station_1_departure=at_station_1,
        resumed_mid_run=not at_station_1,
        accumulated_profit=previous.accumulated_profit,
        completed_runs=previous.completed_runs,
        last_run_profit=previous.last_run_profit,
        last_run_elapsed_s=previous.last_run_elapsed_s,
        total_run_elapsed_s=previous.total_run_elapsed_s,
    )
    app._refresh_haul_stats()
    app._save_saved_state()


def stop_haul_stats(app: HaulTrackingHost) -> None:
    if not app._haul_stats.station_1_buying:
        return
    if app._haul_stats.completed_runs > 0:
        app._announce_tts(
            AnnouncementId.SESSION_COMPLETE,
            cycle_count=app._haul_stats.completed_runs,
            total_profit_short=format_credits_short(app._haul_stats.accumulated_profit),
        )
    app._haul_stats.active = False
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
    stats.completed_runs += 1
    stats.last_run_elapsed_s = elapsed
    stats.last_run_profit = stats.current_run_profit
    stats.total_run_elapsed_s += elapsed
    stats.accumulated_profit += stats.current_run_profit
    stats.clean_run_active = False
    stats.current_run_profit = 0
    stats.current_run_started_at = None
    stats.current_run_elapsed_s = None
    stats.docked_back_at_station_1 = False
    stats.waiting_for_station_1_departure = True
    stats.resumed_mid_run = False
    app._announce_tts(
        AnnouncementId.ROUTE_COMPLETE,
        cycle_count=stats.completed_runs,
        total_profit_short=format_credits_short(stats.accumulated_profit),
    )
    app._save_saved_state()


def handle_haul_event(
    app: HaulTrackingHost,
    ev: dict[str, Any],
    *,
    station_before: str | None,
) -> None:
    stats = app._haul_stats
    if not stats.active or not stats.station_1_buying or not stats.station_1:
        return

    event = ev.get("event", "")
    current_station = station_before or app._ship.station
    at_station_1 = bool(current_station and current_station.lower() == stats.station_1.lower())
    at_station_2 = bool(
        stats.station_2
        and current_station
        and current_station.lower() == stats.station_2.lower()
    )

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
        if stats.clean_run_active and at_station_2:
            stats.current_run_profit -= total_cost
        elif at_station_1 and stats.waiting_for_station_1_departure:
            if stats.current_run_started_at is not None:
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
            app._log(
                "[dim]Ignoring station 1 sale for haul stats "
                "(discarding profit from prior run).[/]"
            )

    app._refresh_haul_stats()
    app._save_saved_state()
