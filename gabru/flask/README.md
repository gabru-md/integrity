# Gabru Flask Framework

The **Gabru Flask Framework** is a web application layer that provides rapid development of RESTful APIs and web interfaces with minimal boilerplate. It consists of three main components: **Server**, **App**, and **Model**.

## Overview

Gabru's Flask framework eliminates the need to manually write CRUD endpoints, HTML templates, and process management code. Instead, you define your data model and the framework automatically generates:

- Complete RESTful API with all CRUD operations
- Web interface for data management
- Dashboard widgets
- Process lifecycle management
- Runtime process control endpoints

## Architecture

```
Server (Flask application wrapper)
  ├── Registers multiple Apps
  ├── Manages ProcessManager
  ├── Provides dashboard routes
  └── Handles process control endpoints
      ↓
App (Blueprint-based application)
  ├── Auto-generates CRUD API endpoints
  ├── Registers background Processes
  ├── Provides widget data
  └── Uses Service for data access
      ↓
Service (Database operations)
  ├── CRUDService or ReadOnlyService
  └── PostgreSQL database access
      ↓
Model (Pydantic data model)
  ├── UIModel or WidgetUIModel
  └── Field-level UI configuration
```

## Core Components

### 1. Server Class (`server.py`)

The **Server** class wraps a Flask application and provides infrastructure for app registration and process management.

#### Basic Usage

```python
from gabru.flask.server import Server
from apps.myapp import myapp

class MyServer(Server):
    def __init__(self):
        super().__init__(
            name="MyServer",
            template_folder="templates",  # Path to HTML templates
            static_folder="static"        # Path to static files (CSS, JS)
        )
        self.setup_apps()

    def setup_apps(self):
        # Register all your apps
        self.register_app(myapp)

    def run_server(self):
        # Start process manager for background workers
        self.start_process_manager()
        # Run Flask server
        self.run()

if __name__ == '__main__':
    server = MyServer()
    server.run_server()
```

#### Built-in Routes

The Server automatically provides these routes:

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Dashboard home with widgets from all apps |
| `/apps` | GET | List all registered apps with metadata |
| `/processes` | GET | Process management UI |
| `/enable_process/<name>` | POST | Enable a process (allows it to run) |
| `/disable_process/<name>` | POST | Disable a process (prevents running) |
| `/start_process/<name>` | POST | Start an enabled process |
| `/stop_process/<name>` | POST | Stop a running process |
| `/download/<filename>` | GET | Download files from server files folder |

#### Configuration

The Server reads these environment variables:

```bash
SERVER_DEBUG=False              # Flask debug mode
SERVER_PORT=5000                # Port to listen on
SERVER_FILES_FOLDER=/tmp        # Directory for file downloads
```

#### Process Management

The Server integrates with `ProcessManager` to control background processes:

```python
# Processes are registered with apps
myapp.register_process(MyProcessor, enabled=True)

# Server starts ProcessManager automatically
server.start_process_manager()

# Runtime control via HTTP endpoints
POST /enable_process/MyProcessor
POST /start_process/MyProcessor
POST /stop_process/MyProcessor
POST /disable_process/MyProcessor
```

#### Custom Routes

Add custom routes by defining them in your server class:

```python
class MyServer(Server):
    def __init__(self):
        super().__init__("MyServer")
        self.setup_apps()
        self.setup_custom_routes()

    def setup_custom_routes(self):
        @self.app.route('/health')
        def health_check():
            return jsonify({"status": "healthy"}), 200

        @self.app.route('/stats')
        def statistics():
            return jsonify({
                "apps": len(self.registered_apps),
                "processes": len(self.get_processes_data())
            })
```

#### Template Filters

Add custom Jinja2 filters for templates:

```python
class MyServer(Server):
    def __init__(self):
        super().__init__("MyServer")
        self.setup_custom_filters()

    def setup_custom_filters(self):
        @self.app.template_filter("currency")
        def currency_format(value):
            return f"${value:,.2f}"
```

### 2. App Class (`app.py`)

The **App** class generates a complete RESTful API and web interface for any data model.

#### Basic Usage

```python
from gabru.flask.app import App
from model.task import Task
from services.tasks import TaskService

# Minimal app definition
tasks_app = App(
    name='Tasks',           # App name (used in URLs)
    service=TaskService(),  # Service for database operations
    model_class=Task        # Pydantic model
)
```

#### Full Configuration

