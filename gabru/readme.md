# Gabru Framework

**Gabru** is a lightweight, custom Python framework that provides the foundational infrastructure for the Rasbhari system. It offers reusable components for database management, web applications, background processes, and event-driven queue processing.

## Overview

Gabru eliminates boilerplate code by providing a structured approach to building data-driven applications with background processes. It's designed specifically for IoT and automation systems running on resource-constrained devices like Raspberry Pi.

### Design Philosophy

- **Convention over Configuration**: Sensible defaults with customization where needed
- **Database-First**: Everything is persisted in PostgreSQL for reliability
- **Process-Oriented**: First-class support for background workers and daemons
- **Type-Safe**: Leverages Python type hints and Pydantic models
- **Event-Driven**: Built-in queue processing for reactive architectures

## Architecture

```
Gabru Framework
├── Database Layer (db/)
│   ├── DB - PostgreSQL connection management
│   └── Service - CRUD and read-only operations
├── Web Layer (flask/)
│   ├── Server - Flask application wrapper
│   ├── App - RESTful API generator
│   └── Model - UI-aware Pydantic models
├── Process Layer
│   ├── Process - Background daemon base class
│   ├── ProcessManager - Lifecycle management
│   └── QueueProcessor (qprocessor/) - Event stream processing
├── Utilities
│   ├── Logger - Multi-file logging system
│   └── Apple (apple/) - iOS/macOS integrations
```

## Core Components

### 1. Database Layer (`db/`)

#### DB Class (`db/db.py`)

A PostgreSQL connection wrapper with automatic reconnection and environment-based configuration.

```python
from gabru.db.db import DB

# Connects using {DB_NAME}_POSTGRES_* environment variables
db = DB("events")  # Uses EVENTS_POSTGRES_DB, EVENTS_POSTGRES_USER, etc.
conn = db.get_conn()
```

**Features:**
- Environment variable configuration per database
- Automatic reconnection on connection loss
- Context manager support (`with` statement)
- Connection pooling via psycopg2

**Environment Variables:**
```bash
# For DB("events")
EVENTS_POSTGRES_DB=events_db
EVENTS_POSTGRES_USER=user
EVENTS_POSTGRES_PASSWORD=password
EVENTS_POSTGRES_HOST=localhost
EVENTS_POSTGRES_PORT=5432
```

#### Service Classes (`db/service.py`)

Generic base classes for data access with built-in CRUD operations.

**ReadOnlyService:**
```python
from gabru.db.service import ReadOnlyService
from gabru.db.db import DB

class MyReadOnlyService(ReadOnlyService[MyModel]):
    def __init__(self):
        super().__init__("mytable", DB("main"))

    def _to_object(self, row: tuple) -> MyModel:
        return MyModel(id=row[0], name=row[1])

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name"]
```

**CRUDService:**
```python
from gabru.db.service import CRUDService

class MyService(CRUDService[MyModel]):
    def __init__(self):
        super().__init__("mytable", DB("main"))

    def _create_table(self):
        # Define table schema
        pass

    def _to_tuple(self, obj: MyModel) -> tuple:
        return (obj.name, obj.value)

    def _to_object(self, row: tuple) -> MyModel:
        return MyModel(id=row[0], name=row[1], value=row[2])

    def _get_columns_for_insert(self) -> List[str]:
        return ["name", "value"]

    def _get_columns_for_update(self) -> List[str]:
        return ["name", "value"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "name", "value"]
```

**Provided Methods:**
- `get_by_id(id)` - Retrieve single entity
- `get_all()` - Retrieve all entities
- `get_recent_items(limit)` - Get N most recent items
- `get_all_items_after(last_id, limit)` - Pagination support
- `find_all(filters, sort_by)` - Advanced querying with filters
- `create(obj)` - Insert new entity (CRUD only)
- `update(obj)` - Update existing entity (CRUD only)
- `delete(id)` - Delete entity (CRUD only)

**Advanced Filtering:**
```python
# Find events of specific types within time range
filters = {
    "event_type": {"$in": ["login", "logout"]},
    "timestamp": {"$lt": max_time, "$gt": min_time}
}
sort_by = {"timestamp": "DESC"}
results = service.find_all(filters=filters, sort_by=sort_by)
```

### 2. Web Layer (`flask/`)

