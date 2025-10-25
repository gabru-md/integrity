import cv2
import time
import sys
from flask import Flask, Response, render_template

CAMERA_INDEX = 0
MJPEG_BOUNDARY = 'frame_boundary'
DELAY_TIME = 0.05

app = Flask(__name__)

video_camera = cv2.VideoCapture(CAMERA_INDEX)

if video_camera.isOpened():
    video_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    video_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print(
        f"Set resolution to {video_camera.get(cv2.CAP_PROP_FRAME_WIDTH)}x{video_camera.get(cv2.CAP_PROP_FRAME_HEIGHT)}")

if not video_camera.isOpened():
    print(f"Error: Could not open video camera with index {CAMERA_INDEX}. Exiting.")
    video_camera = None


def gen_frames():
    if video_camera is None:
        return

    while True:
        success, frame = video_camera.read()

        if not success:
            print("Warning: Failed to read frame from camera. Releasing camera.")
            break

        ret, buffer = cv2.imencode('.jpg', frame)

        if not ret:
            print("Error: Failed to encode frame as JPEG.")
            time.sleep(DELAY_TIME)
            continue

        frame_bytes = buffer.tobytes()

        yield (b'--' + MJPEG_BOUNDARY.encode('utf-8') + b'\r\n'
                                                        b'Content-Type: image/jpeg\r\n'
                                                        b'Content-Length: ' + str(len(frame_bytes)).encode(
            'utf-8') + b'\r\n'
                       b'\r\n' + frame_bytes + b'\r\n')

        time.sleep(DELAY_TIME)


@app.route('/')
def index():
    return render_template('index.html', title='Raspberry Pi Camera Stream')


@app.route('/stream')
def video_feed():
    if video_camera is None:
        return Response("Camera Failed to Initialize.", status=500, mimetype='text/plain')

    return Response(gen_frames(),
                    mimetype=f'multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}')


@app.route('/health')
def health_check():
    return {'status': 'ok'}

if __name__ == '__main__':
    try:
        print("Starting camera stream application...")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

    except Exception as e:
        print(f"An error occurred during application run: {e}", file=sys.stderr)

    finally:
        if video_camera and video_camera.isOpened():
            print("Releasing camera resource.")
            video_camera.release()
        print("Application stopped.")
