// Sidebar "Hub" chip, shared by every page: a peer shows its hub link, a hub its connected peers.
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

  function peerView(status) {
    const state = status.connected ? "ok" : status.last_error ? "down" : "unknown";
    const lines = [
      status.connected ? `Linked since ${localTime(status.connected_since)}` :
        status.last_error ? `Not linked: ${status.last_error}` : "Not linked yet",
      `Hub address: ${status.host}`,
      `Last contact: ${localTime(status.last_contact_at)}`,
      `Outbox: ${status.outbox_pending} waiting for the hub`
    ];
    return { state, label: status.hub_name || status.host, lines };
  }

  function hubView(status) {
    const peers = status.peers_connected;
    return {
      state: "ok",
      label: `${peers} peer${peers === 1 ? "" : "s"}`,
      lines: [`This Control Room is the hub (${status.node_name})`, `${peers} peer(s) linked`]
    };
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
    const view = status.role === "hub" ? hubView(status) : peerView(status);
    chip.dataset.state = view.state;
    chip.querySelector("strong").textContent = view.label;
    chip.title = view.lines.join("\n");
  }

  refresh();
  window.setInterval(refresh, 10000);
})();
