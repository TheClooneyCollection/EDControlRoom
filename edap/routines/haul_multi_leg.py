from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

from edap.actions import ActionDispatchResult
from edap.multi_leg_haul import CargoTransfer, MultiLegHaulDefinition, RouteStop, build_route_stops
from edap.routines._base import RoutineResult
from edap.routines.docking import _undock_until_undocked, _wait_for_clear_of_station, dock, station_refuel_menu
from edap.routines.escape import escape_mass_lock
from edap.routines.haul_support import (
    HaulRuntime,
    TransitResumeState,
    detect_transit_resume_state,
    engage_hyperspace_after_escape,
    is_manual_landing_result,
    manual_landing_result,
    open_navigation_panel_after_arrival,
    read_cargo_json,
    read_latest_journal_events,
    read_market_station,
    sellable_cargo,
    set_galaxy_map_destination_for_haul,
    wait_for_arrival_or_approach_event,
    wait_for_on_land_handoff,
)
from edap.routines.market import market_buy, market_sell
from edap.state import get_latest_journal_log, read_ship_state
from edap.tts import AnnouncementId


class Phase(Enum):
    SELL = auto()
    BUY = auto()
    UNDOCK = auto()
    DEPART_SYSTEM = auto()
    TRANSIT = auto()
    COMPLETE = auto()


@dataclass
class _Ctx:
    runtime: HaulRuntime
    definition: MultiLegHaulDefinition
    stops: tuple[RouteStop, ...]


_read_cargo_json = read_cargo_json
_read_market_station = read_market_station
_wait_for_arrival_or_approach_event = wait_for_arrival_or_approach_event


def _inventory_count(inventory: list[dict], commodity: str) -> int:
    total = 0
    commodity_lower = commodity.lower()
    for item in inventory:
        count = item.get("Count", 0)
        if isinstance(count, bool) or not isinstance(count, (int, float)):
            continue
        if (
            str(item.get("Name", "")).lower() == commodity_lower
            or str(item.get("Name_Localised", "")).lower() == commodity_lower
        ):
            total += int(count)
    return total


def _has_all_cargo(inventory: list[dict], cargo: tuple[CargoTransfer, ...]) -> bool:
    if not cargo:
        return True
    return all(_inventory_count(inventory, item.commodity) >= item.amount for item in cargo)


def _has_any_cargo(inventory: list[dict], cargo: tuple[CargoTransfer, ...]) -> bool:
    return any(_inventory_count(inventory, item.commodity) > 0 for item in cargo)


def _read_ship_position(journal_dir: Path) -> tuple[str, str, str]:
    ship_status = "unknown"
    current_station = ""
    current_system = ""
    log_path = get_latest_journal_log(journal_dir)
    if log_path is not None:
        try:
            state = read_ship_state(log_path)
        except Exception:
            state = None
        if state is not None:
            current_station = str(state.station or "")
            current_system = str(state.location or "")
            status = str(state.status or "")
            if status == "in_station":
                ship_status = "docked"
            elif status in {"in_space", "in_undocking", "starting_docking", "in_docking"}:
                ship_status = "normal_space"
            elif status in {"in_supercruise", "starting_hyperspace", "starting_supercruise"}:
                ship_status = "supercruise"
    if ship_status in {"docked", "unknown"}:
        market_station, market_system = _read_market_station(journal_dir)
        if not current_station and market_station:
            current_station = market_station
        if not current_system and market_system:
            current_system = market_system
        if current_station:
            ship_status = "docked"
    return ship_status, current_station, current_system


def _detect_start_state(ctx: _Ctx) -> tuple[int, Phase]:
    runtime = ctx.runtime
    inventory = _read_cargo_json(runtime.journal_dir)
    ship_status, current_station, current_system = _read_ship_position(runtime.journal_dir)
    current_station_lower = current_station.lower()
    current_system_lower = current_system.lower()

    runtime.progress_fn(
        "Multi-leg phase detect: "
        f"status={ship_status}, station={current_station!r}, system={current_system!r}"
    )

    for stop in ctx.stops:
        if stop.endpoint.station and current_station_lower == stop.endpoint.station.lower():
            if _has_any_cargo(inventory, stop.inbound):
                return stop.index, Phase.SELL
            if stop.outbound and _has_all_cargo(inventory, stop.outbound):
                return stop.index, Phase.UNDOCK
            if stop.outbound:
                return stop.index, Phase.BUY
            return stop.index, Phase.COMPLETE

    for leg in ctx.definition.legs:
        if _has_all_cargo(inventory, leg.cargo):
            source_index = leg.index - 1
            if current_system_lower and current_system_lower == leg.source.system.lower():
                return source_index, Phase.DEPART_SYSTEM if ship_status == "normal_space" else Phase.UNDOCK
            return source_index, Phase.TRANSIT

    return 0, Phase.BUY if ctx.stops and ctx.stops[0].outbound else Phase.COMPLETE


