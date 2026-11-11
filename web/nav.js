// Page navigation shared by every page: renders the sidebar links into <nav id="site-nav"> and marks the
// current page. Desktop shows every item; phones (<= 760px) show the `mobile` items in the top row and put
// the rest behind a "More" menu. Loaded without defer right after the placeholder so the nav never flashes.
// On a hub it also shows the node picker (plan 0015): which node's game every page shows.

// The node this browser looks at on a hub; pages add it to their session and node reads.
// Empty means this server's own game. Peers and standalone servers ignore `node`.
window.EDCRNode = (() => {
  const KEY = "edcr.node";
  let chosen = "";
  try {
    chosen = window.localStorage.getItem(KEY) || "";
  } catch (error) {
    chosen = "";
  }
  return {
    id: () => chosen,
    addTo(searchParams) {
      if (chosen) searchParams.set("node", chosen);
    },
    choose(nodeId) {
      try {
        if (nodeId) window.localStorage.setItem(KEY, nodeId);
        else window.localStorage.removeItem(KEY);
      } catch (error) {
        // Private windows: the choice lasts until the page reloads.
      }
      chosen = nodeId;
    }
  };
})();

(() => {
  const ICON_ATTRS = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"';
  const NAV_GROUPS = [
    {
      label: "Haul",
      items: [
        { href: "/haul", label: "Two-way haul", mobile: true, icon: '<path d="M3 12h5l2 5 4-14 2 9h5"/>' },
        { href: "/multi-haul", label: "Multi-leg haul", icon: '<path d="M4 18h5l3-12 3 12h5"/><path d="M4 6h4m8 0h4"/>' },
        { href: "/markets", label: "Markets", mobile: true, icon: '<path d="M4 20V10m6 10V4m6 16v-7m4 7H2"/>' },
        {
          href: "/routes",
          label: "Routes",
          mobile: true,
          icon: '<circle cx="5" cy="18" r="2"/><circle cx="19" cy="6" r="2"/><path d="M7 18h6a3 3 0 0 0 0-6h-2a3 3 0 0 1 0-6h6"/>'
        }
      ]
    },
    {
      label: "Ship",
      items: [
        {
          href: "/controls",
          label: "Controls",
          mobile: true,
          icon: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>' +
            '<rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'
        },
        { href: "/travel", label: "Travel", icon: '<path d="M3 11l18-8-8 18-2-8-8-2z"/>' }
      ]
    }
  ];
  const MOBILE_QUERY = window.matchMedia("(max-width: 760px)");

  const nav = document.getElementById("site-nav");
  if (!nav) return;

  // "/" serves the two-way haul page.
  const path = window.location.pathname.replace(/\/+$/, "") || "/haul";

  function link(item, extraClass) {
    const anchor = document.createElement("a");
    anchor.className = `nav-item link${extraClass ? ` ${extraClass}` : ""}`;
    anchor.href = item.href;
    anchor.innerHTML = `<svg ${ICON_ATTRS}>${item.icon}</svg>`;
    anchor.append(item.label);
    if (item.href === path) {
      anchor.classList.add("active");
      anchor.setAttribute("aria-current", "page");
    }
    return anchor;
  }

  const moreItems = [];
  NAV_GROUPS.forEach((group) => {
    const label = document.createElement("div");
    label.className = "nav-label";
    label.textContent = group.label;
    nav.append(label);
    group.items.forEach((item) => {
      nav.append(link(item, item.mobile ? "" : "nav-desktop-only"));
      if (!item.mobile) moreItems.push(item);
    });
  });

  const more = document.createElement("div");
  more.className = "nav-more";
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "nav-item nav-more-toggle";
  toggle.id = "nav-more-toggle";
  toggle.setAttribute("aria-expanded", "false");
  toggle.setAttribute("aria-controls", "nav-more-menu");
  toggle.innerHTML = '<span class="nav-more-icon" aria-hidden="true">&#9776;</span><span class="nav-more-text">More</span>';
  const menu = document.createElement("div");
  menu.className = "nav-more-menu";
  menu.id = "nav-more-menu";
  menu.hidden = true;
  moreItems.forEach((item) => menu.append(link(item, "")));
  if (moreItems.some((item) => item.href === path)) toggle.classList.add("active");
  more.append(toggle, menu);
  nav.append(more);

  function setOpen(open, { focusToggle = false } = {}) {
    menu.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    if (open) {
      // The phone nav row scrolls sideways, which would clip an absolutely placed menu, so pin it to the viewport.
      const rect = toggle.getBoundingClientRect();
      menu.style.top = `${Math.round(rect.bottom + 6)}px`;
      const first = menu.querySelector("a");
      if (first) first.focus();
    } else if (focusToggle) {
      toggle.focus();
    }
  }

  toggle.addEventListener("click", () => setOpen(menu.hidden));
  more.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !menu.hidden) {
      event.preventDefault();
      setOpen(false, { focusToggle: true });
    }
  });
  more.addEventListener("focusout", (event) => {
    if (!menu.hidden && !more.contains(event.relatedTarget)) setOpen(false);
  });
  document.addEventListener("click", (event) => {
    if (!menu.hidden && !more.contains(event.target)) setOpen(false);
  });
  MOBILE_QUERY.addEventListener("change", () => setOpen(false));

  // Node picker, hub only: online nodes with their ship and running routine. Desktop shows it under the
  // links; phones put it at the top of the More menu. Picking a node reloads the page onto it.
  // Pages set EDCR_WEB_CONFIG in a script after this one, so read it when a request is made.
  const webConfig = () => window.EDCR_WEB_CONFIG || {};
  const query = new URLSearchParams(window.location.search);
  const picker = document.createElement("label");
  picker.className = "node-picker";
  picker.id = "node-picker";
  picker.hidden = true;
  picker.innerHTML = '<span class="node-picker-label">Node</span><select id="node-select" aria-label="Node to show"></select>' +
    '<span class="node-picker-state" id="node-picker-state"></span>';
  const select = picker.querySelector("select");
  const stateText = picker.querySelector(".node-picker-state");
  let localId = "";

  function placePicker() {
    if (MOBILE_QUERY.matches) menu.prepend(picker);
    else nav.after(picker);
  }
  placePicker();
  MOBILE_QUERY.addEventListener("change", placePicker);

  function accessToken() {
    let stored = "";
    try {
      stored = window.localStorage.getItem("edcr.haul.accessToken") || "";
    } catch (error) {
      stored = "";
    }
    return query.get(webConfig().authQueryParameterName || "access_token") || query.get("access_token") || stored ||
      webConfig().defaultAccessToken || "";
  }

  async function getJson(path) {
    const url = new URL(path, window.location.origin);
    const token = accessToken();
    if (token) url.searchParams.set(webConfig().authQueryParameterName || "access_token", token);
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function shipText(state) {
    const ship = state && state.ship ? state.ship : {};
    return (ship.name || "").trim() || ship.type || "";
  }

  function optionText(node) {
    const parts = [node.name + (node.local ? " (hub)" : "")];
    const ship = shipText(node.state);
    if (ship) parts.push(ship);
    if (node.state && node.state.routine) parts.push(node.state.routine);
    return parts.join(" · ");
  }

  function render(nodes) {
    const local = nodes.find((node) => node.local);
    localId = local ? local.node_id : "";
    const current = window.EDCRNode.id() || localId;
    const shown = nodes.filter((node) => node.connected || node.node_id === current);
    select.replaceChildren(...shown.map((node) => {
      const option = document.createElement("option");
      option.value = node.node_id;
      option.textContent = node.connected ? optionText(node) : `${node.name} (offline)`;
      return option;
    }));
    const picked = nodes.find((node) => node.node_id === current);
    if (!picked) {
      const option = document.createElement("option");
      option.value = current;
      option.textContent = "Unknown node (offline)";
      select.append(option);
    }
    select.value = current;
    const offline = !picked || !picked.connected;
    picker.dataset.state = offline ? "down" : "ok";
    stateText.textContent = offline ? "Offline: pages wait for it" : "";
    picker.title = picked && picked.connected ? optionText(picked) : "This node is not linked to the hub";
  }

  async function refreshNodes() {
    try {
      const payload = await getJson("/api/nodes");
      picker.hidden = false;
      render(payload.nodes || []);
    } catch (error) {
      // Not a hub, or the hub is restarting: keep what is shown.
    }
  }

  select.addEventListener("change", () => {
    // The hub's own game is the default, so it is stored as no choice.
    window.EDCRNode.choose(select.value === localId ? "" : select.value);
    window.location.reload();
  });

  const whenParsed = new Promise((resolve) => {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", resolve, { once: true });
    else resolve();
  });
  whenParsed.then(() => getJson("/api/hub-status")).then((status) => {
    if (status.role !== "hub") return;
    // The hub voice panel (which node the hub voices, Listen here) sits under the picker.
    const voice = document.createElement("script");
    voice.src = "/assets/hub-voice.js";
    document.head.append(voice);
    refreshNodes();
    window.setInterval(refreshNodes, 10000);
  }).catch(() => {});
})();
