# Courier

**Courier** is a notification delivery service that listens to the event stream and sends email notifications for tagged events. It integrates with the Apple ecosystem by triggering Shortcuts automations on iPhone and Apple Watch.

## Overview

Courier operates as a queue processor that continuously monitors the events database. When it finds events tagged with `notification`, it sends email notifications via SendGrid API, which can trigger iOS Shortcuts automations.

**Key Features:**
- Tag-based event filtering (only processes events with `notification` tag)
- Email delivery via SendGrid API
- Integration with Apple Shortcuts for iOS/watchOS notifications
- Persistent notification history in database
- Queue-based processing with automatic state management

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Events    │─────▶│   Courier    │─────▶│    SendGrid     │
│  Database   │      │ (Queue Proc) │      │      API        │
└─────────────┘      └──────────────┘      └─────────────────┘
                             │                       │
                             ▼                       ▼
                    ┌─────────────────┐     ┌───────────────┐
                    │  Notifications  │     │ Email sent to │
                    │    Database     │     │   iPhone      │
                    └─────────────────┘     └───────────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │ Apple Shortcuts │
                                            │   Automation    │
                                            └─────────────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │ iPhone/Watch    │
                                            │  Notification   │
                                            └─────────────────┘
```

## How It Works

### Event Filtering

Courier only processes events tagged with `notification`:

```python
def filter_item(self, event: Event):
    if event.tags and "notification" in event.tags:
        return event
    return None
```

**Example:**
```python
# WILL be processed
{
    "event_type": "contract:invalidation",
    "description": "Gaming contract violated",
    "tags": ["contracts", "notification"]
}

# WILL NOT be processed
{
    "event_type": "exercise:completed",
    "tags": ["health", "tracking"]
}
```

### Notification Creation

When a tagged event is found:
1. Constructs email with SendGrid (`Courier: {event.id}` as subject)
2. Sends email to configured receiver
3. Records notification in database
4. Updates queue cursor

### Error Handling

- SendGrid errors are logged but don't block processing
- Queue cursor always advances (no retries)
- Network exceptions are caught and logged

## Configuration

### Process Registration

Courier is registered in `apps/events.py`:

```python
events_app.register_process(Courier, enabled=False)
```

**Note:** Currently disabled by default to prevent email exhaustion. Enable with `enabled=True`.

### Environment Variables

Required in `.env`:

```bash
# SendGrid Configuration
COURIER_SENDER_EMAIL=notifications@yourdomain.com
COURIER_RECEIVER_EMAIL=your-email@example.com
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Database connections (PostgreSQL)
EVENTS_POSTGRES_DB=events
EVENTS_POSTGRES_USER=postgres
EVENTS_POSTGRES_PASSWORD=yourpassword
EVENTS_POSTGRES_HOST=localhost
EVENTS_POSTGRES_PORT=5432

NOTIFICATIONS_POSTGRES_DB=notifications
NOTIFICATIONS_POSTGRES_USER=postgres
NOTIFICATIONS_POSTGRES_PASSWORD=yourpassword
NOTIFICATIONS_POSTGRES_HOST=localhost
NOTIFICATIONS_POSTGRES_PORT=5432

QUEUE_POSTGRES_DB=queue
QUEUE_POSTGRES_USER=postgres
QUEUE_POSTGRES_PASSWORD=yourpassword
QUEUE_POSTGRES_HOST=localhost
QUEUE_POSTGRES_PORT=5432
```

### SendGrid Setup

1. Sign up at https://sendgrid.com (free tier: 100 emails/day)
2. Generate API Key: Settings > API Keys (with "Mail Send" permissions)
3. Verify sender email: Settings > Sender Authentication

## Database Schema

### Events Table
```sql
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    description TEXT,
    tags TEXT[]  -- PostgreSQL array for filtering
);
```

### Notifications Table
```sql
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(255) NOT NULL,
    notification_data VARCHAR(500) NOT NULL,
    created_at TIMESTAMP
);
```

### Queue Stats Table
```sql
CREATE TABLE IF NOT EXISTS queuestats (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    last_consumed_id INTEGER NOT NULL
);
```

## Usage Examples

### Creating a Notifiable Event

```python
from model.event import Event
from services.events import EventService
from datetime import datetime

