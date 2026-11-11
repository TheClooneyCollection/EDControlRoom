// Sidebar "Hub" chip, shared by every page: shown only when this server has a [hub] configured.
(() => {
  const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
  const PARAM = WEB_CONFIG.authQueryParameterName || "access_token";
  const query = new URLSearchParams(window.location.search);

  function accessToken() {
    return query.get(PARAM) || query.get("access_token") ||
      window.localStorage.getItem("edcr.haul.accessToken") || WEB_CONFIG.defaultAccessToken || "";
  }

  function localTime(iso) {
    return iso ? new Date(iso).toLocaleString([], { hour12: false }) : "never";
  }

  function pushSummary(push) {
    if (!push) return "none yet";
    const stations = push.stations.join(", ");
    const result = push.error ? `failed: ${push.error}` : `${push.written} written, ${push.kept} already newer`;
    return `${localTime(push.at)} ${stations} (${result})`;
  }

  async function refresh() {
    const chip = document.getElementById("hub-chip");
    if (!chip) return;
    let status;
    try {
      const url = new URL("/api/hub-status", window.location.origin);
      const token = accessToken();
      if (token) url.searchParams.set(PARAM, token);
      const response = await fetch(url);
      if (!response.ok) return;
      status = await response.json();
    } catch (error) {
      return;
    }
    chip.hidden = !status.configured;
    if (!status.configured) return;
    const state = status.reachable === true ? "ok" : status.reachable === false ? "down" : "unknown";
    chip.dataset.state = state;
    chip.querySelector("strong").textContent = status.host;
    const lines = [
      state === "ok" ? `Reachable (${Math.round(status.latency_ms ?? 0)} ms)` :
        state === "down" ? `Unreachable: ${status.last_error}` : "Not checked yet",
      `Last ok: ${localTime(status.last_ok_at)}`,
      `Last push: ${pushSummary(status.last_push)}`
    ];
    if (status.resend_pending) lines.push("Resend of recent markets pending");
    chip.title = lines.join("\n");
  }

  refresh();
  window.setInterval(refresh, 10000);
})();
