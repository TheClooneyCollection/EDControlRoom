(function () {
  "use strict";

  const WINDOW_SIZE = 5;

  const state = {
    active: null,
    currentSystem: "",
  };

  function el(id) { return document.getElementById(id); }

  function clearChildren(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function showEmpty() {
    el("active-spansh-empty").classList.remove("hidden");
    el("active-spansh-content").classList.add("hidden");
    el("active-spansh-status").textContent = "Idle";
  }

  function showContent() {
    el("active-spansh-empty").classList.add("hidden");
    el("active-spansh-content").classList.remove("hidden");
  }

  function renderWaypointBar(waypoints, currentIndex) {
    const bar = el("active-spansh-waypoints");
    clearChildren(bar);
    const total = waypoints.length;
    // Center a window of WINDOW_SIZE around currentIndex, clamped.
    let start;
    if (currentIndex < 0) {
      start = 0;
    } else {
      start = Math.max(0, Math.min(total - WINDOW_SIZE, currentIndex - Math.floor(WINDOW_SIZE / 2)));
    }
    const end = Math.min(total, start + WINDOW_SIZE);
    bar.style.gridTemplateColumns = "repeat(" + (end - start) + ", minmax(0, 1fr))";
    for (let i = start; i < end; i += 1) {
      const w = waypoints[i];
      const step = document.createElement("div");
      step.className = "step";
      if (currentIndex >= 0 && i < currentIndex) step.classList.add("done");
      if (currentIndex >= 0 && i === currentIndex) step.classList.add("current");
      const label = document.createElement("div");
      label.className = "step-label";
      const positionLabel = i === 0 ? "Start" : (i === total - 1 ? "End" : ("Waypoint " + i));
      const boostSuffix = w.neutron_boost ? " · N" : "";
      label.textContent = positionLabel + boostSuffix;
      const value = document.createElement("div");
      value.className = "step-value";
      value.textContent = w.system || "-";
      step.appendChild(label);
      step.appendChild(value);
      bar.appendChild(step);
    }
  }

  function computeRemaining(waypoints, currentIndex) {
    if (currentIndex < 0) {
      let jumps = 0;
      let ly = 0;
      let boosts = 0;
      for (let i = 1; i < waypoints.length; i += 1) {
        const w = waypoints[i];
        jumps += Number(w.jumps_from_prev || 0);
        ly += Number(w.ly_from_prev || 0);
        if (w.neutron_boost) boosts += 1;
      }
      return { jumps: jumps, ly: ly, boosts: boosts };
    }
    let jumps = 0;
    let ly = 0;
    let boosts = 0;
    for (let i = currentIndex + 1; i < waypoints.length; i += 1) {
      const w = waypoints[i];
      jumps += Number(w.jumps_from_prev || 0);
      ly += Number(w.ly_from_prev || 0);
      if (w.neutron_boost) boosts += 1;
    }
    return { jumps: jumps, ly: ly, boosts: boosts };
  }

  function render() {
    const panel = el("active-spansh-panel");
    if (!panel) return;
    if (!state.active || !state.active.route || !Array.isArray(state.active.route.waypoints) || state.active.route.waypoints.length < 2) {
      showEmpty();
      return;
    }
    showContent();
    const route = state.active.route;
    const waypoints = route.waypoints;
    const total = waypoints.length;
    const currentLower = (state.currentSystem || "").trim().toLowerCase();
    let currentIndex = -1;
    if (currentLower) {
      currentIndex = waypoints.findIndex(function (w) {
        return String(w.system || "").trim().toLowerCase() === currentLower;
      });
    }

    renderWaypointBar(waypoints, currentIndex);

    const lastEl = el("active-spansh-last");
    const currentEl = el("active-spansh-current");
    const nextEl = el("active-spansh-next");
    if (currentIndex < 0) {
      lastEl.textContent = "off route";
      currentEl.textContent = state.currentSystem || "unknown";
      nextEl.textContent = waypoints[waypoints.length - 1].system || "-";
    } else {
      lastEl.textContent = currentIndex > 0 ? waypoints[currentIndex - 1].system : "start";
      currentEl.textContent = waypoints[currentIndex].system;
      nextEl.textContent = currentIndex < total - 1 ? waypoints[currentIndex + 1].system : "arrived";
    }

    const remaining = computeRemaining(waypoints, currentIndex);
    el("active-spansh-jumps-remaining").textContent = remaining.jumps + " / " + Number(route.total_jumps || 0);
    el("active-spansh-ly-remaining").textContent = remaining.ly.toFixed(1) + " ly";
    el("active-spansh-boosts-remaining").textContent = remaining.boosts + " / " + Number(route.neutron_count || 0);

    const status = el("active-spansh-status");
    if (currentIndex < 0) {
      status.textContent = "Off route";
    } else if (currentIndex >= total - 1) {
      status.textContent = "Arrived";
    } else {
      const jumpsDone = Number(route.total_jumps || 0) - remaining.jumps;
      status.textContent = jumpsDone + " of " + Number(route.total_jumps || 0) + " jumps";
    }
  }

  function applyHydrate(payload) {
    if (!payload) return;
    if (payload.active_spansh_route === null || payload.active_spansh_route === undefined) {
      state.active = null;
    } else {
      state.active = payload.active_spansh_route;
    }
    if (payload.ship && payload.ship.system) {
      state.currentSystem = payload.ship.system;
    }
    render();
  }

  function applyShipState(shipState) {
    if (shipState && shipState.system) {
      state.currentSystem = shipState.system;
      render();
    }
  }

  function init() {
    window.addEventListener("edcr:hydrate", function (event) { applyHydrate(event.detail); });
    window.addEventListener("edcr:ship-state", function (event) { applyShipState(event.detail); });
    if (window.EDCR_HAUL && window.EDCR_HAUL.lastHydrate) {
      applyHydrate(window.EDCR_HAUL.lastHydrate);
    } else {
      render();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
