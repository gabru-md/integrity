# Atmos - Location Tracking Engine

**Atmos** is a location tracking engine designed to continuously determine the position of Bluetooth Low Energy (BLE) beacons within a monitored space. It operates by fetching BLE signal strength (RSSI) data from configured sensor devices and applying **trilateration** to estimate the beacon's coordinates.

## Overview

Atmos runs as a persistent, daemonized process that periodically:
1. Fetches raw BLE data (beacon ID and RSSI) from all configured sensor devices.
2. Uses the known positions of the sensor devices and the measured RSSI (converted to distance) to calculate the coordinates of each detected beacon.
3. Records a location tracking **Event** for each beacon in the central event stream.

## Architecture

```

┌──────────────────┐      ┌─────────────┐
│  BLE Sensors     │◀────▶│    Atmos    │
│ (HTTP Endpoints) │      │  (Process)  │
└──────────────────┘      └─────────────┘
        │                       │
        ▼                       ▼
┌─────────────┐      ┌─────────────────┐
│ BLE Data    │      │    Events       │
│ (Device URL)│      │    Database     │
└─────────────┘      └─────────────────┘

````

## Key Features

* **Real-time Location:** Estimates beacon coordinates using **least-squares trilateration** based on RSSI readings from multiple sensors.
* **Event Generation:** Creates an event (`atmos:{beacon_identifier}`) for every calculated location, feeding the data into the event stream.
* **Extensible Device Fetching:** Gathers raw BLE data by making HTTP requests to configured sensor device URLs.
* **Continuous Operation:** Runs constantly with a configurable sleep interval (`self.sleep_time_sec = 1`).

---

## How It Works

### 1. Distance Conversion (RSSI to Distance)

A simple log-distance path loss model is used to convert the raw **RSSI (Received Signal Strength Indication)** into an approximate **distance in meters**.

The conversion uses a function `rssi_to_distance` with a simple log-distance model:
$$d = 10^{\frac{T_x\text{Power} - \text{RSSI}}{10n}}$$
Where $T_x\text{Power}$ is the signal power at 1 meter (default is $-59$) and $n$ is the path loss exponent (default is $2.0$).

### 2. Location Computation (Trilateration)

The core logic is implemented in `compute_location_from_device_ble_data`.

* It requires **at least three** distance readings from three different, position-known devices to perform 2D location estimation.
* It uses **SciPy's `least_squares`** optimization with the Levenberg-Marquardt method (`lm`) to find the $(x, y)$ coordinates for the beacon that best fit the measured distances (minimizing the residuals).

### 3. Event Creation

The final computed location for a beacon is recorded as an event using `create_tracker_event_dict`.

| Field | Example Value | Description |
| :--- | :--- | :--- |
| `event_type` | `atmos:my_beacon_a` | Based on the beacon identifier. |
| `description` | `(3.45, 1.22)` | The calculated $(x, y)$ coordinates. |
| `tags` | `["atmos"]` | Tag for easy filtering. |

---

## Configuration

### Sensor Device Requirements

The process relies on a **Device Service** to load the sensor devices it should query. For **Atmos** to function, devices must be configured with:

1.  **URL:** The HTTP endpoint for fetching the raw BLE data (e.g., `http://sensor-device-ip/ble_data`).
2.  **Position:** Known $(x, y)$ coordinates in the physical space, essential for trilateration (`device.position = (x, y)`).
3.  **Enabled:** The device must be enabled specifically for the `Atmos` process name.

**Example BLE Data Format (from Device URL):**
```json
{
    "beacon_id_1": {"rssi": -65},
    "beacon_id_2": {"rssi": -80}
}
````

### Dependencies

The location calculation relies on standard scientific Python libraries:

  * `numpy`
  * `scipy.optimize.least_squares`

-----

## Troubleshooting

| Issue | Cause | Solution                                                                                                                       |
| :--- | :--- |:-------------------------------------------------------------------------------------------------------------------------------|
| **No Location Computed** | Fewer than 3 distance readings for a beacon. | Ensure at least three configured devices are detecting the beacon and have a known `position` and a valid `url`.               |
| **No Devices Loaded** | Devices aren't configured or enabled for the process. | Verify device configurations in the database and ensure they are enabled for the process named `Atmos`.                        |
| **Data Fetch Failure** | Device URL is unreachable or returns an error. | Check network connectivity between Atmos and the sensor device. Verify the device's URL is correct and its endpoint is active. |