```python
from datetime import datetime

def process_task_data(json_data):
    """Custom data processing before create/update"""
    if 'id' not in json_data:
        json_data["created_at"] = int(datetime.now().timestamp())
    json_data["title"] = json_data["title"].strip()
    return json_data

tasks_app = App(
    name='Tasks',
    service=TaskService(),
    model_class=Task,
    get_recent_limit=20,                    # Number of items for GET /tasks/
    widget_recent_limit=5,                  # Items in dashboard widget
    _process_model_data_func=process_task_data,  # Data preprocessor
    home_template="custom_tasks.html",      # Custom UI template
    widget_enabled=True                     # Show in dashboard
)

# Register background processes
tasks_app.register_process(TaskProcessor, enabled=True)
tasks_app.register_process(TaskCleanup, enabled=False)
```

#### Auto-generated API Endpoints

Every App automatically gets these RESTful endpoints:

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|--------------|----------|
| `/{app}/` | POST | Create new entity | JSON model | `{message: "..."}` or error |
| `/{app}/` | GET | Get recent entities | - | Array of entities |
| `/{app}/<id>` | GET | Get entity by ID | - | Single entity or 404 |
| `/{app}/<id>` | PUT | Update entity | JSON model | `{message: "..."}` or error |
| `/{app}/<id>` | DELETE | Delete entity | - | `{message: "..."}` or error |
| `/{app}/home` | GET | Web UI | - | HTML page |
| `/{app}/widget/enable` | POST | Enable dashboard widget | - | `{message: "..."}` |
| `/{app}/widget/disable` | POST | Disable dashboard widget | - | `{message: "..."}` |

#### Example API Usage

```bash
# Create a task
curl -X POST http://localhost:5000/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Write documentation", "completed": false}'

# Get recent tasks
curl http://localhost:5000/tasks/

# Get specific task
curl http://localhost:5000/tasks/1

# Update task
curl -X PUT http://localhost:5000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Write documentation", "completed": true}'

# Delete task
curl -X DELETE http://localhost:5000/tasks/1
```

#### Extending the App Class

For custom functionality, extend the App class:

```python
from gabru.flask.app import App
from flask import jsonify, request

class TasksApp(App):
    def __init__(self):
        super().__init__('Tasks', TaskService(), Task)
        self.setup_custom_routes()

    def setup_custom_routes(self):
        @self.blueprint.route('/complete/<int:task_id>', methods=['POST'])
        def mark_complete(task_id):
            task = self.service.get_by_id(task_id)
            if task:
                task.completed = True
                self.service.update(task)
                return jsonify({"message": "Task marked as complete"}), 200
            return jsonify({"error": "Task not found"}), 404

        @self.blueprint.route('/stats', methods=['GET'])
        def get_stats():
            all_tasks = self.service.get_all()
            return jsonify({
                "total": len(all_tasks),
                "completed": sum(1 for t in all_tasks if t.completed)
            })

tasks_app = TasksApp()
```

#### Process Registration

Apps can register background processes that work with their data:

```python
from processes.myprocessor import MyProcessor

# Simple registration
myapp.register_process(MyProcessor, enabled=True)

# With custom name
myapp.register_process(MyProcessor, enabled=True, name="CustomName")

# With additional arguments
myapp.register_process(
    MyProcessor,
    enabled=True,
    arg1="value1",
    arg2="value2"
)

# Multiple processes
myapp.register_process(Processor1, enabled=True)
myapp.register_process(Processor2, enabled=False)  # Disabled initially
```

#### Widget System

Apps can provide data for the dashboard:

```python
# In your app
tasks_app = App('Tasks', TaskService(), Task, widget_enabled=True)

# Widget shows recent items (controlled by widget_recent_limit)
# Only fields with widget_enabled=True are shown in widget

# Control which fields appear in widget via model
class Task(WidgetUIModel):
    id: Optional[int] = Field(default=None, widget_enabled=False)
    title: str = Field(default=None, widget_enabled=True)      # Show in widget
    completed: bool = Field(default=False, widget_enabled=True) # Show in widget
    details: str = Field(default="", widget_enabled=False)      # Hide in widget
```

Runtime control:

```bash
# Enable widget
POST /tasks/widget/enable

# Disable widget
POST /tasks/widget/disable
```

### 3. Model Classes (`model.py`)

Pydantic base models with built-in UI configuration support.

#### UIModel

All fields are **editable by default** in the UI:

```python
from gabru.flask.model import UIModel
from pydantic import Field
from typing import Optional

class Task(UIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)  # Read-only
    title: str = Field(default=None)                             # Editable
    description: str = Field(default="")                         # Editable
    completed: bool = Field(default=False)                       # Editable
    created_at: int = Field(default=None, edit_enabled=False)    # Read-only
```

#### WidgetUIModel

Extends UIModel with widget display control:

```python
from gabru.flask.model import WidgetUIModel
from pydantic import Field
from typing import Optional

class Event(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    event_type: str = Field(default=None, widget_enabled=True)     # Show in widget
    timestamp: int = Field(default=None, widget_enabled=True)      # Show in widget
    description: str = Field(default="", widget_enabled=False)     # Hide from widget
    details: dict = Field(default={}, widget_enabled=False)        # Hide from widget
```

