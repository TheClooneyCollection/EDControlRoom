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

  // While the hub voices this node with its speakers muted, its pages say why they are quiet: a note under
  // the chip and one in the speech settings, if the page has them. `muted` comes from /api/hub-status.
  const notes = [];
  let shownMuted = false;

  function note(anchor, className) {
    const element = document.createElement("p");
    element.className = className;
    element.setAttribute("role", "status");
    element.hidden = true;
    anchor.after(element);
    notes.push(element);
  }

  function mutedText(status) {
    return status.role === "hub" ?
      "Muted: callouts play only in hub pages set to Play in this browser." :
      "Muted by the hub: callouts play on the hub.";
  }

  function showMuted(status) {
    shownMuted = status.muted === true;
    for (const element of notes) {
      element.hidden = !shownMuted;
      element.textContent = shownMuted ? mutedText(status) : "";
    }
  }

  async function refresh() {
    const chip = document.getElementById("hub-chip");
    if (!chip) return;
    if (!notes.length) {
      note(chip, "hub-muted-note");
      const speech = document.getElementById("speech-status");
      if (speech) note(speech, "field-hint hub-muted-note");
    }
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
    showMuted(status.configured ? status : {});
    if (!status.configured) return;
    const view = status.role === "hub" ? hubView(status) : peerView(status);
    if (shownMuted) view.lines.push(mutedText(status));
    chip.dataset.state = view.state;
    chip.querySelector("strong").textContent = shownMuted ? `${view.label} · muted` : view.label;
    chip.title = view.lines.join("\n");
  }

  // An announcement says whether it was muted: when that changes, ask again rather than wait for the poll.
  window.addEventListener("edcr:announcement", (event) => {
    if (Boolean(event.detail && event.detail.muted) !== shownMuted) refresh();
  });

  refresh();
  window.setInterval(refresh, 10000);
})();
