# Rasbhari Browser Extension Spec

The browser extension is the first shipped Capture Automation surface.

## Goals

- connect to any Rasbhari instance with `base_url` and `api_key`
- sync browser actions and rules from Rasbhari
- support manual, confirm, and automatic trigger modes
- capture bounded browser context
- stay downloadable from Rasbhari itself during early rollout

## Non-Goals

- no browser surveillance model
- no ML-first behavior
- no browser-store dependency for v1
- no parallel browser meaning system

## Product Model

- Rasbhari defines meaning
- the extension observes browser context
- rules decide whether an action matches
- the extension asks, triggers, or stages the mapped Rasbhari target

## Distribution

- download the bundle from Rasbhari
- load it unpacked in Chrome first
- keep the install flow simple and local

## Setup

1. download the bundle
2. load unpacked in Chrome
3. enter `base_url`
4. enter `api_key`
5. test the connection
6. sync actions and rules

## Reference

- [Browser Action Model](browser-actions.md)
- [Browser Rule Model](browser-rules.md)
- [Browser Sync And Local History](browser-sync-history.md)
