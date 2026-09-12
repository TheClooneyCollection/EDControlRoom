# Elite Dangerous Bindings Setup

EDControlRoom drives Elite by looking up your live `.binds` file and pressing whatever keys those actions are bound to. Two things need to be true before your first run.

## 1. Arrow-Key Secondaries on the Menu Cursor (Required)

Elite's galaxy map and menu navigation must have **arrow-key secondary bindings** on these four actions:

| Action     | Secondary key |
|------------|---------------|
| `UI_Up`    | Up Arrow      |
| `UI_Down`  | Down Arrow    |
| `UI_Left`  | Left Arrow    |
| `UI_Right` | Right Arrow   |

**Why:** on the default Elite bindings, `W A S D` is bound to pan the galaxy map view, not to move the menu cursor. If EDControlRoom uses `W A S D` for menu nav it will scroll the map instead of picking items, so it needs a separate arrow-key path that only moves the cursor.

**How to set it:** in Elite go to Options -> Controls -> UI Mode. For each of the four actions above, click the empty **secondary** slot and press the matching arrow key. Keep whatever you have on the primary slot.

Without these secondaries, `dest`, `home`, and the galaxy-map portion of `haul` will misnavigate the menus.

## 2. A Complete `.binds` File

EDControlRoom needs to find your active bindings file so it can look up action keys. Auto-detection covers standard installs (macOS CrossOver, Windows Frontier launcher, Steam / Proton). If it does not find yours, set `paths.bindings_file` explicitly in a repo-root `config.toml`.

To inspect, back up, or apply a shipped bindings preset, see [../operators/bindings-files.md](../operators/bindings-files.md).

Next: [getting-started.md](getting-started.md).
