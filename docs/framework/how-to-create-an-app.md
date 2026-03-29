# How To Create An App

## 1. Create the model

Add a Pydantic model in `model/`.

Use `WidgetUIModel` if the app should appear cleanly in dashboard widgets.

Example:

```python
from typing import Optional
from pydantic import Field
from gabru.flask.model import WidgetUIModel

class Habit(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(default="", widget_enabled=True)
    status: str = Field(default="active", widget_enabled=True)
```

## 2. Create the concrete runtime service

Add a concrete service in `services/`.

Point it at the correct database namespace:

- `DB("events")`
- `DB("queue")`
- `DB("rasbhari")`
- `DB("notifications")`
- `DB("thoughts")`

Most new app data should live in `DB("rasbhari")`.

If the app is part of the reusable framework rather than Rasbhari specifically, define it against a framework contract instead of importing Rasbhari services directly.

## 3. Create the app

Add the app in `apps/`.

Example:

```python
from gabru.flask.app import App
from model.habit import Habit
from services.habits import HabitService

habits_app = App(
    name="Habits",
    service=HabitService(),
    model_class=Habit,
    widget_type="timeline"
)
```

`App` only requires that `service` satisfies the `ResourceService` contract. If you need custom routes or widget output, subclass `App`.

## 4. Register background processes if needed

If the app owns a background worker:

```python
habits_app.register_process(HabitProcessor, enabled=True)
```

## 5. Register the app in the server

Update [server.py](/Users/manish/PycharmProjects/integrity/server.py):

```python
self.register_app(habits_app)
```

If your app needs new app-wide services for auth, app state, or dashboard aggregation, wire those into `runtime/providers.py` rather than making `gabru/` import them directly.

## 6. Update docs

Update:

- [apps/README.md](/Users/manish/PycharmProjects/integrity/apps/README.md)
- [readme.md](/Users/manish/PycharmProjects/integrity/readme.md)
- [processes/README.md](/Users/manish/PycharmProjects/integrity/processes/README.md) if you added a process
- [.env.example](/Users/manish/PycharmProjects/integrity/.env.example) and [ENVIRONMENT.md](/Users/manish/PycharmProjects/integrity/ENVIRONMENT.md) if you added new env vars
