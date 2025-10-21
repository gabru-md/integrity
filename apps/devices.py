from flask import Response

from gabru.flask.app import App
from model.device import Device
from processes.atmos.atmos import Atmos
from processes.heimdall.heimdall import Heimdall
from services.devices import DeviceService


class DeviceApp(App):
    def __init__(self):
        super().__init__('Devices', DeviceService(), Device, get_recent_limit=10)
        self.register_process(Heimdall, enabled=False)
        self.register_process(Atmos, enabled=False)
        self.setup_heimdall_routes()

    def setup_heimdall_routes(self):
        @self.blueprint.route('/stream/<device_name>')
        def video_feed(device_name):
            heimdall_instance: Heimdall = self.get_running_process(Heimdall)
            if not heimdall_instance:
                return "Heimdall stream process is not running"
            return Response(heimdall_instance.stream(device_name),
                            mimetype='multipart/x-mixed-replace; boundary=frame')


devices_app = DeviceApp()