event = Event(
    event_type="custom:alert",
    description="Important event occurred!",
    timestamp=datetime.now(),
    tags=["important", "notification"]  # Include "notification" tag
)
EventService().create(event)
```

### Contract Violation (from Sentinel)

```python
invalidation_event = Event(
    event_type="contract:invalidation",
    timestamp=int(time.time()),
    description=f"Contract: {contract.name} was invalidated",
    tags=["contracts", "notification"]
)
event_service.create(invalidation_event)
```

## Integration with Apple Shortcuts

### Setting Up iOS Automation

1. **Open Shortcuts app** → Automation tab
2. **Create Email automation:**
   - Trigger: "When I receive an email"
   - Sender: Your `COURIER_SENDER_EMAIL`
   - Subject contains: "Courier:"
   - Run immediately: ON
3. **Add actions:**
   - Show Notification
   - Title: Email subject
   - Body: Email content
   - Optional: Critical Alert (breaks through Do Not Disturb)

### Advanced Shortcuts

You can parse email content and create conditional notifications:
- Critical alerts for `contract:invalidation`
- Silent logging for `tracking:` events
- Custom formatting based on event type

## Monitoring

### Logs

```bash
tail -f logs/Courier.log
```

Example output:
```
2025-01-15 14:32:11 - Courier - INFO - Email sent via SendGrid: 123
2025-01-15 14:32:11 - Courier - INFO - Item processed successfully
```

### Check Queue Position

```sql
SELECT * FROM queuestats WHERE name = 'Courier';
```

### View Notification History

```sql
SELECT * FROM notifications ORDER BY created_at DESC LIMIT 10;
```

## Troubleshooting

### Notifications not being sent

1. **Check Courier is enabled** in `apps/events.py`
2. **Verify event has `notification` tag:**
   ```sql
   SELECT id, event_type, tags FROM events ORDER BY id DESC LIMIT 10;
   ```
3. **Check SendGrid credentials** in `.env`
4. **Verify SendGrid API key** is valid and sender email is verified

### SendGrid Errors

- **401 Unauthorized**: Invalid API key → regenerate in SendGrid dashboard
- **403 Forbidden**: Sender email not verified → verify in SendGrid settings
- **429 Too Many Requests**: Daily limit exceeded (100 on free tier)

### Queue Stuck

Check and reset if needed:
```sql
-- Check current position
SELECT * FROM queuestats WHERE name = 'Courier';

-- Reset to reprocess all events
UPDATE queuestats SET last_consumed_id = 0 WHERE name = 'Courier';
```

## Performance Tuning

### Rate Limiting

SendGrid free tier: **100 emails/day**

Mitigation strategies:
- Use restrictive tag filtering
- Implement notification cooldown periods
- Upgrade SendGrid plan if needed

### Queue Settings

Default configuration in `courier.py:18-19`:
```python
self.max_queue_size = 10      # Events per batch
self.sleep_time_sec = 5       # Sleep when queue empty
```

Adjust based on your needs:
- Increase `max_queue_size` for high-volume scenarios
- Decrease `sleep_time_sec` for faster response

### Database Indexes

Optimize performance with indexes:
```sql
CREATE INDEX idx_events_tags ON events USING GIN(tags);
CREATE INDEX idx_events_id ON events(id);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
```

## Related Components

- **Events App** (`apps/events.py`): Registers Courier process
- **Event Service** (`services/events.py`): Event database operations
- **Notification Service** (`services/notifications.py`): Notification records
- **QueueProcessor** (`gabru/qprocessor/qprocessor.py`): Base class for queue processing
- **Sentinel** (`processes/sentinel/`): Generates contract violation notifications
- **Heimdall** (`processes/heimdall/`): Can generate tracking notifications

## License

See main project [license](../../license.md).
