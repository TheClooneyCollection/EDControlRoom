let routes = [];
    let selectedRouteIndex = 0;
    let currentView = "two-way";
    let multiLegRoutes = [];
    let selectedMultiLegIndex = 1;
    let hasSearchedRoutes = false;
    let routePage = 1;
    const ROUTES_PER_PAGE = 12;
    const RECONNECT_INITIAL_DELAY_MS = 1000;
    const RECONNECT_MAX_DELAY_MS = 30000;
    const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";
    const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
    const AUTH_QUERY_PARAMETER_NAME = WEB_CONFIG.authQueryParameterName || "access_token";
    const SERVER_DEFAULT_ACCESS_TOKEN = WEB_CONFIG.defaultAccessToken || "";
    const queryParams = new URLSearchParams(window.location.search);
    const queryAccessToken = queryParams.get(AUTH_QUERY_PARAMETER_NAME) || queryParams.get("access_token") || "";
    const cachedAccessToken = window.localStorage.getItem(TOKEN_STORAGE_KEY) || "";
    let accessToken = queryAccessToken || cachedAccessToken || SERVER_DEFAULT_ACCESS_TOKEN;
    let socket = null;
    let clientRole = "observer";
    let commandSequence = 1;
    let hydratedCurrentSystem = "";
    let currentRoutine = {};
    let reconnectDelayMs = RECONNECT_INITIAL_DELAY_MS;
    let reconnectTimer = null;
    let reconnectCountdownTimer = null;
    let reconnectDeadlineMs = 0;
    let reconnectAttempts = 0;
    const pendingCommands = new Map();
    const activityEntries = new Map();
    const WEB_DEFAULTS = {
      startingCapital: "",
      cargoCapacity: "",
      maxHopDistanceLy: "",
      maxHops: "5",
      maxRouteDistanceLy: "500",
      maxStationDistanceLs: "any",
      maxStationDistanceRange: "1000000",
      maxMarketAge: "",
      metric: "Profit / hour",
      requiresLargePad: "true",
      allowPlanetary: "false",
      avoidLoops: "false",
      multiAvoidLoops: "true",
      galaxyMapSettle: "2",
      dockTimeout: "1200",
      ...(WEB_CONFIG.webDefaults || {})
    };

    const VIEW_COPY = {
      "two-way": {
        title: "Two-way haul control",
        description: "Search routes, inspect the selected station-to-station route, and start a two-way haul with structured dispatch. Route selection stays local to this browser; server-side search results are shared data.",
        routine: "Two-way haul"
      },
      "multi-leg": {
        title: "Multi-leg haul control",
        description: "Prepare a finite Spansh-style multi-stop haul route. This page uses a dedicated multi-leg command path and keeps UI state separate from two-way haul.",
        routine: "Multi-leg haul"
      }
    };
    const LARGE_PAD_SHIPS = new Set([
      "anaconda", "belugaliner", "cutter", "empire_cutter", "federation_corvette", "orca",
      "type7", "type9", "type9_military", "type10defender"
    ]);
    const NON_LARGE_PAD_SHIPS = new Set([
      "adder", "asp", "asp_scout", "cobramkiii", "cobramkiv", "diamondback", "diamondbackxl",
      "dolphin", "eagle", "empire_courier", "empire_eagle", "federation_assault_ship",
      "federation_dropship", "federation_dropship_mkii", "federation_gunship",
      "hauler", "independant_trader", "independent_trader", "krait_light", "krait_mkii",
      "mandalay", "python", "python_nx", "sidewinder", "type6", "type6_mkii", "type8",
      "typex", "viper", "viper_mkiv", "vulture"
    ]);

    function routeByIndex(index) {
      return routes.find((route) => route.index === index) || routes[0] || null;
    }

    function multiLegRouteByIndex(index) {
      return multiLegRoutes.find((route) => route.index === index) || multiLegRoutes[0] || null;
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

    function setElementChecked(id, value) {
      const element = document.getElementById(id);
      if (element) {
        element.checked = String(value).toLowerCase() === "true";
      }
    }

    function rangeValueForNumericDefault(value, fallback) {
      const numeric = Number(String(value ?? "").replace(/,/g, ""));
      return Number.isFinite(numeric) ? String(numeric) : fallback;
    }

    function applyWebConfigLabels() {
      setText("session-host", WEB_CONFIG.hostLabel || window.location.host || "-");
      setText("session-target", WEB_CONFIG.inputTargetSummary || "-");
      setText("session-role", roleLabel(WEB_CONFIG.sessionRole));
      setText("status-runtime", WEB_CONFIG.runtimePlatform || "-");
      setText("status-journal", WEB_CONFIG.journalStatus || "-");
      setText("status-input-target", WEB_CONFIG.inputTargetSummary || "-");
    }

    function applySearchDefaults() {
      setElementValue("origin", hydratedCurrentSystem);
      setElementValue("destination", "");
      setElementValue("starting-capital", WEB_DEFAULTS.startingCapital);
      setElementValue("max-hop-distance", WEB_DEFAULTS.maxHopDistanceLy);
      setElementValue("capacity", WEB_DEFAULTS.cargoCapacity);
      setElementValue("metric", WEB_DEFAULTS.metric);
      setElementValue("max-hops", WEB_DEFAULTS.maxHops);
      setElementValue("max-hops-range", rangeValueForNumericDefault(WEB_DEFAULTS.maxHops, "5"));
      setElementValue("route-distance", WEB_DEFAULTS.maxRouteDistanceLy);
      setElementValue("route-distance-range", rangeValueForNumericDefault(WEB_DEFAULTS.maxRouteDistanceLy, "500"));
      setElementValue("station-distance", WEB_DEFAULTS.maxStationDistanceLs);
      setElementValue(
        "station-distance-range",
        rangeValueForNumericDefault(WEB_DEFAULTS.maxStationDistanceLs, WEB_DEFAULTS.maxStationDistanceRange)
      );
      setElementValue("market-age", WEB_DEFAULTS.maxMarketAge);
      setElementChecked("requires-large-pad", WEB_DEFAULTS.requiresLargePad);
      setElementChecked("allow-planetary", WEB_DEFAULTS.allowPlanetary);
      setElementChecked("avoid-loops", WEB_DEFAULTS.avoidLoops);
    }

    function applyHaulDefaults() {
      setElementValue("galaxy-settle", WEB_DEFAULTS.galaxyMapSettle);
      setElementValue("dock-timeout", WEB_DEFAULTS.dockTimeout);
    }

    function applyMultiSearchDefaults() {
      setElementValue("multi-origin", hydratedCurrentSystem);
      setElementValue("multi-starting-capital", WEB_DEFAULTS.startingCapital);
      setElementValue("multi-capacity", document.getElementById("capacity").value || WEB_DEFAULTS.cargoCapacity);
      setElementValue("multi-hop-distance", WEB_DEFAULTS.maxHopDistanceLy);
      setElementValue("multi-max-hops", WEB_DEFAULTS.maxHops);
      setElementValue("multi-station-distance", WEB_DEFAULTS.maxStationDistanceLs);
      setElementValue(
        "multi-station-distance-range",
        rangeValueForNumericDefault(WEB_DEFAULTS.maxStationDistanceLs, WEB_DEFAULTS.maxStationDistanceRange)
      );
      setElementValue("multi-market-age", WEB_DEFAULTS.maxMarketAge);
      setElementChecked("multi-requires-large-pad", WEB_DEFAULTS.requiresLargePad);
      setElementChecked("multi-allow-planetary", WEB_DEFAULTS.allowPlanetary);
      setElementChecked("multi-avoid-loops", WEB_DEFAULTS.multiAvoidLoops);
    }

    function applyFormDefaults() {
      applySearchDefaults();
      applyHaulDefaults();
      applyMultiSearchDefaults();
    }

    function selectedRouteForCurrentView() {
      return currentView === "multi-leg" ? multiLegRouteByIndex(selectedMultiLegIndex) : routeByIndex(selectedRouteIndex);
    }

    function compactLocation(system, station) {
      const systemLabel = system || "-";
      return station ? `${station} in ${systemLabel}` : systemLabel;
    }

    function commodityList(...values) {
      return values.filter((value) => value && value !== "-");
    }

    function cargoPills(items, className) {
      if (!items.length) {
        return `<span class="cargo-pill"><strong>None</strong></span>`;
      }
      return items.map((item) => `
        <span class="cargo-pill ${className}">
          <strong>${escapeHtml(item.name)}</strong>
          ${item.amount ? `<span>${escapeHtml(item.amount)}</span>` : ""}
        </span>
      `).join("");
    }

    function routeCommodityRows(route, cumulativeProfit) {
      const capacity = Number(document.getElementById("capacity")?.value || 0);
      const amount = capacity > 0 ? capacity.toLocaleString() : "-";
      const unitProfit = route.apiRoute?.profit_per_unit || "-";
      const totalProfit = route.profitTrip || "-";
      const primaryCommodity = route.commodity || "Selected cargo";
      const rows = [
        { commodity: primaryCommodity, amount, buy: "-", sell: "-", profit: unitProfit, total: totalProfit }
      ];
      return rows.map((row) => `
        <tr>
          <td>${escapeHtml(row.commodity)}</td>
          <td class="num">${escapeHtml(row.amount)}</td>
          <td class="num">${escapeHtml(row.buy)}</td>
          <td class="num">${escapeHtml(row.sell)}</td>
          <td class="num">${escapeHtml(row.profit)}</td>
          <td class="num">${escapeHtml(row.total)}</td>
        </tr>
      `).join("") + `
        <tr>
          <td></td><td></td><td></td><td></td><td></td>
          <td class="num">${escapeHtml(cumulativeProfit || totalProfit)}</td>
        </tr>
      `;
    }

    function routeResultCard(route, index, cumulativeProfit = "") {
      const isSelected = route.index === selectedRouteIndex;
      const nextLeg = `Then fly ${route.routeDistance || "-"} to ${compactLocation(route.sellSystem, route.sellStation)}.`;
      return `
        <article class="result-card ${isSelected ? "selected" : ""}" data-index="${route.index}">
          <div class="result-card-head">
            <div>
              <div class="result-card-title">
                ${index === 0 ? "Starting at" : ""} ${escapeHtml(compactLocation(route.buySystem, route.buyStation))}
              </div>
              <div class="result-card-sub">
                ${escapeHtml(route.apiRoute?.updated ? `updated ${route.apiRoute.updated}` : "market age pending")} · ${escapeHtml(route.buyStationDistance || "-")}
              </div>
            </div>
            <button class="btn ghost" type="button" data-select-route="${route.index}">Select</button>
          </div>
          <div class="result-card-body">
            <p class="result-copy">Sell everything in your hold and buy the commodities listed below.</p>
            <table class="commodity-table">
              <thead>
                <tr>
                  <th>Commodity</th><th>Amount</th><th>Buy Price</th><th>Sell Price</th><th>Profit</th><th>Total Profit</th>
                </tr>
              </thead>
              <tbody>${routeCommodityRows(route, cumulativeProfit)}</tbody>
            </table>
            <div class="profit-band">Cumulative Profit ${escapeHtml(cumulativeProfit || route.profitTrip || "-")}</div>
            <div class="leg-next">${escapeHtml(nextLeg)}</div>
          </div>
        </article>
      `;
    }

    function multiLegResultCard(route) {
      const isSelected = route.index === selectedMultiLegIndex;
      const rows = route.legs.map((leg) => `
        <tr>
          <td>${escapeHtml(leg.station)}</td>
          <td>${cargoPills(leg.buy, "buy")}</td>
          <td>${cargoPills(leg.sell, "sell")}</td>
          <td class="num">${escapeHtml(leg.profit)}</td>
        </tr>
      `).join("");
      return `
        <article class="result-card ${isSelected ? "selected" : ""}" data-multi-index="${route.index}">
          <div class="result-card-head">
            <div>
              <div class="result-card-title">${escapeHtml(route.name)}</div>
              <div class="result-card-sub">${escapeHtml(route.summary)}</div>
            </div>
            <button class="btn ghost" type="button" data-select-multi-route="${route.index}">Select</button>
          </div>
          <div class="result-card-body">
            <table class="commodity-table">
              <thead>
                <tr><th>Stop</th><th>Buy</th><th>Sell</th><th>Total Profit</th></tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
            <div class="profit-band">Cumulative Profit ${escapeHtml(route.cumulativeProfit)}</div>
            <div class="leg-next">${escapeHtml(route.nextTransit)}</div>
          </div>
        </article>
      `;
    }

    function setView(view) {
      currentView = view === "multi-leg" ? "multi-leg" : "two-way";
      document.querySelectorAll(".page-view").forEach((element) => {
        element.classList.toggle("active", element.dataset.view === currentView);
      });
      document.querySelectorAll(".nav-item[data-view]").forEach((element) => {
        const active = element.dataset.view === currentView;
        element.classList.toggle("active", active);
        element.setAttribute("aria-selected", active ? "true" : "false");
      });
      const copy = VIEW_COPY[currentView];
      setText("page-title", copy.title);
      setText("page-description", copy.description);
      setText("summary-routine", copy.routine);
      updateRoutineContext();
      updateOperatorState();
    }

    function syncRange(rangeId, inputId) {
      const range = document.getElementById(rangeId);
      const input = document.getElementById(inputId);
      if (!range || !input) {
        return;
      }
      range.addEventListener("input", () => {
        input.value = range.value;
      });
      input.addEventListener("input", () => {
        range.value = input.value;
      });
    }

    function setInputValue(id, value) {
      const input = document.getElementById(id);
      if (input && value !== null && value !== undefined && value !== "") {
        input.value = String(value);
      }
    }

    function normalizedShipType(shipType) {
      return String(shipType || "").trim().toLowerCase().replace(/[\s-]/g, "_");
    }

    function requiresLargePadForShip(ship) {
      if (ship.landing_pad_size) {
        return String(ship.landing_pad_size).toLowerCase() === "large";
      }
      const shipType = normalizedShipType(ship.ship_type);
      if (LARGE_PAD_SHIPS.has(shipType)) {
        return true;
      }
      if (NON_LARGE_PAD_SHIPS.has(shipType)) {
        return false;
      }
      return null;
    }

    function formattedJumpRange(ship) {
      const range = Number(ship.laden_jump_range_ly || ship.max_jump_range_ly || ship.jump_range_ly || 0);
      if (!Number.isFinite(range) || range <= 0) {
        return "";
      }
      return String(Math.round(range * 100) / 100);
    }

    function applyShipDefaults(ship) {
      if (ship.credits) {
        WEB_DEFAULTS.startingCapital = String(ship.credits);
        setInputValue("starting-capital", ship.credits);
        setInputValue("multi-starting-capital", ship.credits);
      }
      if (ship.cargo_capacity) {
        WEB_DEFAULTS.cargoCapacity = String(ship.cargo_capacity);
        setInputValue("capacity", ship.cargo_capacity);
        setInputValue("multi-capacity", ship.cargo_capacity);
      }
      const jumpRange = formattedJumpRange(ship);
      if (jumpRange) {
        WEB_DEFAULTS.maxHopDistanceLy = jumpRange;
        setInputValue("max-hop-distance", jumpRange);
        setInputValue("multi-hop-distance", jumpRange);
      }
      const requiresLargePad = requiresLargePadForShip(ship);
      if (requiresLargePad !== null) {
        WEB_DEFAULTS.requiresLargePad = requiresLargePad ? "true" : "false";
        document.getElementById("requires-large-pad").checked = requiresLargePad;
        document.getElementById("multi-requires-large-pad").checked = requiresLargePad;
      }
      updateMultiCommandPreview();
    }

    function routeFromApi(route, fallbackIndex) {
      const stationDistances = [route.from_station_distance, route.to_station_distance].filter(Boolean);
      const index = Number(route.index || fallbackIndex);
      return {
        index,
        profitHour: route.profit_per_hour || "-",
        profitTrip: route.profit_per_trip || "-",
        commodity: route.source_buy_commodity || "",
        targetCommodity: route.target_buy_commodity || "",
        buyStation: route.from_station || "",
        buySystem: route.from_system || "",
        buyStationDistance: route.from_station_distance || "-",
        sellStation: route.to_station || "",
        sellSystem: route.to_system || "",
        sellStationDistance: route.to_station_distance || "-",
        distanceFromSystem: route.distance_from_system || "-",
        routeDistance: route.route_distance || "-",
        stationDistance: stationDistances.length ? stationDistances.join(" / ") : "-",
        apiRoute: { ...route, index }
      };
    }

    function tradeRoutePayload(route) {
      if (!route) {
        return null;
      }
      return {
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
        raw_text: route.apiRoute?.raw_text || "",
        url_links: route.apiRoute?.url_links || []
      };
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

    function profitHourLabel(route) {
      if (!route.profitHour || route.profitHour === "-") {
        return "-";
      }
      return route.profitHour.includes("/") ? route.profitHour : `${route.profitHour}/h`;
    }

    function setResultCount(text) {
      document.getElementById("result-count").textContent = text;
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
      document.getElementById("start-multi-haul").disabled = !active || !multiLegRouteByIndex(selectedMultiLegIndex);
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
        setResultCount(`Found ${routes.length} station/carrier routes`);
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

    function websocketUrl() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const params = new URLSearchParams({
        client_name: WEB_CONFIG.clientName || "web-haul"
      });
      params.set(AUTH_QUERY_PARAMETER_NAME, accessToken);
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
      return String(value || "").replace(/\[\/?[a-zA-Z0-9_#= .-]+\]/g, "");
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
        return `${(amount / 1000000000).toFixed(1)}b CR`;
      }
      if (abs >= 1000000) {
        return `${(amount / 1000000).toFixed(1)}m CR`;
      }
      if (abs >= 1000) {
        return `${(amount / 1000).toFixed(1)}k CR`;
      }
      return `${amount} CR`;
    }

    function updateRoutineContext() {
      const route = selectedRouteForCurrentView();
      if (!route) {
        setText("routine-buying", "-");
        setText("routine-buying-sub", "Waiting for a selected route");
        setText("routine-selling", "-");
        setText("routine-selling-sub", "Waiting for cargo context");
        setText("routine-transit", "-");
        setText("routine-transit-sub", "No route active");
        setText("routine-next-sale", "-");
        setText("routine-next-sale-sub", "No sell order queued");
        return;
      }

      if (currentView === "multi-leg") {
        const currentLeg = route.legs[0] || {};
        const nextLeg = route.legs[1] || currentLeg;
        setText("routine-buying", (currentLeg.buy || []).map((item) => item.name).join(", ") || "-");
        setText("routine-buying-sub", currentLeg.station || route.name);
        setText("routine-selling", (currentLeg.sell || []).map((item) => item.name).join(", ") || "-");
        setText("routine-selling-sub", currentLeg.station || "First stop");
        setText("routine-transit", nextLeg.station || "-");
        setText("routine-transit-sub", route.nextTransit || route.summary);
        setText("routine-next-sale", (nextLeg.sell || []).map((item) => item.name).join(", ") || "-");
        setText("routine-next-sale-sub", nextLeg.station || "Next stop");
        return;
      }

      const sellCargo = commodityList(route.commodity);
      const returnCargo = commodityList(route.targetCommodity);
      setText("routine-buying", sellCargo.join(", ") || "-");
      setText("routine-buying-sub", compactLocation(route.buySystem, route.buyStation));
      setText("routine-selling", sellCargo.join(", ") || "Hold cargo");
      setText("routine-selling-sub", compactLocation(route.sellSystem, route.sellStation));
      setText("routine-transit", compactLocation(route.sellSystem, route.sellStation));
      setText("routine-transit-sub", route.routeDistance ? `${route.routeDistance} route` : "Route distance pending");
      setText("routine-next-sale", returnCargo.join(", ") || sellCargo.join(", ") || "-");
      setText("routine-next-sale-sub", returnCargo.length ? compactLocation(route.buySystem, route.buyStation) : compactLocation(route.sellSystem, route.sellStation));
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
      document.getElementById("routine-elapsed").textContent =
        formatDuration(haulSession.session_elapsed_s || haulSession.current_run_elapsed_s || 0);
      document.getElementById("routine-current-run").textContent =
        `${formatCredits(haulSession.current_run_profit || 0)} / ${formatCredits(haulSession.accumulated_profit || 0)}`;
      document.getElementById("routine-cargo-moved").textContent =
        `${Number(haulSession.cargo_moved_t || 0).toLocaleString()} t`;
      updateRoutineContext();
    }

    function updateRoutePager(start, end, total, totalPages) {
      document.getElementById("route-page-status").textContent = `${start}-${end} of ${total}`;
      document.getElementById("prev-routes").disabled = routePage <= 1;
      document.getElementById("next-routes").disabled = routePage >= totalPages || total === 0;
    }

    function renderRows() {
      const container = document.getElementById("route-results");
      if (!routes.length) {
        const message = hasSearchedRoutes
          ? "No station/carrier routes found."
          : "Search routes to load station/carrier results.";
        container.innerHTML = `<div class="route-sub empty-route-message">${message}</div>`;
        routePage = 1;
        updateRoutePager(0, 0, 0, 1);
        updateRoutineContext();
        return;
      }
      const totalPages = Math.max(1, Math.ceil(routes.length / ROUTES_PER_PAGE));
      routePage = Math.min(Math.max(1, routePage), totalPages);
      const startIndex = (routePage - 1) * ROUTES_PER_PAGE;
      const visibleRoutes = routes.slice(startIndex, startIndex + ROUTES_PER_PAGE);
      container.innerHTML = visibleRoutes.map((route, index) => routeResultCard(route, startIndex + index)).join("");
      updateRoutePager(startIndex + 1, startIndex + visibleRoutes.length, routes.length, totalPages);
      updateRoutineContext();
    }

    function renderSelected() {
      const route = routeByIndex(selectedRouteIndex);
      const startButton = document.getElementById("start-haul");
      const destinationButton = document.getElementById("set-destination");
      if (!route) {
        document.getElementById("selected-title").textContent = "Select a route before starting.";
        document.getElementById("command-preview").textContent = "";
        startButton.disabled = true;
        destinationButton.disabled = true;
        updateRoutineContext();
        return;
      }
      startButton.disabled = clientRole !== "active_operator";
      destinationButton.disabled = clientRole !== "active_operator";
      document.getElementById("selected-title").textContent =
        `${route.buySystem} (${route.buyStation}) -> ${route.sellSystem} (${route.sellStation})`;
      updateCommandPreview();
      updateRoutineContext();
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
        station_1_on_land: "false",
        station_2_buying: route.targetCommodity || "",
        station_2: route.sellStation || "",
        station_2_system: route.sellSystem || "",
        station_2_on_land: "false",
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

    function multiLegCommandPayload() {
      return {
        origin: document.getElementById("multi-origin").value,
        starting_capital: document.getElementById("multi-starting-capital").value,
        cargo_capacity: document.getElementById("multi-capacity").value,
        max_hop_distance_ly: document.getElementById("multi-hop-distance").value,
        max_hops: document.getElementById("multi-max-hops").value,
        max_station_distance_ls: document.getElementById("multi-station-distance").value,
        max_market_age: document.getElementById("multi-market-age").value,
        requires_large_pad: document.getElementById("multi-requires-large-pad").checked,
        allow_planetary: document.getElementById("multi-allow-planetary").checked,
        allow_player_owned: document.getElementById("multi-allow-player-owned").checked,
        allow_restricted_access: document.getElementById("multi-allow-restricted").checked,
        allow_prohibited: document.getElementById("multi-allow-prohibited").checked,
        avoid_loops: document.getElementById("multi-avoid-loops").checked,
        allow_permit_systems: document.getElementById("multi-allow-permit-systems").checked,
        selected_route: multiLegRouteByIndex(selectedMultiLegIndex)
      };
    }

    function updateMultiCommandPreview() {
      const payload = multiLegCommandPayload();
      document.getElementById("multi-command-preview").textContent =
        "command.dispatch_multi_leg_haul\n" +
        JSON.stringify(payload, null, 2);
      updateRoutineContext();
    }

    function renderMultiLegResults() {
      const container = document.getElementById("multi-route-results");
      if (!multiLegRoutes.length) {
        container.innerHTML = `<div class="route-sub empty-route-message">Calculate to preview a multi-leg haul result.</div>`;
        document.getElementById("multi-result-count").textContent = "Calculate to preview multi-leg results";
        document.getElementById("multi-selected-title").textContent = "Select a generated multi-leg route.";
        updateMultiCommandPreview();
        return;
      }
      container.innerHTML = multiLegRoutes.map(multiLegResultCard).join("");
      const selectedRoute = multiLegRouteByIndex(selectedMultiLegIndex);
      document.getElementById("multi-result-count").textContent = `${multiLegRoutes.length} UI preview route`;
      document.getElementById("multi-selected-title").textContent = selectedRoute ? selectedRoute.name : "Select a generated multi-leg route.";
      updateMultiCommandPreview();
    }

    function buildMultiLegPreviewRoute() {
      const origin = document.getElementById("multi-origin").value || hydratedCurrentSystem || "Current system";
      const capacity = document.getElementById("multi-capacity").value || WEB_DEFAULTS.cargoCapacity || "-";
      return {
        index: 1,
        name: `${origin} / 3-stop haul preview`,
        summary: `${document.getElementById("multi-max-hops").value || "5"} hops max · ${capacity} t capacity · multi-cargo ready`,
        cumulativeProfit: "UI estimate pending",
        nextTransit: "Then fly to the next profitable station after backend route calculation.",
        legs: [
          {
            station: origin,
            buy: [{ name: "Silver", amount: `${capacity} t` }, { name: "Bertrandite", amount: "optional" }],
            sell: [],
            profit: "pending"
          },
          {
            station: "Intermediate station",
            buy: [{ name: "Gold", amount: "split hold" }],
            sell: [{ name: "Silver", amount: `${capacity} t` }],
            profit: "pending"
          },
          {
            station: "Final station",
            buy: [],
            sell: [{ name: "Bertrandite", amount: "remaining" }, { name: "Gold", amount: "split hold" }],
            profit: "pending"
          }
        ]
      };
    }

    function applyHydratePayload(payload) {
      const ship = payload.ship || {};
      const haulSession = payload.haul_session || {};
      const routine = payload.routine || {};
      const activity = payload.activity_log || {};
      const serverStatus = payload.server_status || {};
      currentRoutine = routine;
      setText("status-runtime", serverStatus.runtime_platform || WEB_CONFIG.runtimePlatform || "-");
      setText("status-journal", serverStatus.journal_source_status || WEB_CONFIG.journalStatus || "-");
      setText("status-input-target", serverStatus.input_target_summary || WEB_CONFIG.inputTargetSummary || "-");
      setText("session-target", serverStatus.input_target_summary || WEB_CONFIG.inputTargetSummary || "-");
      document.getElementById("summary-current").textContent = ship.system || "-";
      document.getElementById("summary-home").textContent = payload.home_system || "-";
      document.getElementById("summary-destination").textContent = ship.destination_system || "-";
      document.getElementById("summary-cargo").textContent =
        `${ship.cargo_count || 0} / ${ship.cargo_capacity || 0} t`;
      document.getElementById("summary-runs").textContent = haulSession.completed_runs || 0;
      if (ship.system) {
        hydratedCurrentSystem = ship.system;
        document.getElementById("origin").value = hydratedCurrentSystem;
        document.getElementById("multi-origin").value = hydratedCurrentSystem;
      }
      applyShipDefaults(ship);
      if (mergeHydratedRoute(payload.selected_trade_route || payload.running_trade_route)) {
        renderRows();
        renderSelected();
      }
      document.getElementById("summary-profit").textContent = formatCredits(haulSession.accumulated_profit || 0);
      updateRoutinePanel(routine, haulSession, ship);
      updateOperatorState();
      activityEntries.clear();
      (activity.entries || []).forEach(addActivityEntry);
      renderActivityLog();
    }

    document.getElementById("route-results").addEventListener("click", (event) => {
      const card = event.target.closest("[data-index]");
      if (!card) {
        return;
      }
      selectedRouteIndex = Number(card.dataset.index);
      renderRows();
      renderSelected();
      persistSelectedRoute(routeByIndex(selectedRouteIndex));
    });

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
      setResultCount("Searching station/carrier routes...");
      const body = {
        origin: document.getElementById("origin").value,
        destination: document.getElementById("destination").value,
        starting_capital: document.getElementById("starting-capital").value,
        cargo_capacity: document.getElementById("capacity").value,
        max_hop_distance_ly: document.getElementById("max-hop-distance").value,
        max_hops: document.getElementById("max-hops").value,
        max_route_distance_ly: document.getElementById("route-distance").value,
        max_station_distance_ls: document.getElementById("station-distance").value,
        max_market_age: document.getElementById("market-age").value,
        requires_large_pad: document.getElementById("requires-large-pad").checked,
        allow_planetary: document.getElementById("allow-planetary").checked,
        allow_player_owned: document.getElementById("allow-player-owned").checked,
        allow_restricted_access: document.getElementById("allow-restricted").checked,
        allow_prohibited: document.getElementById("allow-prohibited").checked,
        avoid_loops: document.getElementById("avoid-loops").checked,
        allow_permit_systems: document.getElementById("allow-permit-systems").checked,
        metric: document.getElementById("metric").value
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
          setResultCount(`Found ${result.route_count || 0} station/carrier routes`);
          appendActivity(`Route search returned ${result.route_count || 0} result(s).`, "Search", "success");
        })
        .catch((error) => {
          setResultCount("Search failed");
          appendActivity(error.message, "Search", "warning");
        });
    });

    document.getElementById("reset-search").addEventListener("click", () => {
      applySearchDefaults();
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

    document.getElementById("multi-search-form").addEventListener("submit", (event) => {
      event.preventDefault();
      multiLegRoutes = [buildMultiLegPreviewRoute()];
      selectedMultiLegIndex = 1;
      renderMultiLegResults();
      appendActivity("Multi-leg haul preview calculated locally.", "Haul", "success");
    });

    document.getElementById("multi-route-results").addEventListener("click", (event) => {
      const card = event.target.closest("[data-multi-index]");
      if (!card) {
        return;
      }
      selectedMultiLegIndex = Number(card.dataset.multiIndex);
      renderMultiLegResults();
    });

    document.getElementById("reset-multi-search").addEventListener("click", () => {
      applyMultiSearchDefaults();
      updateMultiCommandPreview();
    });

    document.getElementById("start-multi-haul").addEventListener("click", () => {
      if (!multiLegRouteByIndex(selectedMultiLegIndex)) {
        appendActivity("Calculate and select a multi-leg route before starting.", "Haul", "warning");
        return;
      }
      if (!accessToken) {
        appendActivity("Enter and save an access token to start multi-leg haul.", "Haul", "warning");
        return;
      }
      if (clientRole !== "active_operator") {
        appendActivity("Connect to the backend before starting multi-leg haul.", "Haul", "warning");
        return;
      }
      sendCommand("command.dispatch_multi_leg_haul", {
        params: multiLegCommandPayload(),
        raw_command: "web multi_leg_haul start"
      })
        .then(() => {
          appendActivity("Multi-leg haul accepted by backend.", "Haul", "success");
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
    document.querySelectorAll(".nav-item[data-view]").forEach((button) => {
      button.addEventListener("click", () => setView(button.dataset.view));
    });
    syncRange("max-hops-range", "max-hops");
    syncRange("route-distance-range", "route-distance");
    syncRange("station-distance-range", "station-distance");
    syncRange("multi-station-distance-range", "multi-station-distance");

    applyWebConfigLabels();
    applyFormDefaults();
    setView(window.location.pathname.includes("multi") ? "multi-leg" : "two-way");
    renderRows();
    renderSelected();
    renderMultiLegResults();
    renderActivityLog();
    connectWebsocket();
