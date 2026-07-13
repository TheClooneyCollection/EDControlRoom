(function () {
  "use strict";

  const state = {
    active: null,
    currentSystem: "",
  };

  function panel() { return document.getElementById("active-spansh-panel"); }

  function render() {
    const el = panel();
    if (!el) return;
    if (!state.active || !state.active.route || !Array.isArray(state.active.route.waypoints) || state.active.route.waypoints.length < 2) {
      el.classList.add("hidden");
      return;
    }
    const waypoints = state.active.route.waypoints;
    const total = waypoints.length;
    const currentLower = (state.currentSystem || "").trim().toLowerCase();
    let currentIndex = -1;
    if (currentLower) {
      currentIndex = waypoints.findIndex(function (w) {
        return String(w.system || "").trim().toLowerCase() === currentLower;
      });
    }
    const summary = document.getElementById("active-spansh-summary");
    const lastEl = document.getElementById("active-spansh-last");
    const behindEl = document.getElementById("active-spansh-behind");
    const currentEl = document.getElementById("active-spansh-current");
    const aheadEl = document.getElementById("active-spansh-ahead");
    const nextEl = document.getElementById("active-spansh-next");

    if (currentIndex < 0) {
      // Not in any known waypoint. Show first and last as anchors.
      lastEl.textContent = "-";
      behindEl.textContent = "off route";
      currentEl.textContent = state.currentSystem || "unknown";
      aheadEl.textContent = String(total) + " waypoints";
      nextEl.textContent = String(waypoints[waypoints.length - 1].system || "-");
    } else {
      const lastWaypoint = currentIndex > 0 ? waypoints[currentIndex - 1] : null;
      const nextWaypoint = currentIndex < total - 1 ? waypoints[currentIndex + 1] : null;
      const behindCount = currentIndex;
      const aheadCount = (total - 1) - currentIndex;
      lastEl.textContent = lastWaypoint ? lastWaypoint.system : "start";
      behindEl.textContent = behindCount === 1 ? "1 system" : (behindCount + " systems");
      currentEl.textContent = waypoints[currentIndex].system;
      aheadEl.textContent = aheadCount === 1 ? "1 more system" : (aheadCount + " more systems");
      nextEl.textContent = nextWaypoint ? nextWaypoint.system : waypoints[total - 1].system;
    }

    if (summary) {
      const meta = state.active.route.metadata || {};
      const jumps = state.active.route.total_jumps;
      const neutrons = state.active.route.neutron_count;
      const parts = ["Spansh"];
      if (typeof jumps === "number") parts.push(jumps + " jumps");
      if (typeof neutrons === "number") parts.push(neutrons + " boosts");
      if (meta && typeof meta.supercharge_multiplier === "number") {
        parts.push(meta.supercharge_multiplier + "x FSD");
      }
      summary.textContent = parts.join("  ·  ");
    }
    el.classList.remove("hidden");
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
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