def _run_sell(ctx: _Ctx, stop: RouteStop) -> RoutineResult:
    runtime = ctx.runtime
    if not stop.inbound or not sellable_cargo(_read_cargo_json(runtime.journal_dir)):
        return RoutineResult(action="market_sell", dispatch=ActionDispatchResult(action="market_sell", status="ok", reason="nothing to sell"))
    for cargo in stop.inbound:
        available = _inventory_count(_read_cargo_json(runtime.journal_dir), cargo.commodity)
        if available <= 0:
            runtime.progress_fn(f"{cargo.commodity} already absent at {stop.label} - skipping sell.")
            continue
        runtime.progress_fn(f"Selling {cargo.amount}t {cargo.commodity} at {stop.label}...")
        runtime.announce_fn(AnnouncementId.SELLING_CARGO, commodity_name=cargo.commodity)
        result = market_sell(
            runtime.controls,
            runtime.watcher,
            market_path=runtime.market_path,
            target=cargo.commodity,
            amount=str(min(available, cargo.amount)),
            step_delay_s=runtime.timing.step_delay_s,
            max_hold_s=runtime.timing.max_hold_s,
            buy_hold_segments=runtime.market.buy_hold_segments,
            sell_quantity_restore_taps=runtime.market.sell_quantity_restore_taps,
            sell_quantity_restore_tap_delay_s=runtime.market.sell_quantity_restore_tap_delay_s,
            trade_timeout_s=runtime.timing.trade_timeout_s,
            time_fn=runtime.time_fn,
            sleeper=runtime.sleeper,
            progress_fn=runtime.progress_fn,
            announce_fn=runtime.announce_fn,
            critical_level_multiplier=runtime.market.critical_level_multiplier,
        )
        if result.dispatch.status != "ok":
            return result
        if runtime.timing.post_sell_settle_s > 0:
            runtime.sleeper(runtime.timing.post_sell_settle_s)
    return RoutineResult(action="market_sell", dispatch=ActionDispatchResult(action="market_sell", status="ok"))


def _run_buy(ctx: _Ctx, stop: RouteStop) -> RoutineResult:
    runtime = ctx.runtime
    if not stop.outbound:
        return RoutineResult(action="market_buy", dispatch=ActionDispatchResult(action="market_buy", status="ok", reason="no outbound cargo"))
    for cargo in stop.outbound:
        already_loaded = _inventory_count(_read_cargo_json(runtime.journal_dir), cargo.commodity)
        remaining = max(0, cargo.amount - already_loaded)
        if remaining <= 0:
            runtime.progress_fn(f"{cargo.commodity} already loaded for departure from {stop.label} - skipping buy.")
            continue
        runtime.progress_fn(f"Buying {remaining}t {cargo.commodity} at {stop.label}...")
        runtime.announce_fn(AnnouncementId.BUYING_CARGO, commodity_name=cargo.commodity)
        result = market_buy(
            runtime.controls,
            runtime.watcher,
            market_path=runtime.market_path,
            target=cargo.commodity,
            amount=str(remaining),
            step_delay_s=runtime.timing.step_delay_s,
            max_hold_s=runtime.timing.max_hold_s,
            buy_hold_segments=runtime.market.buy_hold_segments,
            trade_timeout_s=runtime.timing.trade_timeout_s,
            time_fn=runtime.time_fn,
            sleeper=runtime.sleeper,
            progress_fn=runtime.progress_fn,
            announce_fn=runtime.announce_fn,
            critical_level_multiplier=runtime.market.critical_level_multiplier,
        )
        if result.dispatch.status != "ok":
            return result
    return RoutineResult(action="market_buy", dispatch=ActionDispatchResult(action="market_buy", status="ok"))


