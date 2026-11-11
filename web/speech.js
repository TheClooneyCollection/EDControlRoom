(function () {
  "use strict";

  // Per-device settings so a laptop already speaking through `say` does not double up with a phone.
  const STORAGE_KEY = "edcr.speech";
  const TEST_TEXT = "Announcements will play on this device.";

  const settings = { enabled: false, voiceURI: "", rate: 1 };
  let unlocked = false;

  function el(id) { return document.getElementById(id); }

  function loadSettings() {
    try {
      Object.assign(settings, JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}"));
    } catch (_) {}
  }

  function saveSettings() {
    try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings)); } catch (_) {}
  }

  function setStatus(text) { el("speech-status").textContent = text; }

  function englishVoices() {
    const voices = window.speechSynthesis.getVoices();
    const english = voices.filter((voice) => voice.lang.toLowerCase().startsWith("en"));
    return english.length ? english : voices;
  }

  function renderVoices() {
    const select = el("speech-voice");
    const voices = englishVoices();
    select.textContent = "";
    const fallback = document.createElement("option");
    fallback.value = "";
    fallback.textContent = "Device default";
    select.appendChild(fallback);
    for (const voice of voices) {
      const option = document.createElement("option");
      option.value = voice.voiceURI;
      option.textContent = `${voice.name} (${voice.lang})`;
      select.appendChild(option);
    }
    select.value = voices.some((voice) => voice.voiceURI === settings.voiceURI) ? settings.voiceURI : "";
  }

  function speak(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = window.speechSynthesis.getVoices().find((item) => item.voiceURI === settings.voiceURI);
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    }
    utterance.rate = settings.rate;
    window.speechSynthesis.speak(utterance);
  }

  // iOS only lets a page speak after a tap; the first tap after load speaks silently to unlock it.
  function unlock() {
    if (unlocked) return;
    unlocked = true;
    const utterance = new SpeechSynthesisUtterance("");
    utterance.volume = 0;
    window.speechSynthesis.speak(utterance);
    renderStatus();
  }

  function renderStatus() {
    if (!settings.enabled) {
      setStatus("Off on this device.");
    } else if (!unlocked) {
      setStatus("Tap anywhere on the page to allow speech.");
    } else {
      setStatus("On. Keep this page open with the screen awake.");
    }
  }

  function init() {
    if (!el("speech-enabled")) return;
    if (!("speechSynthesis" in window)) {
      setStatus("This browser cannot speak.");
      for (const id of ["speech-enabled", "speech-voice", "speech-rate", "speech-test"]) el(id).disabled = true;
      return;
    }
    loadSettings();
    el("speech-enabled").checked = settings.enabled;
    el("speech-rate").value = String(settings.rate);
    el("speech-rate-value").textContent = `${settings.rate}x`;
    renderVoices();
    window.speechSynthesis.addEventListener("voiceschanged", renderVoices);
    renderStatus();

    document.addEventListener("pointerdown", unlock, { once: true });
    el("speech-enabled").addEventListener("change", (event) => {
      settings.enabled = event.target.checked;
      saveSettings();
      unlock();
      if (settings.enabled) speak(TEST_TEXT);
      renderStatus();
    });
    el("speech-voice").addEventListener("change", (event) => {
      settings.voiceURI = event.target.value;
      saveSettings();
    });
    el("speech-rate").addEventListener("input", (event) => {
      settings.rate = Number(event.target.value) || 1;
      el("speech-rate-value").textContent = `${settings.rate}x`;
      saveSettings();
    });
    el("speech-test").addEventListener("click", () => {
      unlock();
      speak(TEST_TEXT);
    });
    window.addEventListener("edcr:announcement", (event) => {
      const text = event.detail && event.detail.message_text;
      // A hub page listening to the hub voice (hub-voice.js) plays that node instead.
      const hubVoice = window.EDCRHubVoice;
      if (hubVoice && hubVoice.listening()) return;
      if (settings.enabled && unlocked && text) speak(text);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
