# Automation

Automation is Rasbhari's capture vertical.

Its job is to reduce manual logging while keeping the system explainable, privacy-safe, and tied to the normal event bus.

## Capture Automation

Capture Automation is the first track inside Automation.

It starts with the browser extension and will later expand to desktop agents, mobile shortcuts, and selected sensors.

The core rules are simple:

- prefer existing Activities when they already model the action
- emit real events with structured payloads when context is needed
- keep the user able to inspect what matched, what was sent, and why
- support manual, confirm, and automatic trigger modes

## Browser Extension

The browser extension is the first shipped client for Capture Automation.

It connects to Rasbhari with `base_url` and `api_key`, syncs browser actions and rules, and sends browser-triggered actions back into the system.

The detailed contracts live in the WIP docs:

- [Browser Actions](wip/browser-actions.md)
- [Browser Rules](wip/browser-rules.md)
- [Browser Extension Spec](wip/browser-extension-spec.md)
- [Browser Sync And Local History](wip/browser-sync-history.md)
- [Browser Extension Implementation Plan](wip/browser-extension-implementation-plan.md)

## Channel Ladder

- Browser extension first
- Desktop agents next
- Mobile shortcuts after that
- Sensors only when the workflow is privacy-safe and worth the complexity
