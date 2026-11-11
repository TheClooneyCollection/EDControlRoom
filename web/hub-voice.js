// Hub voice (plan 0015 step 7), loaded by nav.js on a hub only. Under the node picker: which node's callouts
// the hub voices and whether its speakers say them (both hub-wide, saved on the hub), and "Listen here"
// (per browser). A listening page plays each voiced callout: the hub's Piper WAV, or browser speech when the
// hub has no Piper. While it listens, speech.js stays quiet, so one device never voices two nodes.
(() => {
  const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
  const PARAM = WEB_CONFIG.authQueryParameterName || "access_token";
  const query = new URLSearchParams(window.location.search);
  const LISTEN_KEY = "edcr.hubVoice.listen";
  const SPEECH_KEY = "edcr.speech";
  const MOBILE_QUERY = window.matchMedia("(max-width: 760px)");

  let settings = { node_id: null, node_name: null, speakers: false, piper: false };
  let nodes = [];
  let listen = false;
  let socket = null;
  let audio = null;
  let unlocked = false;
  // Clips play one after another, in the order the hub sent them.
  let playing = Promise.resolve();

  try {
    listen = window.localStorage.getItem(LISTEN_KEY) === "1";
  } catch (error) {
    listen = false;
  }

  window.EDCRHubVoice = { listening: () => listen && Boolean(settings.node_id) };

  const panel = document.createElement("div");
  panel.className = "hub-voice";
  panel.id = "hub-voice";
  panel.innerHTML = '<label class="hub-voice-row"><span class="node-picker-label">Voice</span>' +
    '<select id="hub-voice-node" aria-label="Node whose callouts the hub voices"></select></label>' +
    '<label class="hub-voice-check"><input type="checkbox" id="hub-voice-speakers"> Hub speakers</label>' +
    '<label class="hub-voice-check"><input type="checkbox" id="hub-voice-listen"> Listen here</label>' +
    '<span class="hub-voice-status" id="hub-voice-status" role="status"></span>';
  const select = panel.querySelector("#hub-voice-node");
  const speakersBox = panel.querySelector("#hub-voice-speakers");
  const listenBox = panel.querySelector("#hub-voice-listen");
  const statusText = panel.querySelector("#hub-voice-status");

  function place() {
    const picker = document.getElementById("node-picker");
    if (picker) picker.after(panel);
  }
  place();
  // nav.js moves the picker between the sidebar and the More menu; follow it.
  MOBILE_QUERY.addEventListener("change", place);

  function accessToken() {
    let stored = "";
    try {
      stored = window.localStorage.getItem("edcr.haul.accessToken") || "";
    } catch (error) {
      stored = "";
    }
    return query.get(PARAM) || query.get("access_token") || stored || WEB_CONFIG.defaultAccessToken || "";
  }

  function apiUrl(path, protocol) {
    const url = new URL(path, window.location.origin);
    const token = accessToken();
    if (token) url.searchParams.set(PARAM, token);
    if (protocol) url.protocol = protocol;
    return url;
  }

  async function api(path, options) {
    const response = await fetch(apiUrl(path), options);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function render() {
    const shown = nodes.filter((node) => node.connected || node.node_id === settings.node_id);
    const off = document.createElement("option");
    off.value = "";
    off.textContent = "Off";
    select.replaceChildren(off, ...shown.map((node) => {
      const option = document.createElement("option");
      option.value = node.node_id;
      option.textContent = node.name + (node.local ? " (hub)" : "") + (node.connected ? "" : " (offline)");
      return option;
    }));
    if (settings.node_id && !shown.some((node) => node.node_id === settings.node_id)) {
      const option = document.createElement("option");
      option.value = settings.node_id;
      option.textContent = `${settings.node_name || "Unknown node"} (offline)`;
      select.append(option);
    }
    select.value = settings.node_id || "";
    speakersBox.checked = settings.speakers;
    listenBox.checked = listen;
    statusText.textContent = statusLine();
  }

  function statusLine() {
    if (!settings.node_id) return "The hub voices no node.";
    const local = settings.node_id === settings.local_node_id;
    const where = [];
    if (settings.speakers) where.push(local ? "hub speakers (its own voice)" : "hub speakers");
    else if (local) where.push("hub speakers (its own voice)");
    if (listen) where.push(unlocked ? "here" : "here once you tap the page");
    const sound = listen && !settings.piper ? " Browser speech: the hub has no Piper." : "";
    return where.length ? `${settings.node_name}: ${where.join(", ")}.${sound}` : `${settings.node_name}: tick Hub speakers or Listen here.`;
  }

  async function save(change) {
    try {
      settings = await api("/api/hub-voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(change)
      });
    } catch (error) {
      statusText.textContent = `Not saved: ${error.message}`;
      return;
    }
    render();
  }

  async function refresh() {
    try {
      const [voice, nodeList] = await Promise.all([api("/api/hub-voice"), api("/api/nodes")]);
      settings = voice;
      nodes = nodeList.nodes || [];
      render();
    } catch (error) {
      // The hub is restarting: keep what is shown.
    }
  }

  // Phones only play sound after a tap: the first tap after load (or ticking Listen here) opens the audio.
  function unlock() {
    if (unlocked) return;
    unlocked = true;
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
      audio = new AudioContext();
      audio.resume().catch(() => {});
    }
    if ("speechSynthesis" in window) {
      const silent = new SpeechSynthesisUtterance("");
      silent.volume = 0;
      window.speechSynthesis.speak(silent);
    }
    render();
  }

  function speak(text) {
    if (!("speechSynthesis" in window)) return;
    // The device voice and rate picked in the haul page's speech settings.
    let picked = {};
    try {
      picked = JSON.parse(window.localStorage.getItem(SPEECH_KEY) || "{}");
    } catch (error) {
      picked = {};
    }
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = window.speechSynthesis.getVoices().find((item) => item.voiceURI === picked.voiceURI);
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    }
    utterance.rate = Number(picked.rate) || 1;
    window.speechSynthesis.speak(utterance);
  }

  function wavBytes(base64) {
    const binary = window.atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return bytes.buffer;
  }

  function playBuffer(buffer) {
    return new Promise((resolve) => {
      const source = audio.createBufferSource();
      source.buffer = buffer;
      source.connect(audio.destination);
      source.onended = resolve;
      source.start();
    });
  }

  function play(callout) {
    if (!unlocked) return;
    playing = playing.then(async () => {
      if (callout.wav && audio) {
        try {
          await playBuffer(await audio.decodeAudioData(wavBytes(callout.wav)));
          return;
        } catch (error) {
          // A clip this browser cannot play: say the text instead.
        }
      }
      speak(callout.text);
    });
  }

  function connect() {
    if (!listen || socket) return;
    const current = new WebSocket(apiUrl("/api/hub-voice/listen", window.location.protocol === "https:" ? "wss:" : "ws:"));
    socket = current;
    current.addEventListener("message", (event) => {
      let message = {};
      try {
        message = JSON.parse(event.data);
      } catch (error) {
        return;
      }
      if (message.type === "settings") {
        settings = message.settings || settings;
        render();
      } else if (message.type === "callout") {
        play(message);
      }
    });
    current.addEventListener("close", () => {
      if (socket !== current) return;
      socket = null;
      if (listen) window.setTimeout(connect, 3000);
    });
  }

  function disconnect() {
    if (socket) socket.close();
    socket = null;
  }

  select.addEventListener("change", () => save({ node_id: select.value || null }));
  speakersBox.addEventListener("change", () => save({ speakers: speakersBox.checked }));
  listenBox.addEventListener("change", () => {
    listen = listenBox.checked;
    try {
      if (listen) window.localStorage.setItem(LISTEN_KEY, "1");
      else window.localStorage.removeItem(LISTEN_KEY);
    } catch (error) {
      // Private windows: the choice lasts until the page reloads.
    }
    if (listen) {
      unlock();
      connect();
    } else {
      disconnect();
    }
    render();
  });
  document.addEventListener("pointerdown", unlock, { once: true });

  render();
  refresh();
  connect();
  window.setInterval(refresh, 10000);
})();
