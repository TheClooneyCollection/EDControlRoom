from __future__ import annotations

import unittest
from pathlib import Path

from edap.control_room.routines_haul import _project_two_way_phase
from edap.routines.haul_two_way import Phase


def _haul_web_source() -> str:
    web_dir = Path(__file__).resolve().parents[1] / "web"
    return "\n".join(
        (web_dir / name).read_text(encoding="utf-8")
        for name in ("haul-v1.html", "haul-ui.css", "haul-ui.js")
    )


def _multi_haul_web_source() -> str:
    web_dir = Path(__file__).resolve().parents[1] / "web"
    return "\n".join(
        (web_dir / name).read_text(encoding="utf-8")
        for name in ("multi-haul.html", "haul-ui.css", "multi-haul.js")
    )


class ControlRoomHaulWebTests(unittest.TestCase):
    def test_two_way_phase_projection_compacts_phase_and_station_for_web(self) -> None:
        self.assertEqual(_project_two_way_phase(Phase.AT_STATION_1_SELL), ("sell", 1))
        self.assertEqual(_project_two_way_phase(Phase.AT_STATION_1_BUY), ("buy", 1))
        self.assertEqual(_project_two_way_phase(Phase.UNDOCK_STATION_2), ("undock", 2))
        self.assertEqual(_project_two_way_phase(Phase.DEPART_STATION_2_SYSTEM), ("depart", 2))
        self.assertEqual(_project_two_way_phase(Phase.TRANSIT_TO_STATION_1), ("transit", 1))

    def test_haul_web_exposes_explicit_stop_controls(self) -> None:
        html = _haul_web_source()

        self.assertIn('id="stop-after-run"', html)
        self.assertIn('id="stop-now"', html)
        self.assertIn('sendCommand("command.cancel_active_routine", { mode })', html)

    def test_haul_web_exposes_travel_dispatch(self) -> None:
        html = _haul_web_source()

        self.assertIn('id="start-travel"', html)
        self.assertIn('<button class="btn" type="button" id="clear-travel-target">Clear</button>', html)
        self.assertIn('sendCommand("command.dispatch_travel"', html)
        self.assertIn("updateTravelTarget(route)", html)
        self.assertIn('if (travelTargetDirty && !options.force)', html)
        self.assertIn('raw_command: station ? `web travel ${system} / ${station}` : `web travel ${system}`', html)
        self.assertIn('appendActivity("Enter a target system before starting travel."', html)

    def test_haul_web_exposes_instant_mode_toggle(self) -> None:
        html = _haul_web_source()

        self.assertIn('id="instant-toggle"', html)
        self.assertIn("currentRoutine.instant_mode", html)
        self.assertIn('sendCommand("command.submit_input"', html)
        self.assertIn("raw_input: `instant ${nextMode}`", html)
        self.assertIn('id="clear-haul-stats"', html)
        self.assertIn('id="stop-haul-stats"', html)
        self.assertIn('submitHaulStatsCommand("new_session", "Clear haul stats requested.")', html)
        self.assertIn('submitHaulStatsCommand("stop", "Stop haul stats requested.")', html)
        self.assertIn('sendCommand("command.submit_input",', html)
        self.assertIn("raw_input: rawInput", html)
        self.assertIn('rawInput === "stop" && currentRoutine.routine_active', html)

    def test_haul_web_exposes_pause_resume_controls(self) -> None:
        html = _haul_web_source()

        self.assertIn('id="pause-haul"', html)
        self.assertIn('id="resume-haul"', html)
        self.assertIn('requestHaulPauseCommand("pause", "Haul pause requested.")', html)
        self.assertIn('requestHaulPauseCommand("resume", "Haul resume requested.")', html)
        self.assertIn("currentRoutine.haul_pause_requested", html)
        self.assertIn("routine.haul_paused", html)
        self.assertIn('raw_input: rawInput', html)

    def test_haul_web_active_routine_shows_current_and_accumulated_credits(self) -> None:
        html = _haul_web_source()

        self.assertIn("Current / Accumulated", html)
        self.assertIn(
            "`${formatCredits(haulSession.current_run_profit || 0)} / ${formatCredits(haulSession.accumulated_profit || 0)}`",
            html,
        )

    def test_haul_web_summary_profit_includes_current_run(self) -> None:
        html = _haul_web_source()

        self.assertIn("Session profit", html)
        self.assertIn("function sessionProfit(haulSession)", html)
        self.assertIn(
            "Number(haulSession.accumulated_profit || 0) + Number(haulSession.current_run_profit || 0)",
            html,
        )
        self.assertIn('formatCredits(sessionProfit(haulSession))', html)

    def test_haul_web_route_distance_matches_inara_defaults_and_allows_custom_input(self) -> None:
        html = _haul_web_source()

        self.assertIn('id="route-distance" value="500 Ly" inputmode="numeric"', html)
        self.assertIn('id="route-distance-preset" aria-label="Route distance presets"', html)
        self.assertIn('max_route_distance_ly: document.getElementById("route-distance").value', html)
        self.assertIn('setElementValue("route-distance", routeDistanceLabel(WEB_DEFAULTS.maxRouteDistanceLy))', html)
        self.assertIn('setSelectValue("route-distance-preset", "")', html)
        self.assertIn('document.getElementById("route-distance-preset").addEventListener("change"', html)
        self.assertIn('document.getElementById("route-distance").value = value;', html)
        self.assertIn('return raw.toLowerCase().includes("ly") ? raw : `${raw} Ly`;', html)
        for option in (
            "10 Ly",
            "20 Ly",
            "30 Ly",
            "40 Ly",
            "50 Ly",
            "60 Ly",
            "70 Ly",
            "80 Ly",
            "500 Ly",
            "1,000 Ly",
        ):
            self.assertIn(f'<option value="{option}">{option}</option>', html)

    def test_haul_web_active_routine_shows_secondary_route_context(self) -> None:
        html = _multi_haul_web_source()

        self.assertIn('id="routine-buying"', html)
        self.assertIn('id="routine-selling"', html)
        self.assertIn('id="routine-transit"', html)
        self.assertIn('id="routine-next-sale"', html)
        self.assertIn("function updateRoutineContext()", html)

    def test_haul_web_active_routine_treats_sell_as_final_step(self) -> None:
        html = _haul_web_source()

        expected_steps = [
            'data-phase="buy"><div class="step-label">1. Buy',
            'data-phase="undock"><div class="step-label">2. Undock',
            'data-phase="depart"><div class="step-label">3. Depart',
            'data-phase="transit"><div class="step-label">4. Transit',
            'data-phase="sell"><div class="step-label">5. Sell',
        ]
        step_positions = [html.index(step) for step in expected_steps]
        self.assertEqual(step_positions, sorted(step_positions))
        self.assertIn('const phaseOrder = ["buy", "undock", "depart", "transit", "sell"];', html)

    def test_haul_web_exposes_connection_error_recovery_ui(self) -> None:
        html = _haul_web_source()

        self.assertIn('id="connection-banner"', html)
        self.assertIn('id="reconnect-websocket"', html)
        self.assertIn('id="connection-reconnect"', html)
        self.assertIn("const RECONNECT_INITIAL_DELAY_MS = 1000", html)
        self.assertIn("const RECONNECT_MAX_DELAY_MS = 30000", html)
        self.assertIn("function scheduleReconnect(reason)", html)
        self.assertIn("Math.min(reconnectDelayMs * 2, RECONNECT_MAX_DELAY_MS)", html)
        self.assertIn("event.code === 4401", html)
        self.assertNotIn("|| !receivedConnectionReady", html)

    def test_haul_web_renders_home_and_current_system_from_distinct_hydrate_fields(self) -> None:
        html = _haul_web_source()

        self.assertIn('id="summary-home">-</div>', html)
        self.assertIn('id="summary-current">-</div>', html)
        self.assertIn('document.getElementById("summary-current").textContent = ship.system || "-";', html)
        self.assertIn('document.getElementById("summary-home").textContent = payload.home_system || "-";', html)
        self.assertNotIn("market.station || ship.station || ship.system", html)

    def test_haul_web_activity_log_scrolls_full_hydrated_history(self) -> None:
        html = _haul_web_source()

        self.assertIn(".activity-list", html)
        self.assertIn("overflow-y: auto", html)
        self.assertIn('id="activity-list" role="log" aria-live="polite" tabindex="0"', html)
        self.assertIn("Array.from(activityEntries.values()).reverse()", html)
        self.assertIn('`${entries.length} entries`', html)
        self.assertNotIn("slice(-8)", html)

    def test_haul_web_treats_connected_clients_as_operators(self) -> None:
        html = _haul_web_source()

        self.assertIn('clientRole = "active_operator";', html)
        self.assertIn("Operator connection required", html)
        self.assertNotIn("Only the active operator", html)
        self.assertNotIn("Active operator required", html)

    def test_haul_web_persists_and_hydrates_selected_trade_route(self) -> None:
        html = _haul_web_source()

        self.assertIn('sendCommand("command.select_trade_route", { route: payload })', html)
        self.assertIn("mergeHydratedRoute(payload.selected_trade_route || payload.running_trade_route)", html)
        self.assertIn("trade_route: tradeRoutePayload(route)", html)
        self.assertIn("route_profit_per_trip: route.profitTrip !== \"-\" ? route.profitTrip : \"\"", html)
        self.assertIn("apiRoute: { ...route, index }", html)

    def test_haul_web_route_table_shows_trip_profit(self) -> None:
        html = _haul_web_source()

        self.assertIn("<th>Profit / trip</th>", html)
        self.assertIn('<td class="num profit">${escapeHtml(route.profitTrip || "-")}</td>', html)
        self.assertIn('colspan="8"', html)

    def test_haul_web_uses_spansh_style_parameters_and_result_cards(self) -> None:
        html = _multi_haul_web_source()

        self.assertIn("Starting system / station", html)
        self.assertIn('id="multi-starting-capital"', html)
        self.assertIn('id="multi-hop-distance"', html)
        self.assertIn('id="multi-max-hops"', html)
        self.assertIn('id="multi-station-distance-range"', html)
        self.assertIn("Maximum market age", html)
        self.assertIn("Requires large pad", html)
        self.assertIn('id="multi-route-results"', html)
        self.assertIn("function multiLegResultCard(route)", html)
        self.assertIn("Cumulative Profit", html)

    def test_haul_web_defaults_spansh_parameters_from_current_ship(self) -> None:
        html = _multi_haul_web_source()

        self.assertIn("function applyShipDefaults(ship)", html)
        self.assertIn('setInputValue("multi-starting-capital", ship.credits)', html)
        self.assertIn('setInputValue("multi-capacity", ship.cargo_capacity)', html)
        self.assertIn('ship.laden_jump_range_ly || ship.max_jump_range_ly || ship.jump_range_ly', html)
        self.assertIn("function requiresLargePadForShip(ship)", html)
        self.assertIn('document.getElementById("multi-requires-large-pad").checked = requiresLargePad', html)
        self.assertIn('starting_capital: document.getElementById("multi-starting-capital").value', html)
        self.assertIn('max_hop_distance_ly: document.getElementById("multi-hop-distance").value', html)
        self.assertIn('requires_large_pad: document.getElementById("multi-requires-large-pad").checked', html)

    def test_haul_web_exposes_multi_leg_page_with_dedicated_command(self) -> None:
        html = _multi_haul_web_source()

        self.assertIn("Multi-leg haul control", html)
        self.assertIn('id="multi-search-form"', html)
        self.assertIn('id="multi-route-results"', html)
        self.assertIn('id="start-multi-haul"', html)
        self.assertIn('sendCommand("command.dispatch_multi_leg_haul"', html)
        self.assertIn("function multiLegResultCard(route)", html)
        self.assertIn("multi-cargo ready", html)

    def test_two_way_haul_web_keeps_original_route_table_surface(self) -> None:
        html = _haul_web_source()

        self.assertIn('id="search-form"', html)
        self.assertIn('class="route-table"', html)
        self.assertIn('id="route-rows"', html)
        self.assertIn("Route results", html)
        self.assertNotIn('id="multi-search-form"', html)
        self.assertNotIn("Starting capital", html)

    def test_web_pages_do_not_embed_runtime_specific_demo_defaults(self) -> None:
        html = _haul_web_source() + _multi_haul_web_source()

        self.assertIn("window.EDCR_WEB_CONFIG = {}", html)
        self.assertNotIn("window.EDCR_SERVER_DEFAULT_ACCESS_TOKEN", html)
        self.assertNotIn("MacBook Pro", html)
        self.assertNotIn("edserver.exe", html)
        self.assertNotIn("420 / 784 t", html)
        self.assertNotIn("129.4m CR", html)
        self.assertNotIn("2000000000", html)
        self.assertNotIn("value=\"784\"", html)

    def test_haul_web_includes_mobile_layout_breakpoints(self) -> None:
        html = _haul_web_source()

        self.assertNotIn("min-width: 1160px", html)
        self.assertIn("@media (max-width: 760px)", html)
        self.assertIn(".shell {\n        display: block;", html)
        self.assertIn(".route-table td:nth-child(2)::before { content: \"Profit / hr\"; }", html)
        self.assertIn("empty-route-message", html)
        self.assertIn("@media (max-width: 480px)", html)
