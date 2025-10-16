from gabru.flask.app import App
from model.device import Device
from services.devices import DeviceService

devices_app = App('Devices', DeviceService(), Device)
