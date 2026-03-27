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

## 2. Create the service

Add a CRUD service in `services/`.

Point it at the correct database namespace:

- `DB("events")`
- `DB("queue")`
- `DB("rasbhari")`
- `DB("notifications")`
- `DB("thoughts")`

Most new app data should live in `DB("rasbhari")`.

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

If you need custom routes or widget output, subclass `App`.

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

## 6. Update docs

Update:

- [apps/README.md](/Users/manish/PycharmProjects/integrity/apps/README.md)
- [readme.md](/Users/manish/PycharmProjects/integrity/readme.md)
- [processes/README.md](/Users/manish/PycharmProjects/integrity/processes/README.md) if you added a process
- [.env.example](/Users/manish/PycharmProjects/integrity/.env.example) and [ENVIRONMENT.md](/Users/manish/PycharmProjects/integrity/ENVIRONMENT.md) if you added new env vars
