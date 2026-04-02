# Courier

Courier is Rasbhari's notification delivery worker.

## Current Behavior

- consumes events from the events database
- only processes events tagged with `notification`
- resolves a notification class for each event: `urgent`, `today`, `review`, `suggestion`, `digest`, or `system`
- sends ntfy.sh notifications by default with class-aware title, priority, and tags
- sends email through SendGrid when the event also includes the `email` tag
- records successful deliveries in the notifications database with both delivery channel and notification class

## Retries

ntfy.sh delivery currently retries up to 3 times with delays:

- immediate first attempt
- retry after `2s`
- retry after `5s`

If all attempts fail, the event is logged as a failed delivery.

## Queue Progress

Courier is a `QueueProcessor` and stores progress in `queue.queuestats` under the name `Courier`.

Checkpointing is batched by the shared queue processor logic:

- flush every `10` consumed items
- flush when idle

## Required Variables

- `EVENTS_POSTGRES_*`
- `QUEUE_POSTGRES_*`
- `NOTIFICATIONS_POSTGRES_*`
- `LOG_DIR`

Optional:

- `NTFY_BASE_URL`
- `NTFY_TOPIC`
- `SENDGRID_API_KEY`
- `COURIER_SENDER_EMAIL`
- `COURIER_RECEIVER_EMAIL`

If `NTFY_BASE_URL` is unset, Courier defaults to `https://ntfy.sh`.

## Trigger Examples

### ntfy.sh

```json
{
  "event_type": "system:alert",
  "description": "Backup completed",
  "tags": ["notification", "notification_class:system"]
}
```

### email

```json
{
  "event_type": "report:daily",
  "description": "Daily report ready",
  "tags": ["notification", "notification_class:review", "email"]
}
```

## Notification Classes

- `urgent`: immediate interruption for high-severity issues
- `today`: actionable updates that matter in the current day
- `review`: reflection-ready outputs such as reports
- `suggestion`: optional improvement prompts
- `digest`: low-priority bundled summaries
- `system`: operational or infrastructure state

If no explicit `notification_class:<class>` tag is present, Courier falls back conservatively from event type. Today-class delivery is the default.
