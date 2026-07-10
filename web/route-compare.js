(function () {
  "use strict";
  const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
  const AUTH_PARAM = WEB_CONFIG.authQueryParameterName || "access_token";
  const TOKEN_STORAGE_KEY = "edcr.haul.accessToken";

  function currentToken() {
    const input = document.getElementById("access-token");
    if (input && input.value) return input.value.trim();
    try {
      const cached = window.localStorage.getItem(TOKEN_STORAGE_KEY);
      if (cached) return cached;
    } catch (e) { /* ignore */ }
    return WEB_CONFIG.defaultAccessToken || "";
  }

  function withAuth(url) {
    const token = currentToken();
    if (!token) return url;
    const separator = url.includes("?") ? "&" : "?";
    return url + separator + encodeURIComponent(AUTH_PARAM) + "=" + encodeURIComponent(token);
  }

  function setStatus(text, isError) {
    const el = document.getElementById("rc-status");
    if (!el) return;
    el.textContent = text || "";
    el.classList.toggle("error", !!isError);
  }

  function fmt(n, digits) {
    if (typeof n !== "number" || !isFinite(n)) return "-";
    return n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  function renderRows(tbody, waypoints, kind) {
    tbody.innerHTML = "";
    let running = 0;
    waypoints.forEach(function (w, i) {
      running += (w.ly_from_prev || 0);
      const tr = document.createElement("tr");
      const cells = [
        String(i),
        w.system,
        kind === "in-game" ? (w.star_class || "-") : (w.neutron_boost ? "Yes" : ""),
        fmt(w.ly_from_prev, 2),
        fmt(running, 2),
      ];
      cells.forEach(function (text, idx) {
        const td = document.createElement("td");
        td.textContent = text;
        if (idx === 3 || idx === 4) td.className = "num";
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  function renderComparison(payload) {
    const ig = payload.in_game;
    const sp = payload.spansh;
    document.getElementById("rc-in-game-head").textContent =
      "In-game route  ·  " + ig.total_jumps + " jumps  ·  " + fmt(ig.total_ly, 1) + " LY  ·  neutrons: " + ig.neutron_count;
    document.getElementById("rc-spansh-head").textContent =
      "Spansh route  ·  " + sp.total_jumps + " jumps  ·  " + fmt(sp.total_ly, 1) + " LY  ·  neutrons: " + sp.neutron_count + "  ·  galmap visits: " + sp.galaxy_map_visits;

    renderRows(document.getElementById("rc-in-game-rows"), ig.waypoints, "in-game");
    renderRows(document.getElementById("rc-spansh-rows"), sp.waypoints, "spansh");

    const summary = document.getElementById("rc-summary");
    const delta = payload.jumps_delta;
    const neutronDelta = payload.neutron_delta;
    let deltaLabel;
    if (delta < 0) deltaLabel = "Spansh saves " + Math.abs(delta) + " jumps";
    else if (delta > 0) deltaLabel = "Spansh adds " + delta + " jumps";
    else deltaLabel = "Same jump count";
    let neutronLabel;
    if (neutronDelta > 0) neutronLabel = "+" + neutronDelta + " neutron boosts";
    else if (neutronDelta < 0) neutronLabel = neutronDelta + " neutron boosts";
    else neutronLabel = "same neutron count";
    summary.textContent = deltaLabel + " · " + neutronLabel;
    summary.className = "rc-summary verdict-" + payload.verdict;

    const verdictEl = document.getElementById("route-compare-verdict");
    if (verdictEl) {
      const verdictText = payload.verdict === "spansh_better"
        ? "Spansh better"
        : payload.verdict === "in_game_better"
          ? "In-game better"
          : "Even";
      verdictEl.textContent = verdictText;
    }

    if (payload.tts_phrase) {
      speakOnce(payload.tts_phrase);
    }

    document.getElementById("rc-results").classList.remove("hidden");
  }

  function speakOnce(phrase) {
    try {
      if (typeof window.speechSynthesis === "undefined") return;
      window.speechSynthesis.cancel();
      const utter = new window.SpeechSynthesisUtterance(phrase);
      window.speechSynthesis.speak(utter);
    } catch (e) { /* ignore */ }
  }

  async function fetchComparison(url) {
    setStatus("Fetching...", false);
    try {
      const response = await fetch(withAuth(url), { method: "GET" });
      const text = await response.text();
      let payload = null;
      try { payload = JSON.parse(text); } catch (e) { /* ignore */ }
      if (!response.ok) {
        const message = (payload && payload.detail) || text || ("HTTP " + response.status);
        setStatus("Error: " + message, true);
        return;
      }
      setStatus("", false);
      renderComparison(payload);
    } catch (err) {
      setStatus("Error: " + err, true);
    }
  }

  function buildLiveUrl() {
    const from = encodeURIComponent(document.getElementById("rc-from").value.trim());
    const to = encodeURIComponent(document.getElementById("rc-to").value.trim());
    const range = encodeURIComponent(document.getElementById("rc-range").value.trim());
    const eff = encodeURIComponent(document.getElementById("rc-efficiency").value.trim() || "60");
    const sc = encodeURIComponent(document.getElementById("rc-supercharge").value || "4");
    if (!from || !to || !range) {
      setStatus("From, To, and Range are required.", true);
      return null;
    }
    return "/api/route-compare?from=" + from + "&to=" + to + "&range=" + range + "&efficiency=" + eff + "&supercharge_multiplier=" + sc;
  }

  function init() {
    document.getElementById("rc-compare").addEventListener("click", function () {
      const url = buildLiveUrl();
      if (url) fetchComparison(url);
    });
    document.getElementById("rc-fixture-normal").addEventListener("click", function () {
      fetchComparison("/api/route-compare?fixture=hd232819_xinca_normal");
    });
    document.getElementById("rc-fixture-overcharge").addEventListener("click", function () {
      fetchComparison("/api/route-compare?fixture=hd232819_xinca_overcharge");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
