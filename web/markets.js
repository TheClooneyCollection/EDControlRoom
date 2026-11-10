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

function dealTable(deals) {
  if (!deals.length) {
    return '<p class="empty-note">No profitable commodity in this direction.</p>';
  }
  const rows = deals.map((deal) => `
    <tr>
      <td>${escapeHtml(deal.name)}</td>
      <td>${count(deal.buy_price)}</td>
      <td>${count(deal.stock)}</td>
      <td>${count(deal.sell_price)}</td>
      <td>${count(deal.demand)}</td>
      <td class="profit">${count(deal.profit_per_ton)}</td>
      <td class="profit">${credits(deal.hold_profit)}${deal.hold_tons ? ` <span class="market-category">${count(deal.hold_tons)} t</span>` : ""}</td>
    </tr>`).join("");
  return `<div class="market-table-scroll"><table class="market-table">
    <thead><tr><th>Commodity</th><th>Buy</th><th>Stock</th><th>Sell</th><th>Demand</th><th>Profit/t</th><th>Full hold</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

function roundTripLine(roundTrip) {
  const out = roundTrip.outbound;
  const back = roundTrip.inbound;
  if (!out && !back) {
    return "No profitable round trip between these two markets.";
  }
  const leg = (deal) => (deal ? `${escapeHtml(deal.name)} (${count(deal.profit_per_ton)} Cr/t)` : "nothing");
  return `<strong>Best round trip:</strong> X → Y ${leg(out)}, Y → X ${leg(back)}. `
    + `<span class="profit">${count(roundTrip.profit_per_ton)} Cr/t, ${credits(roundTrip.hold_profit)} per full-hold loop.</span>`;
}

async function refreshComparison() {
  const result = document.getElementById("deal-result");
  const x = document.getElementById("deal-x").value;
  const y = document.getElementById("deal-y").value;
  const request = ++compareRequest;
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
      capacity: document.getElementById("deal-capacity").value.trim()
    });
    if (request !== compareRequest) return;
    const byId = Object.fromEntries(markets.map((market) => [String(market.market_id), market]));
    const nameX = escapeHtml(byId[x] ? byId[x].station : "X");
    const nameY = escapeHtml(byId[y] ? byId[y].station : "Y");
    setText("deal-status", `${count(payload.cargo_capacity)} t hold`);
    result.innerHTML = `
      <div class="deal-round-trip">${roundTripLine(payload.round_trip)}</div>
      <h3>Buy at ${nameX} (X), sell at ${nameY} (Y)</h3>${dealTable(payload.outbound)}
      <h3>Buy at ${nameY} (Y), sell at ${nameX} (X)</h3>${dealTable(payload.inbound)}`;
  } catch (error) {
    if (request !== compareRequest) return;
    setText("deal-status", `Comparison unavailable: ${error.message}`);
    result.innerHTML = "";
  }
}

applyWebConfigLabels();
document.getElementById("access-token").value = accessToken;
document.getElementById("save-token").addEventListener("click", () => {
  accessToken = document.getElementById("access-token").value.trim();
  if (accessToken) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
  refreshMarkets();
// New market visits and ages stay current without a manual refresh.
window.setInterval(refreshMarkets, 30000);
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
document.getElementById("deal-x").addEventListener("change", refreshComparison);
document.getElementById("deal-y").addEventListener("change", refreshComparison);
document.getElementById("deal-capacity").addEventListener("change", refreshComparison);
refreshMarkets();
// New market visits and ages stay current without a manual refresh.
window.setInterval(refreshMarkets, 30000);
