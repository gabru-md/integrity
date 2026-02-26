# Apps

The `apps/` directory contains the **application layer** of Rasbhari. Each app represents a distinct domain or feature and provides a RESTful API and web interface for managing specific types of data.

## What is an App?

An **App** in Rasbhari is a modular, self-contained component built on the `gabru.flask.app.App` framework. Each app:

- **Manages a specific domain** (e.g., Events, Contracts, Devices)
- **Provides a RESTful API** with standard CRUD operations
- **Has a web interface** for viewing and managing data
- **Can register background processes** that react to data changes
- **Integrates with the event-driven architecture** of the system

## Architecture

Each app consists of three main components:

```
App Definition (apps/*.py)
    ↓
Service Layer (services/*.py) → Database (PostgreSQL)
    ↓
Data Model (model/*.py) → Pydantic Models
```

### Key Components

1. **App Definition** (`apps/*.py`)
   - Creates an instance of `App` or extends it
   - Configures the app with a service and model
   - Registers background processes
   - Adds custom routes if needed

2. **Service Layer** (`services/*.py`)
   - Extends `CRUDService` or `ReadOnlyService`
   - Handles all database operations
   - Implements custom queries and business logic

3. **Data Model** (`model/*.py`)
   - Extends `UIModel` or `WidgetUIModel`
   - Defines the data structure using Pydantic
   - Configures UI behavior (edit/widget enabled fields)

## Available Apps

### 1. Events
**Location**: `apps/events.py`

The backbone of Rasbhari's event-driven architecture. Stores all system events that trigger other apps and processes.

- **Purpose**: Log and track all events in the system
- **Key Features**:
  - Tag-based event categorization
  - Timestamped event tracking
  - Event type classification
- **Registered Processes**: Courier (notification service)

### 2. Contracts
**Location**: `apps/contracts.py`

An integrity monitoring system that validates rules against the event stream.

- **Purpose**: Define and validate behavioral rules/constraints
- **Key Features**:
  - Event-triggered contract validation
  - Schedule-based contract checking
  - Condition parsing and evaluation
- **Registered Processes**:
  - Sentinel (event-driven validator)
  - SentinelOC (schedule-based validator)

### 3. Devices
**Location**: `apps/devices.py`

Manages hardware devices (ESP32-Cams, BLE beacons, etc.) used by the system.

- **Purpose**: Configure and access hardware devices
- **Key Features**:
  - Device registration and configuration
  - Process-device association
  - Video streaming endpoints for cameras
- **Registered Processes**:
  - Heimdall (visual monitoring)
  - Atmos (BLE location tracking)

### 4. Shortcuts
**Location**: `apps/shortcuts.py`

Integrates with iOS/iWatch shortcuts to trigger events from mobile devices.

- **Purpose**: Create and manage iOS shortcuts that generate events
- **Key Features**:
  - Shortcut file generation
  - Apple signing service integration
  - Event invocation via shortcuts
- **Custom Routes**:
  - `/sign/<id>` - Sign shortcut files for iOS import
  - `/invoke/<id>` - Trigger event from shortcut

### 5. Thoughts
**Location**: `apps/thoughts.py`

A simple personal note-taking system for recording ideas and important information.

- **Purpose**: Personal tweeting/note-taking engine
- **Key Features**:
  - Quick note creation
  - Timestamped thoughts
  - Simple retrieval interface

## Creating a New App

To create a new app in Rasbhari, follow these steps:

### Step 1: Define the Data Model

Create a new file in `model/` directory:

```python
# model/myentity.py
from pydantic import Field
from typing import Optional
from gabru.flask.model import UIModel

class MyEntity(UIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(default=None)
    description: Optional[str] = Field(default="")
    created_at: Optional[int] = Field(default=None, edit_enabled=False)
```

### Step 2: Create the Service

Create a new file in `services/` directory:

