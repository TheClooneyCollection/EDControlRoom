// Activity log docked to the bottom of the viewport on desktop widths, shared by every page with one.
// Collapsed it shows the newest entry on one line; expanded it shows the full list. Phones keep it in flow.
(() => {
  const STORAGE_KEY = "edcr.activityDock.expanded";
  const DOCKED_QUERY = window.matchMedia("(min-width: 761px)");

  const panel = document.getElementById("activity-panel");
  const toggle = document.getElementById("activity-toggle");
  const list = document.getElementById("activity-list");
  const latest = document.getElementById("activity-latest");
  if (!panel || !toggle || !list || !latest) return;

  function storedExpanded() {
    try {
      return window.localStorage.getItem(STORAGE_KEY) === "true";
    } catch (error) {
      return false;
    }
  }

  function storeExpanded(expanded) {
    try {
      window.localStorage.setItem(STORAGE_KEY, String(expanded));
    } catch (error) {
      // Storage can be blocked; the dock still works for this page view.
    }
  }

  let expanded = storedExpanded();

  function apply() {
    const docked = DOCKED_QUERY.matches;
    const open = expanded || !docked;
    document.body.classList.toggle("has-activity-dock", docked);
    panel.classList.toggle("expanded", open);
    toggle.disabled = !docked;
    toggle.setAttribute("aria-expanded", String(open));
  }

  // Mirror the newest rendered row so the collapsed bar stays live without touching each page's renderer.
  function updateLatest() {
    const row = list.querySelector(".activity-row");
    const time = row ? row.querySelector(".activity-time") : null;
    const text = row ? row.querySelector(".activity-text") : null;
    latest.querySelector(".activity-time").textContent = time ? time.textContent : "--:--:--";
    latest.querySelector(".activity-text").textContent = text ? text.textContent : "Waiting for backend activity.";
  }

  // Main content pads by the dock's height so the bar never hides the last panel.
  function updateDockHeight() {
    const height = document.body.classList.contains("has-activity-dock") ? panel.offsetHeight : 0;
    document.documentElement.style.setProperty("--activity-dock-height", `${height}px`);
  }

  toggle.addEventListener("click", () => {
    expanded = !expanded;
    storeExpanded(expanded);
    apply();
    updateDockHeight();
  });
  DOCKED_QUERY.addEventListener("change", () => {
    apply();
    updateDockHeight();
  });
  new MutationObserver(updateLatest).observe(list, { childList: true, subtree: true, characterData: true });
  if (window.ResizeObserver) new ResizeObserver(updateDockHeight).observe(panel);

  apply();
  updateLatest();
  updateDockHeight();
})();
