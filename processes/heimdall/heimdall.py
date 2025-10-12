from datetime import datetime
import time
from typing import List

from ultralytics import YOLO

from gabru.process import Process
from model.event import Event
from processes.heimdall.model import IdentifiedObject
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

    def process(self):
        while self.running:
            try:
                image_data = self.load_image_data()
                identified_objects_data = self.identify_objects(image_data)
                if identified_objects_data:
                    self.track_identified_objects(identified_objects_data)
            except Exception as e:
                self.log.exception(e)

            self.sleep()

    def load_image_data(self) -> str:
        """
            load image from the camera module
            this can also simply return the URL
            from where the .jpg can be sourced
            e.g.: http://192.168.A.B:PORT/video/stream.jpg
        """
        pass

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

    def track_identified_objects(self, identified_objects_data):
        """ create events in the events db for identified objects """
        for identified_object in identified_objects_data:
            identified_object: IdentifiedObject = identified_object
            tracker_event_dict = create_tracker_event_dict(identified_object)
            # queue an event for tracking
            self.event_service.create(Event(**tracker_event_dict))

    def sleep(self):
        self.log.info(f"Nothing to do, waiting for {self.sleep_time_sec}s")
        time.sleep(self.sleep_time_sec)


def create_tracker_event_dict(identified_object: IdentifiedObject):
    description = f"{identified_object.name} identified in {identified_object.location}"
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