#### Server Class (`flask/server.py`)

A Flask application wrapper with built-in process management and app registration.

```python
from gabru.flask.server import Server
from apps.myapp import myapp

class MyServer(Server):
    def __init__(self):
        super().__init__("MyServer",
                         template_folder="templates",
                         static_folder="static")
        self.setup_apps()

    def setup_apps(self):
        self.register_app(myapp)

    def run_server(self):
        self.start_process_manager()  # Start background processes
        self.run()

if __name__ == '__main__':
    server = MyServer()
    server.run_server()
```

**Built-in Routes:**
- `/` - Dashboard with widgets from all apps
- `/apps` - List all registered apps
- `/processes` - Process management UI
- `/enable_process/<name>` - Enable a process
- `/disable_process/<name>` - Disable a process
- `/start_process/<name>` - Start a process
- `/stop_process/<name>` - Stop a process

#### App Class (`flask/app.py`)

Generates a complete RESTful API and web interface for any data model.

```python
from gabru.flask.app import App
from model.myentity import MyEntity
from services.myentity import MyEntityService

myapp = App(
    'MyApp',                    # App name
    MyEntityService(),          # Service instance
    MyEntity,                   # Pydantic model class
    get_recent_limit=15,        # Items to show on GET /
    widget_recent_limit=3,      # Items in dashboard widget
    home_template="crud.html",  # UI template
    widget_enabled=True         # Show in dashboard
)

# Register background processes
myapp.register_process(MyProcessor, enabled=True)
```

**Auto-generated Endpoints:**
- `POST /{app}/` - Create entity
- `GET /{app}/` - List recent entities
- `GET /{app}/<id>` - Get entity by ID
- `PUT /{app}/<id>` - Update entity
- `DELETE /{app}/<id>` - Delete entity
- `GET /{app}/home` - Web UI
- `POST /{app}/widget/enable` - Enable widget
- `POST /{app}/widget/disable` - Disable widget

**Extending App:**
```python
from gabru.flask.app import App
from flask import jsonify

class CustomApp(App):
    def __init__(self):
        super().__init__('Custom', CustomService(), CustomModel)
        self.setup_custom_routes()

    def setup_custom_routes(self):
        @self.blueprint.route('/custom-action', methods=['POST'])
        def custom_action():
            # Custom logic
            return jsonify({"status": "success"})

custom_app = CustomApp()
```

#### Model Classes (`flask/model.py`)

Pydantic base models with UI configuration support.

```python
from gabru.flask.model import UIModel, WidgetUIModel
from pydantic import Field
from typing import Optional

# UIModel: All fields editable by default
class MyEntity(UIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    name: str = Field(default=None)
    description: str = Field(default="")

# WidgetUIModel: Control widget display
class MyEvent(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    event_type: str = Field(default=None, widget_enabled=True)
    timestamp: int = Field(default=None, widget_enabled=True)
    details: str = Field(default="", widget_enabled=False)
```

**Field Annotations:**
- `edit_enabled` - Show in edit form (default: True for UIModel)
- `widget_enabled` - Show in dashboard widget (default: False)
- `download_enabled` - Enable file download
- `ui_enabled` - Show in any UI component

### 3. Process Layer

#### Process Class (`process.py`)

Base class for long-running background daemons.

```python
from gabru.process import Process
import time

class MyDaemon(Process):
    def __init__(self, name="MyDaemon", enabled=False):
        super().__init__(name=name, enabled=enabled, daemon=True)
        # Initialize resources

    def process(self):
        while self.running:
            # Do work
            self.log.info("Processing...")
            time.sleep(10)

    def stop(self):
        # Cleanup
        super().stop()

# Usage
daemon = MyDaemon(enabled=True)
daemon.start()
```

**Features:**
- Threading-based execution
- Built-in logging
- Graceful shutdown support
- Daemon mode by default

#### ProcessManager (`process.py`)

Manages lifecycle of multiple processes with runtime control.

```python
from gabru.process import ProcessManager

processes = {
    "App1": [(Process1, (), {"enabled": True})],
    "App2": [(Process2, (), {"enabled": False})]
}

manager = ProcessManager(processes_to_manage=processes)
manager.start()

# Runtime control
manager.enable_process("Process2")
manager.run_process("Process2")
manager.pause_process("Process1")
manager.disable_process("Process1")
```

