const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";
const AUTH_QUERY_PARAMETER_NAME = WEB_CONFIG.authQueryParameterName || "access_token";
const SERVER_DEFAULT_ACCESS_TOKEN = WEB_CONFIG.defaultAccessToken || "";
const queryParams = new URLSearchParams(window.location.search);
const queryAccessToken = queryParams.get(AUTH_QUERY_PARAMETER_NAME) || queryParams.get("access_token") || "";
const cachedAccessToken = window.localStorage.getItem(TOKEN_STORAGE_KEY) || "";
let accessToken = queryAccessToken || cachedAccessToken || SERVER_DEFAULT_ACCESS_TOKEN;
let view = "near";
// Either a jump count (measured with the laden jump range) or a flat light-year range.
let range = { jumps: 4 };
let searchRequest = 0;
let shownRoutes = [];
let lastListener = null;
let eddnOffLogged = false;
const EDDN_LOG_LIMIT = 60;

const FIELD_PARAMS = [
  ["route-system", "system"],
  ["route-laden", "laden_jump_range_ly"],
  ["route-capacity", "capacity"],
  ["route-min-supply", "min_supply"],
  ["route-station-ls", "max_station_distance_ls"],
  ["route-age", "max_age_hours"]
];

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

function serverVersionLabel(version, commit) {
  if (!version) {
    return "-";
  }
  return commit ? `${version} (${commit})` : version;
}

function applyWebConfigLabels() {
  setText("host-label", WEB_CONFIG.hostLabel || window.location.host || "-");
  setText("status-runtime", WEB_CONFIG.runtimePlatform || "-");
  setText("status-journal", WEB_CONFIG.journalStatus || "-");
  setText("status-input-target", WEB_CONFIG.inputTargetSummary || "-");
  setText("status-version", serverVersionLabel(WEB_CONFIG.serverVersion, WEB_CONFIG.serverCommit));
}

function millions(value) {
  return `${(Number(value || 0) / 1e6).toFixed(1)}M`;
}

function count(value) {
  return Number(value || 0).toLocaleString();
}

function duration(seconds) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(Math.round(seconds % 60)).padStart(2, "0")}`;
}

function ageLabel(seconds) {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.round(minutes / 60);
  return hours < 48 ? `${hours} h` : `${Math.round(hours / 24)} d`;
}

async function fetchJson(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
  if (accessToken) url.searchParams.set(AUTH_QUERY_PARAMETER_NAME, accessToken);
  const response = await fetch(url, { method: "GET" });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
  return payload;
}

function clockTime(seconds) {
  return new Date(seconds * 1000).toLocaleTimeString([], { hour12: false });
}

function appendLog(text) {
  const log = document.getElementById("eddn-log");
  if (log.dataset.started !== "yes") {
    log.innerHTML = "";
    log.dataset.started = "yes";
  }
  const item = document.createElement("li");
  item.innerHTML = `<time>${escapeHtml(clockTime(Date.now() / 1000))}</time>${escapeHtml(text)}`;
  log.prepend(item);
  while (log.children.length > EDDN_LOG_LIMIT) log.lastElementChild.remove();
}

// One line per check: what arrived since the last check, then the database totals.
function statusLogLine(listener, store) {
  const state = listener.connected ? "connected" : "disconnected";
  const delta = (key) => listener[key] - (lastListener ? lastListener[key] : listener[key]);
  const since = lastListener
    ? `+${count(delta("messages"))} msgs, +${count(delta("markets"))} market updates`
    : `${count(listener.messages)} msgs, ${count(listener.markets)} market updates`;
  const errors = lastListener && delta("errors") > 0 ? `, +${count(delta("errors"))} errors` : "";
  const reconnect = lastListener && delta("reconnects") > 0 ? ", reconnected" : "";
  const newest = store.newest_market_at == null ? "-" : clockTime(store.newest_market_at);
  return `${state}: ${since}${errors}${reconnect} | db ${count(store.markets)} markets, ` +
    `${count(store.prices)} prices, ${count(store.systems)} systems, newest ${newest}`;
}

async function refreshStatus() {
  try {
    const status = await fetchJson("/api/eddn-status");
    if (!status.enabled) {
      setText("eddn-label", "off");
      if (!eddnOffLogged) appendLog("EDDN is off: set [eddn] enabled = true in config.toml and restart the server.");
      eddnOffLogged = true;
      return;
    }
    const state = status.listener.connected ? "live" : "disconnected";
    setText("eddn-label", `${state}, ${count(status.store.markets)} markets`);
    appendLog(statusLogLine(status.listener, status.store));
    lastListener = status.listener;
  } catch (error) {
    setText("eddn-label", "unavailable");
    appendLog(`Status check failed: ${error.message}`);
  }
}

function stationCell(station) {
  const details = [station.system, station.dist_ls == null ? null : `${count(Math.round(station.dist_ls))} Ls`]
    .filter(Boolean).join(" · ");
  return `${escapeHtml(station.station)}<span class="route-sub">${escapeHtml(details)}</span>`;
}

function legCell(leg) {
  if (!leg) {
    return `<span class="route-sub">empty</span>`;
  }
  const detail = `${count(leg.profit_per_ton)}/t × ${count(leg.tons)} t · supply ${count(leg.supply)}`;
  return `${escapeHtml(leg.name)}<span class="route-sub">${escapeHtml(detail)}</span>`;
}

// /haul imports a route from its #route= fragment once it connects, as /markets does.
function haulUrl(tradeRoute) {
  return `/haul#route=${encodeURIComponent(JSON.stringify(tradeRoute))}`;
}

