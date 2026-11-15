# Iteration Log

- Area: `control-room`
- Title: `hub-owned-peer-recommendations`
- Started: `2026-11-15 22:33`

## Summary

- Follow-up to plan 0019: peer recommendations stay on the hub by default; original delivery remains opt-in.

## Changes

- Added strict boolean `[eddn.recommend] deliver_to_peers = false`, with default/true/false/invalid-value behavior tests. Independent config slice committed by a child in its own worktree, integrated linearly; child closed and worktree removed.
- `server/peer_recommendations.py` owns each peer's recommendation state, dismissals and announcer when delivery is off. It emits no peer frame. The original `route_recommendation` frame and peer handler remain; enabling the flag restores that path without a code change (restart when permitted).
- Hub peer websocket sessions overlay the hub list on incoming hydrates and publish fresh full hydrates on recommendation updates/Dismiss, to every viewing page. Dismiss is handled locally with normal operator checks and invalid/stale-key errors. Select remains relayed and clears the hub's old list when the peer confirms its changed route; no travel/haul starts automatically.
- Voice decision: named peer lines use the existing HubVoice path and hub speaker queue, only for the selected/voiced node and enabled hub-speakers/browser switches. Mute <node> affects the peer only, not hub lines. Repeat keys and 300 s gaps are per peer; the hub's disabled announcement setting is respected before publication. Local hub game recommendations are unchanged.
- Final full suite: 1279 tests in 1.103 s, OK (1 skipped), using the repo uv environment; localhost fixture needs escalation. Above the existing 0.7674 s timing budget; required timing report run, principal hotspots remain Node web flow and four existing haul transit tests. No unrelated optimization.
- Tests cover both delivery modes, no-frame default, per-peer isolation/gap/repeat, named/disabled callouts, selected-node voice/speakers/browser/mute, live hydrate refresh with unique message IDs, local Dismiss and malformed commands, multi-page Dismiss synchronization, peer Select, and retained opt-in peer hydration/Dismiss. No game keys, live route selection, service restart or deployment.

## Follow-ups

- Hub restart remains on hold. Secondary/main/user own deployment and live hub/forge verification.
- After permitted restart: check hub `/haul?node=forge` list and Dismiss, named hub-only TTS with voice switches, explicit Select on forge, and no forge recommendation frame/callout. A look-only check uses `/haul` without `#route=`.
- Peer/hub recommendation state is in memory, as before. Set delivery true plus restart later to restore node-owned behavior; no code change or revert needed.