def _undock_and_route(ctx: _Ctx, stop: RouteStop, next_stop: RouteStop) -> RoutineResult:
    runtime = ctx.runtime
    runtime.progress_fn(f"Undocking from {stop.label}...")
    result, pending_events = _undock_until_undocked(
        runtime.controls,
        runtime.watcher,
        undock_timeout_s=runtime.timing.undock_timeout_s,
        step_delay_s=runtime.timing.step_delay_s,
        time_fn=runtime.time_fn,
        sleeper=runtime.sleeper,
        progress_fn=runtime.progress_fn,
    )
    if result.dispatch.status != "ok":
        return result
    route_confirmed = True
    if next_stop.endpoint.system:
        runtime.progress_fn(f"Setting galaxy map destination: {next_stop.endpoint.system}...")
        runtime.announce_fn(AnnouncementId.DESTINATION_SET, system_name=next_stop.endpoint.system)
        route_confirmed = set_galaxy_map_destination_for_haul(
            runtime=runtime,
            destination_system=next_stop.endpoint.system,
        )
    clear_result = _wait_for_clear_of_station(
        runtime.watcher,
        undocked_event=result.trigger_event,
        no_track_timeout_s=runtime.timing.undock_no_track_timeout_s,
        time_fn=runtime.time_fn,
        progress_fn=runtime.progress_fn,
        pending_events=pending_events,
    )
    if clear_result.dispatch.status != "ok":
        runtime.progress_fn(f"Error: {clear_result.dispatch.reason}; haul aborted. You can resume with replay / ctrl-r.")
        runtime.announce_fn(AnnouncementId.HAUL_ABORTED)
        return clear_result
    escape_mass_lock(
        runtime.controls,
        journal_dir=runtime.journal_dir,
        step_delay_s=runtime.timing.step_delay_s,
        boost_delay_s=runtime.timing.mass_lock_boost_delay_s,
        sleeper=runtime.sleeper,
        progress_fn=runtime.progress_fn,
    )
    if route_confirmed:
        engage_hyperspace_after_escape(runtime, progress_message="Mass lock cleared - engaging hyperspace...")
    else:
        runtime.progress_fn("Skipping automatic FSD engage because the galaxy-map route is unconfirmed.")
    return clear_result


def _depart_system(ctx: _Ctx, stop: RouteStop, next_stop: RouteStop) -> RoutineResult:
    runtime = ctx.runtime
    runtime.progress_fn(f"Departing {stop.label} system in normal space...")
    route_confirmed = True
    if next_stop.endpoint.system:
        runtime.progress_fn(f"Setting galaxy map destination: {next_stop.endpoint.system}...")
        runtime.announce_fn(AnnouncementId.DESTINATION_SET, system_name=next_stop.endpoint.system)
        route_confirmed = set_galaxy_map_destination_for_haul(
            runtime=runtime,
            destination_system=next_stop.endpoint.system,
        )
    escape_mass_lock(
        runtime.controls,
        journal_dir=runtime.journal_dir,
        step_delay_s=runtime.timing.step_delay_s,
        boost_delay_s=runtime.timing.mass_lock_boost_delay_s,
        sleeper=runtime.sleeper,
        progress_fn=runtime.progress_fn,
    )
    if route_confirmed:
        engage_hyperspace_after_escape(runtime, progress_message="Mass lock cleared - engaging hyperspace...")
    else:
        runtime.progress_fn("Skipping automatic FSD engage because the galaxy-map route is unconfirmed.")
    return RoutineResult(action="depart_system", dispatch=ActionDispatchResult(action="depart_system", status="ok"))


