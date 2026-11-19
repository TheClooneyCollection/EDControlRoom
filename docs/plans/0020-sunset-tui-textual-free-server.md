# 0020: Sunset the TUI, Textual-Free Server

## Status

Decisions confirmed 2026-11-19; nothing built. Revision 2: the TUI is deleted, not ported. Decisions below; the `/controls` `home set` fix is folded in (step 7).

## Why

The web Control Room is the operator surface. The Textual TUI (no-arg `control_room.py`) and `connect` still shape the server: `serve` / `lan` / `local` / `hub` / `peer` run `HeadlessControlRoomHost` (`edcr/control_room/server/host.py:92`), a subclass of the Textual `ControlRoomApp(App[None])` (`edcr/control_room/app.py:318`). The host fakes what the App touches: 11 widget stubs (`host.py:37-90`), a `query_one` table (`host.py:129-152`), no-op `set_focus` / `_refresh_*` (`host.py:154-170`), an inline `call_from_thread` (`host.py:172`) and its own watcher thread (`host.py:337-359`). Routines run as Textual thread workers (`app.py:1758`) and check `textual.worker.get_current_worker().is_cancelled` (`workers.py:8,70,98,173`).

Costs today:

- `Worker._start` calls `asyncio.create_task` (`textual/worker.py:401`), so a routine starts only on a thread with a running event loop. That is why `NodeLoop` exists (`server/app.py:225`).
- Thread workers run on the default `ThreadPoolExecutor` (`textual/worker.py:326`), so interpreter exit waits for a running routine.
- Any new App method that writes a widget breaks the server until someone adds a stub.
- Tests build Textual `App()`s (hence `_CachedThemeVariables`, `tests/test_control_room.py:217`). The suite is over budget: 1,279 tests in 1.048 s against 0.767 s (measured 2026-11-15).

## Decisions

From the user:

- Delete the TUI: the default no-arg Textual UI and `connect`, plus TUI-only code. No `textual` import anywhere; `textual` leaves `pyproject.toml` and `uv.lock`. Deleted, not kept.
- `control_room.py` with no arguments runs `local`.
- `ship_controls.py` stays as is: `tools/ship_controls.py` (CLI) over `edcr/ship_controls.py`; neither imports Textual.

Proposed:

- `ControlRoomApp` becomes a Textual-free `ControlRoomCore` (`edcr/control_room/core.py`); the server uses it directly. No App/core split, no view port: there is one consumer.
- Routines run on a plain `RoutineRunner` (daemon thread plus `CancelToken`). The 8 stop/pause/exclusive semantics land as tests before the switch.
- Thread hand-off stays as on the server today: direct calls, no lock (parity).
- `connect` goes first, the runner second, the default TUI and the App base third (reasons in Build steps).

## Design

### 1. What the server uses today, and what goes

Kept in the core (the server uses it for real):

| Area | Members (app.py unless noted) |
| --- | --- |
| State | ship, market, haul stats, trade routes, saved state, `RuntimeUIState` routine fields (`models.py:153`), TTS, backend, dependencies (`__init__` 406-483) |
| Routines | facade map (`facade.py:352`) for `_cmd_*`, `_dispatch_*`, `_start_delayed_routine`, `_make_*`; `_run_in_thread` 1758; `_clear_routine` 1762; `workers.py` |
| Stop, pause | 1801-1983: interrupt, stop request, cancel toggle/after run/now, Track only stop, pause/resume, `_wait_for_haul_resume` |
| Journal | `_handle_event` 1711, `_sync_status_state` 1175, `_load_market_json`, `_append_journal_event` 2031, watcher loop |
| TTS | `_announce_tts` 1549, `_publish_announcement` 1564, `_announce_tts_for_event` 1576, startup greeting 1142, `say` / `mute_callouts` (`host.py:191,195`) |
| Activity | `_log` 1494 minus the widget write; `_protocol_activity_log` |
| Persistence | `_load/_save_saved_state` 1033/1078, `persist_trade_route_state` (`host.py:285`, used at `server/app.py:2043`) |
| Commands | `backend.submit_input` (`backend.py:174`) to `commands.dispatch`; `_refuse_busy` 683 |
| Setup | `_build_controls` 982, reload keymap/config 994/1013, startup logs, input-target setters 1106-1136 |
| Hub/peer | `_protocol_event_sink` (`serve.py:200`), `dependencies.data_source.current()` (`serve.py:188`), `_saved_state` (`serve.py:354`), `_tts.render_announcement` (`serve.py:367`), `server/commands.py:11-40` |

