let routes = [];
    let selectedRouteIndex = 0;
    let hasSearchedRoutes = false;
    let routePage = 1;
    let travelTargetDirty = false;
    const ROUTES_PER_PAGE = 12;
    const RECONNECT_INITIAL_DELAY_MS = 1000;
    const RECONNECT_MAX_DELAY_MS = 30000;
    const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";
    const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
    const AUTH_QUERY_PARAMETER_NAME = WEB_CONFIG.authQueryParameterName || "access_token";
    const SERVER_DEFAULT_ACCESS_TOKEN = WEB_CONFIG.defaultAccessToken || "";
    const queryParams = new URLSearchParams(window.location.search);
    const queryAccessToken = queryParams.get(AUTH_QUERY_PARAMETER_NAME) || queryParams.get("access_token") || "";
    let cachedAccessToken = "";
    try { cachedAccessToken = window.localStorage.getItem(TOKEN_STORAGE_KEY) || ""; } catch (_) {}
    let accessToken = queryAccessToken || cachedAccessToken || SERVER_DEFAULT_ACCESS_TOKEN;
    let socket = null;
    let clientRole = "observer";
    let commandSequence = 1;
    let hydratedCurrentSystem = "";
    let lastHydratedRouteKey = "";
    const hydratedFieldValues = new Map();
    let currentRoutine = {};
    let reconnectDelayMs = RECONNECT_INITIAL_DELAY_MS;
    let reconnectTimer = null;
    let reconnectCountdownTimer = null;
    let reconnectDeadlineMs = 0;
    let reconnectAttempts = 0;
    const pendingCommands = new Map();
    const activityEntries = new Map();
    const WEB_DEFAULTS = {
      cargoCapacity: "",
      maxRouteDistanceLy: "500",
      maxStationDistanceLs: "any",
      minSupply: "",
      minDemand: "",
      metric: "Profit / hour",
      surfaceStations: "no",
      galaxyMapSettle: "2.0",
      dockTimeout: "1200",
      ...(WEB_CONFIG.webDefaults || {})
    };

    const HISTORY_WINDOW_KEY = "edcr.haul.historyWindow";
    const HISTORY_WINDOWS = ["today", "48h", "week", "month", "all"];
    let historyWindow = "today";
    try {
      const saved = window.localStorage.getItem(HISTORY_WINDOW_KEY);
      if (HISTORY_WINDOWS.includes(saved)) historyWindow = saved;
    } catch (_) {}
    // Node and ship filters: shown once the history has more than one to pick (hub, or a peer asking it).
    const HISTORY_NODE_KEY = "edcr.haul.historyNode";
    const HISTORY_SHIP_KEY = "edcr.haul.historyShip";
    let historyNode = "all";
    let historyShip = "all";
    try {
      historyNode = window.localStorage.getItem(HISTORY_NODE_KEY) || "all";
      historyShip = window.localStorage.getItem(HISTORY_SHIP_KEY) || "all";
    } catch (_) {}
    let historyCompletedRuns = null;
    let historyRequest = 0;

    function fillHistoryFilter(id, everyLabel, options, selected) {
      const select = document.getElementById(id);
      // A remembered pick with no runs in the history any more stays listed, so it can be cleared.
      if (selected !== "all" && !options.some(([value]) => value === selected)) options = [...options, [selected, selected]];
      select.hidden = options.length < 2 && selected === "all";
      select.innerHTML = [["all", everyLabel], ...options].map(([value, label]) =>
        `<option value="${escapeHtml(value)}"${value === selected ? " selected" : ""}>${escapeHtml(label)}</option>`).join("");
    }

    function renderHistoryFilters(payload) {
      const nodes = (payload.nodes || []).map((node) => [node.id, node.local ? `${node.name} (hub)` : node.name]);
      const ships = (payload.ships || []).map((ship) => [String(ship.id), [ship.name, ship.type].filter(Boolean).join(" · ") || `Ship ${ship.id}`]);
      fillHistoryFilter("history-node", "All nodes", nodes, String(payload.node || "all"));
      fillHistoryFilter("history-ship", "All ships", ships, String(payload.ship || "all"));
    }

    function historyMoney(value) {
      return value == null ? "n/a" : formatCredits(Math.round(Number(value)));
    }

    function historyTable(headers, rows) {
      return `<div class="history-table-scroll"><table class="history-table"><thead><tr>${
        headers.map((name) => `<th scope="col">${name}</th>`).join("")
      }</tr></thead><tbody>${rows.length ? rows.join("") :
        `<tr><td colspan="${headers.length}">No records in this window.</td></tr>`}</tbody></table></div>`;
    }

    function renderHaulHistory(payload) {
      const runs = payload.runs;
      const completed = runs.completed;
      // Total counts aborted runs too: a stop, pause or relaunch splits a run's buy and sell into aborted halves.
      const metrics = [
        ["Total profit", historyMoney(runs.all_in.profit)], ["Total / hour", historyMoney(runs.all_in_profit_per_hour)],
        ["Total time", formatDuration(runs.all_in_duration_s)], ["Runs", `${completed.count} done, ${runs.aborted.count} aborted`]
      ].map(([name, value]) => `<div class="metric"><div class="metric-label">${name}</div><div class="metric-value mono">${value}</div></div>`).join("");
      const expected = completed.expected_count ? `<p>Expected vs actual (${completed.expected_count} completed): ${
        historyMoney(completed.expected_profit)} / ${historyMoney(completed.expected_actual_profit)}; delta ${historyMoney(completed.profit_delta)}</p>` : "";
      const routes = (runs.routes || []).map((route) => `<tr><td>${escapeHtml(route.station_1)} ↔ ${escapeHtml(route.station_2)}</td><td>${route.completed.count} / ${route.aborted.count}</td><td>${historyMoney(route.completed.duration_s > 0 ? route.completed.profit * 3600 / route.completed.duration_s : null)}</td><td>${historyMoney(route.all_in.profit)}</td><td>${historyMoney(route.all_in.cost)}</td><td>${historyMoney(route.all_in.revenue)}</td></tr>`);
      const commodities = (runs.commodities || []).map((item) => `<tr><td>${escapeHtml(item.commodity)}</td><td>${item.all_in.tons_bought} / ${item.all_in.tons_sold} t</td><td>${historyMoney(item.all_in.cost)}</td><td>${historyMoney(item.all_in.revenue)}</td></tr>`);
      const journal = payload.journal;
      const coverage = journal && journal.coverage;
      const journalLine = journal ? `${payload.journal_node ? `${escapeHtml(payload.journal_node)}: ` : ""}Trade profit ${historyMoney(journal.profit)}; balance change ${historyMoney(journal.net_balance_change)}. Coverage: ${coverage.files} files, ${escapeHtml(coverage.first_event_at || "unknown")} to ${escapeHtml(coverage.last_event_at || "unknown")}${coverage.window_start_before_oldest_journal ? "; window predates oldest journal" : ""}; ${coverage.skipped_lines} skipped / ${coverage.unreadable_files} unreadable.` : payload.node !== "all" && payload.journal_node ? `Journal ledger only for ${escapeHtml(payload.journal_node)}, the game this page shows.` : "Journal data unavailable on this server.";
      const content = document.getElementById("history-content");
      // The panel re-renders on refresh; keep Details open if the user opened it.
      const detailsOpen = content.querySelector(".history-details")?.open ? " open" : "";
      content.innerHTML = `
        <div class="history-metrics">${metrics}</div>
        <details class="rc-details history-details"${detailsOpen}><summary class="rc-details-toggle">Details</summary>
        <p>Completed: ${completed.count} runs; profit ${historyMoney(completed.profit)}; ${historyMoney(completed.profit_per_hour)} / hour; mean ${historyMoney(completed.mean_profit)}; best ${historyMoney(completed.best_profit)}</p>
        <p>Aborted: ${runs.aborted.count} runs; realized profit ${historyMoney(runs.aborted.profit)}</p>
        <p>All-in revenue ${historyMoney(runs.all_in.revenue)}; cost ${historyMoney(runs.all_in.cost)}</p>
        ${expected}<h3>Routes</h3>${historyTable(["Route", "Completed / Aborted", "Completed / hour", "Profit", "Cost", "Revenue"], routes)}
        <h3>Commodities</h3>${historyTable(["Commodity", "Bought / Sold", "Cost", "Revenue"], commodities)}
        <p class="history-journal"><strong>All trading (journal):</strong> ${journalLine}</p></details>`;
    }

    async function refreshHaulHistory() {
      const request = ++historyRequest;
      const status = document.getElementById("history-status");
      status.textContent = "Loading";
      document.querySelectorAll("[data-history-window]").forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.historyWindow === historyWindow));
      });
      const url = new URL("/api/haul-stats", window.location.origin);
      url.searchParams.set("window", historyWindow);
      url.searchParams.set("node", historyNode);
      url.searchParams.set("ship", historyShip);
      // `node` filters the history; the journal ledger is the one of the node this page looks at.
      if (window.EDCRNode.id()) url.searchParams.set("view_node", window.EDCRNode.id());
      if (accessToken) url.searchParams.set(AUTH_QUERY_PARAMETER_NAME, accessToken);
      try {
        const response = await fetch(url, { method: "GET" });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
        if (request !== historyRequest) return;
        renderHistoryFilters(payload);
        renderHaulHistory(payload);
        status.textContent = runsHistoryStatus(payload.runs.skipped_lines) + (payload.hub ? ` (from hub ${payload.hub})` : "");
      } catch (error) {
        if (request !== historyRequest) return;
        status.textContent = `History unavailable: ${error.message}`;
        document.getElementById("history-content").textContent = "History could not be loaded. Select a window to retry.";
      }
    }

    function runsHistoryStatus(skipped) {
      return skipped ? `Updated; ${skipped} invalid lines skipped` : "Updated";
    }

    function routeByIndex(index) {
      return routes.find((route) => route.index === index) || routes[0] || null;
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;"
      }[char]));
    }

    function setText(id, value) {
      const element = document.getElementById(id);
      if (element) {
        element.textContent = value;
      }
    }

    function roleLabel(role) {
      return String(role || "observer").replace(/_/g, " ");
    }

    function setElementValue(id, value) {
      const element = document.getElementById(id);
      if (element) {
        element.value = String(value ?? "");
      }
    }

    // Hydrates arrive on every journal change, so only refill a field the operator has not edited or focused.
    function syncHydratedField(id, value) {
      const element = document.getElementById(id);
      const next = String(value ?? "");
      if (!element) {
        return;
      }
      const previous = hydratedFieldValues.get(id);
      hydratedFieldValues.set(id, next);
      if (element === document.activeElement) {
        return;
      }
      if (element.value === "" || element.value === previous) {
        element.value = next;
      }
    }

    function selectHasValue(select, value) {
      return Array.from(select.options).some((option) => option.value === value);
    }

    function setSelectValue(id, value) {
      const select = document.getElementById(id);
      if (!select) {
        return;
      }
      const resolved = String(value ?? "");
      if (resolved && !selectHasValue(select, resolved)) {
        select.add(new Option(resolved, resolved));
      }
      select.value = resolved;
    }

    function routeDistanceLabel(value) {
      const raw = String(value || WEB_DEFAULTS.maxRouteDistanceLy || "").trim();
      if (!raw) {
        return "";
      }
      return raw.toLowerCase().includes("ly") ? raw : `${raw} Ly`;
    }

    function stationDistanceLabel(value) {
      const raw = String(value || WEB_DEFAULTS.maxStationDistanceLs || "").trim();
      if (!raw || raw.toLowerCase() === "any") {
        return "Any";
      }
      const numeric = Number(raw.replace(/,/g, "").split(/\s+/)[0]);
      if (Number.isFinite(numeric)) {
        return `${numeric.toLocaleString()} ls`;
      }
      return raw;
    }

    function serverVersionLabel(version, commit) {
      if (!version) {
        return "-";
      }
      return commit ? `${version} (${commit})` : version;
    }


    function applyWebConfigLabels() {
      setText("session-host", WEB_CONFIG.hostLabel || window.location.host || "-");
      setText("session-target", WEB_CONFIG.inputTargetSummary || "-");
      setText("session-role", roleLabel(WEB_CONFIG.sessionRole));
      setText("status-runtime", WEB_CONFIG.runtimePlatform || "-");
      setText("status-journal", WEB_CONFIG.journalStatus || "-");
      setText("status-input-target", WEB_CONFIG.inputTargetSummary || "-");
      setText("status-version", serverVersionLabel(WEB_CONFIG.serverVersion, WEB_CONFIG.serverCommit));
    }

    function applySearchDefaults() {
      setElementValue("origin", hydratedCurrentSystem);
      setElementValue("destination", "");
      setElementValue("route-distance", routeDistanceLabel(WEB_DEFAULTS.maxRouteDistanceLy));
      setSelectValue("route-distance-preset", "");
      setSelectValue("station-distance", stationDistanceLabel(WEB_DEFAULTS.maxStationDistanceLs));
      setElementValue("capacity", WEB_DEFAULTS.cargoCapacity);
      setElementValue("min-supply", WEB_DEFAULTS.minSupply);
      setElementValue("min-demand", WEB_DEFAULTS.minDemand);
      setSelectValue("metric", WEB_DEFAULTS.metric);
      setSelectValue("surface-stations", WEB_DEFAULTS.surfaceStations);
    }

    function searchScopeLabel() {
      return document.getElementById("surface-stations").value === "no" ? "station/carrier routes" : "routes";
    }

    function applyHaulDefaults() {
      setElementValue("galaxy-settle", WEB_DEFAULTS.galaxyMapSettle);
      setElementValue("dock-timeout", WEB_DEFAULTS.dockTimeout);
    }

    function routeFlag(value) {
      return value === true || ["1", "true", "yes", "y", "on"].includes(String(value ?? "").trim().toLowerCase());
    }

    function routeFromApi(route, fallbackIndex) {
      const stationDistances = [route.from_station_distance, route.to_station_distance].filter(Boolean);
      const index = Number(route.index || fallbackIndex);
      // Routes saved or copied before the rename carry `from_on_land` / `to_on_land`.
      const buyManualLanding = routeFlag(route.from_manual_landing ?? route.from_on_land);
      const sellManualLanding = routeFlag(route.to_manual_landing ?? route.to_on_land);
      return {
        index,
        profitHour: route.profit_per_hour || "-",
        profitTrip: route.profit_per_trip || "-",
        commodity: route.source_buy_commodity || "",
        targetCommodity: route.target_buy_commodity || "",
        buyStation: route.from_station || "",
        buySystem: route.from_system || "",
        buyStationDistance: route.from_station_distance || "-",
        buyManualLanding,
        sellStation: route.to_station || "",
        sellSystem: route.to_system || "",
        sellStationDistance: route.to_station_distance || "-",
        sellManualLanding,
        distanceFromSystem: route.distance_from_system || "-",
        routeDistance: route.route_distance || "-",
        stationDistance: stationDistances.length ? stationDistances.join(" / ") : "-",
        buyStationSupply: route.from_supply || "-",
        buyStationDemand: route.from_demand || "-",
        sellStationSupply: route.to_supply || "-",
        sellStationDemand: route.to_demand || "-",
        apiRoute: { ...route, index, from_manual_landing: buyManualLanding, to_manual_landing: sellManualLanding }
      };
    }

    function tradeRoutePayload(route) {
      if (!route) {
        return null;
      }
      return {
        ...route.apiRoute,
        index: Number(route.index || 0),
        from_station: route.buyStation || "",
        from_system: route.buySystem || "",
        to_station: route.sellStation || "",
        to_system: route.sellSystem || "",
        source_buy_commodity: route.commodity || null,
        target_buy_commodity: route.targetCommodity || null,
        from_station_distance: route.buyStationDistance !== "-" ? route.buyStationDistance : null,
        to_station_distance: route.sellStationDistance !== "-" ? route.sellStationDistance : null,
        distance_from_system: route.distanceFromSystem !== "-" ? route.distanceFromSystem : null,
        route_distance: route.routeDistance !== "-" ? route.routeDistance : null,
        profit_per_trip: route.profitTrip !== "-" ? route.profitTrip : null,
        profit_per_hour: route.profitHour !== "-" ? route.profitHour : null,
        from_supply: route.buyStationSupply !== "-" ? route.buyStationSupply : null,
        from_demand: route.buyStationDemand !== "-" ? route.buyStationDemand : null,
        to_supply: route.sellStationSupply !== "-" ? route.sellStationSupply : null,
        to_demand: route.sellStationDemand !== "-" ? route.sellStationDemand : null,
        from_manual_landing: route.buyManualLanding,
        to_manual_landing: route.sellManualLanding,
        raw_text: route.apiRoute?.raw_text || "",
        url_links: route.apiRoute?.url_links || []
      };
    }

    // Copy only what another Control Room needs to run the route; index, Inara text and market snapshots stay local.
    const ROUTE_TRANSFER_FIELDS = [
      "from_system", "from_station", "source_buy_commodity", "from_station_distance",
      "to_system", "to_station", "target_buy_commodity", "to_station_distance",
      "route_distance", "profit_per_trip", "profit_per_hour", "from_manual_landing", "to_manual_landing"
    ];

    function routeTransferPayload(route) {
      const payload = tradeRoutePayload(route);
      return Object.fromEntries(ROUTE_TRANSFER_FIELDS
        .filter((field) => payload[field] !== null && payload[field] !== "" && payload[field] !== false)
        .map((field) => [field, payload[field]]));
    }

    function routeKey(route) {
      return [
        route.buyStation,
        route.buySystem,
        route.sellStation,
        route.sellSystem,
        route.commodity,
        route.targetCommodity
      ].join("\u001f").toLowerCase();
    }

    function mergeHydratedRoute(apiRoute) {
      if (!apiRoute || typeof apiRoute !== "object") {
        return null;
      }
      const hydratedRoute = routeFromApi(apiRoute, routes.length + 1);
      const hydratedKey = routeKey(hydratedRoute);
      const existingIndex = routes.findIndex((route) => routeKey(route) === hydratedKey);
      if (existingIndex >= 0) {
        hydratedRoute.index = routes[existingIndex].index;
        routes[existingIndex] = hydratedRoute;
      } else {
        routes = [hydratedRoute, ...routes];
      }
      hasSearchedRoutes = true;
      selectedRouteIndex = hydratedRoute.index;
      const routeOffset = routes.findIndex((route) => route.index === selectedRouteIndex);
      routePage = routeOffset >= 0 ? Math.floor(routeOffset / ROUTES_PER_PAGE) + 1 : 1;
      return hydratedRoute;
    }

    function persistSelectedRoute(route) {
      const payload = tradeRoutePayload(route);
      if (!payload || !accessToken || clientRole !== "active_operator" || !isSocketReady()) {
        return;
      }
      sendCommand("command.select_trade_route", { route: payload })
        .catch((error) => {
          appendActivity(error.message, "Haul", "warning");
        });
    }

    async function copySelectedRoute() {
      const route = routeByIndex(selectedRouteIndex);
      if (!route) {
        appendActivity("Select a route before copying it.", "Route", "warning");
        return;
      }
      const textarea = document.getElementById("route-transfer-text");
      textarea.value = JSON.stringify(routeTransferPayload(route), null, 2);
      textarea.focus();
      textarea.select();
      // The Clipboard API only exists on https or localhost; a LAN http page falls back to execCommand.
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(textarea.value);
        } else if (!document.execCommand("copy")) {
          throw new Error("copy rejected");
        }
        appendActivity("Selected route copied to the clipboard.", "Route", "success");
      } catch (error) {
        appendActivity("Route text is selected in the box; press Ctrl+C to copy it.", "Route", "warning");
      }
    }

    function importPastedRoute() {
      const text = document.getElementById("route-transfer-text").value.trim();
      let pasted;
      try {
        pasted = JSON.parse(text);
      } catch (error) {
        appendActivity("Pasted text is not a copied route.", "Route", "warning");
        return;
      }
      const required = ["from_system", "from_station", "to_system", "to_station"];
      if (!pasted || typeof pasted !== "object" || Array.isArray(pasted)
          || required.some((field) => typeof pasted[field] !== "string" || !pasted[field].trim())) {
        appendActivity("Pasted route needs from/to systems and stations.", "Route", "warning");
        return;
      }
      // Keep the index of a matching route; otherwise take a fresh one so it cannot collide with local results.
      const existing = routes.find((route) => routeKey(route) === routeKey(routeFromApi(pasted, 0)));
      const index = existing ? existing.index : routes.reduce((max, route) => Math.max(max, route.index), 0) + 1;
      const route = mergeHydratedRoute({ ...pasted, index });
      renderRows();
      renderSelected();
      persistSelectedRoute(route);
      appendActivity(`Imported route ${route.buySystem} -> ${route.sellSystem}.`, "Route", "success");
    }

    // /markets "Open in haul" links here with the route in a #route= fragment. Importing it after a hydrate
    // keeps the server's saved selection from replacing it, and lets the selection reach the server.
    function importLinkedRoute() {
      const match = window.location.hash.match(/^#route=(.+)$/);
      if (!match) {
        return;
      }
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
      try {
        document.getElementById("route-transfer-text").value = decodeURIComponent(match[1]);
      } catch (error) {
        appendActivity("Linked route is not readable.", "Route", "warning");
        return;
      }
      importPastedRoute();
    }

    function profitHourLabel(route) {
      if (!route.profitHour || route.profitHour === "-") {
        return "-";
      }
      return route.profitHour.includes("/") ? route.profitHour : `${route.profitHour}/h`;
    }

    function setResultCount(text) {
      document.getElementById("result-count").textContent = text;
    }

    // The search's Inara URL, so the operator can check results against Inara's own page.
    function setInaraSearchLink(url) {
      const link = document.getElementById("inara-search-link");
      if (url) {
        link.href = url;
      } else {
        link.removeAttribute("href");
      }
      link.hidden = !url;
    }

    function isSocketReady() {
      return socket && socket.readyState === WebSocket.OPEN;
    }

    function setConnectionBanner(state, title, message) {
      const banner = document.getElementById("connection-banner");
      banner.classList.toggle("hidden", state === "connected");
      banner.classList.toggle("danger", state === "danger");
      banner.classList.toggle("connecting", state === "connecting");
      document.getElementById("connection-title").textContent = title;
      document.getElementById("connection-message").textContent = message;
    }

    function clearReconnectTimer({ resetBackoff = false } = {}) {
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (reconnectCountdownTimer !== null) {
        window.clearInterval(reconnectCountdownTimer);
        reconnectCountdownTimer = null;
      }
      reconnectDeadlineMs = 0;
      if (resetBackoff) {
        reconnectDelayMs = RECONNECT_INITIAL_DELAY_MS;
        reconnectAttempts = 0;
      }
    }

    function resetConnectionRecovery() {
      clearReconnectTimer({ resetBackoff: true });
      setConnectionBanner("connected", "Connected", "Websocket connected.");
    }

    function updateReconnectBanner(reason) {
      const remainingSeconds = Math.max(1, Math.ceil((reconnectDeadlineMs - Date.now()) / 1000));
      setConnectionBanner(
        "danger",
        "Connection issue",
        `${reason} Retrying in ${remainingSeconds}s (attempt ${reconnectAttempts}).`
      );
    }

    function scheduleReconnect(reason) {
      if (!accessToken) {
        setConnectionBanner("danger", "Access token required", "Enter the shared access token to reconnect.");
        return;
      }
      if (reconnectTimer !== null) {
        updateReconnectBanner(reason);
        return;
      }
      const delayMs = reconnectDelayMs;
      reconnectDelayMs = Math.min(reconnectDelayMs * 2, RECONNECT_MAX_DELAY_MS);
      reconnectAttempts += 1;
      reconnectDeadlineMs = Date.now() + delayMs;
      updateReconnectBanner(reason);
      reconnectCountdownTimer = window.setInterval(() => updateReconnectBanner(reason), 1000);
      reconnectTimer = window.setTimeout(() => {
        clearReconnectTimer();
        connectWebsocket({ automatic: true });
      }, delayMs);
    }

    function reconnectNow() {
      if (!accessToken) {
        showAccessTokenPrompt("Enter the shared access token for this server.");
        setConnectionBanner("danger", "Access token required", "Enter the shared access token to reconnect.");
        return;
      }
      appendActivity("Manual websocket reconnect requested.", "Session", "warning");
      clearReconnectTimer({ resetBackoff: true });
      connectWebsocket({ manual: true });
    }

    function updateOperatorState() {
      const active = clientRole === "active_operator";
      const routineActive = Boolean(currentRoutine.routine_active);
      const instantMode = Boolean(currentRoutine.instant_mode);
      const instantToggle = document.getElementById("instant-toggle");
      setText("session-role", roleLabel(clientRole));
      document.getElementById("start-haul").disabled = !active || !routeByIndex(selectedRouteIndex);
      document.getElementById("set-destination").disabled = !active || !routeByIndex(selectedRouteIndex);
      instantToggle.disabled = !active;
      instantToggle.textContent = instantMode ? "Instant on" : "Instant off";
      instantToggle.classList.toggle("on", instantMode);
      instantToggle.setAttribute("aria-pressed", instantMode ? "true" : "false");
      document.getElementById("stop-after-run").disabled = !active || !routineActive;
      document.getElementById("stop-now").disabled = !active || !routineActive;
      document.getElementById("pause-haul").disabled = !active || !routineActive || currentRoutine.active_routine_name !== "haul" || Boolean(currentRoutine.haul_pause_requested);
      document.getElementById("resume-haul").disabled = !active || !routineActive || currentRoutine.active_routine_name !== "haul" || (!currentRoutine.haul_pause_requested && !currentRoutine.haul_paused);
      document.getElementById("clear-haul-stats").disabled = !active;
      document.getElementById("stop-haul-stats").disabled = !active || routineActive;
      document.getElementById("reconnect-websocket").disabled = !accessToken;
      document.getElementById("connection-reconnect").disabled = !accessToken;
      document.querySelector("#search-form .btn.primary").disabled = !active;
      document.getElementById("access-token").value = accessToken;
      if (!accessToken) {
        setResultCount("Backend token required");
      } else if (!isSocketReady()) {
        setResultCount("Connecting to backend...");
      } else if (!active) {
        setResultCount("Operator connection required");
      } else if (routes.length) {
        setResultCount(`Found ${routes.length} ${searchScopeLabel()}`);
      }
    }

    function sendCommand(messageType, payload) {
      if (!isSocketReady()) {
        setConnectionBanner("danger", "Disconnected", "Websocket is not connected. Wait for retry or reconnect now.");
        scheduleReconnect("Websocket is not connected.");
        return Promise.reject(new Error("Websocket is not connected."));
      }
      const messageId = `web-haul-${commandSequence++}`;
      const message = {
        message_type: messageType,
        message_id: messageId,
        payload
      };
      return new Promise((resolve, reject) => {
        const timeout = window.setTimeout(() => {
          pendingCommands.delete(messageId);
          reject(new Error("Timed out waiting for backend response."));
        }, 60000);
        pendingCommands.set(messageId, { resolve, reject, timeout });
        socket.send(JSON.stringify(message));
      });
    }

    window.EDCR_HAUL = window.EDCR_HAUL || {};
    window.EDCR_HAUL.sendCommand = sendCommand;
    window.EDCR_HAUL.galmapSettleTime = galmapSettleTime;

    function websocketUrl() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const params = new URLSearchParams({
        client_name: WEB_CONFIG.clientName || "web-haul"
      });
      params.set(AUTH_QUERY_PARAMETER_NAME, accessToken);
      // On a hub, the node picked in the sidebar (nav.js).
      window.EDCRNode.addTo(params);
      return `${protocol}//${window.location.host}/session?${params.toString()}`;
    }

    function disconnectWebsocket() {
      if (!socket) {
        return;
      }
      const existingSocket = socket;
      socket = null;
      existingSocket.edcrIntentionalClose = true;
      existingSocket.close();
    }

    function connectWebsocket({ automatic = false, manual = false } = {}) {
      refreshHaulHistory();
      if (!accessToken) {
        clearReconnectTimer({ resetBackoff: true });
        setConnectionBanner("danger", "Access token required", "Enter the shared access token to connect.");
        showAccessTokenPrompt("Enter the shared access token for this server.");
        appendActivity("Set an access token to connect backend.", "Session", "warning");
        updateOperatorState();
        return;
      }
      disconnectWebsocket();
      setConnectionBanner(
        "connecting",
        automatic ? "Reconnecting" : "Connecting",
        manual ? "Manual websocket reconnect in progress." : "Opening websocket session."
      );
      updateOperatorState();
      socket = new WebSocket(websocketUrl());
      let receivedConnectionReady = false;
      socket.addEventListener("open", () => {
        appendActivity("Websocket connected.", "Session", "success");
        resetConnectionRecovery();
        updateOperatorState();
      });
      socket.addEventListener("close", (event) => {
        if (event.currentTarget.edcrIntentionalClose) {
          return;
        }
        if (socket === event.currentTarget) {
          socket = null;
        }
        clientRole = "observer";
        if (accessToken && event.code === 4401) {
          clearReconnectTimer({ resetBackoff: true });
          handleAccessTokenRejected();
          updateOperatorState();
          return;
        }
        const reason = receivedConnectionReady ? "Websocket disconnected." : "Unable to open websocket session.";
        appendActivity(reason, "Session", "warning");
        scheduleReconnect(reason);
        updateOperatorState();
      });
      socket.addEventListener("error", () => {
        appendActivity("Websocket error.", "Session", "warning");
        setConnectionBanner("danger", "Websocket error", "The websocket reported an error. Retrying after disconnect.");
        scheduleReconnect("Websocket error.");
      });
      socket.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);
        if (message.message_type === "event.connection_ready") {
          receivedConnectionReady = true;
          clientRole = message.payload.client_role || "observer";
          appendActivity(`Connected as ${clientRole.replace("_", " ")}.`, "Session", "success");
          updateOperatorState();
          return;
        }
        if (message.message_type === "event.active_operator_changed") {
          clientRole = "active_operator";
          updateOperatorState();
          return;
        }
        if (message.message_type === "control_room.hydrate") {
          applyHydratePayload(message.payload || {});
          return;
        }
        if (message.message_type === "event.announcement_emitted") {
          window.dispatchEvent(new CustomEvent("edcr:announcement", { detail: message.payload || {} }));
          return;
        }
        if (message.message_type === "event.activity_log_appended") {
          addActivityEntry(message.payload.entry || {});
          renderActivityLog();
          return;
        }
        const pending = pendingCommands.get(message.correlation_message_id);
        if (!pending) {
          return;
        }
        window.clearTimeout(pending.timeout);
        pendingCommands.delete(message.correlation_message_id);
        if (message.message_type === "response.error") {
          pending.reject(new Error(message.payload.error_message || "Backend command failed."));
        } else {
          pending.resolve(message.payload);
        }
      });
    }

    function saveAccessToken() {
      accessToken = document.getElementById("access-token").value.trim();
      if (accessToken) {
        window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
        appendActivity("Access token saved locally.", "Session", "success");
      } else {
        window.localStorage.removeItem(TOKEN_STORAGE_KEY);
        appendActivity("Access token cleared.", "Session", "warning");
      }
      clientRole = "observer";
      updateOperatorState();
      connectWebsocket();
    }

    function setAccessTokenPromptMessage(message, badgeClass = "neutral") {
      const promptMessage = document.getElementById("token-dialog-message");
      promptMessage.textContent = message;
      promptMessage.classList.toggle("warning", badgeClass === "warning");
    }

    function showAccessTokenPrompt(message = "Enter the shared access token for this server.", badgeClass = "neutral") {
      const dialog = document.getElementById("token-dialog");
      setAccessTokenPromptMessage(message, badgeClass);
      if (dialog.open) {
        return;
      }
      document.getElementById("prompt-access-token").value = accessToken;
      dialog.showModal();
      window.requestAnimationFrame(() => document.getElementById("prompt-access-token").focus());
    }

    function closeAccessTokenPrompt() {
      const dialog = document.getElementById("token-dialog");
      if (dialog.open) {
        dialog.close();
      }
    }

    function handleAccessTokenRejected() {
      clearReconnectTimer({ resetBackoff: true });
      accessToken = "";
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
      document.getElementById("access-token").value = "";
      document.getElementById("prompt-access-token").value = "";
      appendActivity("Access token rejected by backend. Enter the shared token for this server.", "Session", "warning");
      setConnectionBanner("danger", "Access token rejected", "Enter the shared token for this server.");
      showAccessTokenPrompt("Access token rejected. Enter the shared token for this server.", "warning");
    }

    function submitAccessTokenPrompt() {
      accessToken = document.getElementById("prompt-access-token").value.trim();
      document.getElementById("access-token").value = accessToken;
      if (!accessToken) {
        appendActivity("Access token is required to connect backend.", "Session", "warning");
        updateOperatorState();
        return;
      }
      window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
      appendActivity("Access token saved locally.", "Session", "success");
      closeAccessTokenPrompt();
      clientRole = "observer";
      updateOperatorState();
      connectWebsocket();
    }

    function appendActivity(text, label, badgeClass = "neutral") {
      addActivityEntry({
        entry_id: `local-${Date.now()}-${Math.random()}`,
        timestamp: new Date().toISOString(),
        message_text: text,
        severity: badgeClass === "warning" ? "warning" : "info",
        label
      });
      renderActivityLog();
    }

    function addActivityEntry(entry) {
      const id = String(entry.entry_id || `entry-${activityEntries.size + 1}`);
      activityEntries.set(id, {
        entry_id: id,
        timestamp: entry.timestamp || new Date().toISOString(),
        message_text: entry.message_text || "",
        severity: entry.severity || "info",
        label: entry.label || activityLabel(entry.message_text || "")
      });
    }

    function activityLabel(message) {
      const text = String(message).toLowerCase();
      if (text.includes("haul") || text.includes("route")) {
        return "Haul";
      }
      if (text.includes("market") || text.includes("bought") || text.includes("sold")) {
        return "Market";
      }
      if (text.includes("dock") || text.includes("jump") || text.includes("destination")) {
        return "Nav";
      }
      return "Log";
    }

    function activityBadgeClass(entry) {
      if (entry.severity === "warning" || entry.severity === "error") {
        return "warning";
      }
      if (entry.label === "Market") {
        return "success";
      }
      return entry.label === "Haul" ? "warning" : "neutral";
    }

    function activityTime(timestamp) {
      const parsed = Date.parse(timestamp);
      if (Number.isNaN(parsed)) {
        return "--:--:--";
      }
      return new Date(parsed).toLocaleTimeString([], { hour12: false });
    }

    function renderActivityLog() {
      const list = document.getElementById("activity-list");
      const entries = Array.from(activityEntries.values()).reverse();
      document.getElementById("activity-status").textContent = entries.length ? `${entries.length} entries` : "No entries";
      if (!entries.length) {
        list.innerHTML = `<div class="activity-row"><div class="activity-time mono">--:--:--</div><div class="activity-text">Waiting for backend activity.</div><span class="badge neutral">Log</span></div>`;
        return;
      }
      list.innerHTML = entries.map((entry) => `
        <div class="activity-row">
          <div class="activity-time mono">${escapeHtml(activityTime(entry.timestamp))}</div>
          <div class="activity-text">${escapeHtml(stripMarkup(entry.message_text))}</div>
          <span class="badge ${activityBadgeClass(entry)}">${escapeHtml(entry.label)}</span>
        </div>
      `).join("");
    }

    function stripMarkup(value) {
      return String(value || "").replace(/\[\/?[a-zA-Z0-9_#= .-]*\]/g, "");
    }

    function formatDuration(seconds) {
      const safeSeconds = Math.max(0, Number(seconds || 0));
      const hours = Math.floor(safeSeconds / 3600);
      const minutes = Math.floor((safeSeconds % 3600) / 60);
      const secs = Math.floor(safeSeconds % 60);
      return [hours, minutes, secs].map((value) => String(value).padStart(2, "0")).join(":");
    }

    function formatCredits(value) {
      const amount = Number(value || 0);
      const abs = Math.abs(amount);
      if (abs >= 1000000000) {
        return `${(amount / 1000000000).toFixed(2)}b CR`;
      }
      if (abs >= 1000000) {
        return `${(amount / 1000000).toFixed(1)}m CR`;
      }
      if (abs >= 1000) {
        return `${(amount / 1000).toFixed(1)}k CR`;
      }
      return `${amount} CR`;
    }

    function sessionProfit(haulSession) {
      return Number(haulSession.accumulated_profit || 0) + Number(haulSession.current_run_profit || 0);
    }

    function updateRoutinePanel(routine, haulSession, ship) {
      const phase = routine.haul_phase || null;
      const stationIndex = routine.haul_phase_station_index || null;
      const stationLabel = stationIndex ? `Station ${stationIndex}` : "";
      const phaseOrder = ["buy", "undock", "depart", "transit", "sell"];
      const phaseIndex = phase ? phaseOrder.indexOf(phase) : -1;
      let routineStatus = "Running";
      if (routine.haul_paused) {
        routineStatus = "Paused";
      } else if (routine.haul_pause_requested) {
        routineStatus = "Pause requested";
      } else if (routine.haul_stop_requested) {
        routineStatus = "Stop requested";
      }
      document.getElementById("routine-status").textContent =
        routine.routine_active && routine.active_routine_name === "haul"
          ? `${routineStatus}${stationLabel ? ` · ${stationLabel}` : ""}`
          : "Idle";
      document.querySelectorAll("#routine-steps .step").forEach((step, index) => {
        const stepPhase = step.dataset.phase;
        const value = step.querySelector(".step-value");
        step.classList.remove("done", "current");
        if (!routine.routine_active || routine.active_routine_name !== "haul") {
          value.textContent = "Pending";
        } else if (stepPhase === phase) {
          step.classList.add("current");
          value.textContent = phase === "transit" && stationLabel ? `To ${stationLabel}` : stationLabel || "Active";
        } else if (phaseIndex > index) {
          step.classList.add("done");
          value.textContent = "Complete";
        } else {
          value.textContent = "Pending";
        }
      });
      document.getElementById("routine-elapsed").textContent = formatDuration(haulSession.session_elapsed_s || 0);
      const runs = Number(haulSession.completed_runs || 0);
      const runTime = (seconds) => (seconds == null ? "-" : formatDuration(seconds));
      document.getElementById("routine-run-elapsed").textContent = runTime(haulSession.current_run_elapsed_s);
      document.getElementById("routine-last-run").textContent = runTime(haulSession.last_run_elapsed_s);
      document.getElementById("routine-average-run").textContent =
        runs ? formatDuration(Number(haulSession.total_run_elapsed_s || 0) / runs) : "-";
      document.getElementById("routine-current-run").textContent =
        `${formatCredits(haulSession.current_run_profit || 0)} / ${formatCredits(haulSession.accumulated_profit || 0)}`;
      document.getElementById("routine-cargo-moved").textContent =
        `${Number(haulSession.cargo_moved_t || 0).toLocaleString()} t`;
    }

    function updateRoutePager(start, end, total, totalPages) {
      document.getElementById("route-page-status").textContent = `${start}-${end} of ${total}`;
      document.getElementById("prev-routes").disabled = routePage <= 1;
      document.getElementById("next-routes").disabled = routePage >= totalPages || total === 0;
    }

    function renderRows() {
      const tbody = document.getElementById("route-rows");
      if (!routes.length) {
        const message = hasSearchedRoutes
          ? `No ${searchScopeLabel()} found.`
          : `Search routes to load ${searchScopeLabel()}.`;
        tbody.innerHTML = `<tr><td colspan="8" class="route-sub empty-route-message">${message}</td></tr>`;
        routePage = 1;
        updateRoutePager(0, 0, 0, 1);
        return;
      }
      const totalPages = Math.max(1, Math.ceil(routes.length / ROUTES_PER_PAGE));
      routePage = Math.min(Math.max(1, routePage), totalPages);
      const startIndex = (routePage - 1) * ROUTES_PER_PAGE;
      const visibleRoutes = routes.slice(startIndex, startIndex + ROUTES_PER_PAGE);
      tbody.innerHTML = visibleRoutes.map((route) => `
        <tr class="${route.index === selectedRouteIndex ? "selected" : ""}" data-index="${route.index}">
          <td class="mono" data-label="#">${escapeHtml(route.index)}</td>
          <td class="num profit" data-label="Profit / hr">${escapeHtml(profitHourLabel(route))}</td>
          <td class="num profit" data-label="Profit / trip">${escapeHtml(route.profitTrip || "-")}</td>
          <td data-label="Cargo">
            <div class="route-main">${escapeHtml(route.commodity || "No buy commodity")} / ${escapeHtml(route.targetCommodity || "No buy commodity")}</div>
          </td>
          <td data-label="Station 1">
            <div class="route-main">${escapeHtml(route.buyStation)}</div>
            <div class="route-sub mono">${escapeHtml(route.buySystem)} / ${escapeHtml(route.buyStationDistance)}${route.buyManualLanding ? " / manual landing" : ""}</div>
            <div class="route-sub mono">Sup ${escapeHtml(route.buyStationSupply)} / Dem ${escapeHtml(route.buyStationDemand)}</div>
          </td>
          <td data-label="Station 2">
            <div class="route-main">${escapeHtml(route.sellStation)}</div>
            <div class="route-sub mono">${escapeHtml(route.sellSystem)} / ${escapeHtml(route.sellStationDistance)}${route.sellManualLanding ? " / manual landing" : ""}</div>
            <div class="route-sub mono">Sup ${escapeHtml(route.sellStationSupply)} / Dem ${escapeHtml(route.sellStationDemand)}</div>
          </td>
          <td class="num" data-label="Distance">${escapeHtml(route.distanceFromSystem)}</td>
          <td class="num" data-label="Route">${escapeHtml(route.routeDistance)}</td>
        </tr>
      `).join("");
      updateRoutePager(startIndex + 1, startIndex + visibleRoutes.length, routes.length, totalPages);
    }

    function renderSelected() {
      const route = routeByIndex(selectedRouteIndex);
      const startButton = document.getElementById("start-haul");
      const destinationButton = document.getElementById("set-destination");
      if (!route) {
        document.getElementById("selected-title").textContent = "Select a route before starting.";
        document.getElementById("command-preview").textContent = "";
        updateTravelTarget(null, { force: true });
        startButton.disabled = true;
        destinationButton.disabled = true;
        return;
      }
      startButton.disabled = clientRole !== "active_operator";
      destinationButton.disabled = clientRole !== "active_operator";
      document.getElementById("selected-title").textContent =
        `${route.buySystem} (${route.buyStation}) -> ${route.sellSystem} (${route.sellStation})`;
      updateTravelTarget(route);
      updateCommandPreview();
    }

    function updateTravelTarget(route, options = {}) {
      if (travelTargetDirty && !options.force) {
        return;
      }
      document.getElementById("travel-system").value = route ? route.buySystem || "" : "";
      document.getElementById("travel-station").value = route ? route.buyStation || "" : "";
    }

    // The travel target defaults to the route's first station, so it inherits that station's surface flag.
    function travelTargetManualLanding(system, station) {
      const route = routeByIndex(selectedRouteIndex);
      if (!route || !station) {
        return false;
      }
      const matches = (left, right) => String(left || "").toLowerCase() === String(right || "").toLowerCase();
      if (matches(system, route.buySystem) && matches(station, route.buyStation)) {
        return route.buyManualLanding;
      }
      return matches(system, route.sellSystem) && matches(station, route.sellStation) ? route.sellManualLanding : false;
    }

    function selectedHaulParams() {
      const route = routeByIndex(selectedRouteIndex);
      if (!route) {
        return {};
      }
      const settle = document.getElementById("galaxy-settle").value || WEB_DEFAULTS.galaxyMapSettle;
      const timeout = document.getElementById("dock-timeout").value || WEB_DEFAULTS.dockTimeout;
      return {
        station_1_buying: route.commodity || "",
        station_1: route.buyStation || "",
        station_1_system: route.buySystem || "",
        station_1_manual_landing: route.buyManualLanding ? "true" : "false",
        station_2_buying: route.targetCommodity || "",
        station_2: route.sellStation || "",
        station_2_system: route.sellSystem || "",
        station_2_manual_landing: route.sellManualLanding ? "true" : "false",
        route_profit_per_trip: route.profitTrip !== "-" ? route.profitTrip : "",
        galaxy_map_settle: settle,
        dock_timeout: timeout
      };
    }

    function galmapSettleTime() {
      const fallback = Number(WEB_DEFAULTS.galaxyMapSettle || 0);
      const value = Number(document.getElementById("galaxy-settle").value || WEB_DEFAULTS.galaxyMapSettle);
      return Number.isFinite(value) ? value : fallback;
    }

    function updateCommandPreview() {
      const params = selectedHaulParams();
      document.getElementById("command-preview").textContent =
        "command.dispatch_haul_loop\n" +
        Object.entries(params).map(([key, value]) => `  ${key}=${value}`).join("\n");
    }

    function applyHydratePayload(payload) {
      const ship = payload.ship || {};
      const haulSession = payload.haul_session || {};
      if (historyCompletedRuns !== haulSession.completed_runs) {
        historyCompletedRuns = haulSession.completed_runs;
        refreshHaulHistory();
      }
      const routine = payload.routine || {};
      const activity = payload.activity_log || {};
      const serverStatus = payload.server_status || {};
      currentRoutine = routine;
      setText("status-runtime", serverStatus.runtime_platform || WEB_CONFIG.runtimePlatform || "-");
      setText("status-journal", serverStatus.journal_source_status || WEB_CONFIG.journalStatus || "-");
      setText("status-input-target", serverStatus.input_target_summary || WEB_CONFIG.inputTargetSummary || "-");
      setText("status-version", serverVersionLabel(serverStatus.server_version, serverStatus.server_commit));
      setText("session-target", serverStatus.input_target_summary || WEB_CONFIG.inputTargetSummary || "-");
      document.getElementById("summary-current").textContent = ship.system || "-";
      document.getElementById("summary-home").textContent = payload.home_system || "-";
      document.getElementById("summary-destination").textContent = ship.destination_system || "-";
      document.getElementById("summary-cargo").textContent =
        `${ship.cargo_count || 0} / ${ship.cargo_capacity || 0} t`;
      document.getElementById("summary-runs").textContent = haulSession.completed_runs || 0;
      if (ship.system) {
        hydratedCurrentSystem = ship.system;
        syncHydratedField("origin", hydratedCurrentSystem);
      }
      window.EDCR_HAUL = window.EDCR_HAUL || {};
      window.EDCR_HAUL.shipState = {
        system: ship.system || "",
        supercharge_multiplier: ship.supercharge_multiplier || null,
        max_jump_range_ly: ship.max_jump_range_ly || null,
      };
      window.dispatchEvent(new CustomEvent("edcr:ship-state", { detail: window.EDCR_HAUL.shipState }));
      window.EDCR_HAUL.lastHydrate = payload;
      window.dispatchEvent(new CustomEvent("edcr:hydrate", { detail: payload }));
      if (ship.cargo_capacity) {
        WEB_DEFAULTS.cargoCapacity = String(ship.cargo_capacity);
        syncHydratedField("capacity", ship.cargo_capacity);
      }
      // Only a route change from the server moves the selection: repeat hydrates must not undo the operator's
      // row or page choice, or re-render rows under a tap between mousedown and mouseup.
      const hydratedApiRoute = payload.selected_trade_route || payload.running_trade_route;
      const hydratedRouteKey = hydratedApiRoute ? routeKey(routeFromApi(hydratedApiRoute, 0)) : "";
      if (hydratedRouteKey !== lastHydratedRouteKey) {
        lastHydratedRouteKey = hydratedRouteKey;
        if (mergeHydratedRoute(hydratedApiRoute)) {
          renderRows();
          renderSelected();
        }
      }
      importLinkedRoute();
      document.getElementById("summary-profit").textContent = formatCredits(sessionProfit(haulSession));
      updateRoutinePanel(routine, haulSession, ship);
      updateOperatorState();
      activityEntries.clear();
      (activity.entries || []).forEach(addActivityEntry);
      renderActivityLog();
    }

    document.getElementById("route-rows").addEventListener("click", (event) => {
      const row = event.target.closest("tr[data-index]");
      if (!row) {
        return;
      }
      selectedRouteIndex = Number(row.dataset.index);
      renderRows();
      renderSelected();
      persistSelectedRoute(routeByIndex(selectedRouteIndex));
    });

    document.getElementById("copy-route").addEventListener("click", copySelectedRoute);
    document.getElementById("import-route").addEventListener("click", importPastedRoute);

    document.getElementById("search-form").addEventListener("submit", (event) => {
      event.preventDefault();
      if (!accessToken) {
        setResultCount("Backend token required");
        appendActivity("Enter and save an access token to search live routes.", "Search", "warning");
        return;
      }
      if (clientRole !== "active_operator") {
        setResultCount("Operator connection required");
        appendActivity("Connect to the backend before searching routes.", "Search", "warning");
        return;
      }
      setResultCount(`Searching ${searchScopeLabel()}...`);
      setInaraSearchLink("");
      const body = {
        origin: document.getElementById("origin").value,
        destination: document.getElementById("destination").value,
        cargo_capacity: document.getElementById("capacity").value,
        max_route_distance_ly: document.getElementById("route-distance").value,
        max_station_distance_ls: document.getElementById("station-distance").value,
        min_supply: document.getElementById("min-supply").value,
        min_demand: document.getElementById("min-demand").value,
        metric: document.getElementById("metric").value,
        use_surface_stations: document.getElementById("surface-stations").value
      };
      sendCommand("command.search_haul_routes", body)
        .then((payload) => {
          const result = payload.result || {};
          routes = (result.routes || []).map(routeFromApi);
          hasSearchedRoutes = true;
          routePage = 1;
          selectedRouteIndex = routes[0] ? routes[0].index : 0;
          renderRows();
          renderSelected();
          persistSelectedRoute(routeByIndex(selectedRouteIndex));
          setResultCount(`Found ${result.route_count || 0} ${searchScopeLabel()}${result.hub ? ` via hub ${result.hub}` : ""}`);
          setInaraSearchLink(result.query_url || "");
          appendActivity(`Route search returned ${result.route_count || 0} result(s).`, "Search", "success");
        })
        .catch((error) => {
          setResultCount("Search failed");
          setInaraSearchLink("");
          appendActivity(error.message, "Search", "warning");
        });
    });

    document.getElementById("reset-search").addEventListener("click", () => {
      applySearchDefaults();
    });

    document.getElementById("route-distance-preset").addEventListener("change", (event) => {
      const value = event.target.value;
      if (value) {
        document.getElementById("route-distance").value = value;
        event.target.value = "";
      }
    });

    document.getElementById("prev-routes").addEventListener("click", () => {
      routePage = Math.max(1, routePage - 1);
      renderRows();
    });

    document.getElementById("next-routes").addEventListener("click", () => {
      const totalPages = Math.max(1, Math.ceil(routes.length / ROUTES_PER_PAGE));
      routePage = Math.min(totalPages, routePage + 1);
      renderRows();
    });

    document.getElementById("set-destination").addEventListener("click", () => {
      const route = routeByIndex(selectedRouteIndex);
      if (!route) {
        appendActivity("Select a route before setting destination.", "Nav", "warning");
        return;
      }
      if (!accessToken) {
        appendActivity("Enter and save an access token to set destination.", "Nav", "warning");
        return;
      }
      if (clientRole !== "active_operator") {
        appendActivity("Connect to the backend before setting destination.", "Nav", "warning");
        return;
      }
      const destination = route.buySystem || "";
      if (!destination) {
        appendActivity("Selected route is missing a Station 1 system.", "Nav", "warning");
        return;
      }
      sendCommand("command.dispatch_destination", {
        destination,
        galaxy_map_settle: galmapSettleTime(),
        skip_delay: false,
        raw_command: `web set destination ${destination}`
      })
        .then(() => {
          appendActivity(`Destination set for ${destination}.`, "Nav", "success");
        })
        .catch((error) => {
          appendActivity(error.message, "Nav", "warning");
        });
    });

    document.getElementById("travel-from-selected").addEventListener("click", () => {
      const route = routeByIndex(selectedRouteIndex);
      if (!route) {
        appendActivity("Select a route before loading travel target.", "Travel", "warning");
        return;
      }
      travelTargetDirty = false;
      updateTravelTarget(route, { force: true });
    });

    ["travel-system", "travel-station"].forEach((id) => {
      document.getElementById(id).addEventListener("input", () => {
        travelTargetDirty = true;
      });
    });

    document.getElementById("clear-travel-target").addEventListener("click", () => {
      travelTargetDirty = true;
      document.getElementById("travel-system").value = "";
      document.getElementById("travel-station").value = "";
    });

    document.getElementById("start-travel").addEventListener("click", () => {
      const system = document.getElementById("travel-system").value.trim();
      const station = document.getElementById("travel-station").value.trim();
      if (!system) {
        appendActivity("Enter a target system before starting travel.", "Travel", "warning");
        return;
      }
      if (!accessToken) {
        appendActivity("Enter and save an access token to start travel.", "Travel", "warning");
        return;
      }
      if (clientRole !== "active_operator") {
        appendActivity("Connect to the backend before starting travel.", "Travel", "warning");
        return;
      }
      sendCommand("command.dispatch_travel", {
        system,
        station,
        manual_landing: travelTargetManualLanding(system, station),
        raw_command: station ? `web travel ${system} / ${station}` : `web travel ${system}`
      })
        .then(() => {
          appendActivity(station ? `Travel accepted for ${station}.` : `Travel accepted for ${system}.`, "Travel", "success");
        })
        .catch((error) => {
          appendActivity(error.message, "Travel", "warning");
        });
    });

    document.getElementById("start-haul").addEventListener("click", () => {
      const route = routeByIndex(selectedRouteIndex);
      if (!route) {
        appendActivity("Select a route before starting haul.", "Haul", "warning");
        return;
      }
      if (!accessToken) {
        appendActivity("Enter and save an access token to start haul.", "Haul", "warning");
        return;
      }
      if (clientRole !== "active_operator") {
        appendActivity("Connect to the backend before starting haul.", "Haul", "warning");
        return;
      }
      const params = selectedHaulParams();
      sendCommand("command.dispatch_haul_loop", {
        params,
        raw_command: `web haul start ${route.buyStation} -> ${route.sellStation}`,
        trade_route: tradeRoutePayload(route)
      })
        .then(() => {
          appendActivity("Two-way haul accepted by backend.", "Haul", "success");
        })
        .catch((error) => {
          appendActivity(error.message, "Haul", "warning");
        });
    });

    function requestRoutineStop(mode) {
      if (!accessToken) {
        appendActivity("Enter and save an access token to control the active routine.", "Haul", "warning");
        return;
      }
      if (clientRole !== "active_operator") {
        appendActivity("Connect to the backend before stopping routines.", "Haul", "warning");
        return;
      }
      if (!currentRoutine.routine_active) {
        appendActivity("No active routine to stop.", "Haul", "warning");
        return;
      }
      sendCommand("command.cancel_active_routine", { mode })
        .then(() => {
          appendActivity(mode === "after_run" ? "Stop after run requested." : "Immediate stop requested.", "Haul", "warning");
        })
        .catch((error) => {
          appendActivity(error.message, "Haul", "warning");
        });
    }

    function requestHaulPauseCommand(rawInput, successMessage) {
      if (!accessToken) {
        appendActivity("Enter and save an access token to control the active haul.", "Haul", "warning");
        return;
      }
      if (clientRole !== "active_operator") {
        appendActivity("Connect to the backend before controlling haul pause.", "Haul", "warning");
        return;
      }
      if (!currentRoutine.routine_active || currentRoutine.active_routine_name !== "haul") {
        appendActivity("No active haul to control.", "Haul", "warning");
        return;
      }
      sendCommand("command.submit_input", {
        raw_input: rawInput,
        skip_delay: true
      })
        .then(() => {
          appendActivity(successMessage, "Haul", "warning");
        })
        .catch((error) => {
          appendActivity(error.message, "Haul", "warning");
        });
    }

    function requestInstantToggle() {
      if (!accessToken) {
        appendActivity("Enter and save an access token to change instant mode.", "Session", "warning");
        return;
      }
      if (clientRole !== "active_operator") {
        appendActivity("Connect to the backend before changing instant mode.", "Session", "warning");
        return;
      }
      const nextMode = currentRoutine.instant_mode ? "off" : "on";
      sendCommand("command.submit_input", {
        raw_input: `instant ${nextMode}`,
        skip_delay: true
      })
        .then(() => {
          appendActivity(`Instant mode ${nextMode} requested.`, "Session", "success");
        })
        .catch((error) => {
          appendActivity(error.message, "Session", "warning");
        });
    }

    function submitHaulStatsCommand(rawInput, successMessage) {
      if (!accessToken) {
        appendActivity("Enter and save an access token to update haul stats.", "Haul", "warning");
        return;
      }
      if (clientRole !== "active_operator") {
        appendActivity("Connect to the backend before updating haul stats.", "Haul", "warning");
        return;
      }
      if (rawInput === "stop" && currentRoutine.routine_active) {
        appendActivity("Stop the active routine before stopping haul stats.", "Haul", "warning");
        return;
      }
      sendCommand("command.submit_input", {
        raw_input: rawInput,
        skip_delay: true
      })
        .then(() => {
          appendActivity(successMessage, "Haul", "success");
        })
        .catch((error) => {
          appendActivity(error.message, "Haul", "warning");
        });
    }

    document.getElementById("stop-after-run").addEventListener("click", () => {
      requestRoutineStop("after_run");
    });

    document.getElementById("stop-now").addEventListener("click", () => {
      requestRoutineStop("now");
    });

    document.getElementById("pause-haul").addEventListener("click", () => {
      requestHaulPauseCommand("pause", "Haul pause requested.");
    });

    document.getElementById("resume-haul").addEventListener("click", () => {
      requestHaulPauseCommand("resume", "Haul resume requested.");
    });

    document.getElementById("instant-toggle").addEventListener("click", requestInstantToggle);
    document.getElementById("clear-haul-stats").addEventListener("click", () => {
      submitHaulStatsCommand("new_session", "Clear haul stats requested.");
    });
    document.getElementById("stop-haul-stats").addEventListener("click", () => {
      submitHaulStatsCommand("stop", "Stop haul stats requested.");
    });

    document.getElementById("galaxy-settle").addEventListener("input", updateCommandPreview);
    document.getElementById("dock-timeout").addEventListener("input", updateCommandPreview);
    document.getElementById("save-token").addEventListener("click", saveAccessToken);
    document.getElementById("reconnect-websocket").addEventListener("click", reconnectNow);
    document.getElementById("connection-reconnect").addEventListener("click", reconnectNow);
    document.getElementById("connect-token-prompt").addEventListener("click", submitAccessTokenPrompt);
    document.getElementById("cancel-token-prompt").addEventListener("click", closeAccessTokenPrompt);
    document.getElementById("prompt-access-token").addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitAccessTokenPrompt();
      }
    });
    document.getElementById("access-token").addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        saveAccessToken();
      }
    });

    document.querySelectorAll("[data-history-window]").forEach((button) => {
      button.addEventListener("click", () => {
        historyWindow = button.dataset.historyWindow;
        try { window.localStorage.setItem(HISTORY_WINDOW_KEY, historyWindow); } catch (_) {}
        refreshHaulHistory();
      });
    });
    [["history-node", HISTORY_NODE_KEY], ["history-ship", HISTORY_SHIP_KEY]].forEach(([id, key]) => {
      document.getElementById(id).addEventListener("change", (event) => {
        if (id === "history-node") historyNode = event.target.value; else historyShip = event.target.value;
        try { window.localStorage.setItem(key, event.target.value); } catch (_) {}
        refreshHaulHistory();
      });
    });
    refreshHaulHistory();
    applyWebConfigLabels();
    applySearchDefaults();
    applyHaulDefaults();
    renderRows();
    renderSelected();
    renderActivityLog();
    connectWebsocket();
