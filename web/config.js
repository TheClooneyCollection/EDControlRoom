const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";
const AUTH_QUERY_PARAMETER_NAME = WEB_CONFIG.authQueryParameterName || "access_token";
const queryParams = new URLSearchParams(window.location.search);
let accessToken = queryParams.get(AUTH_QUERY_PARAMETER_NAME) || queryParams.get("access_token") ||
  window.localStorage.getItem(TOKEN_STORAGE_KEY) || WEB_CONFIG.defaultAccessToken || "";

// The trip time fields in the order of a leg; `fit: false` fields are never fitted.
const FIELDS = [
  { name: "docked_s", label: "Docked, per station (s)" },
  { name: "travel_base_s", label: "Undock and dock again (s)" },
  { name: "first_jump_s", label: "First jump (s)" },
  { name: "per_extra_jump_s", label: "Each further jump (s)" },
  { name: "supercruise_coeff", label: "Supercruise coeff (s per Ls^1/3)" },
  { name: "surface_extra_s", label: "Surface station landing (s)" },
  { name: "unknown_dist_ls", label: "Ls when a station's is unknown", fit: false }
];
let source = "config";

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
  }[char]));
}

function applyWebConfigLabels() {
  setText("host-label", WEB_CONFIG.hostLabel || window.location.host || "-");
  setText("status-runtime", WEB_CONFIG.runtimePlatform || "-");
  setText("status-journal", WEB_CONFIG.journalStatus || "-");
  setText("status-input-target", WEB_CONFIG.inputTargetSummary || "-");
  const version = WEB_CONFIG.serverVersion;
  setText("status-version", version ? (WEB_CONFIG.serverCommit ? `${version} (${WEB_CONFIG.serverCommit})` : version) : "-");
}

async function request(method, body) {
  const url = new URL("/api/time-model", window.location.origin);
  if (accessToken) url.searchParams.set(AUTH_QUERY_PARAMETER_NAME, accessToken);
  // On a hub, the fit is for the ship of the node picked in the sidebar (nav.js).
  if (method === "GET") window.EDCRNode.addTo(url.searchParams);
  const response = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
  return payload;
}

function number(value, digits = 1) {
  return Number(value).toFixed(digits).replace(/\.0+$/, "");
}

// One leg with `jumps` jumps to an orbital station `ls` from the star, as the server's TimeModel.leg_s.
function legSeconds(model, jumps, ls) {
  const jump = jumps > 0 ? model.first_jump_s + (jumps - 1) * model.per_extra_jump_s : 0;
  return model.docked_s + model.travel_base_s + jump + model.supercruise_coeff * Math.cbrt(ls);
}

function scopeLabel(fit) {
  if (fit.scope === "ship") return `ship ${fit.ship_id}`;
  if (fit.scope === "pooled") return "every ship pooled";
  return "configured values (too few legs)";
}

function showSource(value) {
  source = value;
  document.querySelectorAll("[data-source]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.source === value));
  });
}

function render(payload) {
  const fit = payload.fitted;
  const editable = payload.editable;
  document.getElementById("trip-time-rows").innerHTML = FIELDS.map((field) => {
    const fitted = fit.fitted.includes(field.name);
    const fittedCell = field.fit === false ? `<span class="kept">-</span>` :
      fitted ? number(fit.model[field.name], 2) : `<span class="kept" title="Too few legs to fit it">configured</span>`;
    const legs = field.fit === false ? "" : (fit.support[field.name] ?? 0).toLocaleString();
    return `<tr>
      <td>${escapeHtml(field.label)}</td>
      <td><input class="field mono" data-field="${field.name}" inputmode="decimal" value="${number(payload.configured[field.name], 2)}"${editable ? "" : " disabled"}></td>
      <td class="mono">${fittedCell}</td>
      <td class="mono">${legs}</td>
    </tr>`;
  }).join("");
  document.querySelectorAll("[data-source], #trip-time-save").forEach((button) => { button.disabled = !editable; });
  showSource(payload.source);
  const span = `the last ${number(payload.fit_days)} days`;
  const used = fit.scope === "config"
    ? `No fit yet: ${fit.legs} clean legs in ${span}.`
    : `Fitted for ${scopeLabel(fit)} from ${fit.legs} legs and ${fit.stops} docked stops in ${span}.`;
  const example = `A 1-jump leg to an orbital station 300 Ls out: configured ${Math.round(legSeconds(payload.configured, 1, 300))} s, ` +
    `fitted ${Math.round(legSeconds(fit.model, 1, 300))} s.`;
  const where = editable ? "" : ` These settings live on hub ${payload.hub || "the hub"}; change them on its /config page.`;
  document.getElementById("trip-time-fit").textContent = `${used} ${example}${where}`;
  const active = payload.active.scope === "config" ? "configured values" : `fitted for ${scopeLabel(payload.active)}`;
  setText("trip-time-status", `In use: ${active}`);
}

async function load() {
  try {
    render(await request("GET"));
  } catch (error) {
    setText("trip-time-status", error.message);
  }
}

async function save() {
  const configured = {};
  for (const input of document.querySelectorAll("[data-field]")) {
    const value = Number(input.value);
    if (input.value.trim() === "" || !Number.isFinite(value) || value < 0) {
      setText("trip-time-status", `${input.dataset.field} must be zero or a positive number`);
      input.focus();
      return;
    }
    configured[input.dataset.field] = value;
  }
  setText("trip-time-status", "Saving");
  try {
    render(await request("POST", { source, configured }));
    setText("trip-time-status", `Saved to config.toml. ${document.getElementById("trip-time-status").textContent}`);
  } catch (error) {
    setText("trip-time-status", error.message);
  }
}

applyWebConfigLabels();
document.getElementById("access-token").value = accessToken;
document.getElementById("save-token").addEventListener("click", () => {
  accessToken = document.getElementById("access-token").value.trim();
  if (accessToken) window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
  else window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  load();
});
document.querySelectorAll("[data-source]").forEach((button) => button.addEventListener("click", () => {
  showSource(button.dataset.source);
}));
document.getElementById("trip-time-save").addEventListener("click", save);
load();
