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

# Assuming model is initialized outside the class as before
model = YOLO("yolo11n.pt")


class DeviceStat:
    def __init__(self, name='', frames_processed=0, average_time=0):
        self.name = name
        self.frames_processed = frames_processed
        self.average_time = average_time

    def __str__(self):
        return f"{self.name}: [{self.frames_processed} @ {self.average_time}ms]"


class Heimdall(Process):
    """
        Heimdall looks from the sky and keeps track of where everyone is.
    """

    def __init__(self, **kwargs):
        super().__init__(name='Heimdall', daemon=True)
        self.event_service = EventService()
        self.sleep_time_sec = 30
        self.classes_to_detect = items_to_detection_classes(items_to_detect=['cat', 'person', 'dog', 'mouse'])
        self.device_service = DeviceService()
        self.latest_frame = {}
        self.latest_frame_lock = threading.Lock()
        self.devices = []

        self.device_processor_threads = []
        self.device_frame_read_timeout_sec = 3

        self.device_stats: dict[str, DeviceStat] = {}

    def stream(self, device_name):
        """
        Provides a near-real-time MJPEG stream for multiple clients.
        It uses the latest_frame dictionary, which is non-destructive.
        """
        while True:
            # Safely retrieve the latest frame
            device_stats = self.device_stats[device_name]
            with self.latest_frame_lock:
                frame = self.latest_frame.get(device_name)

            if frame is not None:
                ret, frame_buffer = cv2.imencode('.jpg', frame)
                frame_bytes = frame_buffer.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(device_stats.average_time / 1000)
            if device_stats.frames_processed % 100 == 0:
                self.log.info(f"Streaming {device_name} @ {1000 / device_stats.average_time:.2f} fps.")

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
        Process the device stream, fill the 30s buffer, and save the latest frame.
        Includes critical cleanup logic using try...finally.
        """
        device_streaming_url = device.url
        device_capture = None  # Initialize outside try for scope

        try:
            device_capture = cv2.VideoCapture(device_streaming_url)

            while self.running:
                device_stats = self.device_stats[device.name]
                start_time = time.time()
                ret, frame = device_capture.read()
                if not ret or frame is None:
                    self.log.warning(
                        f"Failed to read frame from {device.name}. Reconnecting in {self.device_frame_read_timeout_sec}s...")
                    time.sleep(self.device_frame_read_timeout_sec)
                    device_capture.release()  # Release before attempting to re-open
                    device_capture = cv2.VideoCapture(device_streaming_url)  # Attempt to reconnect
                    continue

                timestamp = datetime.now()
                self.add_frame_metadata(device_stats, frame, timestamp)
                upscaled_frame = self.upscale_frame(frame)

                with self.latest_frame_lock:
                    self.latest_frame[device.name] = upscaled_frame.copy()

                time_taken_ms = (time.time() - start_time) * 1000

                device_stats.average_time = ((
                                                     device_stats.average_time * device_stats.frames_processed) + time_taken_ms) / (
                                                    device_stats.frames_processed + 1)
                device_stats.frames_processed += 1

                self.device_stats[device.name] = device_stats
        except Exception as e:
            self.log.exception(f"Exception in device processor thread for {device.name}: {e}")

        finally:
            if device_capture:
                self.log.info(f"Releasing video capture for {device.name} due to thread termination/exception.")
                device_capture.release()

    def upscale_frame(self, frame: cv2.typing.MatLike) -> cv2.typing.MatLike:
        """
        Implement the upscaling logic and draw timestamp and FPS on the frame.
        """
        return frame

    def add_frame_metadata(self, device_stats, frame: cv2.typing.MatLike, timestamp):
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        line_type = 2
        if timestamp:
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            font_color = (255, 255, 255)
            position = (10, frame.shape[0] - 10)
            cv2.putText(frame, timestamp_str, position, font, font_scale, font_color, line_type)
        if device_stats and device_stats.frames_processed > 0 and device_stats.average_time > 0:
            fps = 1000 / device_stats.average_time
            fps_text = f"FPS: {fps:.2f}"
            font_color = (0, 255, 255)
            font_scale = 0.5
            (text_width, text_height), baseline = cv2.getTextSize(fps_text, font, font_scale, line_type)
            position_fps = (frame.shape[1] - text_width - 10, text_height + 10)

            cv2.putText(frame, fps_text, position_fps, font, font_scale, font_color, line_type)

    def start_device_processor_threads(self):
        for device in self.devices:
            self.device_stats[device.name] = DeviceStat(name=device.name)
            device_processor_thread = threading.Thread(name=f"{device.name} Stream Processor",
                                                       target=self.process_device,
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
        get the most recent frame for the device (0s delay)
        """
        with self.latest_frame_lock:
            latest_frame = self.latest_frame.get(device.name)
        return latest_frame

    def identify_objects(self, image_data) -> List[IdentifiedObject]:
        """ identify objects data from the image_data """

        results = model(image_data, classes=self.classes_to_detect, verbose=False)
        identified_objects = []

        if results:
            result = results[0]

            detected_class_names = [result.names[int(c)] for c in result.boxes.cls.tolist()]
            for detected_class_name in detected_class_names:
                if detected_class_name == 'dog' or detected_class_name == 'mouse':
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