def _run_transit(ctx: _Ctx, next_stop: RouteStop) -> RoutineResult:
    runtime = ctx.runtime
    recent_events = read_latest_journal_events(runtime.journal_dir)
    resume_state = detect_transit_resume_state(recent_events, next_stop.endpoint)
    pending_events: list[dict[str, object]] = []
    if resume_state == TransitResumeState.AWAITING_DOCKED:
        runtime.progress_fn(f"Docking already in progress for {next_stop.label} - waiting for Docked.")
        return station_refuel_menu(
            runtime.controls,
            runtime.watcher,
            dock_timeout_s=runtime.timing.dock_timeout_s,
            settle_s=runtime.timing.settle_s,
            time_fn=runtime.time_fn,
            sleeper=runtime.sleeper,
            progress_fn=runtime.progress_fn,
        )
    if resume_state == TransitResumeState.NONE:
        arrival_observed, pending_events = _wait_for_arrival_or_approach_event(
            runtime.watcher,
            destination_system=next_stop.endpoint.system,
            deadline=runtime.time_fn() + runtime.timing.dock_timeout_s,
            time_fn=runtime.time_fn,
        )
        if arrival_observed:
            runtime.progress_fn("Arrived in destination system")
            open_navigation_panel_after_arrival(runtime, station_name=next_stop.endpoint.station)
    elif resume_state == TransitResumeState.ARRIVED_IN_DESTINATION_SYSTEM:
        open_navigation_panel_after_arrival(runtime, station_name=next_stop.endpoint.station)
    elif resume_state == TransitResumeState.POST_DROP_NEAR_STATION:
        if next_stop.endpoint.on_land:
            runtime.progress_fn(f"Already in normal space near on-land {next_stop.label} - handing off for manual landing.")
        else:
            runtime.progress_fn(f"Already in normal space near {next_stop.label} - skipping drop wait.")

    if next_stop.endpoint.on_land:
        if resume_state == TransitResumeState.POST_DROP_NEAR_STATION:
            runtime.progress_fn(
                f"{next_stop.label} is marked on-land; manual landing required from normal space. "
                "Resume multi-leg haul after landing."
            )
            return manual_landing_result(next_stop.endpoint)
        runtime.progress_fn(
            f"{next_stop.label} is marked on-land; waiting for SupercruiseExit before handing off."
        )
        drop_event = wait_for_on_land_handoff(
            runtime.watcher,
            destination=next_stop.endpoint,
            pending_events=pending_events,
            deadline=runtime.time_fn() + runtime.timing.dock_timeout_s,
            time_fn=runtime.time_fn,
        )
        if drop_event is None:
            return RoutineResult(
                action="manual_landing",
                dispatch=ActionDispatchResult(
                    action="manual_landing",
                    status="error",
                    reason=f"timed out waiting for SupercruiseExit near {next_stop.endpoint.station}",
                ),
            )
        runtime.progress_fn(
            f"Reached normal space near on-land {next_stop.label}; manual landing required. "
            "Resume multi-leg haul after landing."
        )
        return manual_landing_result(next_stop.endpoint)

    result = dock(
        runtime.controls,
        runtime.watcher,
        wait_for_supercruise_exit=resume_state != TransitResumeState.POST_DROP_NEAR_STATION,
        auto_refuel=True,
        max_retries=runtime.travel.max_dock_retries,
        request_timeout_s=runtime.timing.request_timeout_s,
        dock_timeout_s=runtime.timing.dock_timeout_s,
        settle_s=runtime.timing.settle_s,
        step_delay_s=runtime.timing.step_delay_s,
        supercruise_exit_settle_s=runtime.timing.supercruise_exit_settle_s,
        boost_settle_s=runtime.timing.boost_settle_s,
        deny_retry_delay_s=runtime.timing.deny_retry_delay_s,
        abort_on_interdiction=True,
        time_fn=runtime.time_fn,
        sleeper=runtime.sleeper,
        progress_fn=runtime.progress_fn,
        pending_events=pending_events,
        announce_fn=runtime.announce_fn,
        announce_station_name=next_stop.endpoint.station,
    )
    if result.action == "Interdicted" and result.dispatch.status != "ok":
        runtime.progress_fn(
            "Interdiction detected during multi-leg haul transit; haul aborted. "
            "Escape or re-enter supercruise, then resume haul."
        )
        runtime.announce_fn(AnnouncementId.HAUL_ABORTED)
    return result


def multi_leg_haul(
    runtime: HaulRuntime,
    *,
    definition: MultiLegHaulDefinition,
    stop_requested_fn: Callable[[], bool] | None = None,
) -> RoutineResult:
    stops = build_route_stops(definition)
    if not stops:
        raise ValueError("Multi-leg haul definition has no stops")
    ctx = _Ctx(runtime=runtime, definition=definition, stops=stops)

    stop_index, phase = _detect_start_state(ctx)
    if phase != Phase.BUY or stop_index != 0:
        runtime.progress_fn(f"Resuming multi-leg haul from stop {stop_index + 1} phase {phase.name}")
    last_result = RoutineResult(action="multi_leg_haul", dispatch=ActionDispatchResult(action="multi_leg_haul", status="ok"))

    while stop_index < len(stops):
        stop = stops[stop_index]
        next_stop = stops[stop_index + 1] if stop_index + 1 < len(stops) else None
        if phase == Phase.COMPLETE:
            return last_result
        if stop_requested_fn is not None and stop_requested_fn() and phase in {Phase.BUY, Phase.UNDOCK, Phase.DEPART_SYSTEM}:
            runtime.progress_fn(f"Stop requested at {stop.label}; halting before departure.")
            return last_result
        if phase == Phase.SELL:
            last_result = _run_sell(ctx, stop)
            if last_result.dispatch.status != "ok":
                return last_result
            phase = Phase.BUY if stop.outbound else Phase.COMPLETE
            continue
        if phase == Phase.BUY:
            last_result = _run_buy(ctx, stop)
            if last_result.dispatch.status != "ok":
                return last_result
            phase = Phase.UNDOCK if next_stop is not None else Phase.COMPLETE
            continue
        if phase == Phase.UNDOCK:
            if next_stop is None:
                return last_result
            last_result = _undock_and_route(ctx, stop, next_stop)
            if last_result.dispatch.status != "ok":
                return last_result
            phase = Phase.TRANSIT
            continue
        if phase == Phase.DEPART_SYSTEM:
            if next_stop is None:
                return last_result
            last_result = _depart_system(ctx, stop, next_stop)
            if last_result.dispatch.status != "ok":
                return last_result
            phase = Phase.TRANSIT
            continue
        if phase == Phase.TRANSIT:
            if next_stop is None:
                return last_result
            last_result = _run_transit(ctx, next_stop)
            if is_manual_landing_result(last_result):
                return last_result
            if last_result.dispatch.status != "ok":
                return last_result
            stop_index += 1
            phase = Phase.SELL
            continue
    return last_result