**Process States:**
- **Enabled + Running**: Process is active and doing work
- **Enabled + Paused**: Process can be started but not currently running
- **Disabled**: Process cannot run (must be enabled first)

**Methods:**
- `enable_process(name)` - Allow process to run
- `disable_process(name)` - Prevent process from running
- `run_process(name)` - Start an enabled process
- `pause_process(name)` - Pause a running process
- `get_process_status(name)` - Check if process is alive

#### QueueProcessor (`qprocessor/`)

Event-driven processor that consumes items from a database table.

```python
from gabru.qprocessor.qprocessor import QueueProcessor
from services.events import EventService
from model.event import Event

class MyEventProcessor(QueueProcessor[Event]):
    def __init__(self, name="MyProcessor", enabled=False):
        super().__init__(
            name=name,
            service=EventService(),
            enabled=enabled
        )
        self.sleep_time_sec = 5      # Poll interval
        self.max_queue_size = 10     # Batch size

    def filter_item(self, event: Event):
        # Return None to skip, or return event to process
        if "notification" in event.tags:
            return event
        return None

    def _process_item(self, event: Event) -> bool:
        try:
            # Process the event
            self.log.info(f"Processing: {event.event_type}")
            # ... do work ...
            return True
        except Exception as e:
            self.log.exception(e)
            return False

# Register with an app
myapp.register_process(MyEventProcessor, enabled=True)
```

**How It Works:**
1. Polls database for items with ID > `last_consumed_id`
2. Loads items in batches (configurable size)
3. Filters items (optional)
4. Processes each item sequentially
5. Updates `last_consumed_id` in `queuestats` table
6. Sleeps if queue is empty

**Benefits:**
- Crash recovery: Resumes from last processed ID
- No message loss: Database is source of truth
- Simple debugging: Just query the source table
- Backpressure handling: Configurable batch size

**Queue Statistics:**
Progress is tracked in the `queuestats` table:
```sql
CREATE TABLE queuestats (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    last_consumed_id INT
);
```

See [qprocessor/README.md](qprocessor/README.md) for detailed guide.

### 4. Logger (`log.py`)

Multi-file logging system with automatic log separation.

```python
from gabru.log import Logger

log = Logger.get_log("MyComponent")
log.info("Information message")
log.warning("Warning message")
log.error("Error message")
log.exception(exception_object)
```

**Log Files (in `LOG_DIR`):**
- `main.log` - All INFO+ messages from all components
- `{component}.log` - Component-specific logs
- `warnings.log` - WARNING+ messages only
- `exceptions.log` - ERROR+ messages with stack traces

**Configuration:**
```bash
LOG_DIR=/var/log/rasbhari
```

### 5. Apple Integration (`apple/`)

Utilities for integrating with iOS/macOS ecosystem, particularly shortcuts.

See `apps/shortcuts.py` for usage examples.

## Environment Variables

Gabru uses environment variables for configuration. Create a `.env` file:

```bash
# Server Configuration
SERVER_DEBUG=False
SERVER_PORT=5000
SERVER_FILES_FOLDER=/var/rasbhari/files

# Logging
LOG_DIR=/var/log/rasbhari

# Database Configuration (per database)
MAIN_POSTGRES_DB=rasbhari_main
MAIN_POSTGRES_USER=rasbhari
MAIN_POSTGRES_PASSWORD=password
MAIN_POSTGRES_HOST=localhost
MAIN_POSTGRES_PORT=5432

EVENTS_POSTGRES_DB=rasbhari_events
EVENTS_POSTGRES_USER=rasbhari
EVENTS_POSTGRES_PASSWORD=password
EVENTS_POSTGRES_HOST=localhost
EVENTS_POSTGRES_PORT=5432

QUEUE_POSTGRES_DB=rasbhari_queue
QUEUE_POSTGRES_USER=rasbhari
QUEUE_POSTGRES_PASSWORD=password
QUEUE_POSTGRES_HOST=localhost
QUEUE_POSTGRES_PORT=5432
```

## Quick Start

### 1. Create a Data Model

```python
# model/task.py
from pydantic import Field
from typing import Optional
from gabru.flask.model import UIModel

class Task(UIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    title: str = Field(default=None)
    completed: bool = Field(default=False)
    created_at: Optional[int] = Field(default=None, edit_enabled=False)
```

