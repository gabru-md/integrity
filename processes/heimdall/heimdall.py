import threading
from datetime import datetime
import time
from typing import List

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
    def __init__(self, name='', frames_processed=0, average_time=0, bbox=None):
        self.name = name
        self.frames_processed = frames_processed
        self.average_time = average_time
        self.bbox = bbox

    def __str__(self):
        return f"{self.name}: [{self.frames_processed} @ {self.average_time}ms]"


class Heimdall(Process):
    """
        Heimdall looks from the sky and keeps track of where everyone is.
    """

    def __init__(self, **kwargs):
        super().__init__(daemon=True, **kwargs)
        self.event_service = EventService()
        self.sleep_time_sec = 30
        # Included person, cat, dog, mouse in detection classes
        self.classes_to_detect = items_to_detection_classes(items_to_detect=['cat', 'person', 'dog', 'mouse'])
        self.device_service = DeviceService()
        self.latest_frame = {}
        self.latest_frame_lock = threading.Lock()
        self.devices = []
        self.zoom_factor = 3.0

        self.device_processor_threads = []
        self.device_frame_read_timeout_sec = 3
        self.bbox_enabled = False

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
            if device_stats.frames_processed > 0 and device_stats.frames_processed % 100 == 0:
                self.log.info(f"Streaming {device_name} @ {1000 / device_stats.average_time:.2f} fps.")

    def process(self):
        self.log.info("Starting Heimdall")
        self.devices = self.device_service.get_devices_enabled_for(self.name)
        if len(self.devices) == 0:
            self.log.info("No devices are configured, exiting.")
            return
        self.start_device_processor_threads()
        self.run_process_detection()

    def _get_animal_bbox(self, results):
        """Finds the bounding box of the largest cat/dog/mouse in the detection results."""
        best_box = None
        max_area = 0

        # Check if any results were found
        if not results or not results[0].boxes:
            return None

        result = results[0]

        # Target classes for zoom
        animal_classes = ['cat', 'dog', 'mouse']

        # Iterate over all detections
        for i, box in enumerate(result.boxes.xyxy.cpu().numpy()):
            # box is in format [x1, y1, x2, y2]
            x1, y1, x2, y2 = box.astype(int)

            # Get the class name for the current box
            class_id = int(result.boxes.cls.cpu().numpy()[i])
            class_name = result.names[class_id]

            # Check if it's one of the target animals
            if class_name in animal_classes:
                area = (x2 - x1) * (y2 - y1)
                if area > max_area:
                    max_area = area
                    best_box = [x1, y1, x2, y2]

        return best_box

    def _zoom_and_draw_metadata(self, frame: cv2.typing.MatLike, device_stats, timestamp):
        """Crops/Zooms the frame to the object, then adds timestamp and FPS metadata."""

        # Frame dimensions
        H, W = frame.shape[:2]

        # 1. Apply Zoom/Crop
        bbox = device_stats.bbox
        if bbox and self.bbox_enabled:
            x1, y1, x2, y2 = bbox

            # Calculate center and dimensions of the bounding box
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # Add a margin around the object (e.g., 50% on each side)
            margin_factor = 1.0  # 1.0 means the crop box will be 2x the object size
            obj_width = x2 - x1
            obj_height = y2 - y1

            # Determine the size of the square crop area
            # Use the max dimension of the object for the size of the crop box
            crop_half_side = int(max(obj_width, obj_height) * self.zoom_factor / 2)

            # Calculate the top-left and bottom-right corners of the potential crop box
            crop_x1 = max(0, center_x - crop_half_side)
            crop_y1 = max(0, center_y - crop_half_side)
            crop_x2 = min(W, center_x + crop_half_side)
            crop_y2 = min(H, center_y + crop_half_side)

            # Ensure the crop box is square based on the size we were able to crop
            actual_crop_size = min(crop_x2 - crop_x1, crop_y2 - crop_y1)

            # Re-center the crop box based on the 'actual_crop_size' to ensure it's square
            crop_x1 = center_x - actual_crop_size // 2
            crop_x2 = center_x + actual_crop_size // 2
            crop_y1 = center_y - actual_crop_size // 2
            crop_y2 = center_y + actual_crop_size // 2

            # Re-validate bounds after re-centering
            crop_x1 = max(0, crop_x1)
            crop_y1 = max(0, crop_y1)
            crop_x2 = min(W, crop_x2)
            crop_y2 = min(H, crop_y2)

            # Final crop
            cropped_frame = frame[crop_y1:crop_y2, crop_x1:crop_x2]

            # Resize the cropped frame back to the original frame size for streaming consistency
            if cropped_frame.size > 0:
                frame = cv2.resize(cropped_frame, (W, H), interpolation=cv2.INTER_LINEAR)

        # 2. Add Metadata (Timestamp and FPS)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        line_type = 2
        # Timestamp (Bottom Left)
        if timestamp:
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            font_color = (255, 255, 255)  # White
            position = (10, frame.shape[0] - 10)  # Bottom-left
            cv2.putText(frame, timestamp_str, position, font, font_scale, font_color, line_type)

        # FPS (Top Right)
        if device_stats and device_stats.frames_processed > 0 and device_stats.average_time > 0:
            fps = 1000 / device_stats.average_time
            fps_text = f"FPS: {fps:.2f}"
            font_color = (0, 255, 255)  # Yellow (BGR)
            font_scale = 0.5

            (text_width, text_height), baseline = cv2.getTextSize(fps_text, font, font_scale, line_type)
            position_fps = (frame.shape[1] - text_width - 10, text_height + 10)

            cv2.putText(frame, fps_text, position_fps, font, font_scale, font_color, line_type)

        return frame

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

                # --- NEW REAL-TIME DETECTION AND PROCESSING ---
                # 1. Run Detection
                results = model(frame, classes=self.classes_to_detect, verbose=False)

                # 2. Get Animal Bounding Box
                animal_bbox = self._get_animal_bbox(results)
                if animal_bbox:
                    device_stats.bbox = animal_bbox

                timestamp = datetime.now()

                # 3. Zoom/Crop and Add Metadata
                processed_frame = self._zoom_and_draw_metadata(frame, device_stats, timestamp)

                # Update the latest frame for the web stream
                with self.latest_frame_lock:
                    self.latest_frame[device.name] = processed_frame.copy()

                time_taken_ms = (time.time() - start_time) * 1000

                # Update running average time
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
                    # Note: This detection still runs periodically for event tracking
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