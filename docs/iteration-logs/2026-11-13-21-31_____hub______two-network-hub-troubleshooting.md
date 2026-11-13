# Iteration Log

- Area: `hub`
- Title: `two-network-hub-troubleshooting`
- Started: `2026-11-13 21:31`

## Summary

- A peer could not find the hub because the hub machine was on two subnets (Wi-Fi on one, Ethernet on another) and the peer was on the other one. The hub binds and advertises over mDNS on one address only, normally the default-route one.

## Changes

- `docs/user/hub.md`: the `no hub found on the LAN` troubleshooting row now covers a hub on two networks and points at the `Uvicorn running on` line to see which address it uses.

## Follow-ups

- None. Code unchanged; advertising on every interface was not requested.