function renderRoutes(payload) {
  const table = document.getElementById("route-table");
  const query = payload.query;
  const reach = range.jumps ? `${query.jumps} jumps (${query.max_route_ly.toFixed(1)} Ly)` : `${query.max_route_ly} Ly`;
  const where = query.view === "near" ? `near ${query.system}` : "anywhere";
  setText("routes-status", `${payload.routes.length} routes ${where}, ${reach}, from ${count(payload.markets_considered)} markets`);
  if (!payload.routes.length) {
    table.innerHTML = `<p class="empty-note">No profitable round trips match these filters.</p>`;
    return;
  }
  shownRoutes = payload.routes;
  const rows = payload.routes.map((route, index) => `
    <tr>
      <td data-label="Stations"><div>${stationCell(route.station_1)}</div><div>${stationCell(route.station_2)}</div></td>
      <td data-label="Out">${legCell(route.outbound)}</td>
      <td data-label="Back">${legCell(route.inbound)}</td>
      <td data-label="Per hour" class="profit">${millions(route.profit_per_hour)}</td>
      <td data-label="Per trip">${millions(route.profit_per_trip)}</td>
      <td data-label="Jumps">${route.jumps}<span class="route-sub">${route.distance_ly} Ly</span></td>
      <td data-label="Est. trip">${duration(route.trip_s)}</td>
      <td data-label="Data age">${ageLabel(Math.max(route.station_1.age_s, route.station_2.age_s))}</td>
      <td data-label="Haul">${route.trade_route
        ? `<div class="route-actions">
            <a class="btn" href="${escapeHtml(haulUrl(route.trade_route))}">Open in haul</a>
            <button class="btn" type="button" data-copy-route="${index}">Copy</button>
          </div>`
        : `<span class="route-sub">name unknown</span>`}</td>
    </tr>`).join("");
  table.innerHTML = `
    <table class="route-table">
      <thead><tr>
        <th>Stations</th><th>Out (1 → 2)</th><th>Back (2 → 1)</th>
        <th>Per hour</th><th>Per trip</th><th>Jumps</th><th>Est. trip</th><th>Data age</th><th>Haul</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

async function search() {
  const request = ++searchRequest;
  const params = { view };
  FIELD_PARAMS.forEach(([id, key]) => {
    const value = document.getElementById(id).value.trim();
    if (value) params[key] = value;
  });
  if (view === "global") delete params.system;
  if (range.jumps) params.jumps = range.jumps;
  if (range.ly) params.max_route_ly = range.ly;
  params.surface = document.getElementById("route-surface").checked ? "yes" : "no";
  params.carriers = document.getElementById("route-carriers").checked ? "yes" : "no";
  setText("routes-status", "Searching");
  try {
    const payload = await fetchJson("/api/eddn-routes", params);
    if (request === searchRequest) renderRoutes(payload);
  } catch (error) {
    if (request !== searchRequest) return;
    setText("routes-status", "Search failed");
    document.getElementById("route-table").innerHTML = `<p class="empty-note">${escapeHtml(error.message)}</p>`;
  }
}

// Copies the route as JSON for the /haul "Copy / paste route" box.
async function copyRoute(button) {
  const route = shownRoutes[Number(button.dataset.copyRoute)];
  const text = JSON.stringify(route.trade_route, null, 2);
  try {
    await navigator.clipboard.writeText(text);
  } catch (error) {
    // Plain-http LAN pages have no clipboard API; fall back to a selected textarea.
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  button.textContent = "Copied";
}

function pressOnly(selector, button) {
  document.querySelectorAll(selector).forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
}

applyWebConfigLabels();
// Start from the haul search surface choice (`use_surface_stations`) so surface ports are not hidden by default.
document.getElementById("route-surface").checked = (WEB_CONFIG.webDefaults || {}).allowPlanetary === "true";
document.getElementById("access-token").value = accessToken;
document.getElementById("save-token").addEventListener("click", () => {
  accessToken = document.getElementById("access-token").value.trim();
  if (accessToken) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
  refreshStatus();
  search();
});
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => {
  view = button.dataset.view;
  pressOnly("[data-view]", button);
  search();
}));
document.querySelectorAll("[data-jumps], [data-range]").forEach((button) => button.addEventListener("click", () => {
  range = button.dataset.jumps ? { jumps: Number(button.dataset.jumps) } : { ly: Number(button.dataset.range) };
  pressOnly("[data-jumps], [data-range]", button);
  search();
}));
document.getElementById("routes-search").addEventListener("click", search);
document.getElementById("route-table").addEventListener("click", (event) => {
  const button = event.target.closest("[data-copy-route]");
  if (button) copyRoute(button);
});
refreshStatus();
search();
window.setInterval(refreshStatus, 10000);
