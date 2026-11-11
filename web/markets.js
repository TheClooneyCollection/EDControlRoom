const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";
const AUTH_QUERY_PARAMETER_NAME = WEB_CONFIG.authQueryParameterName || "access_token";
const SERVER_DEFAULT_ACCESS_TOKEN = WEB_CONFIG.defaultAccessToken || "";
const queryParams = new URLSearchParams(window.location.search);
const queryAccessToken = queryParams.get(AUTH_QUERY_PARAMETER_NAME) || queryParams.get("access_token") || "";
const cachedAccessToken = window.localStorage.getItem(TOKEN_STORAGE_KEY) || "";
let accessToken = queryAccessToken || cachedAccessToken || SERVER_DEFAULT_ACCESS_TOKEN;
let markets = [];
let selectedMarketId = null;
let sortKey = "name";
let sortDescending = false;
let compareRequest = 0;
let shownTradeRoute = null;
let shownComparison = null;
let chosenDeals = { outbound: null, inbound: null };
const WINDOW_STORAGE_KEY = "edcr.markets.measuredWindow";
// Measured profit per hour window: the server's MEASURED_WINDOWS, 7 days by default.
const MEASURED_WINDOWS = [["48h", "48h"], ["7d", "7 days"], ["30d", "30 days"], ["all", "All"]];
let measuredWindow = "7d";
try {
  const saved = window.localStorage.getItem(WINDOW_STORAGE_KEY);
  if (MEASURED_WINDOWS.some(([value]) => value === saved)) measuredWindow = saved;
} catch (error) {
  // Storage can be blocked; the default window still works.
}

