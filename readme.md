# Rasbhari

**Rasbhari** (Hindi for "raspberry") is an event-driven automation and monitoring system designed to run on **Raspberry Pi**. It simplifies daily life through intelligent automation, behavioral monitoring, and IoT device integration.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1%2B-green)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12%2B-blue)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](license.md)

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Applications](#applications)
- [Background Processes](#background-processes)
- [Documentation](#documentation)
- [System Requirements](#system-requirements)
- [Contributing](#contributing)
- [License](#license)

## Overview

Rasbhari runs on a **Raspberry Pi** and provides a comprehensive framework for building event-driven automation systems. All activities generate **events** that flow through the system, triggering automated responses, notifications, and behavioral monitoring.

### What Makes Rasbhari Unique?

- **Event-Driven Core**: Everything is an event - from sensor readings to user actions
- **Database-First**: PostgreSQL as the single source of truth for reliability
- **Self-Contained Framework**: Custom `gabru` framework optimized for edge computing
- **IoT Integration**: Native support for ESP32, Arduino, BLE beacons, cameras
- **Behavioral Monitoring**: Contract system validates rules against event history
- **Zero-Config APIs**: Automatic RESTful API generation from data models
- **iOS Integration**: Native shortcuts support for iPhone/iWatch automation

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Rasbhari System                             │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        Web Interface Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │Dashboard │  │  Apps UI │  │Processes │  │ Widgets  │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────────┐
│                        Application Layer                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Events  │  │Contracts │  │ Devices  │  │Shortcuts │  +more     │
│  │   App    │  │   App    │  │   App    │  │   App    │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────────┐
│                      Background Processes                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Sentinel │  │ Courier  │  │Heimdall  │  │  Atmos   │           │
│  │(Validate)│  │ (Notify) │  │ (Vision) │  │(Location)│           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────────┐
│                        Gabru Framework                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │   Flask Layer    │  │   Process Layer  │  │  Database Layer │  │
│  │                  │  │                  │  │                 │  │
│  │ • Server         │  │ • Process        │  │ • DB            │  │
│  │ • App (CRUD API) │  │ • ProcessManager │  │ • CRUDService   │  │
│  │ • Model (UI)     │  │ • QueueProcessor │  │ • ReadOnlyServ. │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐                        │
│  │   Logger         │  │  Apple Integration│                       │
│  │ (Multi-file)     │  │  (Shortcuts)      │                       │
│  └──────────────────┘  └──────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────────┐
│                     PostgreSQL Databases                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  events  │  │contracts │  │  queue   │  │  main    │  +more     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────────┐
│                      Hardware & External APIs                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ESP32-Cam │  │BLE Beacon│  │ SendGrid │  │iOS/iWatch│           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Event Generation**: Activities generate events (user actions, sensor data, timers)
2. **Event Storage**: Events stored in PostgreSQL events database
3. **Queue Processing**: Background processes poll for new events
4. **Event Filtering**: Processes filter events by type/tags
5. **Processing Logic**: Custom logic processes relevant events
6. **Action Execution**: Send notifications, validate contracts, trigger automations
7. **Dashboard Updates**: Widgets display real-time system state

## Key Features

### 🎯 Event-Driven Architecture
- All activities generate immutable events
- Events as single source of truth
- Time-series event storage with partitioning
- Complex event pattern matching

### 🔧 Gabru Framework
- **Zero-Config APIs**: Define a Pydantic model → Get full REST API
- **Process Management**: Built-in background worker lifecycle control
- **Queue Processing**: Database-backed queue for reliable event processing
- **Auto-UI Generation**: Web interface generated from data models

### 🎨 Theming System
- **Multiple Themes**: Choose from Nature, Twilight, Dark, Solarized, and Console.
- **Dark/Light Mode**: Intelligent switching based on theme selection.
- **Persistence**: Remembers your preference across sessions.
- **Console Mode**: High-contrast, monospace theme for the hacker aesthetic.

### 🧭 Dashboard Control Surface
- **Reliability Row**: Quick health view for processes, queues, notifications, devices, and event flow.
- **Pinned Widgets**: Keep the most important widgets fixed at the top.
- **Drag Reorder**: Arrange dashboard widgets to match how you actually use the system.
- **Universal Timeline**: One feed for skills, projects, notifications, and system events.
- **Action-First Widgets**: Trigger common actions directly from the dashboard.

### 📊 Applications
- **Events**: Event logging and querying system
- **Contracts**: Behavioral rule validation (e.g., "Exercise before gaming")
- **Devices**: Hardware device management (cameras, sensors, beacons)
- **Shortcuts**: iOS/iWatch shortcut integration
- **Thoughts**: Personal note-taking system
- **Skills**: Gamified XP and leveling tied to tagged activities

### 🤖 Background Processes
- **Sentinel**: Validates behavioral contracts against event history
- **Courier**: Notification delivery via ntfy.sh (default) and SendGrid (email)
- **Heimdall**: Visual monitoring with YOLO object detection
- **Atmos**: BLE-based indoor location tracking
- **SkillXPProcessor**: Converts skill tags on events into XP and level-up milestones
- **Log Viewer**: Built-in real-time log monitoring for all active processes.

### 📱 IoT Integration
- ESP32-CAM for video streaming
- BLE beacons for presence detection
- Trilateration for indoor positioning
- ESP32/Arduino device support

## Quick Start

### Prerequisites

- Raspberry Pi 3B+ or newer (or any Linux system)
- Python 3.8+
- PostgreSQL 12+

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/rasbhari.git
   cd rasbhari
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL databases**
   ```bash
   # Create databases
   sudo -u postgres psql
   CREATE DATABASE rasbhari_events;
   CREATE DATABASE rasbhari_contracts;
   CREATE DATABASE rasbhari_queue;
   CREATE DATABASE rasbhari_main;
   \q
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
    # Add your Open WebUI URL for the AI chat overlay
    # OPEN_WEBUI_URL="http://localhost:8080"
    nano .env
    ```

5. **Run the server**
   ```bash
   python server.py
   ```

6. **Access the dashboard**
   ```
   Open http://localhost:5000 in your browser
   ```

### First Steps

After installation:

1. **Create your first event**
   ```bash
   curl -X POST http://localhost:5000/events/ \
     -H "Content-Type: application/json" \
     -d '{
       "event_type": "test",
       "description": "My first event",
       "tags": ["test"]
     }'
   ```

2. **View the dashboard**
   - Navigate to `http://localhost:5000`
   - See all apps and their recent data
   - Access individual app UIs

3. **Chat with AI**
   - Click the floating chat button on the bottom right of the dashboard.
   - Interact with your configured Ollama service via Open WebUI.

4. **Configure the AI Chat**
   - Ensure you have Ollama running and Open WebUI accessible.
   - Set the `OPEN_WEBUI_URL` environment variable in your `.env` file.
     Example: `OPEN_WEBUI_URL="http://localhost:8080"`

5. **Explore the documentation**
   - [Gabru Framework Guide](gabru/readme.md)
   - [Creating Apps](apps/README.md)
   - [Background Processes](processes/)

## Applications

Rasbhari includes several built-in applications:

### Events App
The backbone of the system. Stores all events with timestamps, types, and tags.

- **API**: `POST /events/`, `GET /events/`, `GET /events/<id>`
- **Documentation**: See [Apps README](apps/README.md#1-events)

### Contracts App
Define behavioral rules and validate them against event history.

- **Example**: "No gaming unless exercise happened today"
- **Processes**: Sentinel (event-driven), SentinelOC (scheduled)
- **Documentation**: [Apps README](apps/README.md#2-contracts), [Sentinel Process](processes/sentinel/readme.md)

### Devices App
Manage IoT hardware devices (cameras, sensors, beacons).

- **Supported**: ESP32-CAM, BLE beacons, ESP32, Arduino
- **Processes**: Heimdall (vision), Atmos (location)
- **Documentation**: [Apps README](apps/README.md#3-devices)

### Skills App
Gamify deliberate practice by linking event tags to skill progression.

- **Example**: Trigger an activity with `#python` and gain +20 XP in the `Python` skill.
- **Widget**: Multi-ring dashboard view plus recent level-up timeline.
- **Process**: SkillXPProcessor consumes event tags and updates skill state.

### Shortcuts App
Create iOS/iWatch shortcuts that generate events.

- **Features**: Shortcut signing, event triggering
- **Use Case**: Voice command → Event → Automation
- **Documentation**: [Apps README](apps/README.md#4-shortcuts)

### Thoughts App
Simple personal note-taking system.

- **Purpose**: Quick notes and ideas
- **Documentation**: [Apps README](apps/README.md#5-thoughts)

**Want to create your own app?** See the [App Creation Guide](apps/README.md#creating-a-new-app)

## Background Processes

### Sentinel
Validates behavioral contracts against historical events.

**Example Contract**: "Gaming only allowed after 30 minutes of exercise today"

- When a `gaming:start` event occurs
- Sentinel checks for `exercise:complete` events today
- If no exercise found → Sends contract violation notification

📖 [Sentinel Documentation](processes/sentinel/readme.md)

### Courier
Notification delivery service.

- Listens for events tagged with `notification`
- Sends emails via SendGrid API
- Triggers iOS shortcuts for push notifications

📖 [Courier Documentation](processes/courier/readme.md)

### Heimdall
Visual monitoring with YOLO object detection.

- Streams from ESP32-CAM devices
- Detects objects (people, cats, etc.)
- Generates tracking events

📖 [Heimdall Documentation](processes/heimdall/readme.md)

### Atmos
BLE-based indoor location tracking.

- Uses trilateration from multiple BLE beacons
- Tracks device location in 2D space
- Generates presence events

📖 [Atmos Documentation](processes/atmos/readme.md)

### 📜 Log Monitoring
View real-time logs for any active process directly from the dashboard.
- **Live Logs**: Fetch the latest 100 lines of logs.
- **Troubleshooting**: Instantly diagnose issues without SSH access.

**Want to create your own process?** See the [QueueProcessor Guide](gabru/qprocessor/README.md)

## Documentation

### Framework Documentation
- **[Gabru Framework](gabru/readme.md)** - Complete framework guide
  - Database layer (DB, Services)
  - Web layer (Server, App, Model)
  - Process layer (Process, ProcessManager, QueueProcessor)
  - Logger and utilities
- **[Flask Framework](gabru/flask/README.md)** - Web application layer
- **[QueueProcessor](gabru/qprocessor/README.md)** - Event processing guide

### Application Documentation
- **[Apps Guide](apps/README.md)** - Creating and extending apps
- Individual app documentation in `apps/` directory

### Process Documentation
- **[Sentinel](processes/sentinel/readme.md)** - Contract validation
- **[Courier](processes/courier/readme.md)** - Notifications
- **[Heimdall](processes/heimdall/readme.md)** - Visual monitoring
- **[Atmos](processes/atmos/readme.md)** - Location tracking

### Setup Guides
- **Installation Guide**: See [Quick Start](#quick-start) above
- **Environment Variables**: See [.env.example](.env.example)

## System Requirements

### Hardware
- **Minimum**: Raspberry Pi 3B+ (1GB RAM)
- **Recommended**: Raspberry Pi 4 (2GB+ RAM)
- **Storage**: 16GB+ SD card (Class 10)
- **Optional**: ESP32-CAM, BLE beacons for IoT features

### Software
- **OS**: Raspberry Pi OS (Debian-based) or any Linux distribution
- **Python**: 3.8 or higher
- **PostgreSQL**: 12 or higher
- **Optional**: macOS with Apple Shortcuts for iOS integration

### Network
- Local network access for web interface
- Internet connection for:
  - SendGrid email notifications
  - iOS shortcut syncing
  - Python package installation

### Key Dependencies
- **Flask 3.1+**: Web framework
- **Pydantic 2.11+**: Data validation
- **psycopg2**: PostgreSQL adapter
- **ultralytics**: YOLO object detection (for Heimdall)
- **scipy**: Location calculations (for Atmos)
- **sendgrid**: Email notifications (for Courier)

Full dependency list: [requirements.txt](requirements.txt)

## Project Structure

```
rasbhari/
├── gabru/                  # Core framework
│   ├── db/                # Database layer
│   ├── flask/             # Web layer
│   ├── qprocessor/        # Queue processing
│   ├── apple/             # iOS integration
│   ├── log.py            # Logging system
│   └── process.py        # Process management
├── apps/                  # Application definitions
│   ├── events.py
│   ├── contracts.py
│   ├── devices.py
│   ├── shortcuts.py
│   └── thoughts.py
├── services/              # Database services
│   ├── events.py
│   ├── contracts.py
│   └── ...
├── model/                 # Data models
│   ├── event.py
│   ├── contract.py
│   └── ...
├── processes/             # Background processes
│   ├── sentinel/         # Contract validator
│   ├── courier/          # Notification service
│   ├── heimdall/         # Visual monitoring
│   └── atmos/            # Location tracking
├── templates/             # HTML templates
├── static/                # CSS, JavaScript
├── util/                  # Utilities
├── server.py             # Main entry point
├── requirements.txt      # Python dependencies
└── .env.example          # Environment template
```

## Development

### Creating a New App

1. Define your data model (Pydantic)
2. Create a service (extends CRUDService)
3. Create an app (instantiate App class)
4. Register with server

Full guide: [Creating a New App](apps/README.md#creating-a-new-app)

### Creating a Background Process

1. Extend QueueProcessor class
2. Implement `filter_item()` and `_process_item()`
3. Register with an app

Full guide: [QueueProcessor Guide](gabru/qprocessor/README.md)

### Adding Custom Routes

Extend the App class and add custom Flask routes:

```python
from gabru.flask.app import App

class CustomApp(App):
    def __init__(self):
        super().__init__('Custom', CustomService(), CustomModel)
        self.setup_custom_routes()

    def setup_custom_routes(self):
        @self.blueprint.route('/custom', methods=['GET'])
        def custom_endpoint():
            return {"data": "custom"}
```

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

### Areas for Contribution
- New applications (finance, health, etc.)
- New background processes
- Hardware integrations
- Documentation improvements
- Bug fixes and optimizations

## Troubleshooting

### Common Issues

**Database connection failed**
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Verify credentials in `.env` file
- Ensure databases exist: `sudo -u postgres psql -l`

**Process not starting**
- Check if `enabled=True` when registering
- Verify `start_process_manager()` is called
- Check logs in `LOG_DIR` directory

**Import errors**
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (need 3.8+)

**Port already in use**
- Change `SERVER_PORT` in `.env`
- Or kill process using port 5000: `sudo lsof -ti:5000 | xargs kill`

## License

This project is licensed under the MIT License - see the [license.md](license.md) file for details.

## Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Data validation by [Pydantic](https://docs.pydantic.dev/)
- Object detection by [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
- Email delivery via [SendGrid](https://sendgrid.com/)

---

**Built with ❤️ for automation and simplicity**

For questions or support, please open an issue on GitHub.
