# Import Foundation

Rasbhari now has a shared import foundation for future calendar, device, webhook, and external-system integrations.

## Goal

The import layer is designed to keep integrations small and predictable:

- adapters fetch source-specific records
- the pipeline normalizes them
- Rasbhari stores a durable import record
- the pipeline emits a normal event into the event bus

This keeps integrations compatible with promises, skills, reports, and notifications without every new source inventing its own ingestion model.

## Core Pieces

- [services/import_pipeline.py](../services/import_pipeline.py)
  - defines `NormalizedImportItem`
  - defines the `ImportSourceAdapter` protocol
  - converts normalized items into persisted import records and event bus entries
- [services/import_records.py](../services/import_records.py)
  - stores imported source records in `import_records`
  - dedupes by `(user_id, source_type, source_name, external_id)`
  - falls back to a deterministic fingerprint
- [model/import_record.py](../model/import_record.py)
  - canonical stored shape for imported records

## Adapter Shape

A future adapter only needs to implement:

```python
class ImportSourceAdapter(Protocol):
    def fetch_records(self, user_id: int, since: Optional[datetime] = None) -> list[NormalizedImportItem]:
        ...
```

Each returned `NormalizedImportItem` should already contain:

- `source_type`
- `source_name`
- `external_id` when the upstream source has one
- `occurred_at`
- `title`
- `description`
- `tags`
- `raw_payload`
- `normalized_event_type`

## Event Bus Compatibility

Imported records become normal Rasbhari events with stable tags like:

- `imported`
- `source:<source-type>`
- `source_name:<source-name>`

Plus any normalized tags provided by the adapter.

This means imported calendar entries, device sightings, or other signals can flow through existing:

- promises
- skills
- reports
- notifications
- dashboard and report surfaces

without adding special-case downstream logic.

## Design Rules

- adapters should be thin and source-specific
- normalization belongs in the shared pipeline
- imported data should be deduped before emitting events
- event emission should use explicit normalized event types
- raw payloads should be stored for later debugging or reprocessing

## What This Does Not Do Yet

- no specific calendar integration
- no specific device import integration
- no scheduling or polling layer for adapters
- no user-facing import management UI yet

This is the foundation those features should build on later.