#### Field Configuration Options

Available in `json_schema_extra`:

```python
from pydantic import Field

class MyEntity(UIModel):
    # Control edit form visibility
    name: str = Field(default=None, edit_enabled=True)
    readonly_field: str = Field(default=None, edit_enabled=False)

    # Control widget display
    widget_field: str = Field(default=None, widget_enabled=True)
    hidden_field: str = Field(default=None, widget_enabled=False)

    # Enable file downloads (for file path fields)
    file_path: str = Field(default=None, download_enabled=True)

    # General UI visibility (overrides edit_enabled and widget_enabled)
    visible: str = Field(default=None, ui_enabled=True)
    invisible: str = Field(default=None, ui_enabled=False)
```

#### Model Validation

Leverage Pydantic validation:

```python
from pydantic import Field, field_validator
from gabru.flask.model import UIModel
from typing import Optional

class Task(UIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    title: str = Field(default=None, min_length=1, max_length=200)
    priority: int = Field(default=1, ge=1, le=5)  # Between 1-5

    @field_validator('title')
    @classmethod
    def title_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

    @field_validator('priority')
    @classmethod
    def priority_must_be_valid(cls, v):
        if v not in [1, 2, 3, 4, 5]:
            raise ValueError('Priority must be between 1 and 5')
        return v
```

## Complete Example: Building a Todo App

### Step 1: Define the Model

```python
# model/todo.py
from pydantic import Field, field_validator
from typing import Optional
from gabru.flask.model import WidgetUIModel

class Todo(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    title: str = Field(default=None, widget_enabled=True)
    description: Optional[str] = Field(default="", widget_enabled=False)
    completed: bool = Field(default=False, widget_enabled=True)
    priority: int = Field(default=1, ge=1, le=3, widget_enabled=True)
    created_at: Optional[int] = Field(default=None, edit_enabled=False, widget_enabled=True)

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title is required')
        return v.strip()
```

### Step 2: Create the Service

```python
# services/todos.py
from gabru.db.service import CRUDService
from gabru.db.db import DB
from model.todo import Todo
from typing import List

class TodoService(CRUDService[Todo]):
    def __init__(self):
        super().__init__("todos", DB("main"))

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS todos (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        completed BOOLEAN DEFAULT FALSE,
                        priority INT DEFAULT 1,
                        created_at BIGINT
                    )
                """)
                self.db.conn.commit()

    def _to_tuple(self, todo: Todo) -> tuple:
        return (todo.title, todo.description, todo.completed,
                todo.priority, todo.created_at)

    def _to_object(self, row: tuple) -> Todo:
        return Todo(
            id=row[0], title=row[1], description=row[2],
            completed=row[3], priority=row[4], created_at=row[5]
        )

    def _get_columns_for_insert(self) -> List[str]:
        return ["title", "description", "completed", "priority", "created_at"]

    def _get_columns_for_update(self) -> List[str]:
        return ["title", "description", "completed", "priority", "created_at"]

    def _get_columns_for_select(self) -> List[str]:
        return ["id", "title", "description", "completed", "priority", "created_at"]
```

### Step 3: Create the App

```python
# apps/todos.py
from datetime import datetime
from gabru.flask.app import App
from model.todo import Todo
from services.todos import TodoService

def process_todo_data(json_data):
    # Add timestamp when creating
    if 'id' not in json_data:
        json_data["created_at"] = int(datetime.now().timestamp())

    # Sanitize inputs
    if 'title' in json_data:
        json_data["title"] = json_data["title"].strip()

    return json_data

todos_app = App(
    'Todos',
    TodoService(),
    Todo,
    _process_model_data_func=process_todo_data,
    get_recent_limit=25,
    widget_recent_limit=5,
    widget_enabled=True
)
```

### Step 4: Register with Server

```python
# server.py
from gabru.flask.server import Server
from apps.todos import todos_app

class TodoServer(Server):
    def __init__(self):
        super().__init__("TodoApp")
        self.register_app(todos_app)

if __name__ == '__main__':
    server = TodoServer()
    server.run()
```

### Step 5: Run and Use

```bash
# Start server
python server.py

# Access API
curl http://localhost:5000/todos/                    # List todos
curl http://localhost:5000/todos/home                # Web UI
curl http://localhost:5000/                          # Dashboard

# Create todo
curl -X POST http://localhost:5000/todos/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learn Gabru Framework",
    "description": "Read all documentation",
    "priority": 1
  }'
```

## Advanced Usage

### Custom Templates

Create a custom HTML template:

```html
<!-- templates/custom_todos.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{{ app_name }} - Custom View</title>
</head>
<body>
    <h1>{{ app_name }}</h1>

    <!-- Access model attributes -->
    {% for attr in model_class_attributes %}
        <p>{{ attr.name }}: {{ attr.type }}</p>
    {% endfor %}

    <!-- Your custom UI here -->
</body>
</html>
```

