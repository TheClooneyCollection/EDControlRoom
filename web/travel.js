// Travel page shell: owns the websocket and exposes the same window.EDCR_HAUL bridge and edcr:* events the
// haul page used to provide, so active-route.js and route-compare.js work unchanged.
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
let commandSequence = 1;
let webDefaults = { galaxyMapSettle: "2.0", ...(WEB_CONFIG.webDefaults || {}) };
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
  return String(value || "").replace(/\[\/?[a-zA-Z0-9_#= .-]*\]/g, "");
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

function serverVersionLabel(version, commit) {
  if (!version) {
    return "-";
  }
  return commit ? `${version} (${commit})` : version;
}

function applyWebConfigLabels() {
  setText("host-label", WEB_CONFIG.hostLabel || window.location.host || "-");
  setText("target-label", WEB_CONFIG.inputTargetSummary || "-");
  setText("role-label", roleLabel(WEB_CONFIG.sessionRole));
  setText("status-runtime", WEB_CONFIG.runtimePlatform || "-");
  setText("status-journal", WEB_CONFIG.journalStatus || "-");
  setText("status-input-target", WEB_CONFIG.inputTargetSummary || "-");
  setText("status-version", serverVersionLabel(WEB_CONFIG.serverVersion, WEB_CONFIG.serverCommit));
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

function galmapSettleTime() {
  const value = Number(webDefaults.galaxyMapSettle);
  return Number.isFinite(value) && value > 0 ? value : 2;
}

function applyHydrate(payload) {
  const serverStatus = payload.server_status || {};
  const ship = payload.ship || {};
  setText("status-runtime", serverStatus.runtime_platform || WEB_CONFIG.runtimePlatform || "-");
  setText("status-journal", serverStatus.journal_source_status || WEB_CONFIG.journalStatus || "-");
  setText("status-input-target", serverStatus.input_target_summary || WEB_CONFIG.inputTargetSummary || "-");
  setText("status-version", serverVersionLabel(serverStatus.server_version, serverStatus.server_commit));
  setText("target-label", serverStatus.input_target_summary || WEB_CONFIG.inputTargetSummary || "-");
  setText("summary-system", ship.system || "-");
  setText("summary-destination", ship.destination_system || "-");
  webDefaults = { ...webDefaults, ...(serverStatus.web_form_defaults || {}) };
  activityEntries.clear();
  ((payload.activity_log || {}).entries || []).forEach(addActivityEntry);
  renderActivityLog();
  window.EDCR_HAUL.shipState = {
    system: ship.system || "",
    supercharge_multiplier: ship.supercharge_multiplier || null,
    max_jump_range_ly: ship.max_jump_range_ly || null,
  };
  window.dispatchEvent(new CustomEvent("edcr:ship-state", { detail: window.EDCR_HAUL.shipState }));
  window.EDCR_HAUL.lastHydrate = payload;
  window.dispatchEvent(new CustomEvent("edcr:hydrate", { detail: payload }));
}

function websocketUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const params = new URLSearchParams({ client_name: "web-travel" });
  params.set(AUTH_QUERY_PARAMETER_NAME, accessToken);
  // On a hub, the node picked in the sidebar (nav.js).
  window.EDCRNode.addTo(params);
  return `${protocol}//${window.location.host}/session?${params.toString()}`;
}

function sendCommand(messageType, payload) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return Promise.reject(new Error("Websocket is not connected."));
  }
  const messageId = `web-travel-${commandSequence++}`;
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
    addLocalActivity("Enter and save an access token to use travel.", "warning");
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
      setText("role-label", roleLabel(message.payload.client_role));
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
    setText("role-label", "disconnected");
    reconnectTimer = window.setTimeout(connectWebsocket, 3000);
  });
}

window.EDCR_HAUL = window.EDCR_HAUL || {};
window.EDCR_HAUL.sendCommand = sendCommand;
window.EDCR_HAUL.galmapSettleTime = galmapSettleTime;

applyWebConfigLabels();
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
connectWebsocket();
