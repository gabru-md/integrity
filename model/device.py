from typing import Optional

from pydantic import Field

from gabru.flask.model import WidgetUIModel


class Device(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(widget_enabled=True, description="Friendly name for the device")
    description: Optional[str] = Field(default=None, description="Optional note about what the device does")
    location: str = Field(widget_enabled=True, description="Where the device is placed")
    type: str = Field(widget_enabled=True, description="Category of device such as camera, sensor, or light")

    vendor: Optional[str] = Field(default=None, ui_enabled=False, description="Manufacturer or vendor")
    model: Optional[str] = Field(widget_enabled=True, description="Model name or number")

    # this is used for geo-locating the beacons
    coordinates: str = Field(default=None, widget_enabled=False, ui_enabled=False)
    # this is used incase there is url to access something
    url: str = Field(default=None, widget_enabled=False, description="Network URL or endpoint used to access the device")
    config_json: Optional[str] = Field(default=None, widget_enabled=False, ui_enabled=False, description="Raw device configuration JSON")
    authorized_apps: Optional[str] = Field(default=None, widget_enabled=False, description="Apps or processes that are allowed to use this device")
    enabled: bool = Field(default=None, description="Whether the device is currently enabled for use")

    def get_coordinates(self):
        """
        returns the coordinates in metres to be used for rssi calc
        """
        if self.coordinates:
            try:
                parts = [part.strip() for part in self.coordinates.split(',')]

                if len(parts) == 2:
                    x_cm = int(parts[0])
                    y_cm = int(parts[1])

                    x_m = x_cm / 100.0
                    y_m = y_cm / 100.0

                    return x_m, y_m

            except ValueError:
                pass
            except TypeError:
                pass

        return 0.0, 0.0
