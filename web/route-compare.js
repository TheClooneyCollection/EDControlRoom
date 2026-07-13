(function () {
  "use strict";
  const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
  const AUTH_PARAM = WEB_CONFIG.authQueryParameterName || "access_token";
  const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";
  const state = { lastRouteId: null, userEditedFrom: false, userEditedRange: false, userEditedSupercharge: false };

  function applyShipStatePrefill(shipState) {
    if (!shipState) return;
    const fromField = document.getElementById("rc-from");
    if (fromField && !state.userEditedFrom && shipState.system) {
      fromField.value = shipState.system;
    }
    const rangeField = document.getElementById("rc-range");
    if (rangeField && !state.userEditedRange && shipState.max_jump_range_ly) {
      rangeField.value = String(shipState.max_jump_range_ly);
    }
    const scField = document.getElementById("rc-supercharge");
    if (scField && !state.userEditedSupercharge && (shipState.supercharge_multiplier === 4 || shipState.supercharge_multiplier === 6)) {
      scField.value = String(shipState.supercharge_multiplier);
    }
    const hint = document.getElementById("rc-supercharge-hint");
    if (hint) {
      if (shipState.supercharge_multiplier === 6) {
        hint.textContent = "(detected: Overcharge Mk II 6x)";
      } else if (shipState.supercharge_multiplier === 4) {
        hint.textContent = "(detected: Normal 4x)";
      } else {
        hint.textContent = "(no Loadout event seen yet)";
      }
    }
  }

  function currentToken() {
    const input = document.getElementById("access-token");
    if (input && input.value) return input.value.trim();
    try {
      const cached = window.localStorage.getItem(TOKEN_STORAGE_KEY);
      if (cached) return cached;
    } catch (e) { /* ignore */ }
    return WEB_CONFIG.defaultAccessToken || "";
  }

  function withAuth(url) {
    const token = currentToken();
    if (!token) return url;
    const separator = url.includes("?") ? "&" : "?";
    return url + separator + encodeURIComponent(AUTH_PARAM) + "=" + encodeURIComponent(token);
  }

  function setStatus(text, isError) {
    const el = document.getElementById("rc-status");
    if (!el) return;
    el.textContent = text || "";
    el.classList.toggle("error", !!isError);
  }

  function fmt(n, digits) {
    if (typeof n !== "number" || !isFinite(n)) return "-";
    return n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  function renderRows(tbody, waypoints, kind) {
    tbody.innerHTML = "";
    let running = 0;
    waypoints.forEach(function (w, i) {
      running += (w.ly_from_prev || 0);
      const tr = document.createElement("tr");
      const cells = [
        String(i),
        w.system,
        kind === "in-game" ? (w.star_class || "-") : (w.neutron_boost ? "Yes" : ""),
        fmt(w.ly_from_prev, 2),
        fmt(running, 2),
      ];
      cells.forEach(function (text, idx) {
        const td = document.createElement("td");
        td.textContent = text;
        if (idx === 3 || idx === 4) td.className = "num";
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  function renderComparison(payload) {
    const ig = payload.in_game;
    const sp = payload.spansh;
    document.getElementById("rc-in-game-head").textContent =
      "In-game route  ·  " + ig.total_jumps + " jumps  ·  " + fmt(ig.total_ly, 1) + " LY  ·  neutrons: " + ig.neutron_count;
    const galmapVisits = sp.metadata && typeof sp.metadata.galaxy_map_visits === "number"
      ? sp.metadata.galaxy_map_visits
      : "-";
    document.getElementById("rc-spansh-head").textContent =
      "Spansh route  ·  " + sp.total_jumps + " jumps  ·  " + fmt(sp.total_ly, 1) + " LY  ·  neutrons: " + sp.neutron_count + "  ·  galmap visits: " + galmapVisits;

    renderRows(document.getElementById("rc-in-game-rows"), ig.waypoints, "in-game");
    renderRows(document.getElementById("rc-spansh-rows"), sp.waypoints, "spansh");

    const summary = document.getElementById("rc-summary");
    const delta = payload.jumps_delta;
    const neutronDelta = payload.neutron_delta;
    let deltaLabel;
    if (delta < 0) deltaLabel = "Spansh saves " + Math.abs(delta) + " jumps";
    else if (delta > 0) deltaLabel = "Spansh adds " + delta + " jumps";
    else deltaLabel = "Same jump count";
    let neutronLabel;
    if (neutronDelta > 0) neutronLabel = "+" + neutronDelta + " neutron boosts";
    else if (neutronDelta < 0) neutronLabel = neutronDelta + " neutron boosts";
    else neutronLabel = "same neutron count";
    summary.textContent = deltaLabel + " · " + neutronLabel;
    summary.className = "rc-summary verdict-" + payload.verdict;

    const verdictEl = document.getElementById("route-compare-verdict");
    if (verdictEl) {
      const verdictText = payload.verdict === "spansh_better"
        ? "Spansh better"
        : payload.verdict === "in_game_better"
          ? "In-game better"
          : "Even";
      verdictEl.textContent = verdictText;
    }

    document.getElementById("rc-results").classList.remove("hidden");
    const details = document.getElementById("rc-details");
    if (details && details.open) details.open = false;

    state.lastRouteId = payload.route_id || null;
    const switchBtn = document.getElementById("rc-switch");
    if (switchBtn) {
      switchBtn.disabled = !state.lastRouteId;
      switchBtn.title = state.lastRouteId ? "Fly the Spansh route waypoint by waypoint" : "Run Compare first";
    }
  }

  async function fetchComparison(url) {
    setStatus("Fetching...", false);
    try {
      const response = await fetch(withAuth(url), { method: "GET" });
      const text = await response.text();
      let payload = null;
      try { payload = JSON.parse(text); } catch (e) { /* ignore */ }
      if (!response.ok) {
        const message = (payload && payload.detail) || text || ("HTTP " + response.status);
        setStatus("Error: " + message, true);
        return;
      }
      setStatus("", false);
      renderComparison(payload);
    } catch (err) {
      setStatus("Error: " + err, true);
    }
  }

  function buildLiveUrl() {
    const from = encodeURIComponent(document.getElementById("rc-from").value.trim());
    const to = encodeURIComponent(document.getElementById("rc-to").value.trim());
    const range = encodeURIComponent(document.getElementById("rc-range").value.trim());
    const eff = encodeURIComponent(document.getElementById("rc-efficiency").value.trim() || "60");
    const sc = encodeURIComponent(document.getElementById("rc-supercharge").value || "4");
    if (!from || !to || !range) {
      setStatus("From, To, and Range are required.", true);
      return null;
    }
    return "/api/route-compare?from=" + from + "&to=" + to + "&range=" + range + "&efficiency=" + eff + "&supercharge_multiplier=" + sc;
  }

  function dispatchSpanshRoute() {
    if (!state.lastRouteId) {
      setStatus("Run Compare first to cache a route.", true);
      return;
    }
    const sendCommand = window.EDCR_HAUL && window.EDCR_HAUL.sendCommand;
    if (typeof sendCommand !== "function") {
      setStatus("Websocket bridge is not ready yet; wait for /haul to connect.", true);
      return;
    }
    const stationField = document.getElementById("rc-station");
    const station = stationField ? stationField.value.trim() : "";
    setStatus("Dispatching Spansh route...", false);
    sendCommand("command.dispatch_spansh_route", {
      route_id: state.lastRouteId,
      station,
    }).then(function (payload) {
      const result = (payload && payload.result) || {};
      const dest = result.destination_system || "destination";
      const suffix = station ? " then dock at " + station : "";
      setStatus("Spansh route accepted: heading to " + dest + suffix + ".", false);
    }).catch(function (err) {
      setStatus("Dispatch failed: " + (err && err.message ? err.message : err), true);
    });
  }

  function init() {
    document.getElementById("rc-compare").addEventListener("click", function () {
      const url = buildLiveUrl();
      if (url) fetchComparison(url);
    });
    document.getElementById("rc-fixture-normal").addEventListener("click", function () {
      fetchComparison("/api/route-compare?fixture=hd232819_xinca_normal");
    });
    document.getElementById("rc-fixture-overcharge").addEventListener("click", function () {
      fetchComparison("/api/route-compare?fixture=hd232819_xinca_overcharge");
    });
    const switchBtn = document.getElementById("rc-switch");
    if (switchBtn) switchBtn.addEventListener("click", dispatchSpanshRoute);

    const fromField = document.getElementById("rc-from");
    if (fromField) fromField.addEventListener("input", function () { state.userEditedFrom = true; });
    const rangeField = document.getElementById("rc-range");
    if (rangeField) rangeField.addEventListener("input", function () { state.userEditedRange = true; });
    const scField = document.getElementById("rc-supercharge");
    if (scField) scField.addEventListener("change", function () { state.userEditedSupercharge = true; });

    if (window.EDCR_HAUL && window.EDCR_HAUL.shipState) {
      applyShipStatePrefill(window.EDCR_HAUL.shipState);
    }
    window.addEventListener("edcr:ship-state", function (event) {
      applyShipStatePrefill(event.detail);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
