# Browser Extension Sync And Local History

This document defines how the Rasbhari browser extension should:

- connect to a Rasbhari instance using `base_url` and `api_key`
- sync user-specific browser actions and rules
- keep a local cache of the synced configuration
- record local execution history for trust and debugging

It complements the broader [browser extension spec](browser-extension-spec.md), [browser action model](browser-actions.md), and [browser rule model](browser-rules.md).

## Why This Exists

The browser extension is meant to be generic.

That means:

- it should not hardcode one Rasbhari deployment
- it should not hardcode one user's rules
- it should not become the canonical source of automation meaning

Rasbhari should own the meaning and configuration.
The extension should own local execution and local visibility.

That split requires an explicit sync and history model.

## Connection Model

The extension should connect to any Rasbhari instance using:

- `base_url`
- `api_key`

### `base_url`

The root address of the target Rasbhari instance, for example:

- `http://rasbhari.local:5000`
- `https://rasbhari.onrender.com`
- `http://100.x.x.x:5000`

The extension should normalize this value so later API calls behave consistently.

### `api_key`

The Rasbhari user API key already supported by the product.

The extension should use it the same way other Rasbhari API clients do:

- `X-API-Key: <key>`
- or `Authorization: ApiKey <key>` if needed later

### Connection Test

The extension should provide a `Test Connection` action that verifies:

- the URL is reachable
- the API key is valid
- the response belongs to a usable Rasbhari instance

The test should fail clearly if:

- the URL is wrong
- the key is invalid
- the server is unreachable
- the response is not Rasbhari-compatible

## Rasbhari As Configuration Authority

Rasbhari should own:

- browser action definitions
- user-specific browser rules
- target metadata
- trigger defaults
- any future action labels or domain-specific customizations

The extension should not be the long-term source of truth for those things.

The extension should own:

- connection settings
- local cached config
- local confirmation state
- local history

That keeps the extension reusable and keeps product meaning inside Rasbhari.

## Sync Model

The extension should sync a user-specific bundle from Rasbhari.

That bundle should conceptually include:

- extension metadata
- available browser actions
- active browser rules
- target metadata needed to execute those rules
- sync timestamps or version markers

### First Sync Flow

1. user enters `base_url`
2. user enters `api_key`
3. extension validates connection
4. extension requests browser automation config
5. Rasbhari returns the user's action and rule bundle
6. extension stores that bundle locally
7. extension becomes ready to evaluate rules and show actions

### Ongoing Sync Flow

The extension should support:

- manual resync
- startup sync
- periodic background refresh later if useful

For the first version, manual resync plus startup sync is enough.

## Suggested Sync Shape

The extension should think in terms of a single synced automation package.

That package should conceptually contain:

- `instance`
- `user`
- `actions`
- `rules`
- `synced_at`
- optional `version`

### `instance`

Basic metadata about the Rasbhari instance, such as:

- normalized base URL
- product label

### `user`

Basic user metadata useful for the extension UI, such as:

- user id
- display name
- experience mode if relevant later

### `actions`

The browser actions available to this user.

These should align with the shared browser action model.

### `rules`

The enabled and disabled browser rules for the user.

The extension should cache disabled rules too, so local state matches Rasbhari state and the UI can explain what is configured even if not active.

### `synced_at`

Timestamp of the last successful sync.

### `version`

Optional config version marker so the extension can detect changes more explicitly later.

## Local Cache

The extension should keep a local cache of the last successful sync.

The local cache is needed so the extension can:

- remain functional between syncs
- evaluate rules without asking Rasbhari on every browser event
- remain understandable even if the server is temporarily unreachable

### Cache behavior

- successful sync replaces the local cached config
- failed sync leaves the previous config intact
- the extension should make clear whether it is using stale config

This prevents network fragility from making the extension useless.

## Confirmation Lifecycle

For `confirm` rules, the extension should maintain lightweight local pending state.

That pending state should include:

- which rule matched
- what browser action was proposed
- what payload would be sent
- when the proposal was created

When the user:

- confirms: send the execution request and write a history entry
- cancels: do not send, but still write a history entry

This makes confirmation behavior visible rather than invisible.

## Execution Model

When a rule leads to a send, the extension should record:

- what rule matched
- what target it intended to trigger
- what payload it sent
- what Rasbhari returned

The extension should not just record "success" or "failure" with no context.

The user should be able to understand what the extension actually attempted.

## Local History

The extension should maintain a local history of its own behavior.

This history is for:

- trust
- debugging
- product transparency

### Each history entry should include:

- `timestamp`
- `rule_id`
- `rule_name`
- `browser_action`
- `trigger_mode`
- `matched_url`
- `matched_domain`
- short payload summary
- `confirmation_required`
- `confirmation_result`
- `send_result`
- Rasbhari response summary

### Suggested value examples

`confirmation_result`:

- `not_needed`
- `confirmed`
- `cancelled`
- `expired`

`send_result`:

- `sent`
- `failed`
- `not_sent`

### Response summary

The history entry should capture a compact summary of what Rasbhari returned, such as:

- created event id
- triggered activity id
- created project update id
- error message

The goal is not to mirror the entire response body, only the useful result.

## History Retention

The first version can keep history local and lightweight.

Recommended behavior:

- keep the most recent 50 to 100 entries
- allow clearing local history
- do not sync local history back to Rasbhari by default

That keeps the extension simple and privacy-respecting.

## History States

History should cover more than successful sends.

It should include:

- matched but cancelled
- matched and confirmed
- matched and auto-sent
- failed to send
- failed to sync

That gives the user a truthful picture of the extension's behavior.

## Failure Handling

The extension should distinguish between:

- connection failure
- sync failure
- rule-match success but send failure
- user cancellation

These are not the same failure mode, and the history should not flatten them into one generic error.

## Suggested User Flows

### Flow 1: Initial Sync

1. user enters `base_url` and `api_key`
2. extension validates connection
3. extension syncs automation config
4. extension shows:
   - connected instance
   - last sync time
   - available action count
   - active rule count

### Flow 2: Confirm Rule Match

1. a browser rule matches
2. extension prepares proposed payload
3. extension asks for confirmation
4. user confirms
5. extension sends request to Rasbhari
6. extension records local history with confirmation result and Rasbhari response summary

### Flow 3: Auto Rule Match

1. a strong deterministic rule matches
2. extension sends automatically
3. extension records local history entry
4. user can inspect what happened afterward

### Flow 4: Cancelled Match

1. a confirm rule matches
2. extension asks
3. user cancels
4. extension records a local history entry marked `cancelled`

This is important because the user should still see that the extension proposed something.

## Minimal First API Expectations

This document does not define the exact API routes, but the extension will need Rasbhari endpoints for:

- connection validation
- sync package fetch
- execution of browser-triggered actions

Those endpoints should remain thin and should route back into normal Rasbhari app and event flows.

## v1 Recommendation

The first implementation should support:

- `base_url` + `api_key` connection
- startup sync
- manual resync
- local cached rules and actions
- local history
- visible confirmation handling
- compact response summaries

This is enough to make the extension trustworthy and usable without overbuilding live sync or full remote audit.

## Relationship To Rasbhari

The sync model keeps Rasbhari as the source of truth.
The history model keeps the extension trustworthy to the user.

Together they allow the browser extension to behave like a real Rasbhari surface rather than a detached plugin with hidden behavior.