What the web sends, checked in `web/`: `command.submit_input` with `dock`, `undock`, `jump`, `escape`, `boost`, `buy`/`sell <commodity> <amount>`, `pause`, `resume`, `instant on|off`, `say`, `voice set|save`, `home set <system>`, `reload_config`, `reload_keymap`; and explicit messages `dispatch_destination`, `dispatch_haul_loop` (incl. Track only), `dispatch_travel`, `dispatch_spansh_route`, `dispatch_multi_leg_haul`, `dispatch_route_all_in_one`, `select_trade_route`, `dismiss_route_recommendation`, `cancel_active_routine`. No web page reads `command_history`, `default_haul` or `history_entries` from hydrate, and none drives a prompt.

Deletable once the TUI is gone:

- Textual UI in `app.py`: CSS, `compose`, `ActivityLog` 216-316, mount 812-868, panel refreshes 1181-1210, market tabs 1214-1238, picker rendering 1240-1330, replay visibility 1331-1348, activity display order 1349-1395, `_refresh_command_input` 1410, key/input/option handlers 2101-2365, bindings and `action_*` 1767-1800, SIGINT drain, the update-check worker 1745, `_finalize_shutdown`'s `self.exit()`.
- `connect`: `_mount_remote_runtime` 855, `_handle_backend_event` / `_apply_backend_event` / `_apply_data_state` / `_play_local_announcement` 877-980, remote exit prompt 1984-2020, `_local_activity_log`, `exit_detaches_remote_session` branches (`backend.py:210`, `app.py:1874,1914,1949`), `edcr/control_room/client/backend.py` and `connect.py`.
- Prompts: the interactive flows in `prompts.py` (haul, haul search, dest, confirm; `#cmd` writes 122, 262), `PromptState` fields except `haul_params` (which `dispatch_haul_loop` reads, `routines_haul.py:499`, set by `dependencies.py:343`), the prompt branches of `backend.submit_input` 175-203, `handle_haul_prompt` / `handle_haul_confirm_prompt` on the execution protocol (`dependencies.py:157-159,389-393`).
- Replay and history browsing: `replay.py`, `HistoryState`, `ReplayBrowserState`, the `replay`/`history` verbs.
- Route picker UI: `TradeRoutePickerState.open`, presented URL/time and `open/close_trade_route_picker` (`routines_haul.py:342-356`). `selected_route_index` stays until checked: the data source reads it (`dependencies.py:491`) and `selected_or_saved_trade_route` (`routines_haul.py:319`) falls back to the saved route.
- `app_view_actions.py`, `view_actions.py`, `view_models.py`: only the TUI uses them. In `rendering.py`, the panel renderers go; `activity_line`, `read_cargo_inventory`, `fmt_duration`, ledger and history lines stay (`bootstrap.py:84`, `haul_tracking.py:7`, `commands.py:16`).
- The host's widget stubs and overrides (`host.py:37-172`).

Kept, to check during the step: command history recording (`_record_history_entry`, `saved_state.history`, `default_haul`) is written to the state file and published in hydrate but read by nothing on the web. Keep it in this plan so old state files load; drop it later (Decisions).

Found while checking: `/controls` Set home sends `home set <system>`, and the host refuses every `home` command as client-local (`host.py:23`, `_CLIENT_LOCAL_REMOTE_VERBS`), logging "Unknown command". With prompts gone, the filter shrinks to verbs that still need a prompt, and `home set` runs.

### 2. Target shape

