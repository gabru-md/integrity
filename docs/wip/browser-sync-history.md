# Browser Sync And Local History

The browser extension should sync a small Rasbhari-owned automation bundle and keep a local record of what it did.

## Connection

- `base_url`
- `api_key`
- connection test

## Synced Bundle

- browser actions
- browser rules
- target metadata
- sync timestamp

## Local Cache

- keep the last good sync
- keep working when the server is temporarily unreachable
- show when config is stale

## Local History

Each entry should record:

- timestamp
- matched rule
- target
- payload sent
- confirmation state
- Rasbhari response

## Reference

- [Browser Action Model](browser-actions.md)
- [Browser Rule Model](browser-rules.md)
- [Browser Extension Spec](browser-extension-spec.md)
