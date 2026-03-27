# Apps

The `apps/` directory contains the **application layer** of Rasbhari. Each app represents a distinct domain or feature and provides a RESTful API and web interface for managing specific types of data.

## What is an App?

An **App** in Rasbhari is a modular, self-contained component built on the `gabru.flask.app.App` framework. Each app:

- **Manages a specific domain** (e.g., Events, Contracts, Devices)
- **Provides a RESTful API** with standard CRUD operations
- **Has a web interface** for viewing and managing data
- **Can register background processes** that react to data changes
- **Integrates with the event-driven architecture** of the system
- **Provides a customizable Dashboard Widget**

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
- **Widget**: `count` (Shows total event count)
- **Purpose**: Log and track all events in the system.

### 2. Devices
**Location**: `apps/devices.py`
- **Widget**: `basic` (Shows recently active devices)
- **Purpose**: Configure and access hardware devices (ESP32-Cams, BLE beacons).

### 3. Projects
**Location**: `apps/projects.py`
- **Widget**: `kanban` (Shows status-based project cards)
- **Purpose**: Structure and track progress on larger objectives.

### 4. Thoughts
**Location**: `apps/thoughts.py`
- **Widget**: `count` (Shows total thoughts captured)
- **Purpose**: Personal tweeting/note-taking engine.

### 5. Promises
**Location**: `apps/promises.py`
- **Widget**: `basic` (Shows recent commitments)
- **Purpose**: Setup, track, and manage promises and commitments.

### 7. Activities
**Location**: `apps/activities.py`
- **Widget**: `timeline` (Shows a vertical timeline of recent activity triggers)
- **Purpose**: Configure repeatable event emission for common tasks.

### 8. Skills
**Location**: `apps/skills.py`
- **Widget**: `skill_tree` (Shows multi-skill XP progress rings and recent level-up timeline)
- **Purpose**: Turns tagged activities into XP, levels, and unlock requirements for personal growth tracking.

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
- `widget_type`: Type of dashboard widget. Options:
    - `basic`: List of recent items (Default)
    - `count`: Large number showing total items
    - `timeline`: Vertical list with "time-ago" markers
    - `kanban`: Grid of status-labeled cards
    - `progress_ring`: Circular progress visualization
    - `skill_tree`: Multiple progress rings plus embedded level-up history
- `widget_config`: Dictionary for additional widget settings (e.g., specific fields to use for progress)

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

## Best Practices

1. **Choose the right widget**: Use `count` for high-volume data (Events), `timeline` for sequential logs (Activities), `kanban` for state-driven items (Projects), and `skill_tree` when progress and milestones both matter.
2. **Keep apps focused**: Each app should manage a single domain.
3. **Use services for logic**: Keep database operations in the service layer.
4. **Validate with Pydantic**: Use model validation for data integrity.