const COMMODITY_COLUMNS = [
  { key: "name", label: "Commodity" },
  { key: "buy_price", label: "Buy" },
  { key: "sell_price", label: "Sell" },
  { key: "stock", label: "Stock" },
  { key: "demand", label: "Demand" },
  { key: "mean_price", label: "Mean" }
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

function credits(value) {
  return `${Number(value || 0).toLocaleString()} Cr`;
}

function count(value) {
  return Number(value || 0).toLocaleString();
}

function ageLabel(timestamp) {
  const time = Date.parse(timestamp);
  if (Number.isNaN(time)) {
    return "unknown age";
  }
  const minutes = Math.max(0, Math.round((Date.now() - time) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} days ago`;
}

function marketLabel(market) {
  return `${market.station || "?"} (${market.system || "?"})`;
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

async function refreshMarkets() {
  setText("markets-status", "Loading");
  try {
    const payload = await fetchJson("/api/recent-markets");
    markets = payload.markets || [];
    const capacity = document.getElementById("deal-capacity");
    if (!capacity.value && payload.cargo_capacity) capacity.value = String(payload.cargo_capacity);
    setText("cargo-label", payload.cargo_capacity ? `${payload.cargo_capacity} t` : "-");
    if (!markets.some((market) => market.market_id === selectedMarketId)) {
      selectedMarketId = markets.length ? markets[0].market_id : null;
    }
    setText("markets-status", markets.length
      ? `${markets.length} station${markets.length === 1 ? "" : "s"}, newest first`
      : "No markets yet. Open the commodities market at a station.");
    renderMarketList();
    renderMarketTable();
    renderDealPickers();
    refreshComparison();
  } catch (error) {
    setText("markets-status", `Markets unavailable: ${error.message}`);
  }
}

function renderMarketList() {
  document.getElementById("market-list").innerHTML = markets.map((market) => `
    <button class="market-pick" type="button" data-market-id="${market.market_id}" aria-pressed="${market.market_id === selectedMarketId}">
      <span class="market-pick-name">${escapeHtml(market.station || "?")}</span>
      <span class="market-pick-sub">${escapeHtml(market.system || "?")} · ${escapeHtml(market.station_type || "station")} · ${escapeHtml(ageLabel(market.timestamp))}</span>
    </button>`).join("");
}

function sortedItems(items) {
  const direction = sortDescending ? -1 : 1;
  return [...items].sort((left, right) => {
    const a = left[sortKey];
    const b = right[sortKey];
    if (typeof a === "string") return direction * a.localeCompare(b);
    return direction * (a - b);
  });
}

function renderMarketTable() {
  const container = document.getElementById("market-table");
  const market = markets.find((entry) => entry.market_id === selectedMarketId);
  if (!market) {
    setText("market-title", "Commodities");
    setText("market-age", "-");
    container.innerHTML = '<p class="empty-note">Select a market.</p>';
    return;
  }
  setText("market-title", marketLabel(market));
  setText("market-age", ageLabel(market.timestamp));
  const showEmpty = document.getElementById("show-empty").checked;
  const items = sortedItems(market.items.filter((item) => showEmpty || item.stock > 0 || item.demand > 0));
  const head = COMMODITY_COLUMNS.map((column) => {
    const active = column.key === sortKey;
    const arrow = active ? (sortDescending ? " ↓" : " ↑") : "";
    return `<th><button class="sort" type="button" data-sort="${column.key}" aria-pressed="${active}">${column.label}${arrow}</button></th>`;
  }).join("");
  const rows = items.map((item) => `
    <tr>
      <td>${escapeHtml(item.name)}<span class="market-category">${escapeHtml(item.category)}</span></td>
      <td>${item.buy_price ? count(item.buy_price) : "-"}</td>
      <td>${item.sell_price ? count(item.sell_price) : "-"}</td>
      <td>${count(item.stock)}</td>
      <td>${count(item.demand)}</td>
      <td>${count(item.mean_price)}</td>
    </tr>`).join("");
  container.innerHTML = items.length
    ? `<table class="market-table"><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`
    : '<p class="empty-note">No commodities with stock or demand.</p>';
}

function renderDealPickers() {
  ["deal-x", "deal-y"].forEach((id, index) => {
    const select = document.getElementById(id);
    const previous = select.value;
    select.innerHTML = markets.map((market) => (
      `<option value="${market.market_id}">${escapeHtml(marketLabel(market))}</option>`
    )).join("");
    const fallback = markets[index] || markets[0];
    const keep = markets.some((market) => String(market.market_id) === previous);
    select.value = keep ? previous : (fallback ? String(fallback.market_id) : "");
  });
}

const DEAL_CHOICES = 3;

// Each leg offers its best few deals; the picked ones make the round trip and the /haul route.
function legTable(leg, label, deals) {
  if (!deals.length) {
    return `<h3>${label}</h3><p class="empty-note">Nothing profitable; fly empty.</p>`;
  }
  const rows = deals.slice(0, DEAL_CHOICES).map((deal) => `
    <tr>
      <td><input type="radio" name="deal-${leg}" value="${escapeHtml(deal.commodity)}"
        aria-label="${escapeHtml(deal.name)}" ${deal.commodity === chosenDeals[leg] ? "checked" : ""}></td>
      <td>${escapeHtml(deal.name)}</td>
      <td>${count(deal.buy_price)}</td>
      <td>${count(deal.stock)}</td>
      <td>${count(deal.sell_price)}</td>
      <td>${count(deal.demand)}</td>
      <td class="profit">${count(deal.profit_per_ton)}</td>
      <td class="profit">${credits(deal.hold_profit)}${deal.hold_tons ? ` <span class="market-category">${count(deal.hold_tons)} t</span>` : ""}</td>
    </tr>`).join("");
  return `<h3>${label}</h3><div class="market-table-scroll"><table class="market-table">
    <thead><tr><th></th><th>Commodity</th><th>Buy</th><th>Supply</th><th>Sell</th><th>Demand</th><th>Profit/t</th><th>Full hold</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

function chosenDeal(leg) {
  const deals = (shownComparison.payload[leg] || []).slice(0, DEAL_CHOICES);
  return deals.find((deal) => deal.commodity === chosenDeals[leg]) || deals[0] || null;
}

// Same model as /routes: profit per trip over the estimated round-trip time.
function estimatedProfitPerHour(perTrip, trip) {
  return trip && trip.trip_s ? Math.round(perTrip * 3600 / trip.trip_s) : null;
}

function minutes(seconds) {
  return `${Math.round(seconds / 60)} min`;
}

function metric(label, value, note) {
  return `<div><span class="field-label">${label}</span>
    <span class="deal-metric-value mono">${value}</span>${note ? `<span class="deal-metric-note">${note}</span>` : ""}</div>`;
}

function shipLabel(ship) {
  if (!ship || ship.id === null || ship.id === undefined) return "any ship (current ship unknown)";
  const name = ship.name ? ` "${escapeHtml(ship.name)}"` : "";
  return `this ship (${escapeHtml(ship.type || "ship")}${name})`;
}

// Completed haul runs on the pair, for the current ship, over the picked window.
function measuredMetric(payload, trip) {
  const measured = payload.measured;
  const options = MEASURED_WINDOWS.map(([value, label]) =>
    `<option value="${value}"${value === measuredWindow ? " selected" : ""}>${label}</option>`).join("");
  const select = `<select class="select deal-window" id="deal-window" aria-label="Measured window">${options}</select>`;
  const windowText = (MEASURED_WINDOWS.find(([value]) => value === payload.measured_window) || [null, "the window"])[1];
  const span = windowText === "All" ? "ever" : `in the last ${windowText}`;
  let note;
  if (!measured) {
    note = `No completed haul runs on this route ${span} by ${shipLabel(payload.measured_ship)}.`;
  } else {
    note = `${count(measured.runs)} completed run${measured.runs === 1 ? "" : "s"} ${span} by ${shipLabel(payload.measured_ship)}, `
      + `${minutes(measured.loop_s)} loop`;
    if (measured.laden_jump_range_ly !== null) {
      const now = trip && trip.laden_jump_range_ly;
      const changed = now && Math.abs(now - measured.laden_jump_range_ly) >= 0.05 ? ` (now ${now} Ly)` : "";
      note += `, flown at ${measured.laden_jump_range_ly} Ly laden${changed}`;
    }
    if (measured.unknown_ship_runs) note += `; ${count(measured.unknown_ship_runs)} ship unknown`;
  }
  return `<div><span class="deal-window-head"><span class="field-label">Measured per hour</span>${select}</span>
    <span class="deal-metric-value mono">${measured ? `${credits(measured.profit_per_hour)}/h` : "-"}</span>
    <span class="deal-metric-note">${note}</span></div>`;
}

// Inara's trade route view: profit per ton, profit per trip and profit per hour, plus our measured runs.
function dealMetrics(perTon, perTrip, perHour, trip, payload) {
  let hourNote;
  if (perHour !== null) {
    const legs = trip.jumps ? `${trip.jumps} jump${trip.jumps === 1 ? "" : "s"} each way, ${trip.distance_ly} Ly` : "same system";
    hourNote = `Estimate: ${minutes(trip.trip_s)} round trip, ${legs} at ${trip.laden_jump_range_ly} Ly laden`;
  } else if (trip && trip.hint) {
    // A peer has no station facts of its own; the hub supplies them.
    hourNote = escapeHtml(trip.hint);
  } else {
    const missing = (trip && trip.missing) || [];
    hourNote = missing.length ? `Missing ${escapeHtml(missing.join(", "))}. Docking there or EDDN data fills it in.` : "No trip estimate.";
  }
  return `<div class="deal-metrics">
    ${metric("Profit per ton", `${count(perTon)} Cr/t`, "Both legs added")}
    ${metric("Profit per trip", credits(perTrip), "Full-hold round trip")}
    ${metric("Profit per hour", perHour !== null ? `${credits(perHour)}/h` : "-", hourNote)}
    ${measuredMetric(payload, trip)}
  </div>`;
}

// The picked round trip as a /haul route: X is the first station, Y the second.
function tradeRoute(marketX, marketY, out, back, perHour) {
  return {
    index: 0,
    from_station: marketX.station, from_system: marketX.system,
    to_station: marketY.station, to_system: marketY.system,
    source_buy_commodity: out ? out.name : null,
    target_buy_commodity: back ? back.name : null,
    profit_per_trip: credits((out ? out.hold_profit : 0) + (back ? back.hold_profit : 0)),
    profit_per_hour: perHour !== null ? credits(perHour) : null,
    from_supply: out ? count(out.stock) : null,
    to_demand: out ? count(out.demand) : null,
    to_supply: back ? count(back.stock) : null,
    from_demand: back ? count(back.demand) : null,
    from_manual_landing: false, to_manual_landing: false
  };
}

function renderComparison() {
  const result = document.getElementById("deal-result");
  const { payload, marketX, marketY } = shownComparison;
  const out = chosenDeal("outbound");
  const back = chosenDeal("inbound");
  chosenDeals = { outbound: out ? out.commodity : null, inbound: back ? back.commodity : null };
  const nameX = escapeHtml(marketX.station);
  const nameY = escapeHtml(marketY.station);
  const legs = legTable("outbound", `Buy at ${nameX} (X), sell at ${nameY} (Y)`, payload.outbound)
    + legTable("inbound", `Buy at ${nameY} (Y), sell at ${nameX} (X)`, payload.inbound);
  if (!out && !back) {
    shownTradeRoute = null;
    result.innerHTML = `<p class="empty-note">No profitable round trip between these two markets.</p>${legs}`;
    return;
  }
  const perTon = (out ? out.profit_per_ton : 0) + (back ? back.profit_per_ton : 0);
  const perTrip = (out ? out.hold_profit : 0) + (back ? back.hold_profit : 0);
  const perHour = estimatedProfitPerHour(perTrip, payload.trip);
  shownTradeRoute = tradeRoute(marketX, marketY, out, back, perHour);
  // /haul imports a route from its #route= fragment once it connects.
  const haulUrl = `/haul#route=${encodeURIComponent(JSON.stringify(shownTradeRoute))}`;
  result.innerHTML = `
    <div class="deal-round-trip"><strong>Round trip:</strong> X → Y ${out ? escapeHtml(out.name) : "nothing"},
      Y → X ${back ? escapeHtml(back.name) : "nothing"}.
      ${dealMetrics(perTon, perTrip, perHour, payload.trip, payload)}
      <div class="deal-actions">
        <button class="btn" type="button" id="deal-copy">Copy route</button>
        <a class="btn" href="${escapeHtml(haulUrl)}">Open in haul</a>
      </div>
    </div>
    ${legs}`;
}

// Copies the route as JSON for the /haul "Copy / paste route" box.
async function copyTradeRoute(button) {
  const text = JSON.stringify(shownTradeRoute, null, 2);
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

async function refreshComparison() {
  const result = document.getElementById("deal-result");
  const x = document.getElementById("deal-x").value;
  const y = document.getElementById("deal-y").value;
  const request = ++compareRequest;
  shownTradeRoute = null;
  if (!x || !y) {
    setText("deal-status", "Pick two markets");
    result.innerHTML = "";
    return;
  }
  if (x === y) {
    setText("deal-status", "Pick two different markets");
    result.innerHTML = "";
    return;
  }
  setText("deal-status", "Comparing");
  try {
    const payload = await fetchJson("/api/market-compare", {
      x,
      y,
      capacity: document.getElementById("deal-capacity").value.trim(),
      laden_jump_range_ly: document.getElementById("deal-laden").value.trim(),
      window: measuredWindow
    });
    if (request !== compareRequest) return;
    const byId = Object.fromEntries(markets.map((market) => [String(market.market_id), market]));
    // A new pair starts from the best deals; the periodic refresh of the same pair keeps the picks.
    const pair = `${x}:${y}`;
    if (!shownComparison || shownComparison.pair !== pair) {
      chosenDeals = { outbound: null, inbound: null };
    }
    shownComparison = { pair, payload, marketX: byId[x] || { station: "X", system: "" },
      marketY: byId[y] || { station: "Y", system: "" } };
    setText("deal-status", `${count(payload.cargo_capacity)} t hold`);
    renderComparison();
  } catch (error) {
    if (request !== compareRequest) return;
    setText("deal-status", `Comparison unavailable: ${error.message}`);
    result.innerHTML = "";
  }
}

applyWebConfigLabels();
// A blank jump range falls back to haul_search.toml on the server, as on /routes; show that value.
const ladenDefault = (WEB_CONFIG.webDefaults || {}).maxRouteDistanceLy;
if (ladenDefault) document.getElementById("deal-laden").placeholder = `${ladenDefault} (haul search)`;
document.getElementById("access-token").value = accessToken;
document.getElementById("save-token").addEventListener("click", () => {
  accessToken = document.getElementById("access-token").value.trim();
  if (accessToken) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
  refreshMarkets();
});
document.getElementById("markets-refresh").addEventListener("click", refreshMarkets);
document.getElementById("market-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-market-id]");
  if (!button) return;
  selectedMarketId = Number(button.dataset.marketId);
  renderMarketList();
  renderMarketTable();
});
document.getElementById("market-table").addEventListener("click", (event) => {
  const button = event.target.closest("[data-sort]");
  if (!button) return;
  if (button.dataset.sort === sortKey) {
    sortDescending = !sortDescending;
  } else {
    sortKey = button.dataset.sort;
    sortDescending = sortKey !== "name";
  }
  renderMarketTable();
});
document.getElementById("show-empty").addEventListener("change", renderMarketTable);
document.getElementById("deal-result").addEventListener("click", (event) => {
  const button = event.target.closest("#deal-copy");
  if (button) copyTradeRoute(button);
});
document.getElementById("deal-result").addEventListener("change", (event) => {
  if (event.target.id === "deal-window") {
    measuredWindow = event.target.value;
    try {
      window.localStorage.setItem(WINDOW_STORAGE_KEY, measuredWindow);
    } catch (error) {
      // Not remembered across loads; this page still uses it.
    }
    refreshComparison();
    return;
  }
  const leg = event.target.name === "deal-outbound" ? "outbound" : event.target.name === "deal-inbound" ? "inbound" : null;
  if (!leg) return;
  chosenDeals[leg] = event.target.value;
  renderComparison();
});
document.getElementById("deal-x").addEventListener("change", refreshComparison);
document.getElementById("deal-y").addEventListener("change", refreshComparison);
document.getElementById("deal-capacity").addEventListener("change", refreshComparison);
document.getElementById("deal-laden").addEventListener("change", refreshComparison);
refreshMarkets();
// New market visits and ages stay current without a manual refresh.
window.setInterval(refreshMarkets, 30000);
