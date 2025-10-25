import threading
from datetime import datetime
import time
from typing import List

from queue import Queue, Empty

import cv2
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
        self.sleep_time_sec = 30
        self.classes_to_detect = items_to_detection_classes(items_to_detect=['cat', 'person', 'dog'])
        self.device_service = DeviceService()  # I can implement a app context to manage db conns
        self.frame_buffers = {}
        self.latest_frame = {}
        self.latest_frame_lock = threading.Lock()
        self.devices = []

        self.device_processor_threads = []
        self.delay_seconds = 30
        self.target_fps = 10
        self.buffer_max_size = self.delay_seconds * self.target_fps
        self.device_frame_read_timeout_sec = 3

    def stream(self, device_name):
        while True:
            # safely retrieve the latest frame
            with self.latest_frame_lock:
                frame = self.latest_frame.get(device_name)

            if frame is not None:
                ret, frame_buffer = cv2.imencode('.jpg', frame)
                frame_bytes = frame_buffer.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            time.sleep(0.25)

    def process(self):
        self.log.info("Starting Heimdall")
        self.devices = self.device_service.get_devices_enabled_for(self.name)
        if len(self.devices) == 0:
            self.log.info("No devices are configured, exiting.")
            return
        self.start_device_processor_threads()
        self.run_process_detection()

    def process_device(self, device: Device):
        """
        process from the device.url stream
        """
        device_streaming_url = device.url
        device_capture = None

        device_frame_buffer_queue: Queue = self.frame_buffers[device.name]

        try:
            device_capture = cv2.VideoCapture(device_streaming_url)
            while not device_frame_buffer_queue.full() and self.running:
                self.log.info("Filling for initial load from device")
                ret, frame = device_capture.read()
                if ret and frame is not None:
                    timestamp = datetime.now()
                    upscaled_frame = self.upscale_frame(frame, timestamp)
                    device_frame_buffer_queue.put(upscaled_frame)
                    with self.latest_frame_lock:
                        self.latest_frame[device.name] = upscaled_frame.copy()
                else:
                    time.sleep(self.device_frame_read_timeout_sec)  # wait if frame is not ready yet
            self.log.info(f"{device.name} frame buffer filling complete")
            while self.running:
                ret, frame = device_capture.read()
                if not ret or frame is None:
                    self.log.warning(f"Failed to read frame from {device.name}. Reconnecting in 3s...")
                    time.sleep(self.device_frame_read_timeout_sec)
                    device_capture = cv2.VideoCapture(device_streaming_url)  # Attempt to reconnect
                    continue

                timestamp = datetime.now()
                upscaled_frame = self.upscale_frame(frame, timestamp)
                if device_frame_buffer_queue.full():
                    try:
                        # Remove the oldest frame (the one that has completed the 30s delay)
                        device_frame_buffer_queue.get_nowait()
                    except Empty:
                        # This should theoretically not happen if the queue is full,
                        # but it handles rare race conditions during shutdown or unexpected drain.
                        self.log.warning(f"{device.name} buffer reported full but was empty on get.")
                else:
                    # If the queue is not full, it's either the initial fill
                    # or a refilling process after an outage. Just put the frame.
                    pass

                device_frame_buffer_queue.put(upscaled_frame)

                with self.latest_frame_lock:
                    self.latest_frame[device.name] = upscaled_frame.copy()
        except Exception as e:
            self.log.exception(f"Exception in device processor thread for {device.name}: {e}")
        finally:
            if device_capture:
                self.log.info(f"Releasing video capture for {device.name}")
                device_capture.release()


    def upscale_frame(self, frame: cv2.typing.MatLike, timestamp: datetime = None) -> cv2.typing.MatLike:
        """ implement the upscaling logic in this, upscaling will depend on the device """
        if timestamp:
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[
                            :-3]  # Truncate microseconds for millisecond precision
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            font_color = (255, 255, 255)  # White
            line_type = 2
            position = (10, frame.shape[0] - 10)  # Bottom-left corner, 10 pixels up/right from the edge
            cv2.putText(frame, timestamp_str, position, font, font_scale, font_color, line_type)
        return frame


    def start_device_processor_threads(self):
        for device in self.devices:
            self.frame_buffers[device.name] = Queue(maxsize=self.buffer_max_size)
            device_processor_thread = threading.Thread(name=f"{device.name} Stream Processor", target=self.process_device,
                                                       args=(device,), daemon=True)
            self.log.info(f"Starting thread to process device: {device.name}")
            device_processor_thread.start()
            self.device_processor_threads.append(device_processor_thread)


    def run_process_detection(self):
        while self.running:
            try:
                for device in self.devices:
                    image_data = self.load_image_data(device)
                    if image_data is None:
                        self.log.info(f"No image data for detection for device: {device.name}")
                        continue
                    identified_objects_data = self.identify_objects(image_data)
                    if identified_objects_data:
                        self.track_identified_objects(device, identified_objects_data)
            except Exception as e:
                self.log.exception(e)
            self.sleep()


    def load_image_data(self, device: Device):
        """
        get the most recent frame for the device
        """
        with self.latest_frame_lock:
            latest_frame = self.latest_frame[device.name]
        if latest_frame is None:
            return None
        return latest_frame


    def identify_objects(self, image_data) -> List[IdentifiedObject]:
        """ identify objects data from the image_data """

        results = model(image_data, classes=self.classes_to_detect, verbose=False)
        identified_objects = []

        if results:
            result = results[0]

            detected_class_names = [result.names[int(c)] for c in result.boxes.cls.tolist()]
            for detected_class_name in detected_class_names:
                if detected_class_name == 'dog':  # yolo identifies my cat as a dog
                    detected_class_name = 'cat'
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
