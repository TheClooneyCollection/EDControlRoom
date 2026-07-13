(function () {
  "use strict";
  const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
  const AUTH_PARAM = WEB_CONFIG.authQueryParameterName || "access_token";
  const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";
  const state = {
    lastRouteId: null,
    userEditedFrom: false,
    userEditedRange: false,
    userEditedSupercharge: false,
    navrouteWaitDefault: 6.0,
    compareRetryDefault: 3,
  };

  function navrouteWaitSeconds() {
    const raw = document.getElementById("rc-navroute-wait");
    const text = raw && raw.value ? raw.value.trim() : "";
    if (!text) return state.navrouteWaitDefault;
    const parsed = parseFloat(text);
    return isFinite(parsed) && parsed >= 0 ? parsed : state.navrouteWaitDefault;
  }

  function compareRetryAttempts() {
    const raw = document.getElementById("rc-compare-retries");
    const text = raw && raw.value ? raw.value.trim() : "";
    if (!text) return state.compareRetryDefault;
    const parsed = parseInt(text, 10);
    return isFinite(parsed) && parsed >= 1 ? parsed : state.compareRetryDefault;
  }

  async function loadRouteCompareConfig() {
    try {
      const response = await fetch(withAuth("/api/route-compare/config"), { method: "GET" });
      if (!response.ok) return;
      const payload = await response.json();
      if (typeof payload.navroute_wait_seconds === "number") {
        state.navrouteWaitDefault = payload.navroute_wait_seconds;
        const waitField = document.getElementById("rc-navroute-wait");
        if (waitField && !waitField.value) waitField.value = String(payload.navroute_wait_seconds);
      }
      if (typeof payload.compare_retry_attempts === "number") {
        state.compareRetryDefault = payload.compare_retry_attempts;
        const retryField = document.getElementById("rc-compare-retries");
        if (retryField && !retryField.value) retryField.value = String(payload.compare_retry_attempts);
      }
    } catch (err) { /* ignore; keep defaults */ }
  }

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

  function updateSwitchButton() {
    const switchBtn = document.getElementById("rc-switch");
    if (!switchBtn) return;
    switchBtn.disabled = !state.lastRouteId;
    switchBtn.title = state.lastRouteId ? "Fly the Spansh route waypoint by waypoint" : "Run Compare or Fetch Spansh first";
    switchBtn.classList.toggle("ghost", !state.lastRouteId);
    switchBtn.classList.toggle("primary", !!state.lastRouteId);
  }

  function renderSpanshOnly(payload) {
    const sp = payload.spansh;
    const galmapVisits = sp.metadata && typeof sp.metadata.galaxy_map_visits === "number"
      ? sp.metadata.galaxy_map_visits
      : "-";
    document.getElementById("rc-in-game-head").textContent = "In-game route  ·  (not fetched)";
    document.getElementById("rc-in-game-rows").innerHTML = "";
    document.getElementById("rc-spansh-head").textContent =
      "Spansh route  ·  " + sp.total_jumps + " jumps  ·  " + fmt(sp.total_ly, 1) + " LY  ·  neutrons: " + sp.neutron_count + "  ·  galmap visits: " + galmapVisits;
    renderRows(document.getElementById("rc-spansh-rows"), sp.waypoints, "spansh");

    const summary = document.getElementById("rc-summary");
    summary.textContent = "Spansh route ready · " + sp.total_jumps + " jumps · " + fmt(sp.total_ly, 1) + " LY";
    summary.className = "rc-summary";

    const verdictEl = document.getElementById("route-compare-verdict");
    if (verdictEl) verdictEl.textContent = "Spansh only";

    document.getElementById("rc-results").classList.remove("hidden");
    const details = document.getElementById("rc-details");
    if (details && details.open) details.open = false;

    state.lastRouteId = payload.route_id || null;
    updateSwitchButton();
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
    updateSwitchButton();
  }

  async function attemptComparison(url) {
    const response = await fetch(withAuth(url), { method: "GET" });
    const text = await response.text();
    let payload = null;
    try { payload = JSON.parse(text); } catch (e) { /* ignore */ }
    return { response, payload, text };
  }

  async function fetchComparison(url) {
    setStatus("Fetching...", false);
    try {
      const { response, payload, text } = await attemptComparison(url);
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

  function buildQuery() {
    const from = document.getElementById("rc-from").value.trim();
    const to = document.getElementById("rc-to").value.trim();
    const range = document.getElementById("rc-range").value.trim();
    const eff = document.getElementById("rc-efficiency").value.trim() || "60";
    const sc = document.getElementById("rc-supercharge").value || "4";
    if (!from || !to || !range) {
      setStatus("From, To, and Range are required.", true);
      return null;
    }
    return "from=" + encodeURIComponent(from)
      + "&to=" + encodeURIComponent(to)
      + "&range=" + encodeURIComponent(range)
      + "&efficiency=" + encodeURIComponent(eff)
      + "&supercharge_multiplier=" + encodeURIComponent(sc);
  }

  function buildLiveUrl() {
    const q = buildQuery();
    return q ? "/api/route-compare?" + q : null;
  }

  function buildSpanshUrl() {
    const q = buildQuery();
    return q ? "/api/spansh-route?" + q : null;
  }

  async function fetchSpanshOnly() {
    const url = buildSpanshUrl();
    if (!url) return null;
    setStatus("Fetching Spansh route...", false);
    try {
      const response = await fetch(withAuth(url), { method: "GET" });
      const text = await response.text();
      let payload = null;
      try { payload = JSON.parse(text); } catch (e) { /* ignore */ }
      if (!response.ok) {
        const message = (payload && payload.detail) || text || ("HTTP " + response.status);
        setStatus("Error: " + message, true);
        return null;
      }
      setStatus("", false);
      renderSpanshOnly(payload);
      return payload;
    } catch (err) {
      setStatus("Error: " + err, true);
      return null;
    }
  }

  function dispatchDestination() {
    const to = document.getElementById("rc-to").value.trim();
    if (!to) {
      setStatus("Enter a To system before setting the in-game route.", true);
      return Promise.reject(new Error("missing destination"));
    }
    const sendCommand = window.EDCR_HAUL && window.EDCR_HAUL.sendCommand;
    if (typeof sendCommand !== "function") {
      setStatus("Websocket bridge is not ready yet; wait for /haul to connect.", true);
      return Promise.reject(new Error("no ws bridge"));
    }
    setStatus("Setting in-game destination to " + to + "...", false);
    const galaxyMapSettle = (window.EDCR_HAUL && typeof window.EDCR_HAUL.galmapSettleTime === "function")
      ? window.EDCR_HAUL.galmapSettleTime()
      : 0.5;
    return sendCommand("command.dispatch_destination", {
      destination: to,
      galaxy_map_settle: galaxyMapSettle,
      skip_delay: false,
      raw_command: "web route-compare set destination " + to,
    }).then(function (payload) {
      setStatus("In-game destination set for " + to + ".", false);
      return payload;
    }).catch(function (err) {
      setStatus("Set destination failed: " + (err && err.message ? err.message : err), true);
      throw err;
    });
  }

  async function allInOne() {
    const from = document.getElementById("rc-from").value.trim();
    const to = document.getElementById("rc-to").value.trim();
    const range = document.getElementById("rc-range").value.trim();
    if (!from || !to || !range) {
      setStatus("From, To, and Range are required.", true);
      return;
    }
    const eff = document.getElementById("rc-efficiency").value.trim() || "60";
    const sc = document.getElementById("rc-supercharge").value || "4";
    const stationField = document.getElementById("rc-station");
    const station = stationField ? stationField.value.trim() : "";
    const sendCommand = window.EDCR_HAUL && window.EDCR_HAUL.sendCommand;
    if (typeof sendCommand !== "function") {
      setStatus("Websocket bridge is not ready yet; wait for /haul to connect.", true);
      return;
    }
    const galaxyMapSettle = (window.EDCR_HAUL && typeof window.EDCR_HAUL.galmapSettleTime === "function")
      ? window.EDCR_HAUL.galmapSettleTime()
      : 0.5;
    const waitSeconds = navrouteWaitSeconds();
    const maxAttempts = compareRetryAttempts();
    setStatus("All-in-one dispatched. Server is coordinating set-destination + fetch-spansh + compare...", false);
    try {
      const response = await sendCommand("command.dispatch_route_all_in_one", {
        from,
        to,
        range: parseFloat(range),
        efficiency: parseInt(eff, 10),
        supercharge_multiplier: parseInt(sc, 10),
        galaxy_map_settle: galaxyMapSettle,
        navroute_wait_seconds: waitSeconds,
        compare_retry_attempts: maxAttempts,
        station,
        raw_command: "web route-compare all-in-one " + from + " -> " + to,
      });
      const result = (response && response.result) || {};
      if (result.comparison) {
        setStatus("", false);
        renderComparison(result.comparison);
      } else {
        setStatus("All-in-one complete but no comparison payload returned.", true);
      }
    } catch (err) {
      const message = err && err.message ? err.message : String(err);
      setStatus("All-in-one failed: " + message, true);
    }
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
    const setDestBtn = document.getElementById("rc-set-destination");
    if (setDestBtn) setDestBtn.addEventListener("click", function () {
      dispatchDestination().catch(function () { /* status already set */ });
    });
    const fetchSpanshBtn = document.getElementById("rc-fetch-spansh");
    if (fetchSpanshBtn) fetchSpanshBtn.addEventListener("click", function () { fetchSpanshOnly(); });
    const allInOneBtn = document.getElementById("rc-all-in-one");
    if (allInOneBtn) allInOneBtn.addEventListener("click", function () { allInOne(); });
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
    loadRouteCompareConfig();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
