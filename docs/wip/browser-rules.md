# Browser Rule Model

Browser Rules decide when a Browser Action should apply.

They follow the pattern:

- if user does `A`
- on website `B`
- then trigger `C`

## Rule Shape

- `id`
- `name`
- `enabled`
- `browser_action`
- `trigger_mode`
- `conditions`
- `match_scope`
- `target_type`
- `target_config`
- `payload_mapping`
- `priority`

## Trigger Modes

- `manual`
- `confirm`
- `automatic`

## Match Scope

- `domain_equals`
- `domain_in`
- `domain_suffix`
- `url_contains`
- `url_prefix`

## Target Types

- `activity`
- `event`
- `project_update`
- `quick_log`

## Notes

- prefer Activity-first targeting
- keep conditions explainable
- keep rules bounded to the smallest useful scope
- let payload mapping carry browser context explicitly

## Reference

- [Browser Action Model](browser-actions.md)
- [Browser Extension Spec](browser-extension-spec.md)
- [Browser Sync And Local History](browser-sync-history.md)
