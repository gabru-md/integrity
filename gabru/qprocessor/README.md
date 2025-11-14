# QueueProcessor

The **QueueProcessor** is a generic, database-backed queue processing system designed for reliable event-driven architectures. It enables background workers to consume and process items from database tables with automatic crash recovery and progress tracking.

## Overview

Unlike traditional message queues (RabbitMQ, Redis, etc.), QueueProcessor uses the database itself as the message queue. This approach provides several advantages for IoT and edge computing scenarios:

- **Simplicity**: No additional infrastructure needed
- **Reliability**: Database ACID guarantees
- **Debuggability**: Query the queue directly with SQL
- **Crash Recovery**: Automatic resume from last processed item
- **Backpressure**: Built-in batch size limits

## Architecture

```
Database Table (Source)
    ↓
QueueProcessor polls for new items (ID > last_consumed_id)
    ↓
Loads batch into in-memory queue
    ↓
filter_item() - Optional filtering
    ↓
_process_item() - Your custom processing logic
    ↓
Updates last_consumed_id in queuestats table
    ↓
Repeat
```

## Core Concepts

### Queue Statistics Table

Progress is tracked in a dedicated `queuestats` table:

```sql
CREATE TABLE queuestats (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,  -- Processor name
    last_consumed_id INT                 -- Last processed item ID
);
```

Each QueueProcessor instance has a row in this table that persists its progress.

### Processing Flow

1. **Poll**: Query source table for items where `id > last_consumed_id`
2. **Batch**: Load up to `max_queue_size` items
3. **Filter**: Apply `filter_item()` to skip unwanted items
4. **Process**: Call `_process_item()` for each filtered item
5. **Update**: Increment `last_consumed_id` after each item
6. **Sleep**: If no items available, sleep for `sleep_time_sec`
7. **Repeat**: Continue until `running = False`

### State Management

- **last_consumed_id**: Tracks progress, stored in database
- **queue**: In-memory buffer of items to process
- **running**: Boolean flag to stop the processor
- **enabled**: Whether the processor can run (managed by ProcessManager)

## Basic Usage

### 1. Create a QueueProcessor

```python
from gabru.qprocessor.qprocessor import QueueProcessor
from services.events import EventService
from model.event import Event

class MyEventProcessor(QueueProcessor[Event]):
    def __init__(self, name="MyProcessor", enabled=False):
        super().__init__(
            name=name,
            service=EventService(),  # Service to read items
            enabled=enabled
        )
        # Configure polling behavior
        self.sleep_time_sec = 5      # How long to wait when queue is empty
        self.max_queue_size = 10     # How many items to fetch per batch

    def filter_item(self, event: Event):
        """
        Return None to skip this item, or return the item to process it.
        This runs BEFORE _process_item() for every fetched item.
        """
        # Only process events with 'notification' tag
        if "notification" in event.tags:
            return event
        return None  # Skip this event

    def _process_item(self, event: Event) -> bool:
        """
        Process a single filtered item.
        Return True on success, False on failure.
        """
        try:
            self.log.info(f"Processing event: {event.event_type}")
            # Your custom processing logic here
            send_email(event.description)
            return True
        except Exception as e:
            self.log.exception(e)
            return False  # Mark as failed but still advances last_consumed_id
```

### 2. Register with an App

```python
from gabru.flask.app import App
from model.event import Event
from services.events import EventService

events_app = App('Events', EventService(), Event)

# Register the processor to run with the app
events_app.register_process(MyEventProcessor, enabled=True)
```

### 3. Start via Server

The ProcessManager automatically starts enabled processes:

```python
from gabru.flask.server import Server

class MyServer(Server):
    def __init__(self):
        super().__init__("MyServer")
        self.register_app(events_app)

server = MyServer()
server.run_server()  # Starts process manager, which starts processors
```

## Configuration Options

### Constructor Parameters

```python
def __init__(self, name, service: ReadOnlyService[T], enabled=False):
    super().__init__(name=name, enabled=enabled, daemon=True)
    self.service = service           # Service to read items from
    self.sleep_time_sec = 5          # Poll interval when queue is empty
    self.max_queue_size = 10         # Batch size for fetching items
```

### Tuning Guidelines

**sleep_time_sec:**
- **Low (1-5s)**: Near real-time processing, higher CPU usage
- **Medium (5-15s)**: Balanced for most use cases
- **High (30-60s)**: Low-priority background tasks

**max_queue_size:**
- **Small (5-20)**: Lower memory, more frequent DB queries
- **Medium (20-100)**: Balanced for most use cases
- **Large (100-1000)**: Higher throughput, more memory usage

## Advanced Patterns

