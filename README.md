# Brain Relay

**Keep the work intact when you switch AI conversations.**

[中文](README.zh-CN.md) · [MIT license](LICENSE)

A task capsule holds your goal, context, confirmed decisions, candidates, rejected approaches, next steps and source references. Edit it locally, then copy a complete handoff into any AI. You can use the entire main workflow without an account, API key or model.

![Brain Relay, synthetic example](docs/images/workspace-light.png)

## Run in two minutes

Python 3.10 or later is required. From this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
brain-relay
```

Open **http://127.0.0.1:7332**. On Windows, activate with `.venv\Scripts\activate`. `python -m brain_relay` is an equivalent launcher; `--port 7340` selects another port.

1. Click **Load synthetic example** to see a complete capsule, or **New capsule** to start yours.
2. Edit the goal and context. Review decisions individually: candidates remain unconfirmed. Rejected approaches stay separate from actions.
3. Click **Save capsule locally**. Reopen it from **Saved capsules** after a restart.
4. Click **Preview handoff**, review the text, then **Copy** or **Download .txt**.
5. Use **Preview JSON export** and **Download .json** to share a capsule. Another person can **Import JSON**, review, and save it.

The preview is exactly what the download contains. Review source excerpts as well as task text: Relay does **not** automatically redact personal information that you enter.

## What works in this Alpha

- Ordinary editable forms, UTF-8 JSON import/export and atomic local saves.
- Confirmed and candidate decisions remain distinct. No conversion of rejected approaches into next steps.
- Source references, record timestamps and capsule update time appear in the handoff.
- Optional character budget. If the complete text does not fit, Relay refuses a partial handoff and reports the required size and omitted categories. No silent truncation. Characters are Unicode code points, **not model tokens**.
- English/Chinese interface, saved language preference, light/dark themes, keyboard navigation, mobile layout and `/styleguide`.
- Optional model extraction produces a reviewable draft. All extracted decisions start unconfirmed, and no model job saves a capsule automatically.

## Optional model extraction

Configure a chat-completions-compatible provider **before starting** the server. Set `BRAIN_MODEL_URL` to the full endpoint, `BRAIN_MODEL_NAME` to the model identifier and `BRAIN_MODEL_KEY` to its API key. All three must be set, or all must be absent. Local providers requiring no authentication can use a dummy, non-secret value for the key.

Example with a **local** compatible server:

```bash
export BRAIN_MODEL_URL=http://127.0.0.1:1234/v1/chat/completions
export BRAIN_MODEL_NAME=your-local-model
export BRAIN_MODEL_KEY=local-unused
brain-relay
```

For remote providers use HTTPS and inject the key from your secret manager into the process environment. Do not place it in source files, `.env`, shell history or the browser. The application does not read credential stores or `.env` files. It does not use HTTP proxy environment variables. Redirects are rejected, so Authorization is never forwarded to a redirect destination.

Clicking **Extract a draft** sends only the pasted conversation, its task title, schema and extraction instructions to that configured provider. A provider may charge for requests and has its own data handling policy. Manual editing never contacts a model. No real paid model is needed for the test suite.

The server key stays out of browser responses, local capsule files, exports and logs. Upstream errors are returned as a generic failure. Malformed model output fails validation; there is no fallback to a canned result. The model can still misunderstand the conversation or invent content—check every draft and its sources yourself. Reference validity and human confirmation do not prove semantic accuracy.

## Local data and limits

Default data directory: `~/.local/share/brain-relay`. Override with `RELAY_DATA_DIR=/path/to/data`. Back up `capsules.json`; exporting individual capsules is also supported. Updates replace the same capsule ID. If you edit while a save is in progress, the submitted snapshot is saved and newer edits remain visibly unsaved. Outdated previews are discarded after edits, capsule switches or budget changes. Importing an existing ID requires an overwrite confirmation in the UI. Failed writes do not replace the previous file; invalid existing data is reported rather than silently reset.

This is a **single-user, single-process local app**. Use only one process per data directory. There are no accounts, synchronization or encryption at rest. The server binds only `127.0.0.1`, validates loopback Host values and rejects cross-site or missing-CSRF writes. Do not expose the Flask development server to a public network or deploy behind a public reverse proxy. Use your operating system's account and disk protections for local data.

Limits: 100 saved capsules; 100 entries per section; 20,000 characters per main text field; 250,000 UTF-8 bytes per capsule; 500,000 request bytes; 60,000 conversation characters. Jobs: two workers, at most eight outstanding jobs, at most 32 retained records and 30-minute retention. Jobs are in memory and disappear on restart. Provider I/O timeout is 35 seconds; browser polling is bounded and offers **Check status** if the job remains active. A restart preserves saved capsules.

There is no chat-history recorder. Pasted conversations are held only for the extraction request, not stored separately. The user-reviewed extracted fields may contain excerpts; those are part of the capsule and its export.

## API

Start with `GET /api/bootstrap` to obtain a session cookie and `csrf_token`. Send `X-CSRF-Token` and that cookie on writes. Browser callers must be same-origin. All requests/responses are JSON unless noted.

- `GET /`, `GET /styleguide`: interface and live component gallery.
- `GET /healthz`: liveness.
- `GET /api/bootstrap`: saved capsules, CSRF token and `model_configured` (no provider secret).
- `GET /api/example`: an explicit `origin: "demo"` synthetic capsule; never saves itself.
- `POST /api/capsules`, `POST /api/import`: validate and save the capsule object, replacing the same ID.
- `GET /api/capsules/<id>/export`: saved capsule JSON attachment.
- `POST /api/handoff`: `{ "capsule": {...}, "max_chars": null }`; returns `{ "text": "...", "chars": 123 }`. Insufficient budget: HTTP 422, `code: "budget_too_small"`, `required_chars`, `max_chars` and `omitted` counts. No partial text is returned.
- `POST /api/extract`: `{ "conversation": "...", "title": "..." }`; returns HTTP 202 with `task_id`. No configured model: HTTP 503.
- `GET /api/jobs/<task_id>`: `queued`, `running`, `succeeded` with draft `result`, or `failed` with safe `error`. Queue full: HTTP 503. Expired/missing job: HTTP 404.

The complete version-1 schema is illustrated by [the synthetic example](brain_relay/examples/park-map.json). Unknown fields and unsupported schema versions are rejected. Each item has a strict JSON boolean `confirmed`; strings such as `"false"` are invalid. Timestamps include timezone information. `origin` is `manual`, `demo`, or `configured provider`—a provenance hint, not an authenticity signature. The portable domain functions are `validate_capsule(data)` and `render_handoff(capsule, max_chars=None)` in `brain_relay.relay`.

## Development

```bash
python -m pip install '.[test]'
python -m pytest -q
```

Tests exercise round trips, actual persistence after a new app instance, confirmation semantics, budgets, hostile text, cross-site requests, provider failures and a local HTTP fake provider. CI runs on Python 3.10 and 3.14, builds a wheel and tests installed templates/examples outside the checkout. Browser state regressions run in CI on both Python versions. To run them locally, install `.[test,browser]`, run `python -m playwright install chromium`, then `python -m pytest -q`. They launch isolated loopback servers with temporary data and cover editing after save, delayed save/preview/import responses and output invalidation. Without the browser extra, this module is explicitly skipped. No frontend build is required. UI guidance is in [DESIGN.md](DESIGN.md).