### 2. Create a Service

```python
# services/tasks.py
from gabru.db.service import CRUDService
from gabru.db.db import DB
from model.task import Task
from typing import List

class TaskService(CRUDService[Task]):
    def __init__(self):
        super().__init__("tasks", DB("main"))

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        completed BOOLEAN DEFAULT FALSE,
                        created_at BIGINT
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, task: Task) -> tuple:
        return (task.title, task.completed, task.created_at)

    def _to_object(self, row: tuple) -> Task:
        return Task(id=row[0], title=row[1], completed=row[2], created_at=row[3])

    def _get_columns_for_insert(self) -> List[str]:
        return ["title", "completed", "created_at"]

    def _get_columns_for_update(self) -> List[str]:
        return ["title", "completed", "created_at"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "title", "completed", "created_at"]
```

### 3. Create an App

```python
# apps/tasks.py
from datetime import datetime
from gabru.flask.app import App
from model.task import Task
from services.tasks import TaskService

def process_data(json_data):
    if 'id' not in json_data:
        json_data["created_at"] = int(datetime.now().timestamp())
    return json_data

tasks_app = App(
    'Tasks',
    TaskService(),
    Task,
    _process_model_data_func=process_data,
    get_recent_limit=20
)
```

### 4. Register with Server

```python
# server.py
from gabru.flask.server import Server
from apps.tasks import tasks_app

class MyServer(Server):
    def __init__(self):
        super().__init__("MyServer")
        self.register_app(tasks_app)

if __name__ == '__main__':
    server = MyServer()
    server.run()
```

### 5. Run the Server

```bash
python server.py
```

Your API is now available:
- `POST /tasks/` - Create task
- `GET /tasks/` - List tasks
- `GET /tasks/1` - Get task
- `PUT /tasks/1` - Update task
- `DELETE /tasks/1` - Delete task
- `GET /tasks/home` - Web UI

## Best Practices

### Database Management
- Use separate databases for different concerns (events, queue, main)
- Always implement `_create_table()` for automatic schema setup
- Use partitioning for large tables (see `EventService` example)

### Service Layer
- Keep business logic in services, not in apps
- Use `find_all()` with filters for complex queries
- Implement custom methods for domain-specific operations

### Process Development
- Always call `super().__init__()` in process constructors
- Use `self.running` flag to check if process should continue
- Clean up resources in `stop()` method
- Set appropriate `sleep_time_sec` for QueueProcessors

### App Organization
- One app per domain/entity
- Use `_process_model_data_func` for data transformation
- Extend App class for custom routes
- Register processes that react to app data changes

### Error Handling
- Use `try-except` in process loops
- Log exceptions with `log.exception(e)`
- Return `False` from `_process_item()` on failure
- Handle database connection failures gracefully

## Advanced Topics

### Custom Queue Processing Logic

Override `filter_item()` for complex filtering:

```python
def filter_item(self, event: Event):
    # Multi-condition filtering
    if event.event_type not in ["login", "logout"]:
        return None
    if datetime.now().hour < 9:  # Only during business hours
        return None
    return event
```

### Process Communication

Processes can communicate via the database:

```python
# Process A writes events
event_service.create(Event(event_type="task_completed", ...))

# Process B (QueueProcessor) reacts to events
class TaskReactor(QueueProcessor[Event]):
    def filter_item(self, event: Event):
        return event if event.event_type == "task_completed" else None

    def _process_item(self, event: Event) -> bool:
        # React to task completion
        send_notification(event)
        return True
```

### Multi-Database Apps

```python
class AnalyticsService(ReadOnlyService[Event]):
    def __init__(self):
        # Read from events database
        super().__init__("events", DB("events"))

class ReportService(CRUDService[Report]):
    def __init__(self):
        # Write to main database
        super().__init__("reports", DB("main"))
```

## Related Documentation

- [Apps Layer](../apps/README.md) - Application development guide
- [QueueProcessor Guide](qprocessor/README.md) - Event-driven processing
- [Flask Framework](flask/README.md) - Web layer details
- [Processes](../processes/) - Example background processes

## Contributing

When adding features to Gabru:
1. Maintain backward compatibility
2. Add type hints to all public methods
3. Document with docstrings
4. Keep dependencies minimal
5. Write examples in this README
