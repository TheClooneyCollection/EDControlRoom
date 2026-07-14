# Iteration Log

- Area: `control-room`
- Title: `friendly-spansh-errors`
- Started: `2026-07-14 15:14`

## Summary

- Translate Spansh route validation responses into actionable web errors while retaining the upstream response body in server logs.

## Changes

- `edap/control_room/server/app.py`: added Spansh HTTP error parsing; missing finishing systems return HTTP 400 with `Spansh says could not find target system`, other upstream API errors retain their message, and 5xx responses remain 502.
- `tests/test_route_compare_endpoint.py`: added endpoint coverage for the missing-target response.

## Follow-ups

- Keep validating system names before submitting routes; no retry is attempted for Spansh request-validation errors.
