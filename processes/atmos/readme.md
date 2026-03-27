# Atmos

Atmos is the BLE location worker.

## Current Behavior

- reads enabled devices authorized for `Atmos`
- fetches BLE RSSI JSON from each device's `url`
- converts RSSI to distance
- triangulates beacon locations when at least 3 readings are available
- emits `atmos:<beacon_id>` events with the computed coordinates in the description

## Device Requirements

Each participating device should have:

- `enabled=True`
- `authorized_apps` including `Atmos`
- `url` pointing to a BLE JSON endpoint
- `coordinates` set as `"x_cm,y_cm"`

Example BLE endpoint response:

```json
{
  "beacon_a": {"rssi": -65},
  "beacon_b": {"rssi": -72}
}
```

## Notes

- Atmos sleeps for `1s` between cycles.
- If there are no configured devices, the process exits.
- Triangulation requires SciPy.
