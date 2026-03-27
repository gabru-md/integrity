# Courier

Courier is Rasbhari's notification delivery worker.

## Current Behavior

- consumes events from the events database
- only processes events tagged with `notification`
- sends ntfy.sh notifications by default
- sends email through SendGrid when the event also includes the `email` tag
- records successful deliveries in the notifications database

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

- `NTFY_TOPIC`
- `SENDGRID_API_KEY`
- `COURIER_SENDER_EMAIL`
- `COURIER_RECEIVER_EMAIL`

## Trigger Examples

### ntfy.sh

```json
{
  "event_type": "system:alert",
  "description": "Backup completed",
  "tags": ["notification"]
}
```

### email

```json
{
  "event_type": "report:daily",
  "description": "Daily report ready",
  "tags": ["notification", "email"]
}
```