Use it in your app:

```python
todos_app = App(
    'Todos',
    TodoService(),
    Todo,
    home_template="custom_todos.html"  # Use custom template
)
```

### Data Processing Function

Transform data before saving:

```python
def process_data(json_data):
    # Add computed fields
    if 'title' in json_data:
        json_data['slug'] = json_data['title'].lower().replace(' ', '-')

    # Validate business rules
    if json_data.get('priority') == 1 and json_data.get('completed'):
        raise ValueError("High priority tasks cannot be marked complete directly")

    # Set defaults
    json_data.setdefault('completed', False)

    return json_data

myapp = App(
    'MyApp',
    MyService(),
    MyModel,
    _process_model_data_func=process_data
)
```

### Accessing Running Processes

Get a running process instance from your app:

```python
class MyApp(App):
    def setup_custom_routes(self):
        @self.blueprint.route('/process-status')
        def process_status():
            process = self.get_running_process(MyProcessor)
            if process:
                return jsonify({
                    "running": process.running,
                    "last_id": process.q_stats.last_consumed_id
                })
            return jsonify({"error": "Process not running"}), 503
```

## Best Practices

### 1. App Organization

- **One app per entity/domain**: Don't mix multiple entities in one app
- **Keep apps simple**: Use services for complex logic
- **Use meaningful names**: App names appear in URLs and UI

### 2. Model Design

- **Use appropriate base class**: UIModel for forms, WidgetUIModel for dashboards
- **Configure field visibility**: Set edit_enabled and widget_enabled appropriately
- **Add validation**: Use Pydantic validators for business rules
- **Document fields**: Add descriptions to help users

### 3. Process Management

- **Register with apps**: Link processes to the apps that use their data
- **Set enabled appropriately**: Only enable processes that should run on startup
- **Use descriptive names**: Makes process management UI clearer

### 4. Server Configuration

- **Separate concerns**: Put custom routes in separate methods
- **Use environment variables**: Don't hardcode configuration
- **Handle errors gracefully**: Add try-except in custom routes

### 5. Template Development

- **Inherit from base**: Use template inheritance for consistency
- **Access provided variables**: `app_name`, `model_class_attributes`, etc.
- **Keep logic minimal**: Use template filters for formatting

## Troubleshooting

### Problem: App not accessible

**Check:**
- Is the app registered with `server.register_app(myapp)`?
- Is the server running?
- Check URL: `http://localhost:5000/{app_name}/`

### Problem: Fields not showing in UI

**Check:**
- Set `edit_enabled=True` for edit form fields
- Set `widget_enabled=True` for dashboard widget fields
- Check `ui_enabled` isn't set to False

### Problem: Process not starting

**Check:**
- Is `enabled=True` when registering?
- Is `server.start_process_manager()` called?
- Check logs for initialization errors

### Problem: Data validation failing

**Check:**
- Pydantic field constraints (min_length, ge, le, etc.)
- Custom validators not raising proper ValueError
- Check API response for validation error details

## Related Documentation

- [Gabru Framework](../readme.md) - Overall framework documentation
- [Apps Layer](../../apps/README.md) - App development guide
- [QueueProcessor](../qprocessor/README.md) - Background process guide
- [Database Layer](../readme.md#1-database-layer-db) - DB and Service classes

## API Reference

### Server Class

```python
class Server:
    def __init__(self, name: str, template_folder="templates", static_folder="static")
    def register_app(self, app: App)
    def run(self)
    def start_process_manager(self)
    def get_apps_data(self) -> list
    def get_processes_data(self) -> list
    def get_widgets_data(self) -> dict
```

### App Class

```python
class App(Generic[T]):
    def __init__(
        self,
        name: str,
        service: CRUDService[T],
        model_class: type,
        get_recent_limit=10,
        widget_recent_limit=3,
        _process_model_data_func=None,
        home_template="crud.html",
        widget_enabled=True
    )

    def register_process(self, process_class: type, *args, **kwargs)
    def get_running_process(self, process_class: type) -> Process
    def widget_data(self) -> tuple
    def set_widget_enabled(self, enabled: bool) -> bool
```

### Model Classes

```python
class UIModel(BaseModel):
    # All fields editable by default
    pass

class WidgetUIModel(UIModel):
    # Extends UIModel with widget_enabled control
    pass
```

## Examples in Codebase

See these files for real-world examples:

- `apps/events.py` - Event logging system
- `apps/contracts.py` - Contract management
- `apps/devices.py` - Extended App class with custom routes
- `apps/shortcuts.py` - Custom routes for iOS integration
- `server.py` - Complete server implementation
