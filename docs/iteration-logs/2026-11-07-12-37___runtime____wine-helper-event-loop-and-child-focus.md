# Iteration Log

- Area: `runtime`
- Title: `wine-helper-event-loop-and-child-focus`
- Started: `2026-11-07 12:37`

## Summary

- **CPU report:** a long-lived server helper (old pid 48229) sat at 99.7% CPU after about 10 minutes. It did not reproduce: fresh helpers measured 0.0% (`ps -o pcpu`) idle, connected, after `target`/`focus`, after disconnect, with `--log`, and on a tty or `/dev/null`. A probe showed `select` under Wine blocks correctly (49 wakes/s at a 20ms timeout). Held-key CPU was not measured, since it needs game input.
- **Focus retest:** the 3x focus retry on main still fails live (`helper.log`: one `attach_thread_input`, four `already`, then repeated `focus_failed fg=explorer.exe err=5`). Every live success came from a freshly started process. A long-lived probe helper recovered once in-process (`attach_thread_input`, 0.02s) during 4 minutes of Mac app switching, so the failure needs more than one drift or a longer-lived helper.

## Changes

- **CPU spin root cause (reproduced):** two helpers at ~100% CPU, both PPID 1, stdio on the user's terminal `ttys021`, both in its process group, last log line `disconnected`, port 47811 no longer listening. `sample` showed the main thread inside `_sigtramp` and a busy Rosetta exception-server thread. Sending SIGINT to a probe helper reproduced it at once (104%) for both the old polling loop and the new event loop; it still answers requests, but after `bye` it never exits. `SetConsoleCtrlHandler(NULL,TRUE)` did not help. A plain orphan (parent gone, no signal) stays at 0-1.2% and exits on `bye`. So quitting Control Room with Ctrl-C in its terminal hit the helper too, and the next Control Room could start a second helper because the stuck one had closed its socket.
- Managed launch now uses `subprocess.Popen(argv, stdin=DEVNULL, start_new_session=True)`, so terminal signals never reach the helper. SIGKILL stops a spinning helper cleanly.
- `edap_input_helper.c` main loop waits on events instead of polling: `WSAEventSelect` on the listen and client sockets plus `MsgWaitForMultipleObjects`, with the timeout from the nearest held-key deadline (1s idle cap, 20ms retry after a failed release). A busy guard logs `busy_wakes` once and backs off 10ms per extra wake above 1000 wakes/s.
- Focus falls back to a short-lived child of the helper exe (`--focus-hwnd <decimal hwnd>`, 700ms timeout) when the in-process steps fail. The step is `child_focus`; failures log `focus_failed fg=<process> err=<code> child=<code>` (`0` focused, `1` refused, `100` didn't start, `101` timed out). Child mode verified from macOS: real hwnd exited 0 in 0.7s, a bogus hwnd exited 1.
- Design doc, background-input troubleshooting and runtime status updated.

## Follow-ups

- Live retest: reinstall the helper into the bottle, quit Control Room and confirm no old helper remains, start the server, run a routine while switching Mac apps, then check `helper.log` for `child_focus` or `focus_failed ... child=N`, and `ps -o pcpu` on the helper idle and during routines.
