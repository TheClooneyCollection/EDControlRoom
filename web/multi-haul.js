const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";
const SERVER_DEFAULT_ACCESS_TOKEN = WEB_CONFIG.defaultAccessToken || window.EDCR_SERVER_DEFAULT_ACCESS_TOKEN || "";
const queryAccessToken = new URLSearchParams(window.location.search).get(WEB_CONFIG.authQueryParameterName || "access_token") || "";
const cachedAccessToken = window.localStorage.getItem(TOKEN_STORAGE_KEY) || "";
let accessToken = queryAccessToken || cachedAccessToken || SERVER_DEFAULT_ACCESS_TOKEN;
let socket = null;
let clientRole = "observer";
let commandSequence = 1;
let hydratedCurrentSystem = "";
let selectedMultiLegIndex = 1;
let multiLegRoutes = [];
const pendingCommands = new Map();

const LARGE_PAD_SHIPS = new Set([
  "anaconda", "belugaliner", "cutter", "empire_cutter", "federation_corvette", "orca",
  "type7", "type9", "type9_military", "type10defender"
]);
const NON_LARGE_PAD_SHIPS = new Set([
  "adder", "asp", "asp_scout", "cobramkiii", "cobramkiv", "diamondback", "diamondbackxl",
  "dolphin", "eagle", "empire_courier", "empire_eagle", "federation_assault_ship",
  "federation_dropship", "federation_gunship", "hauler", "independant_trader",
  "independent_trader", "krait_light", "krait_mkii", "mandalay", "python", "python_nx",
  "sidewinder", "type6", "type8", "typex", "viper", "viper_mkiv", "vulture"
]);

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

function setInputValue(id, value) {
  const input = document.getElementById(id);
  if (input && value !== null && value !== undefined && value !== "") {
    input.value = String(value);
  }
}

function formatCredits(value) {
  const amount = Number(value || 0);
  return `${amount.toLocaleString()} CR`;
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

function multiLegRouteByIndex(index) {
  return multiLegRoutes.find((route) => route.index === index) || multiLegRoutes[0] || null;
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
        <button class="btn ghost" type="button">Select</button>
      </div>
      <div class="result-card-body">
        <table class="commodity-table">
          <thead><tr><th>Stop</th><th>Buy</th><th>Sell</th><th>Total Profit</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <div class="profit-band">Cumulative Profit ${escapeHtml(route.cumulativeProfit)}</div>
        <div class="leg-next">${escapeHtml(route.nextTransit)}</div>
      </div>
    </article>
  `;
}

function updateRoutineContext() {
  const route = multiLegRouteByIndex(selectedMultiLegIndex);
  if (!route) {
    setText("routine-buying", "-");
    setText("routine-selling", "-");
    setText("routine-transit", "-");
    setText("routine-next-sale", "-");
    return;
  }
  const first = route.legs[0] || {};
  const second = route.legs[1] || first;
  setText("routine-buying", (first.buy || []).map((item) => item.name).join(", ") || "-");
  setText("routine-buying-sub", first.station || route.name);
  setText("routine-selling", (first.sell || []).map((item) => item.name).join(", ") || "-");
  setText("routine-selling-sub", first.station || "First stop");
  setText("routine-transit", second.station || "-");
  setText("routine-transit-sub", route.nextTransit || route.summary);
  setText("routine-next-sale", (second.sell || []).map((item) => item.name).join(", ") || "-");
  setText("routine-next-sale-sub", second.station || "Next stop");
}

function buildMultiLegPreviewRoute() {
  const origin = document.getElementById("multi-origin").value || hydratedCurrentSystem || "Current system";
  const capacity = document.getElementById("multi-capacity").value || "784";
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
  document.getElementById("multi-command-preview").textContent =
    "command.dispatch_multi_leg_haul\n" + JSON.stringify(multiLegCommandPayload(), null, 2);
}

function renderMultiLegResults() {
  const container = document.getElementById("multi-route-results");
  if (!multiLegRoutes.length) {
    container.innerHTML = `<div class="route-sub empty-route-message">Calculate to preview a multi-leg haul result.</div>`;
    setText("multi-result-count", "Calculate to preview multi-leg results");
    updateMultiCommandPreview();
    updateRoutineContext();
    return;
  }
  container.innerHTML = multiLegRoutes.map(multiLegResultCard).join("");
  const selected = multiLegRouteByIndex(selectedMultiLegIndex);
  setText("multi-result-count", `${multiLegRoutes.length} UI preview route`);
  setText("multi-selected-title", selected ? selected.name : "Select a generated multi-leg route.");
  updateMultiCommandPreview();
  updateRoutineContext();
}

function applyShipDefaults(ship) {
  if (ship.system) {
    hydratedCurrentSystem = ship.system;
    setInputValue("multi-origin", ship.station ? `${ship.system} / ${ship.station}` : ship.system);
    setText("summary-current", ship.system);
  }
  setText("summary-ship", ship.ship_type || "-");
  setText("summary-cargo", `${ship.cargo_count || 0} / ${ship.cargo_capacity || 0} t`);
  setText("summary-capital", formatCredits(ship.credits || 0));
  if (ship.credits) {
    setInputValue("multi-starting-capital", ship.credits);
  }
  if (ship.cargo_capacity) {
    setInputValue("multi-capacity", ship.cargo_capacity);
  }
  const jumpRange = formattedJumpRange(ship);
  if (jumpRange) {
    setInputValue("multi-hop-distance", jumpRange);
  }
  const requiresLargePad = requiresLargePadForShip(ship);
  if (requiresLargePad !== null) {
    document.getElementById("multi-requires-large-pad").checked = requiresLargePad;
  }
  updateMultiCommandPreview();
}

function websocketUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const params = new URLSearchParams({
    client_name: "web-multi-haul",
    [WEB_CONFIG.authQueryParameterName || "access_token"]: accessToken
  });
  return `${protocol}//${window.location.host}/session?${params.toString()}`;
}

function isSocketReady() {
  return socket && socket.readyState === WebSocket.OPEN;
}

function sendCommand(messageType, payload) {
  if (!isSocketReady()) {
    return Promise.reject(new Error("Websocket is not connected."));
  }
  const messageId = `web-multi-haul-${commandSequence++}`;
  const message = { message_type: messageType, message_id: messageId, payload };
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      pendingCommands.delete(messageId);
      reject(new Error("Timed out waiting for backend response."));
    }, 60000);
    pendingCommands.set(messageId, { resolve, reject, timeout });
    socket.send(JSON.stringify(message));
  });
}

