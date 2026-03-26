# Courier

**Courier** is a notification delivery service that listens to the event stream and dispatches alerts via **ntfy.sh** (default) or **Email** (SendGrid). It enables real-time monitoring on iPhone, Apple Watch, and desktop.

## Overview

Courier operates as a `QueueProcessor` that monitors the events database. It filters for events tagged with `notification` and dispatches them through the appropriate channel based on additional tags.

**Key Features:**
- **ntfy.sh Integration**: Default delivery method for instant push notifications on iOS/Android.
- **Email Delivery**: Fallback or secondary delivery via SendGrid (triggered by `email` tag).
- **Tag-Based Routing**: Intelligent dispatching based on event tags.
- **Persistent History**: Every dispatched notification is logged in the `notifications` table.
- **Configurable**: ntfy topics and email credentials managed via environment variables.

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Events    │─────▶│   Courier    │─────▶│     ntfy.sh     │ (Default)
│  Database   │      │ (Queue Proc) │      │      API        │
└─────────────┘      └──────────────┘      └─────────────────┘
                             │                       │
                             │             ┌─────────────────┐
                             ├────────────▶│    SendGrid     │ (If 'email' tag)
                             │             │      API        │
                             │             └─────────────────┘
                             ▼                       
                    ┌─────────────────┐     
                    │  Notifications  │     
                    │    Database     │     
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

### Routing Logic

Once an event passes the filter, Courier decides how to send it:
1. **Email**: If the tags contain `email`, it uses SendGrid.
2. **ntfy.sh**: If the `email` tag is absent, it defaults to ntfy.sh using the configured topic.

### ntfy.sh Integration
Courier sends a POST request to `https://ntfy.sh/{NTFY_TOPIC}`. 
- **Title**: `Rasbhari Alert: {event_type}`
- **Priority**: High
- **Tags**: Includes `warning`, `robot`, and any custom tags from the event.

## Configuration

### Environment Variables

Update your `.env` file:

```bash
# ntfy.sh Configuration
NTFY_TOPIC=rasbhari-alert-7eh5b-5kja54-28nag3

# SendGrid Configuration (Optional for email)
COURIER_SENDER_EMAIL=notifications@yourdomain.com
COURIER_RECEIVER_EMAIL=your-email@example.com
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Process Registration

Registered in `apps/events.py`:

```python
# Enabled by default as ntfy is lightweight
events_app.register_process(Courier, enabled=True)
```

## Usage Examples

### Standard ntfy Notification (Default)

```python
event = Event(
    event_type="security:motion",
    description="Motion detected in living room",
    tags=["notification", "security"]
)
# Result: Push notification sent to ntfy.sh topic
```

### Email Notification

```python
event = Event(
    event_type="system:report",
    description="Daily summary report...",
    tags=["notification", "email"]
)
# Result: Email sent via SendGrid
```

## Monitoring

### Logs
```bash
tail -f logs/Courier.log
```

### Database History
```sql
SELECT * FROM notifications ORDER BY created_at DESC LIMIT 10;
```

## Troubleshooting

1. **ntfy not received**: Ensure the `NTFY_TOPIC` matches the one you are subscribed to in the ntfy app.
2. **Email not received**: Check `SENDGRID_API_KEY` and ensure the sender email is verified in SendGrid.
3. **Queue stuck**: Check `queuestats` table for the `Courier` entry and reset `last_consumed_id` to 0 if necessary.
