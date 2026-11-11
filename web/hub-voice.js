// Hub voice (plan 0015 step 7), loaded by nav.js on a hub only. Under the node picker: play the picked node's
// callouts on the hub speakers (hub-wide, saved on the hub) and in this browser (per browser), and mute the
// node so they play only here. The picked node is the voiced one, hub-wide: picking a node in any hub page
// voices it (nav.js). A listening page plays each voiced callout: the hub's Piper WAV, or browser speech when
// the hub has no Piper. While it listens, speech.js stays quiet, so one device never voices two nodes.
(() => {
  const WEB_CONFIG = window.EDCR_WEB_CONFIG || {};
  const PARAM = WEB_CONFIG.authQueryParameterName || "access_token";
  const query = new URLSearchParams(window.location.search);
  const LISTEN_KEY = "edcr.hubVoice.listen";
  const SPEECH_KEY = "edcr.speech";
  const MOBILE_QUERY = window.matchMedia("(max-width: 760px)");

  let settings = { node_id: "", node_name: "", speakers: false, mute: false, muted: false, local_node_id: "", piper: false };
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

  window.EDCRHubVoice = { listening: () => listen };

  const panel = document.createElement("div");
  panel.className = "hub-voice";
  panel.id = "hub-voice";
  panel.innerHTML = '<p class="hub-voice-help">Each machine speaks its own callouts. These play the picked ' +
    'node\'s callouts here too.</p>' +
    '<label class="hub-voice-check" id="hub-voice-speakers-row"><input type="checkbox" id="hub-voice-speakers"> ' +
    'Play on hub speakers</label>' +
    '<label class="hub-voice-check"><input type="checkbox" id="hub-voice-listen"> Play in this browser</label>' +
    '<label class="hub-voice-check"><input type="checkbox" id="hub-voice-mute"> <span id="hub-voice-mute-label">Mute the node</span></label>' +
    '<span class="hub-voice-status" id="hub-voice-status" role="status"></span>' +
    '<button type="button" class="hub-voice-follow" id="hub-voice-follow" hidden></button>';
  const speakersRow = panel.querySelector("#hub-voice-speakers-row");
  const speakersBox = panel.querySelector("#hub-voice-speakers");
  const listenBox = panel.querySelector("#hub-voice-listen");
  const muteBox = panel.querySelector("#hub-voice-mute");
  const muteLabel = panel.querySelector("#hub-voice-mute-label");
  const statusText = panel.querySelector("#hub-voice-status");
  const follow = panel.querySelector("#hub-voice-follow");

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

  function local() {
    return settings.node_id === settings.local_node_id;
  }

  // The node this browser picked; empty means the hub's own game.
  function picked() {
    return (window.EDCRNode && window.EDCRNode.id()) || settings.local_node_id;
  }

  // Another browser picked the voiced node since this page picked its own.
  function pickedElsewhere() {
    return Boolean(settings.local_node_id) && picked() !== settings.node_id;
  }

  // A node's name from /api/nodes; empty when the list does not have it (yet).
  function nodeName(nodeId) {
    const node = nodes.find((item) => item.node_id === nodeId);
    return node ? node.name : "";
  }

  // The voiced node's name. An older hub sends no node_name: fall back to the node list, then to words.
  function voicedName() {
    return settings.node_name || nodeName(settings.node_id) || "the voiced node";
  }

  function render() {
    const name = voicedName();
    // The hub's own game already speaks on the hub speakers.
    speakersRow.hidden = local();
    speakersBox.checked = settings.speakers;
    listenBox.checked = listen;
    const playing = (settings.speakers && !local()) || listen;
    muteLabel.textContent = `Mute ${name}`;
    muteBox.checked = settings.mute;
    // Mute only while its callouts play here, so none are lost; unticking always works.
    muteBox.disabled = !playing && !settings.mute;
    muteBox.parentElement.title = `${name} stops speaking its own callouts; they play only on the hub. ` +
      "It speaks again when nothing plays them here or its hub link drops.";
    follow.hidden = !pickedElsewhere();
    if (!follow.hidden) follow.textContent = `Voice ${nodeName(picked()) || "the node picked here"} instead`;
    statusText.textContent = statusLines().join(" ");
  }

  // One short sentence per fact: who is voiced, where it plays, what to do next.
  function statusLines() {
    const name = voicedName();
    const lines = [];
    if (pickedElsewhere()) {
      const hub = local() ? " (hub)" : "";
      const other = settings.node_name || nodeName(settings.node_id) ? `${name}${hub}` : "a different node";
      lines.push(`Another browser picked ${other}; the hub is voicing it.`);
    }
    const where = [];
    if (settings.speakers && !local()) where.push("on the hub speakers");
    if (listen) where.push("in this browser");
    if (!where.length) {
      // Muted while nothing plays here: another hub page is playing them.
      lines.push(settings.muted ? `${capitalised(name)} is muted; another browser on the hub plays its callouts.` :
        `${capitalised(name)} speaks its callouts only on its own machine.`);
      return lines;
    }
    lines.push(`Playing ${name}'s callouts ${where.join(" and ")}.`);
    if (settings.muted) lines.push(`${capitalised(name)} is muted, so its own machine stays quiet.`);
    if (listen && !unlocked) lines.push("Tap the page once to allow sound.");
    if (listen && !settings.piper) lines.push("The hub has no Piper, so this browser's own voice reads them.");
    return lines;
  }

  function capitalised(text) {
    return text.charAt(0).toUpperCase() + text.slice(1);
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

  follow.addEventListener("click", () => save({ node_id: picked() }));
  muteBox.addEventListener("change", () => save({ mute: muteBox.checked }));
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
