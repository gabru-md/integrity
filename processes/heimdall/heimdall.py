from datetime import datetime
import time
from typing import List

from ultralytics import YOLO

from gabru.process import Process
from model.device import Device
from model.event import Event
from processes.heimdall.model import IdentifiedObject
from services.devices import DeviceService
from services.events import EventService

model = YOLO("yolo11n.pt")


class Heimdall(Process):
    """
        Heimdall looks from the sky and keeps track of where everyone is.
    """

    def __init__(self, **kwargs):
        super().__init__(name='Heimdall', daemon=True)
        self.event_service = EventService()
        self.sleep_time_sec = 5
        self.classes_to_detect = items_to_detection_classes(items_to_detect=['cat', 'person'])
        self.device_service = DeviceService()  # I can implement a app context to manage db conns
        self.devices = self.device_service.get_devices_enabled_for(self.name)

    def process(self):
        while self.running:
            try:
                if len(self.devices) == 0:
                    self.log.info("No devices are configured, exiting.")
                    # breaks from the loop and the process dies
                    break
                for device in self.devices:
                    image_data = self.load_image_data(device)
                    identified_objects_data = self.identify_objects(image_data)
                    if identified_objects_data:
                        self.track_identified_objects(device, identified_objects_data)
            except Exception as e:
                self.log.exception(e)

            self.sleep()

    @staticmethod
    def load_image_data(device: Device) -> str:
        """
            load image from the camera module
            this can also simply return the URL
            from where the .jpg can be sourced
            e.g.: http://192.168.A.B:PORT/video/stream.jpg
        """
        return device.url

    def identify_objects(self, image_data) -> List[IdentifiedObject]:
        """ identify objects data from the image_data """

        results = model(image_data, classes=self.classes_to_detect, verbose=False)
        identified_objects = []

        if results:
            result = results[0]

            detected_class_names = [result.names[int(c)] for c in result.boxes.cls.tolist()]
            for detected_class_name in detected_class_names:
                identified_objects.append(
                    IdentifiedObject(name=detected_class_name, location='apartment', tags=['heimdall', 'tracking']))

        return identified_objects

    def track_identified_objects(self, device, identified_objects_data):
        """ create events in the events db for identified objects """
        for identified_object in identified_objects_data:
            identified_object: IdentifiedObject = identified_object
            # make sure to add the device_name
            identified_object.device_name = device.name
            tracker_event_dict = create_tracker_event_dict(identified_object)
            # queue an event for tracking
            self.event_service.create(Event(**tracker_event_dict))

        self.log.info(f"Identified {len(identified_objects_data)} objects")

    def sleep(self):
        self.log.info(f"Nothing to do, waiting for {self.sleep_time_sec}s")
        time.sleep(self.sleep_time_sec)


def create_tracker_event_dict(identified_object: IdentifiedObject):
    description = f"{identified_object.name} identified in {identified_object.location} by {identified_object.device_name}"
    return {
        "event_type": f"tracking:{identified_object.name}",
        "timestamp": int(datetime.now().timestamp()),
        "description": description,
        "tags": identified_object.tags
    }


def items_to_detection_classes(items_to_detect):
    name_to_id = {v: k for k, v in model.names.items()}
    desired_classes = [name_to_id[name] for name in items_to_detect if name in name_to_id]
    return desired_classes