### Pattern 1: Tag-Based Filtering

Process only events with specific tags:

```python
def filter_item(self, event: Event):
    required_tags = {"urgent", "notification"}
    if required_tags.intersection(set(event.tags)):
        return event
    return None
```

### Pattern 2: Time-Based Filtering

Process only during certain hours:

```python
from datetime import datetime

def filter_item(self, event: Event):
    current_hour = datetime.now().hour
    # Only process during business hours (9 AM - 5 PM)
    if 9 <= current_hour < 17:
        return event
    return None
```

### Pattern 3: Conditional Processing

Different logic based on item properties:

```python
def _process_item(self, event: Event) -> bool:
    if event.event_type == "error":
        return self.handle_error_event(event)
    elif event.event_type == "warning":
        return self.handle_warning_event(event)
    else:
        return self.handle_normal_event(event)
```

### Pattern 4: External API Integration

Batch external API calls to reduce overhead:

```python
class BatchAPIProcessor(QueueProcessor[Event]):
    def __init__(self, name="BatchAPI", enabled=False):
        super().__init__(name, EventService(), enabled)
        self.batch = []
        self.batch_size = 50

    def _process_item(self, event: Event) -> bool:
        self.batch.append(event)

        if len(self.batch) >= self.batch_size:
            # Send batch to external API
            success = api.send_batch(self.batch)
            self.batch.clear()
            return success

        return True  # Item added to batch successfully
```

### Pattern 5: Multi-Stage Processing

Chain multiple processors:

```python
# Stage 1: Validate events
class EventValidator(QueueProcessor[Event]):
    def _process_item(self, event: Event) -> bool:
        if self.is_valid(event):
            # Write to validated_events table
            validated_event_service.create(ValidatedEvent(**event.dict()))
            return True
        return False

# Stage 2: Process validated events
class ValidatedEventProcessor(QueueProcessor[ValidatedEvent]):
    def _process_item(self, event: ValidatedEvent) -> bool:
        # Process only validated events
        return self.do_processing(event)
```

## Error Handling

### Handling Process Failures

QueueProcessor advances `last_consumed_id` even on failures to prevent getting stuck:

```python
def _process_item(self, event: Event) -> bool:
    try:
        dangerous_operation(event)
        return True
    except RetryableError as e:
        # Log but don't fail - item will be skipped
        self.log.warning(f"Retryable error, skipping: {e}")
        return False  # Advances to next item
    except FatalError as e:
        # Log critical error
        self.log.exception(e)
        # Could implement dead-letter queue here
        dead_letter_service.create(FailedEvent(event, str(e)))
        return False  # Still advances to prevent blocking
```

### Dead Letter Queue Pattern

```python
class RobustProcessor(QueueProcessor[Event]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_event_service = FailedEventService()
        self.max_retries = 3

    def _process_item(self, event: Event) -> bool:
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.process_with_external_api(event)
                return True
            except TemporaryError as e:
                retry_count += 1
                self.log.warning(f"Retry {retry_count}/{self.max_retries}: {e}")
                time.sleep(2 ** retry_count)  # Exponential backoff

        # All retries failed - move to dead letter queue
        self.failed_event_service.create(FailedEvent(
            event_id=event.id,
            error="Max retries exceeded",
            payload=event.dict()
        ))
        return False
```

## Monitoring and Debugging

### Check Processor Progress

Query the queuestats table:

```sql
SELECT name, last_consumed_id
FROM queuestats
WHERE name = 'MyProcessor';
```

### Count Unprocessed Items

```python
# Get processor's current position
processor_stats = queue_service.find_all(filters={"name": "MyProcessor"})[0]
last_id = processor_stats.last_consumed_id

# Count remaining items
remaining = event_service.count_items_after(last_id)
print(f"Unprocessed items: {remaining}")
```

### Log Analysis

QueueProcessor logs important events:

```
# Normal operation
INFO - MyProcessor - Nothing to do, waiting for 5s
INFO - MyProcessor - Item processed successfully

# Failures
WARN - MyProcessor - Failure to process item
ERROR - MyProcessor - Error processing item from the queue
```

### Reset Processor

To reprocess all items from the beginning:

```sql
UPDATE queuestats
SET last_consumed_id = 0
WHERE name = 'MyProcessor';
```

Then restart the processor.

## Best Practices

### 1. Idempotent Processing

Design `_process_item()` to be idempotent (safe to run multiple times):

```python
def _process_item(self, event: Event) -> bool:
    # Check if already processed
    if notification_service.exists_for_event(event.id):
        self.log.info(f"Event {event.id} already processed, skipping")
        return True

    # Process and mark as done
    send_notification(event)
    notification_service.mark_processed(event.id)
    return True
```

