const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";
const AUTH_QUERY_PARAMETER_NAME = WEB_CONFIG.authQueryParameterName || "access_token";
const queryParams = new URLSearchParams(window.location.search);
let cachedToken = "";
try { cachedToken = window.localStorage.getItem(TOKEN_STORAGE_KEY) || ""; } catch (error) { /* Private window. */ }
let accessToken = queryParams.get(AUTH_QUERY_PARAMETER_NAME) || queryParams.get("access_token") || cachedToken || WEB_CONFIG.defaultAccessToken || "";
let defaultsLoaded = false;
let formEdited = false;
let searchRequest = 0;
const FIELDS = ["system", "radius_ly", "pad"];
const field = (id) => document.getElementById(id);
const setText = (id, value) => { field(id).textContent = value; };

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[char]));
}

function numberLabel(value) {
  return value == null ? "?" : Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function ageLabel(seconds) {
  if (seconds == null) return "unknown";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
  if (seconds < 172800) return `${Math.floor(seconds / 3600)} h`;
  return `${Math.floor(seconds / 86400)} d`;
}

function prefill(query) {
  FIELDS.forEach((key) => { field(key).value = query[key === "system" ? "reference_system" : key] ?? ""; });
  field("carriers").checked = Boolean(query.include_carriers);
  field("spansh").checked = Boolean(query.use_spansh);
}

function searchParams(useDefaults) {
  const params = new URLSearchParams({ service: field("service").value === "custom" ? field("custom-service").value.trim() : field("service").value });
  if (!useDefaults) {
    FIELDS.forEach((key) => {
      if (key !== "pad" || field(key).value) params.set(key, field(key).value.trim());
    });
    params.set("carriers", field("carriers").checked ? "1" : "0");
    params.set("spansh", field("spansh").checked ? "1" : "0");
  }
  window.EDCRNode.addTo(params);
  // A bookmarked explicit node takes precedence over the browser's saved choice.
  if (queryParams.has("node")) params.set("node", queryParams.get("node"));
  if (accessToken) params.set(AUTH_QUERY_PARAMETER_NAME, accessToken);
  return params;
}

function renderResults(payload) {
  const stations = payload.stations || [];
  const limit = payload.query.limit;
  const shown = limit && stations.length >= limit ? `First ${stations.length} stations` : `${stations.length} stations`;
  setText("results-status", stations.length ? `${shown} · ${payload.label || payload.service} · nearest first` : "No matching stations. Try widening the radius or relaxing the filters.");
  const rows = stations.map((station) => `<tr>
    <td>${escapeHtml(station.station_name)} ${station.is_carrier ? '<span class="carrier-badge">Carrier</span>' : ""}</td>
    <td>${escapeHtml(station.system_name)}</td>
    <td class="numeric">${escapeHtml(numberLabel(station.distance_ly))}</td>
    <td class="numeric">${escapeHtml(numberLabel(station.dist_ls))}</td>
    <td>${escapeHtml(station.max_pad || "?")}</td>
    <td>${escapeHtml(station.station_type || "Unknown")}</td>
    <td>${escapeHtml(ageLabel(station.age_s))}</td>
    <td>${escapeHtml(station.source)}</td>
  </tr>`).join("");
  field("results").innerHTML = stations.length ? `<table class="service-table"><thead><tr><th>Station</th><th>System</th><th>Distance (ly)</th><th>Arrival (Ls)</th><th>Pad</th><th>Type</th><th>Services age</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table>` : "";
  const reasons = { carrier: "carriers hidden", pad: "hidden by pad", radius: "hidden by radius" };
  const hidden = Object.entries(payload.hidden || {}).filter(([, count]) => count > 0)
    .map(([reason, count]) => `${numberLabel(count)} ${reasons[reason] || `hidden by ${reason}`}`);
  setText("hidden-counts", hidden.length ? `Hub: ${hidden.join(" · ")}` : "Hub: no stations hidden by filters.");
  setText("coverage-status", `Hub knows services for ${numberLabel(payload.hub_known)} stations.`);
  const spansh = payload.spansh || {};
  setText("spansh-status", spansh.error ? `Spansh: ${spansh.error}` : spansh.asked
    ? `Spansh: filtered server-side, ${numberLabel(spansh.count)} matches` : "Spansh: not requested.");
}

async function search(useDefaults) {
  const request = ++searchRequest;
  const url = new URL("/api/nearest-services", window.location.origin);
  url.search = searchParams(useDefaults).toString();
  setText("results-status", "Searching hub and selected sources…");
  field("results").innerHTML = "";
  setText("hidden-counts", "");
  setText("coverage-status", "");
  setText("spansh-status", "");
  field("search").disabled = true;
  try {
    const response = await fetch(url, { method: "GET" });
    const payload = await response.json();
    if (request !== searchRequest) return;
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    if (!defaultsLoaded && !formEdited) prefill(payload.query);
    defaultsLoaded = true;
    renderResults(payload);
  } catch (error) {
    if (request === searchRequest) setText("results-status", `Services unavailable: ${error.message}`);
  } finally {
    if (request === searchRequest) field("search").disabled = false;
  }
}

field("services-form").addEventListener("input", () => { formEdited = true; });
field("services-form").addEventListener("change", () => { formEdited = true; });
field("services-form").addEventListener("submit", (event) => { event.preventDefault(); search(false); });
field("access-token").value = accessToken;
field("save-token").addEventListener("click", () => {
  accessToken = field("access-token").value.trim();
  try { window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken); } catch (error) { /* This tab still works. */ }
  search(!defaultsLoaded && !formEdited);
});
setText("host-label", WEB_CONFIG.hostLabel || window.location.host || "-");
setText("status-runtime", WEB_CONFIG.runtimePlatform || "-");
setText("status-journal", WEB_CONFIG.journalStatus || "-");
setText("status-input-target", WEB_CONFIG.inputTargetSummary || "-");
setText("status-version", WEB_CONFIG.serverVersion ? `${WEB_CONFIG.serverVersion}${WEB_CONFIG.serverCommit ? ` (${WEB_CONFIG.serverCommit})` : ""}` : "-");
if (queryParams.has("node")) window.EDCRNode.choose(queryParams.get("node"));
function updateCustomService() {
  const custom = field("service").value === "custom";
  field("custom-service-field").hidden = !custom;
  field("custom-service").disabled = !custom;
  field("custom-service").required = custom;
}
field("service").addEventListener("change", updateCustomService);
const initialService = queryParams.get("service") || "carriermanagement";
if (Array.from(field("service").options).some((option) => option.value === initialService && option.value !== "custom")) {
  field("service").value = initialService;
} else {
  field("service").value = "custom";
  field("custom-service").value = initialService;
}
updateCustomService();
search(true);
