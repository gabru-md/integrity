# Heimdall

**Heimdall** is a visual monitoring daemon that uses YOLO11 object detection to identify and track objects from camera streams. It watches over your space and records tracking events to the database.

## Overview

Heimdall runs as a continuous background process that captures images from a camera source, identifies objects using the YOLO11 deep learning model, and creates tracking events in the events database.

**Key Features:**
- Real-time object detection using YOLO11
- Configurable object classes (person, cat, etc.)
- Automatic tracking event creation
- Lightweight daemon process
- Integration with event-driven architecture

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Camera    │─────▶│   Heimdall   │─────▶│     Events      │
│   Stream    │      │  (YOLO11)    │      │    Database     │
└─────────────┘      └──────────────┘      └─────────────────┘
                             │                       │
                             ▼                       ▼
                    ┌─────────────────┐     ┌───────────────┐
                    │ Object Detection│     │ Tracking      │
                    │  (person, cat)  │     │ Events        │
                    └─────────────────┘     └───────────────┘
```

## How It Works

### Detection Loop

Heimdall runs continuously every 5 seconds (processes/heimdall/heimdall.py:36):
1. Load image from camera stream
2. Run YOLO11 object detection
3. Filter detected objects by configured classes
4. Create tracking events for identified objects
5. Sleep and repeat

### Object Identification

Detection is configured for specific object classes (processes/heimdall/heimdall.py:24):

```python
self.classes_to_detect = items_to_detection_classes(
    items_to_detect=['cat', 'person']
)
```

When objects are detected, tracking events are created:

```python
# Example tracking event
{
    "event_type": "tracking:person",
    "timestamp": 1736953200,
    "description": "person identified in apartment",
    "tags": ["heimdall", "tracking"]
}
```

### Camera Integration

The `load_image_data()` method needs to be implemented for your specific camera (processes/heimdall/heimdall.py:38-45):

```python
def load_image_data(self) -> str:
    """
    Return camera URL or image path
    e.g.: http://192.168.1.100:8080/video/stream.jpg
    """
    pass
```

## Configuration

### Process Registration

Heimdall should be registered in your app (similar to other processes):

```python
app.register_process(Heimdall, enabled=False)
```

### Environment Variables

Required in `.env`:

```bash
# Database connection (PostgreSQL)
EVENTS_POSTGRES_DB=events
EVENTS_POSTGRES_USER=postgres
EVENTS_POSTGRES_PASSWORD=yourpassword
EVENTS_POSTGRES_HOST=localhost
EVENTS_POSTGRES_PORT=5432
```

### Detection Settings

Customize in `processes/heimdall/heimdall.py`:

```python
# Objects to detect
items_to_detect = ['cat', 'person']  # Line 24

# Detection interval
self.sleep_time_sec = 5  # Line 23
```

Available YOLO11 object classes include: person, cat, dog, car, bicycle, etc.

### YOLO Model

Heimdall uses `yolo11n.pt` (nano model) for fast detection (processes/heimdall/heimdall.py:12):
- Model auto-downloads on first run
- Stored in local directory
- Lightweight and optimized for Raspberry Pi

## Database Schema

### Events Table
```sql
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(255) NOT NULL,  -- e.g., "tracking:person"
    timestamp TIMESTAMP NOT NULL,
    description TEXT,                  -- e.g., "person identified in apartment"
    tags TEXT[]                        -- ["heimdall", "tracking"]
);
```

## Usage Examples

### Basic Implementation

Complete the camera integration:

```python
from processes.heimdall.heimdall import Heimdall

class MyHeimdall(Heimdall):
    def load_image_data(self) -> str:
        # Return camera stream URL
        return "http://192.168.1.100:8080/video/stream.jpg"
```

### Custom Detection Classes

Modify to detect different objects:

```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.classes_to_detect = items_to_detection_classes(
        items_to_detect=['dog', 'car', 'bicycle']
    )
```

### Query Tracking Events

```sql
-- Recent tracking events
SELECT * FROM events
WHERE event_type LIKE 'tracking:%'
ORDER BY timestamp DESC
LIMIT 10;

-- Person detections today
SELECT * FROM events
WHERE event_type = 'tracking:person'
  AND timestamp >= CURRENT_DATE;
```

## Camera Setup

### Raspberry Pi Camera Module

```python
from picamera2 import Picamera2

def load_image_data(self) -> str:
    picam2 = Picamera2()
    picam2.start()
    return picam2.capture_file("temp.jpg")
```

### IP Camera / RTSP Stream

```python
def load_image_data(self) -> str:
    return "http://192.168.1.100:8080/video/stream.jpg"
```

### USB Webcam

```python
import cv2

def load_image_data(self):
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cv2.imwrite("temp.jpg", frame)
    cap.release()
    return "temp.jpg"
```

## Monitoring

### Logs

```bash
tail -f logs/Heimdall.log
```

Example output:
```
2025-01-15 14:30:05 - Heimdall - INFO - Nothing to do, waiting for 5s
2025-01-15 14:30:10 - Heimdall - INFO - Detected: person
2025-01-15 14:30:10 - Heimdall - INFO - Created tracking event
```

### Check Recent Detections

```sql
SELECT event_type, COUNT(*) as count, MAX(timestamp) as last_seen
FROM events
WHERE tags @> ARRAY['heimdall']
GROUP BY event_type;
```

## Troubleshooting

### No detections happening

1. **Check Heimdall is running** in process manager
2. **Implement `load_image_data()`** method for your camera
3. **Verify camera stream** is accessible
4. **Check detection classes** match available YOLO classes

### YOLO model errors

- Model downloads automatically on first run
- Requires internet connection initially
- Check disk space for model file (~6MB for yolo11n.pt)

### Camera connection issues

- Verify camera URL is reachable: `curl http://camera-ip:port/stream.jpg`
- Check camera permissions on Raspberry Pi
- Test camera independently before integrating

### Performance issues

- Use nano model (`yolo11n.pt`) for Raspberry Pi
- Increase `sleep_time_sec` to reduce CPU usage
- Limit detection classes to needed objects only
- Consider reducing image resolution

## Related Components

- **Events App** (`apps/events.py`): Manages event storage
- **Event Service** (`services/events.py`): Event database operations
- **Process** (`gabru/process.py`): Base daemon class
- **Sentinel** (`processes/sentinel/`): Can create contracts based on tracking events
- **Courier** (`processes/courier/`): Can send notifications for tracking events

## License

See main project [license](../../license.md)