# Processes

The `processes/` directory contains the **background worker layer** of Rasbhari. Each process represents a distinct background task that reacts to events, monitors sensors, or performs periodic maintenance.

## What is a Process?

A **Process** in Rasbhari is a background worker that runs in its own thread. Each process is built on the `gabru.process.Process` framework and can:

- **React to events** in real-time
- **Perform periodic checks** using a timer
- **Update the state** of the database
- **Emit new events** for other processes to handle
- **Be enabled or disabled** from the dashboard

## Process Types

### 1. Queue Processor
Extends `gabru.qprocessor.QueueProcessor`. Designed to consume a stream of data (like events) from a database table and process them one by one.

### 2. Standard Process
Extends `gabru.process.Process`. A generic background thread for tasks like video streaming or periodic sensor polling.

## Available Processes

### 1. Promise Processor
**Location**: `processes/promise_processor.py`
**Trigger**: Events or periodic schedule

The core logic for the Promises app. It monitors the event stream for tags or types that match active promises and performs periodic checks to determine if recurring promises (daily, weekly, monthly) were fulfilled or broken.

- **Key Features**:
  - Streak management
  - Completion rate calculation
  - Next check scheduling
  - Event-driven fulfillment detection

### 2. Heimdall
**Location**: `processes/heimdall/heimdall.py`
**Trigger**: Continuous

A visual monitoring process that handles camera streams and can perform computer vision tasks.

### 3. Courier
**Location**: `processes/courier/courier.py`
**Trigger**: Events

A notification service that reacts to specific events and sends alerts (e.g., via Telegram or local notification).

### 4. Atmos
**Location**: `processes/atmos/atmos.py`
**Trigger**: Continuous

A Bluetooth Low Energy (BLE) scanning process for room-level location tracking.

### 5. Skill XP Processor
**Location**: `processes/skill_xp_processor.py`
**Trigger**: Events

Consumes the event stream, matches tags like `#python` or `fitness` to configured skills, awards XP, recalculates levels, writes level-up history, and emits `skill:level_up` events for the rest of the system to react to.

## Implementation Details

### Creating a New Process

To create a new process, extend either `Process` or `QueueProcessor`:

```python
from gabru.process import Process
import time

class MyProcess(Process):
    def __init__(self, **kwargs):
        super().__init__(name="MyProcess", **kwargs)

    def process(self):
        while self.running:
            self.log.info("Processing...")
            time.sleep(60)
```

### Registering a Process

Processes are typically registered within an App definition:

```python
# apps/my_app.py
my_app.register_process(MyProcess, enabled=True)
```

The `ProcessManager` will then automatically start the process when the server runs.
