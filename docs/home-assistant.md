# Home Assistant Integration

Rasbhari can ingest selected high-level Home Assistant events without taking over home automation logic.

Home Assistant should keep the device-specific logic: sensors, debounce windows, thresholds, presence, scenes, and automations. Rasbhari should only receive semantic events that are useful for promises, skills, reports, and timelines.

## Endpoint

```http
POST /integrations/home-assistant/events
X-API-Key: <rasbhari-api-key>
Content-Type: application/json
```

Payload:

```json
{
  "event_type": "home:litterbox_cleaned",
  "description": "Litterbox was cleaned",
  "tags": ["cat", "litterbox"],
  "payload": {
    "entity_id": "binary_sensor.litterbox_cleaned",
    "room": "bathroom"
  }
}
```

Rasbhari adds:

- `user_id` from the API key
- current timestamp
- tags: `home`, `source:home_assistant`, `integration:home_assistant`
- payload fields: `source=home_assistant`, `integration=home_assistant`

The event is stored as a normal Rasbhari `Event`, so promises, skills, reports, notifications, and processors can react through the existing event pipeline.

## Home Assistant REST Command

Example `configuration.yaml`:

```yaml
rest_command:
  rasbhari_event:
    url: "http://rasbhari.local/integrations/home-assistant/events"
    method: POST
    headers:
      X-API-Key: "YOUR_RASBHARI_API_KEY"
      Content-Type: "application/json"
    payload: >
      {
        "event_type": "{{ event_type }}",
        "description": "{{ description }}",
        "tags": {{ tags | tojson }},
        "payload": {{ payload | tojson }}
      }
```

Example automation action:

```yaml
action: rest_command.rasbhari_event
data:
  event_type: "home:litterbox_cleaned"
  description: "Litterbox was cleaned"
  tags:
    - cat
    - litterbox
  payload:
    entity_id: "binary_sensor.litterbox_cleaned"
    room: "bathroom"
```

## Good Event Candidates

- `home:litterbox_cleaned`
- `home:trash_taken_out`
- `home:laundry_finished`
- `home:plants_watered`
- `home:work_desk_started`
- `home:work_desk_ended`
- `home:tv_started`
- `home:tv_stopped`
- `home:long_tv_session`

Avoid sending raw sensor chatter. Home Assistant should decide when something matters, then send one clean event to Rasbhari.