```
control_room.py [local]          ->  edcr/control_room/cli.py main()
serve | lan | local | hub | peer ->  server/serve.py
                                      HeadlessControlRoomHost(ControlRoomCore)
                                      core.py: state, journal, TTS, persistence, haul stats,
                                               routine dispatch, stop/pause, RoutineRunner
                                      web pages + /api + peer link
```

Plan 0008 is the architecture target today, and its premise ("one `ControlRoomApp` for local and connect UI") no longer holds. What still holds: no snapshot protocol, data-source hydrate messages, explicit execution intents. Those now describe the server and the web pages. Proposed: mark 0008 "Superseded by 0020" in its Status, with one paragraph naming what carries over. Its Target Shape stays as history. `docs/status/control-room.md` stops calling 0008 the active target.

### 3. Routines without Textual workers

`edcr/control_room/routine_runner.py`:

- `CancelToken`: `cancel()`, `is_cancelled`, a `threading.Event` the sleeper waits on.
- `current_token()` reads a `ContextVar` set inside the routine thread; outside a routine it raises `NoActiveRoutine`, as `get_current_worker` raises `NoActiveWorker`.
- `RoutineRunner(start_thread)`; `start(fn, name) -> RoutineHandle` (`cancel()`, `token`, `join(timeout)`). A new start cancels the previous token (today's `exclusive=True`). `start_thread` is injected: production a daemon `threading.Thread(name=f"routine-{name}")`, tests inline. `cancel_all()` for shutdown.

Semantics to keep, each a test before the switch:

1. Stop now: `handle.cancel()`; `RoutineCancelled` at the next `CancellationProxy` call on controls or watcher (`workers.py:25,114,119`), progress (`workers.py:106`) or sleeper tick (`workers.py:127`); "Routine cancelled." logged; `clear_routine` runs.
2. Cancel during the start delay: the `PendingRoutineCancelled` message (`workers.py:150-155,196`).
3. A routine that returns after a cancel still logs "Routine cancelled." (`workers.py:176`).
4. Stop after run and pause stay flags (`_haul_stop_requested`, `_haul_pause_requested`) read by `haul_loop_two_way` (`routines_haul.py:657-662`). Stop now during a pause works because `_wait_for_haul_resume` (1859) sleeps with the cancellable sleeper.
5. Stop toggle escalation (`_cancel_active_routine` 1866-1910): first stop after run, second cancel now. `self._routine_worker.cancel()` (1910, 1968) becomes `handle.cancel()`.
6. `clear_routine` identity guard (`workers.py:218-222`): a replaced routine leaves the newer one's state alone.
7. Shutdown cancels the routine and the watcher. Today only the TUI does (`app.py:2097-2098`); the server's `close()` (`host.py:183`) gains cancel plus a 1 s join.
8. Track only runs no routine; every stop ends it (`_stop_haul_tracking` 1970).

Call sites:

- Textual worker API: `workers.py:8,70,98-101,173,176,215`; `app.py:1741` (`_start_watcher`), `1758` (`_run_in_thread`), `2097-2098`.
- Via `_start_delayed_routine` (unchanged, get the runner through the facade): `routines_trade.py:109,193,284`, `routines_movement.py:16,42,71`, `routines_station.py:26,58`, `routines_travel.py:98`, `routines_nav.py:87`, `routines_spansh.py:54`, `routines_haul.py:483,650,738`.
- Explicit cancel checks: `routines_trade.py:252`, `facade.py:105`.
- `call_from_thread` (becomes a direct call or is dropped): `routines_haul.py:464,471,476,477,660`, `routines_trade.py:254,277,279,282`, `workers.py:77,80-82,107,157,159,177-215`, `app.py:1860,1864`; protocols `interfaces.py:135`, `workers.py:66`.
- Tests on the Textual API: `tests/test_control_room.py:4836,4855,4880` (`get_current_worker`); `tests/test_hub_relay.py:15-16,61-75` (a Textual `App` with an `@work` routine, for `NodeLoop`).

### 4. Journal watcher

One `run_watcher_loop(journal_dir, stop, handle_event, sync_status, load_market, refresh_haul, refresh_s)` on a plain thread replaces `workers.start_watcher_loop` (`workers.py:69`) and `host._watch_loop` (`host.py:343`). Keep the host's 0.1 s idle sleep (`host.py:359`); `JournalWatcher.poll` sleeps too (`edcr/state.py`).

### 5. No-arg start

Today `local` serves on `127.0.0.1` and prints the URL; it does not open a browser (`app.py:2503-2520`). No arguments becomes `local` and, like it, prints the URL without opening a browser.

## Build steps

Each step is one commit with its tests; `uv run python3 -m unittest discover -s tests` green; `Ran N tests in` recorded before and after in the iteration log. User docs change in the step that removes the feature, so docs never describe a missing mode.

Order: `connect` first, because it is independent and removes the remote branches the later steps would otherwise have to carry. The runner comes before the TUI deletion, so the safety-critical change ships alone, is tested and live-checked on the hub while the rest is unchanged, and the big deletion is then a move with semantics already pinned. The App base cannot go before the runner anyway: routines need Textual workers until then.

1. **Remove `connect`.** Delete `client/backend.py`, `client/connect.py`, the `connect` branch and `--client-name` / `--claim-operator` (`app.py:2537-2550`), the remote branches listed in Design 1, and `exit_detaches_remote_session`. Move `client/target.py` to `edcr/control_room/protocol/target.py` for `tools/scratch/scratch_control_room_remote.py`. Delete `tests/test_control_room_client.py` (42) and the 3 remote exit prompt tests. Docs: `docs/operators/control-room-remote.md`, the TUI client and `--no-tts` same-machine paragraph in `docs/user/getting-started.md:74`, `docs/user/troubleshooting.md`, the connect caveat in `docs/status/control-room.md`.
2. **Runner.** `routine_runner.py` with tests (inline `start_thread`): cancel wakes a waiting sleeper at once, a new start cancels the previous token, the context var is per thread, `cancel_all`, `join`. No wiring.
3. **Routines on the runner.** `workers.py` drops `textual`; `_run_in_thread` returns a `RoutineHandle`; `_routine_worker` holds it; the sleeper waits on the token event in 0.1 s slices; `close()` cancels and joins. The 8 semantics as tests through the headless host. Rewrite the 3 `get_current_worker` patches and the `test_hub_relay.py` Textual routine. Live hub check before step 4: Stop now, Stop after run, pause and resume mid-haul, from `/haul` and from a hub page on a peer.
4. **One watcher loop.** `run_watcher_loop` on a plain thread; delete `host._watch_loop` and `_start_watcher`. Tests with an injected clock and stop event.
5. **No TUI.** Move `main()` and the LAN detection helpers (`app.py:2370-2465`) to `edcr/control_room/cli.py`; no arguments means `local`; `control_room.py` calls `cli.main` and drops its `app` re-exports (moved to their modules or deleted with their tests). `ControlRoomApp` is no longer launched, but still exists. Docs: README "Terminal Control Room (TUI)" block (`README.md:127-138`) and `docs/assets/tui-control-room.png`, the `haul search` TUI line (`README.md:76`), Quick Start, `docs/user/getting-started.md`, `install.md`, `commands-reference.md`, `haul-workflow.md`, `hub.md`, `background-input.md`, `docs/user/README.md`, `docs/README.md`, `docs/operators/control-room.md`. The README TOC changes only if a section heading changes (none planned; check).
6. **Core without the App base.** Rename `ControlRoomApp` to `ControlRoomCore` in `core.py`, drop `App` and every Textual UI member (Design 1), and fold the host's stubs and overrides away. `HeadlessControlRoomHost(ControlRoomCore)` keeps `say`, `mute_callouts`, `submit_input` filtering, `dispatch_*` refreshes, `persist_trade_route_state`. Delete `app_view_actions.py`, `view_actions.py`, `view_models.py`, the panel renderers in `rendering.py`. Tests: `_HarnessApp` / `_ProtocolHarnessApp` build the core (base swap, no `App()`); delete widget, key, focus, auto-follow, exit-binding and SIGINT-drain tests; retarget `test_binding_conflicts.py:104` and `test_route_recommend_node.py:75`.
7. **No prompts, replay or picker UI.** Delete `replay.py`, the prompt flows in `prompts.py`, the dead `PromptState` / `HistoryState` / `ReplayBrowserState` / picker fields, the prompt branches of `backend.submit_input`, `handle_haul_prompt` / `handle_haul_confirm_prompt`. Shrink `_CLIENT_LOCAL_REMOTE_VERBS` to verbs that only opened a prompt (they log "use the web page" instead of "Unknown command"); `home set` runs. Tests: delete prompt and replay tests; add `home set` through `submit_input`.
8. **Drop the dependency.** `uv remove textual` (updates `pyproject.toml` and `uv.lock`; `rich` stays a direct dependency, 18 modules use `rich.markup`). Guard test: no `.py` file under `edcr/`, `tools/` or the repo root imports `textual` (a source scan, no subprocess).
9. **Docs and plans.** 0008 marked superseded (Design 2); `docs/status/control-room.md` and `docs/status/README.md`; AGENTS.md (only `ship_controls.py`, `AGENTS.md:92,99`, which stays correct; the "Preserve existing OpenCV/navigation behavior" rule is unrelated); iteration log; archive refresh.

Test estimate: about 42 (client) + 3 (remote exit) + 60-80 (TUI-only in `test_control_room.py`: keys, focus, auto-follow, replay, prompts, picker, exit prompt, SIGINT drain) go, so 105-125 of 1,279. About 170 in `test_control_room.py`, 18 in `test_control_room_protocol.py` and a few elsewhere are rewritten by a base-class swap. Runtime: the five Textual-heavy modules now take about 0.38 s (`test_control_room` 0.194, `test_hub_relay` 0.083, `test_control_room_server` 0.077, protocol 0.013, client 0.012). I expect 0.1-0.2 s less, to about 0.85-0.95 s for about 1,160 tests; still over the 0.7 s budget, so the timing report runs after step 6.

## Risks

- **Stop/cancel semantics.** Stop now mid-haul is a safety stop. The 8 semantics land as tests in step 3 and the live hub check gates step 4.
- **Exclusive start.** Textual cancels the old worker when a new one starts. The runner does the same, so a missed refusal path cannot run two routines on one set of controls.
- **Daemon threads.** A daemon routine thread dies at exit mid-keypress. `close()` cancels and joins first so held keys release through the normal cancel path.
- **Thread safety.** The server already mutates state from watcher, routine, web loop and `NodeLoop` threads with no lock. This plan keeps that unchanged, no better and no worse.
- **Event loop assumption.** `NodeLoop` and handlers may rely on dispatch happening on a loop thread. Leave `NodeLoop` in place; simplify it only after a live check.
- **Deleting something the web uses.** Design 1 lists what the web sends; each deletion step re-greps `web/` and `server/app.py` for the member, and the server round-trip tests cover the web commands. `selected_route_index` and command history are kept until shown unused.
- **Users on the TUI or `connect`.** Both go without a deprecation release. The release notes and README say the web page replaces them.
- **Test timing.** No step adds a subprocess or a real sleep: runner tests use inline threads and token events, the watcher an injected clock, the guard a source scan.

## Decisions (confirmed with the user, 2026-11-19)

1. No arguments does not open a browser; it prints the URL like `local`.
2. Command history (`saved_state.history`, `default_haul`, the hydrate `command_history`) stays in this plan so old state files load; drop it in a follow-up once nothing reads it.
3. `help` / `commands` stay as they are. No web page has a free-text command box (`/controls` buttons send fixed strings), so nothing sends them; `replay` / `history` go.
4. Keep both `ControlRoomCore` (logic) and `HeadlessControlRoomHost` (say, mute, the command filter). Merge later if the host stays thin.
5. `current_token()` outside a routine raises `NoActiveRoutine`, as Textual does.
6. `close()` cancels a running routine on exit and joins for 1 s.
7. `NodeLoop` is not simplified in this plan; note it in status.
8. One release after step 9, titled for the TUI sunset; `pyproject.toml` version per the release style.
