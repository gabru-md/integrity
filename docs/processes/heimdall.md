# Heimdall

Heimdall is Rasbhari's camera and object-tracking worker.

## Current Behavior

- loads devices enabled for `Heimdall`
- spawns one frame-processing thread per device
- reads frames from `device.url`
- runs YOLO11n detection
- detects `cat`, `person`, `dog`, and `mouse`
- normalizes `dog` and `mouse` detections into `tracking:cat` events
- emits `tracking:*` events tagged with `heimdall` and `tracking`
- serves recent frames to the dashboard stream endpoint

## Notes

- the periodic event-tracking loop sleeps for `30s`
- streaming uses the latest processed frame rather than pulling directly from the source on each client request
- bounding-box zoom exists but is disabled by default (`bbox_enabled = False`)

## Device Requirements

Each device used by Heimdall should have:

- `enabled=True`
- `authorized_apps` including `Heimdall`
- `url` pointing to a readable camera/video source

## Dependencies

- OpenCV
- `ultralytics`
- the `yolo11n.pt` model file, which is auto-loaded by the current implementation
