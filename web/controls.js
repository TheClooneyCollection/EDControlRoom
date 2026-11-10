const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";
const AUTH_QUERY_PARAMETER_NAME = WEB_CONFIG.authQueryParameterName || "access_token";
const SERVER_DEFAULT_ACCESS_TOKEN = WEB_CONFIG.defaultAccessToken || "";
const ACTIVITY_LIMIT = 80;
const queryParams = new URLSearchParams(window.location.search);
const queryAccessToken = queryParams.get(AUTH_QUERY_PARAMETER_NAME) || queryParams.get("access_token") || "";
const cachedAccessToken = window.localStorage.getItem(TOKEN_STORAGE_KEY) || "";
let accessToken = queryAccessToken || cachedAccessToken || SERVER_DEFAULT_ACCESS_TOKEN;
let socket = null;
let reconnectTimer = null;
let clientRole = "observer";
let commandSequence = 1;
let currentRoutine = {};
let webDefaults = { galaxyMapSettle: "2.0", homeSystem: "", ...(WEB_CONFIG.webDefaults || {}) };
const pendingCommands = new Map();
const activityEntries = new Map();

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  }[char]));
}

function stripMarkup(value) {
  return String(value || "").replace(/\[\/?[a-zA-Z0-9_#= .-]+\]/g, "");
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

function applyWebConfigLabels() {
  setText("host-label", WEB_CONFIG.hostLabel || window.location.host || "-");
  setText("target-label", WEB_CONFIG.inputTargetSummary || "-");
  setText("role-label", roleLabel(WEB_CONFIG.sessionRole));
  setText("status-runtime", WEB_CONFIG.runtimePlatform || "-");
  setText("status-journal", WEB_CONFIG.journalStatus || "-");
  setText("status-input-target", WEB_CONFIG.inputTargetSummary || "-");
}

function routineLabel(routine) {
  if (!routine.routine_active) {
    return "Idle";
  }
  const name = routine.active_routine_name || "Running";
  if (routine.haul_paused) {
    return `${name} (paused)`;
  }
  if (routine.haul_pause_requested) {
    return `${name} (pause requested)`;
  }
  return name;
}

function updateButtons() {
  const operator = clientRole === "active_operator";
  const active = Boolean(currentRoutine.routine_active);
  const haulActive = active && currentRoutine.active_routine_name === "haul";
  document.querySelectorAll("button[data-needs-idle]").forEach((button) => {
    button.disabled = !operator || active;
  });
  document.querySelectorAll("button[data-needs-active]").forEach((button) => {
    button.disabled = !operator || !active;
  });
  document.querySelectorAll("button[data-needs-haul]").forEach((button) => {
    button.disabled = !operator || !haulActive;
  });
  if (!webDefaults.homeSystem) {
    document.getElementById("nav-plot-home").disabled = true;
  }
  const instant = document.getElementById("toggle-instant");
  instant.disabled = !operator;
  instant.setAttribute("aria-checked", currentRoutine.instant_mode ? "true" : "false");
  const label = active ? `Busy: ${routineLabel(currentRoutine)}` : "Idle";
  document.querySelectorAll(".busy-state").forEach((element) => {
    element.textContent = label;
    element.classList.toggle("busy", active);
  });
  setText("summary-routine", routineLabel(currentRoutine));
}

function addActivityEntry(entry) {
  const id = String(entry.entry_id || `entry-${activityEntries.size + 1}`);
  activityEntries.set(id, {
    timestamp: entry.timestamp || new Date().toISOString(),
    message_text: entry.message_text || "",
    severity: entry.severity || "info"
  });
  while (activityEntries.size > ACTIVITY_LIMIT) {
    activityEntries.delete(activityEntries.keys().next().value);
  }
}

function addLocalActivity(message, severity) {
  addActivityEntry({ entry_id: `local-${Date.now()}-${Math.random()}`, message_text: message, severity });
  renderActivityLog();
}

function activityTime(timestamp) {
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? "--:--:--" : date.toLocaleTimeString([], { hour12: false });
}

function badgeClass(severity) {
  if (severity === "warning" || severity === "error") {
    return "warning";
  }
  return severity === "success" ? "success" : "neutral";
}

function renderActivityLog() {
  const list = document.getElementById("activity-list");
  const entries = Array.from(activityEntries.values()).reverse();
  setText("activity-status", entries.length ? `${entries.length} entries` : "No entries");
  if (!entries.length) {
    list.innerHTML = `<div class="activity-row"><div class="activity-time mono">--:--:--</div><div class="activity-text">Waiting for backend activity.</div><span class="badge neutral">Log</span></div>`;
    return;
  }
  list.innerHTML = entries.map((entry) => `
    <div class="activity-row">
      <div class="activity-time mono">${escapeHtml(activityTime(entry.timestamp))}</div>
      <div class="activity-text">${escapeHtml(stripMarkup(entry.message_text))}</div>
      <span class="badge ${badgeClass(entry.severity)}">${escapeHtml(entry.severity)}</span>
    </div>
  `).join("");
}

function applyHydrate(payload) {
  const serverStatus = payload.server_status || {};
  const ship = payload.ship || {};
  setText("status-runtime", serverStatus.runtime_platform || WEB_CONFIG.runtimePlatform || "-");
  setText("status-journal", serverStatus.journal_source_status || WEB_CONFIG.journalStatus || "-");
  setText("status-input-target", serverStatus.input_target_summary || WEB_CONFIG.inputTargetSummary || "-");
  setText("target-label", serverStatus.input_target_summary || WEB_CONFIG.inputTargetSummary || "-");
  setText("summary-system", ship.system || "-");
  setText("summary-station", ship.station || "-");
  setText("summary-cargo", `${ship.cargo_count || 0} / ${ship.cargo_capacity || 0} t`);
  webDefaults = { ...webDefaults, ...(serverStatus.web_form_defaults || {}) };
  setText("nav-home-system", webDefaults.homeSystem || "not set");
  currentRoutine = payload.routine || {};
  updateButtons();
  activityEntries.clear();
  ((payload.activity_log || {}).entries || []).forEach(addActivityEntry);
  renderActivityLog();
}

function websocketUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const params = new URLSearchParams({ client_name: "web-controls" });
  params.set(AUTH_QUERY_PARAMETER_NAME, accessToken);
  return `${protocol}//${window.location.host}/session?${params.toString()}`;
}

function isSocketReady() {
  return socket && socket.readyState === WebSocket.OPEN;
}

function sendCommand(messageType, payload) {
  if (!isSocketReady()) {
    return Promise.reject(new Error("Websocket is not connected."));
  }
  const messageId = `web-controls-${commandSequence++}`;
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
    addLocalActivity("Enter and save an access token to use the controls.", "warning");
    return;
  }
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (socket) {
    socket.close();
  }
  const ws = new WebSocket(websocketUrl());
  socket = ws;
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.message_type === "event.connection_ready") {
      clientRole = message.payload.client_role || "observer";
      setText("role-label", roleLabel(clientRole));
      updateButtons();
      return;
    }
    if (message.message_type === "control_room.hydrate") {
      applyHydrate(message.payload || {});
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
  ws.addEventListener("close", () => {
    if (socket !== ws) {
      return;
    }
    clientRole = "observer";
    setText("role-label", "disconnected");
    updateButtons();
    reconnectTimer = window.setTimeout(connectWebsocket, 3000);
  });
}

function submitInput(rawInput, { skipDelay = false } = {}) {
  sendCommand("command.submit_input", { raw_input: rawInput, skip_delay: skipDelay })
    .catch((error) => addLocalActivity(error.message, "warning"));
}

function tradeCommand(verb) {
  const commodity = document.getElementById("trade-commodity").value.trim();
  const amount = document.getElementById("trade-amount").value.trim() || "max";
  if (!commodity) {
    addLocalActivity(`Enter a commodity to ${verb}.`, "warning");
    return;
  }
  submitInput(`${verb} ${commodity} ${amount}`);
}

function galaxyMapSettle() {
  const value = Number(webDefaults.galaxyMapSettle);
  return Number.isFinite(value) && value > 0 ? value : 2;
}

function plotDestination(destination) {
  if (!destination) {
    addLocalActivity("Enter a system to plot a route to.", "warning");
    return;
  }
  sendCommand("command.dispatch_destination", {
    destination,
    galaxy_map_settle: galaxyMapSettle(),
    skip_delay: false,
    raw_command: `web dest ${destination}`
  })
    .then(() => addLocalActivity(`Plotting route to ${destination}.`, "success"))
    .catch((error) => addLocalActivity(error.message, "warning"));
}

function startTravel() {
  const system = document.getElementById("nav-system").value.trim();
  const station = document.getElementById("nav-station").value.trim();
  if (!system) {
    addLocalActivity("Enter a system to travel to.", "warning");
    return;
  }
  sendCommand("command.dispatch_travel", {
    system,
    station,
    on_land: Boolean(station) && document.getElementById("nav-on-land").checked,
    raw_command: station ? `web travel ${system} / ${station}` : `web travel ${system}`
  })
    .then(() => addLocalActivity(station ? `Travel accepted for ${station}.` : `Travel accepted for ${system}.`, "success"))
    .catch((error) => addLocalActivity(error.message, "warning"));
}

function stopRoutine(mode) {
  sendCommand("command.cancel_active_routine", { mode })
    .catch((error) => addLocalActivity(error.message, "warning"));
}

applyWebConfigLabels();
setText("nav-home-system", webDefaults.homeSystem || "not set");
updateButtons();
renderActivityLog();
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
document.querySelectorAll("button[data-command]").forEach((button) => {
  // Routine controls act on the running routine, so they skip the launch delay.
  const skipDelay = !button.hasAttribute("data-needs-idle");
  button.addEventListener("click", () => submitInput(button.dataset.command, { skipDelay }));
});
document.getElementById("nav-plot").addEventListener("click", () => {
  plotDestination(document.getElementById("nav-system").value.trim());
});
document.getElementById("nav-travel").addEventListener("click", startTravel);
document.getElementById("nav-plot-home").addEventListener("click", () => plotDestination(webDefaults.homeSystem));
document.getElementById("nav-set-home").addEventListener("click", () => {
  submitInput(`home set ${document.getElementById("nav-system").value.trim()}`.trim(), { skipDelay: true });
});
document.getElementById("trade-buy").addEventListener("click", () => tradeCommand("buy"));
document.getElementById("trade-sell").addEventListener("click", () => tradeCommand("sell"));
document.getElementById("stop-after-run").addEventListener("click", () => stopRoutine("after_run"));
document.querySelectorAll("button[data-stop-now]").forEach((button) => {
  button.addEventListener("click", () => stopRoutine("now"));
});
document.getElementById("toggle-instant").addEventListener("click", () => {
  submitInput(`instant ${currentRoutine.instant_mode ? "off" : "on"}`, { skipDelay: true });
});
connectWebsocket();