function connectWebsocket() {
  if (!accessToken) {
    return;
  }
  socket = new WebSocket(websocketUrl());
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.message_type === "event.connection_ready") {
      clientRole = "active_operator";
      setText("role-label", clientRole.replace("_", " "));
      return;
    }
    if (message.message_type === "control_room.hydrate") {
      const payload = message.payload || {};
      applyShipDefaults(payload.ship || {});
      setText("routine-status", payload.routine?.routine_active ? payload.routine.active_routine_name || "Running" : "Idle");
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

function syncRange(rangeId, inputId) {
  const range = document.getElementById(rangeId);
  const input = document.getElementById(inputId);
  range.addEventListener("input", () => {
    input.value = range.value;
    updateMultiCommandPreview();
  });
  input.addEventListener("input", () => {
    range.value = input.value;
    updateMultiCommandPreview();
  });
}

document.getElementById("host-label").textContent = WEB_CONFIG.hostLabel || "-";
document.getElementById("target-label").textContent = WEB_CONFIG.inputTargetSummary || "foreground window";
document.getElementById("access-token").value = accessToken;
document.getElementById("save-token").addEventListener("click", () => {
  accessToken = document.getElementById("access-token").value.trim();
  if (accessToken) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    connectWebsocket();
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
});
document.getElementById("multi-search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  multiLegRoutes = [buildMultiLegPreviewRoute()];
  selectedMultiLegIndex = 1;
  renderMultiLegResults();
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
  setInputValue("multi-origin", hydratedCurrentSystem);
  setInputValue("multi-starting-capital", "2000000000");
  setInputValue("multi-capacity", "784");
  setInputValue("multi-hop-distance", "60");
  setInputValue("multi-max-hops", "5");
  setInputValue("multi-station-distance", "1000000");
  document.getElementById("multi-station-distance-range").value = "1000000";
  document.getElementById("multi-market-age").value = "";
  renderMultiLegResults();
});
document.getElementById("start-multi-haul").addEventListener("click", () => {
  sendCommand("command.dispatch_multi_leg_haul", {
    params: multiLegCommandPayload(),
    raw_command: "web multi_leg_haul start"
  }).catch((error) => {
    setText("multi-result-count", error.message);
  });
});
document.querySelectorAll("#multi-search-form input, #multi-search-form select").forEach((input) => {
  input.addEventListener("input", updateMultiCommandPreview);
  input.addEventListener("change", updateMultiCommandPreview);
});
syncRange("multi-station-distance-range", "multi-station-distance");
renderMultiLegResults();
connectWebsocket();
