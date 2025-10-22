# Rasbhari

**Rasbhari** is a collection of code designed to automate and simplify daily life, built around an **event-driven architecture**. Its core is the **`gabru`** module, which provides the essential framework for building the entire system.

## Overview

Rasbhari runs on a **Raspberry Pi** and consists of multiple interconnected applications that utilize a central framework for data handling, logging, and process management. All actions and information flow through a system of generated **events**.

**Key Components:**

  * **`gabru` Framework**: Provides core classes for `App`, `Service`, `Entity`, and processes.
  * **Event-Driven Architecture**: All activities (like eating food or ordering) generate **events** stored in a PostgreSQL database.
  * **Decoupled Processes**: Hardware devices and processes are separated via the **Devices App**, allowing for cleaner, more flexible code.

-----

## Architecture

The system is built on a foundation of framework modules, a central database, and multiple applications that manage specific concerns.

### `gabru` Framework

The `gabru` module contains the low-level, reusable components:

  * **`App`**: The base class for all applications.
  * **Services**: `ReadOnlyService` and `CRUDService` for data management.
  * **Database (`DB`)**: Structured connection layer for **PostgreSQL**.
  * **Logging**: A system-wide logger that collects logs into the `LOGS_DIR`.
  * **Processes**: Includes `QueueProcessor` for event-driven logic and a generic `Process` class for background daemons.

-----

## Applications

Multiple applications run on the Raspberry Pi, each managing a specific domain and often leveraging events to trigger actions in other apps.

### Events

The **Events App** is the backbone of the entire platform. It allows for the creation and storage of various types of events in the events database. These events are consumed by other apps to initiate processes or create derivative data.

| Processes | Description |
| :--- | :--- |
| **[Courier](processes/courier/readme.md)** | A **notification delivery service** that listens to the event stream for events tagged with `notification`. It sends email notifications via **SendGrid API**, often configured to trigger **iOS Shortcuts** automations. |

### Contracts

The **Contracts App** is the project's **integrity system**. It enables the creation of rules or "contracts" that monitor and act upon the stream of events generated from different sources. The core function is provided by two processes: **Sentinel** (event-triggered) and **SentinelOC** (schedule-based).

| Processes | Description |
| :--- | :--- |
| **[Sentinel](processes/sentinel/readme.md)** | The **Event-Driven contract validator**. It listens for specific events, evaluates complex behavioral rules (contracts) against historical events, and publishes a `contract:invalidation` event if a rule is broken (e.g., "Gaming only after exercise"). |
| **[SentinelOC](processes/sentinel/readme.md)** | The **Open Contract validator**. It runs periodically (e.g., every 15 minutes) to evaluate contracts that are **not** triggered by an event, such as a daily check (e.g., "Check every day if exercise happened"). |

### Devices

The **Devices App** manages the configuration and access for various hardware devices (`ESP32-Cams`, `ESP32`, `Arduino`, `BLE Beacon`) that form the Rasbhari ecosystem.

  * It uses a **`DeviceService`** to decouple applications from specific hardware code.
  * *Example Use Case*: Configuring **ESP32Cams** to be used by the **Heimdall** process to track a cat.

| Processes | Description |
| :--- | :--- |
| **[Heimdall](processes/heimdall/readme.md)** | A visual monitoring daemon that utilizes devices (like ESP32Cams) for object detection and tracking. |
| **[Atmos](processes/atmos/readme.md)** | A **BLE device location tracker**. It uses data from multiple BLE beacons/receivers and a **trilateration algorithm** to determine the precise location (X, Y) of moving devices in a defined area. |

### Shortcuts

A simple utility app that enables the creation of shortcuts on platforms like iOS/iWatch, which, when invoked, generate a specified event.

  * **iOS Integration**: Shortcuts require signing with a local Apple signing service (e.g., on a MacBook) before they can be imported and used on an iPhone or iWatch.
  * The generated events then trigger a chain of configured processes across the platform.

### Thoughts

**Thoughts** is an extremely simple, personal **tweeting engine** that provides complete control over personal notes. It is used to remember and note important things.

-----
