# Brain Relay

## New chat. Same work.

You have already explained the goal, ruled out two approaches and agreed on the next step. Then you open another AI conversation—and spend the first few messages explaining it all again.

**Brain Relay gives your next conversation a starting point: what you are doing, what is settled, what is still open and what happens next.**

[Try the example](#try-the-example) · [Download Alpha](https://github.com/Xfireman/brain-relay/releases/tag/v0.1.0-alpha.1) · [中文](README.zh-CN.md)

Local app · No API key needed for the core workflow · MIT · Alpha

### Keep the decisions that make the work yours

A general summary can flatten the details that matter: “we considered this” becomes “we decided this,” or an approach you rejected comes back as a suggestion.

Relay gives each kind of information its own place. You review the goal, context, decisions, rejected approaches, next steps and references, then copy the handoff into your next AI conversation.

Here is an abridged handoff from the included fictional **Neighborhood park map** example:

> - **Goal:** create a bilingual walking map for new neighbors.
> - **Confirmed:** use a printable A4 map.
> - **Still open:** consider a QR code for accessible routes.
> - **Rejected:** collecting visitor location data.
> - **Next:** verify bus stops and accessible entrances.

That distinction travels with the task. The next assistant can see which ideas need confirmation and which approaches you have already ruled out. You still review what it does with the handoff.

![An editable task and its handoff preview, using a fictional example](docs/images/workspace-light.png)

*Edit on the left, preview the handoff on the right. The downloaded text matches the preview.*

### Bring it to the next place you work

- **Switch AI conversations:** copy a handoff into the next chat without installing a browser extension or connecting accounts.
- **Return tomorrow:** reopen a saved task with its decisions and next steps intact.
- **Hand it to a colleague:** export a reviewed capsule; they can import, edit and continue their own copy.

You choose what goes into a task capsule. The core workflow is manual, local and works without a model. A configured model can help extract a draft from pasted conversation text; its decisions remain unconfirmed until you review them.

## Try the example

Requires Python 3.10+ and Git. On macOS or Linux:

```sh
git clone https://github.com/Xfireman/brain-relay.git
cd brain-relay
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
brain-relay
```

Open **http://127.0.0.1:7332**, then:

1. Click **Load synthetic example**.
2. Notice how the printable map, optional QR code and rejected location tracking stay separate.
3. Add your own next step and **Save capsule locally**.
4. Choose **Preview handoff**, read it, then **Copy** it into a new AI conversation.

For a file you can edit later, use **Preview JSON export** and **Download .json**. Review the full contents before sharing; text and source excerpts you entered are included.

On Windows, use `py -m venv .venv` and `.venv\Scripts\activate`. You can also [download the source archive](https://github.com/Xfireman/brain-relay/releases/tag/v0.1.0-alpha.1) and install from the extracted directory. After installation, `brain-relay` works from any directory; `--port 7340` changes the port.

### A small, deliberate handoff

Use Relay when **a task matters enough that restarting the explanation is getting in the way**. The handoff is editable text, so you can inspect exactly what another AI receives. If you set a character budget that cannot fit the complete handoff, Relay reports the shortfall instead of silently dropping decisions.

This Alpha saves to your computer. Moving work between tools happens by copying text or transferring a file; automatic account synchronization is outside this release.

For a reusable method, see [Brain Recipes](https://github.com/Xfireman/brain-recipes). To ask questions of selected notes, see [Brain Twin](https://github.com/Xfireman/brain-twin).

## Optional model extraction

<details>
<summary>Set up conversation-to-draft extraction</summary>

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

</details>

## Local data and limits

<details>
<summary>Storage, privacy and operating limits</summary>

Default data directory: `~/.local/share/brain-relay`. Override with `RELAY_DATA_DIR=/path/to/data`. Back up `capsules.json`; exporting individual capsules is also supported. Updates replace the same capsule ID. If you edit while a save is in progress, the submitted snapshot is saved and newer edits remain visibly unsaved. Outdated previews are discarded after edits, capsule switches or budget changes. Importing an existing ID requires an overwrite confirmation in the UI. Failed writes do not replace the previous file; invalid existing data is reported rather than silently reset.

This is a **single-user, single-process local app**. Use only one process per data directory. There are no accounts, synchronization or encryption at rest. The server binds only `127.0.0.1`, validates loopback Host values and rejects cross-site or missing-CSRF writes. Do not expose the Flask development server to a public network or deploy behind a public reverse proxy. Use your operating system's account and disk protections for local data.

Limits: 100 saved capsules; 100 entries per section; 20,000 characters per main text field; 250,000 UTF-8 bytes per capsule; 500,000 request bytes; 60,000 conversation characters. Jobs: two workers, at most eight outstanding jobs, at most 32 retained records and 30-minute retention. Jobs are in memory and disappear on restart. Provider I/O timeout is 35 seconds; browser polling is bounded and offers **Check status** if the job remains active. A restart preserves saved capsules.

There is no chat-history recorder. Pasted conversations are held only for the extraction request, not stored separately. The user-reviewed extracted fields may contain excerpts; those are part of the capsule and its export.

</details>

## API

<details>
<summary>API endpoints and capsule format</summary>

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

</details>

## Development

<details>
<summary>Tests, browser checks and development setup</summary>

```bash
python -m pip install '.[test]'
python -m pytest -q
```

Tests exercise round trips, actual persistence after a new app instance, confirmation semantics, budgets, hostile text, cross-site requests, provider failures and a local HTTP fake provider. CI runs on Python 3.10 and 3.14, builds a wheel and tests installed templates/examples outside the checkout. Browser state regressions run in CI on both Python versions. To run them locally, install `.[test,browser]`, run `python -m playwright install chromium`, then `python -m pytest -q`. They launch isolated loopback servers with temporary data and cover editing after save, delayed save/preview/import responses and output invalidation. Without the browser extra, this module is explicitly skipped. No frontend build is required. UI guidance is in [DESIGN.md](DESIGN.md).

</details>
