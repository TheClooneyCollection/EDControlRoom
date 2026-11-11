# Command API

Run Control Room commands over HTTP, so scripts, `curl`, or automation tools like Shortcuts can start routines such as `undock`, `dock`, or `jump`.

## Find Host, Port, and Token

Start a server as usual (`lan`, `serve`, or `local`, see [getting-started.md](getting-started.md)).

- **Host and port:** the address in the startup log, for example `Uvicorn running on http://192.168.1.50:8765`. The default port is `8765`; change it with `--port`.
- **Token:** `edcr` unless you started the server with `--token <your-token>`.

Send the token as `Authorization: Bearer <token>` or as `?access_token=<token>` in the URL. A missing or wrong token gets `401`, like every other `/api` route.

## Run a Command

`POST /api/command` with a JSON body:

```json
{"raw_input": "undock", "skip_delay": false}
```

- `raw_input`: the command text, exactly as you would type it in the Control Room command box. See [commands-reference.md](commands-reference.md).
- `skip_delay` (optional): `true` skips the configured start delay for this command, same as a leading `!`.

```sh
HOST=http://192.168.1.50:8765
TOKEN=edcr

curl -X POST "$HOST/api/command" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"raw_input": "undock"}'

curl -X POST "$HOST/api/command" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"raw_input": "dock", "skip_delay": true}'

# Pause a running two-way haul at the next station
curl -X POST "$HOST/api/command" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"raw_input": "pause"}'
```

The command runs on the server, so its output shows in the server activity log and on the web `/controls` page.

## Stop a Running Routine

The text command `stop` only freezes haul session stats. To cancel a routine, use `POST /api/stop`:

```sh
# Cancel now (same as STOP NOW on /controls)
curl -X POST "$HOST/api/stop" -H "Authorization: Bearer $TOKEN"

# Let a haul finish the current run first
curl -X POST "$HOST/api/stop" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"mode": "after_run"}'
```

## Responses

`/api/command` success (`200`):

```json
{"accepted": true, "raw_input": "undock", "routine_active": true, "active_routine_name": null}
```

`routine_active` and `active_routine_name` are the state right after the command was handed over. A routine with a start delay already counts as active.

| Status | Meaning |
| --- | --- |
| `200` | Command handed to Control Room (`accepted: true`). It can still fail later, check the activity log. |
| `400` | Body is not JSON, `raw_input` is missing or empty, `skip_delay` is not a boolean, or `/api/stop` got an unknown `mode`. |
| `401` | Missing or wrong token. |
| `409` | Refused because a routine is already running (`accepted: false`, `detail` names it). For `/api/stop`: no routine is running. |
| `503` | This server cannot run commands. |

## Limits

- Commands that open a prompt or only show local info (`haul`, `dest`, `home`, `market`, `help`, `history`, `replay`, `commands`) are not run by the server; the activity log reports them as unknown. Use the web pages for those.
- `200` means accepted, not finished. Poll `GET /hydrate` (`routine.routine_active`) or watch `/controls` to see when a routine ends.
