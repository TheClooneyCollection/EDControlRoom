const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";
const AUTH_QUERY_PARAMETER_NAME = WEB_CONFIG.authQueryParameterName || "access_token";
const queryParams = new URLSearchParams(window.location.search);
let cachedToken = "";
try { cachedToken = window.localStorage.getItem(TOKEN_STORAGE_KEY) || ""; } catch (error) { /* Private window. */ }
let accessToken = queryParams.get(AUTH_QUERY_PARAMETER_NAME) || queryParams.get("access_token") || cachedToken || WEB_CONFIG.defaultAccessToken || "";
let defaultsLoaded = false;
let searchRequest = 0;
const FIELDS = ["system", "radius_ly", "min_supply", "pad", "max_age_hours"];
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
  const params = new URLSearchParams({ commodity: field("commodity").value.trim() });
  if (!useDefaults) {
    FIELDS.forEach((key) => params.set(key, field(key).value.trim()));
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
  const offers = payload.offers || [];
  setText("results-status", offers.length ? `${offers.length} markets · ${payload.name || payload.commodity} · cheapest first` : "No matching markets. Try widening the radius or relaxing the filters.");
  const showDistance = Boolean(payload.query.reference_system);
  const rows = offers.map((offer) => {
    const price = `${escapeHtml(numberLabel(offer.buy_price))} Cr`;
    return `<tr>
      <td class="numeric">${offer.suspect_price ? `<s title="price looks fake">${price}</s>` : price}</td>
      <td class="numeric">${escapeHtml(numberLabel(offer.supply))}</td>
      <td>${escapeHtml(offer.station_name)} ${offer.is_carrier ? '<span class="carrier-badge">Carrier</span>' : ""}</td>
      <td>${escapeHtml(offer.system_name)}</td>
      ${showDistance ? `<td class="numeric">${escapeHtml(numberLabel(offer.distance_ly))}</td>` : ""}
      <td class="numeric">${escapeHtml(numberLabel(offer.dist_ls))}</td>
      <td>${escapeHtml(offer.max_pad || "?")}</td>
      <td class="${offer.age_s > 86400 ? "old-age" : ""}">${escapeHtml(ageLabel(offer.age_s))}</td>
      <td>${escapeHtml(offer.source)}</td>
    </tr>`;
  }).join("");
  field("results").innerHTML = offers.length ? `<table class="market-table"><thead><tr><th>Price</th><th>Supply</th><th>Station</th><th>System</th>${showDistance ? "<th>Distance (ly)</th>" : ""}<th>Arrival (Ls)</th><th>Pad</th><th>Age</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table>` : "";
  const reasons = { carrier: "carriers hidden", pad: "hidden by pad", supply: "hidden by supply", age: "hidden by age", radius: "hidden by radius" };
  const hidden = Object.entries(payload.hidden || {}).filter(([, count]) => count > 0)
    .map(([reason, count]) => `${numberLabel(count)} ${reasons[reason] || `hidden by ${reason}`}`);
  setText("hidden-counts", hidden.length ? `Hub: ${hidden.join(" · ")}` : "Hub: no markets hidden by filters.");
  const spansh = payload.spansh || {};
  setText("spansh-status", spansh.error ? `Spansh: ${spansh.error}` : spansh.asked
    ? `Spansh: filtered server-side, ${numberLabel(spansh.count)} matches` : "Spansh: not requested.");
}

async function search(useDefaults) {
  const request = ++searchRequest;
  const url = new URL("/api/cheapest-markets", window.location.origin);
  url.search = searchParams(useDefaults).toString();
  setText("results-status", "Searching hub and selected sources…");
  field("results").innerHTML = "";
  setText("hidden-counts", "");
  setText("spansh-status", "");
  field("search").disabled = true;
  try {
    const response = await fetch(url, { method: "GET" });
    const payload = await response.json();
    if (request !== searchRequest) return;
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    if (!defaultsLoaded) { prefill(payload.query); defaultsLoaded = true; }
    renderResults(payload);
  } catch (error) {
    if (request === searchRequest) setText("results-status", `Markets unavailable: ${error.message}`);
  } finally {
    if (request === searchRequest) field("search").disabled = false;
  }
}

field("cheapest-form").addEventListener("submit", (event) => { event.preventDefault(); search(!defaultsLoaded); });
field("access-token").value = accessToken;
field("save-token").addEventListener("click", () => {
  accessToken = field("access-token").value.trim();
  try { window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken); } catch (error) { /* This tab still works. */ }
  search(!defaultsLoaded);
});
setText("host-label", WEB_CONFIG.hostLabel || window.location.host || "-");
setText("status-runtime", WEB_CONFIG.runtimePlatform || "-");
setText("status-journal", WEB_CONFIG.journalStatus || "-");
setText("status-input-target", WEB_CONFIG.inputTargetSummary || "-");
setText("status-version", WEB_CONFIG.serverVersion ? `${WEB_CONFIG.serverVersion}${WEB_CONFIG.serverCommit ? ` (${WEB_CONFIG.serverCommit})` : ""}` : "-");
if (queryParams.has("node")) window.EDCRNode.choose(queryParams.get("node"));
field("commodity").value = queryParams.get("commodity") || "tritium";
search(true);
