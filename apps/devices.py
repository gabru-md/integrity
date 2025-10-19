from gabru.flask.app import App
from model.device import Device
from processes.atmos.atmos import Atmos
from services.devices import DeviceService

devices_app = App('Devices', DeviceService(), Device)

devices_app.register_process(Atmos, enabled=False)