### 2. Graceful Shutdown

Clean up resources in the `stop()` method:

```python
class CleanProcessor(QueueProcessor[Event]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.external_client = ExternalAPIClient()

    def stop(self):
        # Flush pending operations
        self.external_client.flush()
        self.external_client.close()
        super().stop()
```

### 3. Efficient Filtering

Filter early to avoid unnecessary processing:

```python
def filter_item(self, event: Event):
    # Fast checks first
    if event.event_type not in self.allowed_types:
        return None

    # Expensive checks only if necessary
    if self.is_duplicate(event):
        return None

    return event
```

### 4. Logging Strategy

Log enough for debugging but not too much:

```python
def _process_item(self, event: Event) -> bool:
    # Log start of processing
    self.log.info(f"Processing event {event.id}: {event.event_type}")

    try:
        result = self.do_work(event)
        # Log important outcomes
        if result.has_warnings:
            self.log.warning(f"Event {event.id} processed with warnings: {result.warnings}")
        return True
    except Exception as e:
        # Always log exceptions
        self.log.exception(f"Failed to process event {event.id}: {e}")
        return False
```

### 5. Configuration Management

Use environment variables or config files:

```python
import os

class ConfigurableProcessor(QueueProcessor[Event]):
    def __init__(self, name="Configurable", enabled=False):
        super().__init__(name, EventService(), enabled)
        # Load from environment
        self.sleep_time_sec = int(os.getenv("PROCESSOR_SLEEP_TIME", "5"))
        self.max_queue_size = int(os.getenv("PROCESSOR_BATCH_SIZE", "10"))
        self.api_endpoint = os.getenv("EXTERNAL_API_URL")
```

## Comparison with Traditional Message Queues

| Feature | QueueProcessor (DB) | RabbitMQ/Redis |
|---------|---------------------|----------------|
| Infrastructure | PostgreSQL only | Separate service |
| Setup Complexity | Low | Medium-High |
| Crash Recovery | Automatic | Manual/Complex |
| Debugging | SQL queries | Queue-specific tools |
| Guaranteed Delivery | Yes (ACID) | Depends on config |
| Throughput | Medium (100-1000/s) | High (10k+/s) |
| Latency | Medium (1-10s) | Low (ms) |
| Best For | IoT, edge, simple systems | High-throughput, low-latency |

## Real-World Examples

### Example 1: Courier (Notification Service)

See `processes/courier/courier.py`:

```python
class Courier(QueueProcessor[Event]):
    def filter_item(self, event: Event):
        # Only process events tagged with 'notification'
        return event if "notification" in event.tags else None

    def _process_item(self, event: Event) -> bool:
        # Send email notification
        send_email(event.description)
        # Trigger iOS shortcut
        trigger_shortcut(event.event_type)
        return True
```

### Example 2: Sentinel (Contract Validator)

See `processes/sentinel/sentinel.py`:

```python
class Sentinel(QueueProcessor[Event]):
    def filter_item(self, event: Event):
        # Only process trigger events that have associated contracts
        contracts = contract_service.find_by_trigger(event.event_type)
        return event if contracts else None

    def _process_item(self, event: Event) -> bool:
        # Validate contracts against historical events
        for contract in self.get_contracts_for_event(event):
            if self.is_contract_violated(contract, event):
                self.publish_violation_event(contract, event)
        return True
```

## Troubleshooting

### Problem: Processor Not Starting

**Check:**
1. Is `enabled=True` when registering the process?
2. Is ProcessManager started? (`server.start_process_manager()`)
3. Check logs for initialization errors

### Problem: Items Not Being Processed

**Check:**
1. Are items actually in the source table?
2. What is `last_consumed_id` vs max ID in table?
3. Is `filter_item()` filtering everything out?
4. Check processor logs for errors

### Problem: Processor Running Too Fast/Slow

**Tune:**
- Increase `sleep_time_sec` to slow down
- Decrease `sleep_time_sec` for faster polling
- Adjust `max_queue_size` for batch processing

### Problem: Memory Usage Too High

**Solutions:**
- Reduce `max_queue_size`
- Process items more quickly in `_process_item()`
- Check for memory leaks in your processing logic

## Related Documentation

- [Gabru Framework](../readme.md) - Overall framework guide
- [Process Layer](../readme.md#3-process-layer) - Base Process class
- [ProcessManager](../readme.md#processmanager-processpy) - Lifecycle management
- [Courier Process](../../processes/courier/readme.md) - Real-world example
- [Sentinel Process](../../processes/sentinel/readme.md) - Contract validation example
