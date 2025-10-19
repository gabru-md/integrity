from datetime import datetime
import requests
from gabru.process import Process
from model.device import Device
from model.event import Event
from services.devices import DeviceService
import time
import numpy as np

from services.events import EventService


def create_tracker_event_dict(beacon_identifier, coordinates):
    description = f"{coordinates}"
    return {
        "event_type": f"atmos:{beacon_identifier}",
        "timestamp": int(datetime.now().timestamp()),
        "description": description,
        "tags": ["atmos"]
    }


def rssi_to_distance(rssi: float) -> float:
    """
        Approximate distance (in meters) from RSSI using a simple log-distance model.
        Adjust constants as needed for your environment.
    """
    tx_power = -59
    n = 2.0  # path loss exponent
    return 10 ** ((tx_power - rssi) / (10 * n))


class Atmos(Process):
    """
    Constantly keeps track of where everyone is
    in your space.
    """

    def __init__(self, **kwargs):
        super().__init__(name='Atmos', daemon=True)
        self.sleep_time_sec = 1
        self.device_service = DeviceService()
        self.event_service = EventService()
        self.devices = self.device_service.get_devices_enabled_for(self.name)

    def process(self):
        while self.running:
            try:
                if len(self.devices) == 0:
                    self.log.info("No devices are configured, exiting.")
                    # breaks from the loop and the process dies
                    break
                ble_data_map = {}  # {'device1':{'name':{'rssi':-34}, 'name': {}}, }
                for device in self.devices:
                    ble_data = self.get_device_ble_data(device)
                    if ble_data:
                        ble_data_map[device.name] = ble_data

                beacon_locations = self.compute_location_from_device_ble_data(ble_data_map)  # {'name': (x, y), ...}
                for beacon_identifier, coordinates in beacon_locations:
                    self.track_location(beacon_identifier, coordinates)
            except Exception as e:
                self.log.exception(e)

            self.sleep()

    def sleep(self):
        self.log.info(f"Nothing to do, waiting for {self.sleep_time_sec}s")
        time.sleep(self.sleep_time_sec)

    def get_device_ble_data(self, device: Device):
        # call device.url to fetch the data
        try:
            if not device.url:
                self.log.warning(f"Device {device.name} has no URL.")
                return None

            response = requests.get(device.url, timeout=5)
            response.raise_for_status()
            ble_data = response.json()
            return ble_data

        except Exception as e:
            self.log.error(f"Failed to fetch BLE data from {device.name}: {e}")
            return None

    def compute_location_from_device_ble_data(self, ble_data_map):
        """
        Compute beacon coordinates from BLE RSSI data using triangulation.
        Each device must have known coordinates (device.position = (x, y)).
        Returns: {beacon_id: (x, y)}
        """
        beacon_positions = {}

        # Collect all beacon measurements from all devices
        beacon_measurements = {}
        for device in self.devices:
            device_name = device.name
            device_pos = device.coordinates
            if device_pos is None:
                self.log.warning(f"Device {device_name} has no known position, skipping.")
                continue

            beacons = ble_data_map.get(device_name, {})
            for beacon_id, data in beacons.items():
                rssi = data.get("rssi")
                if rssi is None:
                    continue
                distance = rssi_to_distance(rssi)
                beacon_measurements.setdefault(beacon_id, []).append((device_pos, distance))

        # For each beacon, estimate position using least-squares triangulation
        for beacon_id, readings in beacon_measurements.items():
            if len(readings) < 3:
                # Need at least 3 distances for 2D triangulation
                self.log.warning(f"Not enough readings to triangulate {beacon_id} (need >=3, got {len(readings)}).")
                continue

            # Separate device coordinates and distances
            positions = np.array([p for p, _ in readings])
            distances = np.array([d for _, d in readings])

            # Initial guess: centroid of all devices
            x0 = np.mean(positions[:, 0])
            y0 = np.mean(positions[:, 1])
            initial_guess = np.array([x0, y0])

            # Define the residual function for least squares
            def residuals(xy):
                x, y = xy
                return np.sqrt((positions[:, 0] - x) ** 2 + (positions[:, 1] - y) ** 2) - distances

            # Solve using simple iterative method (gradient-free)
            from scipy.optimize import least_squares
            result = least_squares(residuals, initial_guess, method='lm')

            beacon_positions[beacon_id] = tuple(result.x)

        return beacon_positions

    def track_location(self, beacon_identifier, coordinates):
        tracker_event_dict = create_tracker_event_dict(beacon_identifier, coordinates)
        self.event_service.create(Event(**tracker_event_dict))