```python
# services/myentity.py
from model.myentity import MyEntity
from gabru.db.service import CRUDService
from gabru.db.db import DB
from typing import List

class MyEntityService(CRUDService[MyEntity]):
    def __init__(self):
        super().__init__("myentities", DB("main"))

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS myentities (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        created_at BIGINT
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, entity: MyEntity) -> tuple:
        return (entity.name, entity.description, entity.created_at)

    def _to_object(self, row: tuple) -> MyEntity:
        return MyEntity(
            id=row[0],
            name=row[1],
            description=row[2],
            created_at=row[3]
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "description", "created_at"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "description", "created_at"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "description", "created_at"]
```

### Step 3: Create the App Definition

Create a new file in `apps/` directory:

```python
# apps/myentity.py
from datetime import datetime
from gabru.flask.app import App
from model.myentity import MyEntity
from services.myentity import MyEntityService

def process_data(json_data):
    # Add timestamp if creating new entity
    if 'id' not in json_data:
        json_data["created_at"] = int(datetime.now().timestamp())
    return json_data

myentity_app = App(
    'MyEntity',
    MyEntityService(),
    MyEntity,
    _process_model_data_func=process_data,
    get_recent_limit=10
)

# Optional: Register processes
# myentity_app.register_process(MyProcess, enabled=True)
```

### Step 4: Register the App

Add your app to the server in `server.py`:

```python
from apps.myentity import myentity_app

class RasbhariServer(Server):
    def setup_apps(self):
        # ... existing apps ...
        self.register_app(myentity_app)
```

### Step 5: Create UI Templates (Optional)

If you want a custom UI, create templates in `templates/` directory. Otherwise, the default `crud.html` template will be used.

## App Configuration Options

When creating an `App` instance, you can configure:

- `name`: The app name (used for routes and logging)
- `service`: The service instance for data operations
- `model_class`: The Pydantic model class
- `get_recent_limit`: Number of recent items to show (default: 10)
- `widget_recent_limit`: Number of items in dashboard widget (default: 3)
- `_process_model_data_func`: Custom function to process data before saving
- `home_template`: Custom HTML template (default: "crud.html")
- `widget_enabled`: Whether to show in dashboard (default: True)

## Standard API Endpoints

Every app automatically gets these RESTful endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/{app}/` | Create a new entity |
| `GET` | `/{app}/` | Get recent entities |
| `GET` | `/{app}/<id>` | Get entity by ID |
| `PUT` | `/{app}/<id>` | Update entity |
| `DELETE` | `/{app}/<id>` | Delete entity |
| `GET` | `/{app}/home` | Web interface |
| `POST` | `/{app}/widget/enable` | Enable dashboard widget |
| `POST` | `/{app}/widget/disable` | Disable dashboard widget |

## Extending Apps

You can extend the base `App` class to add custom functionality:

```python
from gabru.flask.app import App
from flask import jsonify

class MyCustomApp(App):
    def __init__(self):
        super().__init__('MyApp', MyService(), MyModel)
        self.setup_custom_routes()

    def setup_custom_routes(self):
        @self.blueprint.route('/custom-action', methods=['POST'])
        def custom_action():
            # Your custom logic here
            return jsonify({"message": "Custom action executed"})

myapp = MyCustomApp()
```

See `apps/devices.py` for a real example of extending the App class.

## Best Practices

1. **Keep apps focused**: Each app should manage a single domain
2. **Use services for logic**: Keep database operations in the service layer
3. **Validate with Pydantic**: Use model validation for data integrity
4. **Register processes carefully**: Only enable processes that are needed
5. **Document custom routes**: Add clear docstrings for any custom endpoints
6. **Handle errors gracefully**: Use try-except blocks and return meaningful error messages

## Related Documentation

- [Gabru Framework](../gabru/readme.md) - Core framework documentation
- [Processes](../processes/) - Background processes that work with apps
- [Services](../services/) - Service layer implementation details
- [Models](../model/) - Data model definitions
