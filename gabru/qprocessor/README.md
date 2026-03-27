# QueueProcessor

`QueueProcessor` is Gabru's database-backed stream processor. In Rasbhari it is used for notifications, promises, project updates, and skill XP progression.

## Core Idea

Instead of an external queue broker, processors read rows from a database table in ID order and remember progress in `queue.queuestats`.

```text
source table
    -> fetch rows with id > last_consumed_id
    -> optional filter
    -> process matching items
    -> checkpoint progress
```

## Queue State

Each processor has a row in the queue database:

```sql
CREATE TABLE queuestats (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    last_consumed_id INT
);
```

## Current Checkpoint Behavior

The current implementation is batched:

- rows are consumed one by one in memory
- `last_consumed_id` is advanced in memory for every consumed row
- queue state is flushed every `10` consumed items by default
- queue state is also flushed when the queue goes idle

This is the current durability/performance tradeoff in the codebase.

## Minimal Example

```python
from gabru.qprocessor.qprocessor import QueueProcessor
from model.event import Event
from services.events import EventService

class MyProcessor(QueueProcessor[Event]):
    def __init__(self, **kwargs):
        super().__init__(name="MyProcessor", service=EventService(), **kwargs)
        self.sleep_time_sec = 5
        self.max_queue_size = 10

    def filter_item(self, event: Event):
        if "important" in (event.tags or []):
            return event
        return None

    def _process_item(self, event: Event) -> bool:
        self.log.info(f"Processing {event.id}")
        return True
```

## Current Rasbhari Processors Using This

- `Courier`
- `PromiseProcessor`
- `ProjectUpdater`
- `SkillXPProcessor`

## Important Operational Notes

- Processors always consume in ID order.
- Filtered items still advance queue progress.
- Failed `_process_item()` calls still advance queue progress in the current design, so processors do not get stuck on one bad row.
- If queue state is lost or points at an older ID, processors can replay older events.

## Tuning

Useful settings on a processor instance:

- `sleep_time_sec`
- `max_queue_size`
- `checkpoint_every`

For lower replay risk, reduce `checkpoint_every`.
For fewer DB writes, increase it.
