from typing import Optional

from pydantic import Field

from gabru.flask.model import WidgetUIModel


class Device(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(widget_enabled=True)
    description: Optional[str] = Field(default=None)
    location: str = Field(widget_enabled=True)
    type: str = Field(widget_enabled=True)

    vendor: Optional[str] = Field(default=None, ui_enabled=False)
    model: Optional[str] = Field(widget_enabled=True)

    # this is used for geo-locating the beacons
    coordinates: str = Field(default=None, widget_enabled=False, ui_enabled=False)
    # this is used incase there is url to access something
    url: str = Field(default=None, widget_enabled=False)
    config_json: Optional[str] = Field(default=None, widget_enabled=False, ui_enabled=False)
    authorized_apps: Optional[str] = Field(default=None, widget_enabled=False)
    enabled: bool = Field(default=None)

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
