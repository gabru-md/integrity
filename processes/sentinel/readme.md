*xample: "This document provides a deep dive into the Sentinel service, intended for developers who wish to understand its architecture or users who want to create and manage contracts."*

# Sentinel

**Sentinel** is a contract validation system that monitors events and enforces behavioral rules (contracts) on your Raspberry Pi. It acts as a guardian that ensures specific conditions are met based on the events happening in your system.

## Overview

Sentinel consists of two independent processes:
- **Sentinel**: Event-driven contract validator (triggered by specific events)
- **SentinelOC**: Open contract validator (runs periodically on a schedule)

## What are Contracts?

Contracts are rules that define expected behaviors or conditions. They can:
- Be triggered by specific events (e.g., "gaming should only happen after exercise")
- Run periodically without triggers (e.g., "check every hour if exercise happened today")
- Support complex conditions with logical operators (AND, OR, NOT)
- Include time windows (e.g., "within the last 2 hours")

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Events    │─────▶│   Sentinel   │─────▶│ Contract Valid? │
│  Database   │      │  (Triggered) │      │   Yes/No Event  │
└─────────────┘      └──────────────┘      └─────────────────┘
                              │
                              │ Reads contracts
                              ▼
                     ┌─────────────────┐
                     │ Contract Service│
                     └─────────────────┘
                              ▲
                              │
                     ┌──────────────┐
                     │  SentinelOC  │◀────── Timer (15 min)
                     │    (Open)    │
                     └──────────────┘
```

## How It Works

### 1. Sentinel (Event-Triggered)

Sentinel listens to the events database as a queue processor. When a new event arrives:

1. **Filter**: Check if any contract is triggered by this event type
2. **Evaluate**: Parse and evaluate the contract conditions against historical events
3. **Validate**: Determine if the contract is still valid
4. **Notify**: If invalid, publish a `contract:invalidation` event (tagged for notification)

**Example Flow:**
```
Event: "gaming:league_of_legends" arrives
  ↓
Sentinel finds contract: "Gaming only after exercise"
  ↓
Check: Did "exercise" event occur within required timeframe?
  ↓
NO → Publish "Contract violated: Gaming only after exercise"
```

### 2. SentinelOC (Open Contracts)

SentinelOC validates contracts that are **not** triggered by events. It runs every 15 minutes and:

1. **Query**: Fetch all open contracts that are due for validation
2. **Evaluate**: Check conditions using the contract's frequency as the time window
3. **Update**: Update `last_run_date` and calculate `next_run_date` based on frequency
4. **Notify**: If invalid, publish a `contract:invalidation` event

**Supported Frequencies:**
- `hourly`: Check every hour
- `daily`: Check every day
- `weekly`: Check every week
- `monthly`: Check every month

## Contract Language

Sentinel uses a simple domain-specific language (DSL) to define contracts:

### Syntax

```
<trigger_event> AFTER <conditions>
```

### Basic Examples

**Simple condition:**
```
gaming:league_of_legends AFTER exercise
```
*"Gaming is allowed only after an exercise event occurs"*

**With time window:**
```
gaming:league_of_legends AFTER exercise WITHIN 2h
```
*"Gaming is allowed only if exercise happened within the last 2 hours"*

**Count-based:**
```
gaming:league_of_legends AFTER 2x exercise WITHIN 6h
```
*"Gaming requires at least 2 exercise sessions in the last 6 hours"*

### Logical Operators

**AND operator:**
```
gaming:league_of_legends AFTER exercise AND laundry:loaded
```
*"Gaming requires both exercise AND laundry to be loaded"*

**OR operator:**
```
gaming:league_of_legends AFTER exercise OR cooking_dinner
```
*"Gaming is allowed after either exercise OR cooking dinner"*

**NOT operator:**
```
gaming:league_of_legends AFTER NOT hand_wash
```
*"Gaming is only allowed if hand_wash has NOT occurred"*

**Complex combinations:**
```
gaming:league_of_legends AFTER (2x exercise WITHIN 1h) AND (laundry:loaded WITHIN 30m)
```
*"Gaming requires 2 exercises in the last hour AND laundry loaded in the last 30 minutes"*

### Time Units

- `s` - seconds
- `m` - minutes
- `h` - hours

## Contract Types

### Trigger-Based Contracts

Contracts with a `trigger_event` field are evaluated whenever that event occurs.

**Contract Model:**
```python
{
    "name": "Gaming after exercise",
    "trigger_event": "gaming:league_of_legends",
    "conditions": "gaming:league_of_legends AFTER 2x exercise WITHIN 6h",
    "start_time": "2025-01-01 00:00:00",
    "end_time": "2025-12-31 23:59:59",
    "frequency": null,
    "last_run_date": null,
    "next_run_date": null
}
```

### Open Contracts

Contracts without a `trigger_event` (or `trigger_event = null`) are evaluated periodically based on `frequency`.

**Contract Model:**
```python
{
    "name": "Daily exercise check",
    "trigger_event": null,
    "conditions": "health:daily_check AFTER exercise",
    "frequency": "daily",
    "start_time": "2025-01-01 00:00:00",
    "end_time": "2025-12-31 23:59:59",
    "last_run_date": 1736899200,
    "next_run_date": 1736985600
}
```

## Components

### Parser (`condition/parser.py`)

Converts human-readable contract strings into Abstract Syntax Trees (AST), then into evaluation-ready dictionaries.

**Input:**
```
gaming:league_of_legends AFTER (2x exercise WITHIN 1h) AND (laundry:loaded WITHIN 30m)
```

**Output:**
```json
{
  "name": "Generated Contract",
  "trigger": "gaming:league_of_legends",
  "conditions": {
    "operator": "AND",
    "terms": [
      {
        "type": "event_count",
        "event": "exercise",
        "min_count": 2,
        "time_window": 1,
        "unit": "h"
      },
      {
        "type": "event_count",
        "event": "laundry:loaded",
        "min_count": 1,
        "time_window": 30,
        "unit": "m"
      }
    ]
  }
}
```

### Evaluator (`condition/evaluator.py`)

Evaluates parsed contract conditions against the event database.

**Key Methods:**
- `evaluate_contract_on_trigger()`: For event-triggered contracts
- `evaluate_open_contract()`: For open contracts with frequency
- `_evaluate_conditions()`: Recursive condition evaluation with support for AND/OR/NOT

**Evaluation Logic:**
1. Calculate time window from contract or frequency
2. Query events within the time range
3. Count matching events
4. Compare against required minimum count
5. Apply logical operators (AND/OR/NOT)

## Database Schema

### Contracts Table

```sql
CREATE TABLE contracts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    frequency VARCHAR(50),           -- hourly, daily, weekly, monthly
    trigger_event VARCHAR(255),      -- null for open contracts
    conditions TEXT,                 -- DSL string
    violation_message TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    last_run_date TIMESTAMP,
    next_run_date TIMESTAMP
);
```

## Events Generated

When a contract is violated, Sentinel publishes:

```python
{
    "event_type": "contract:invalidation",
    "timestamp": 1736899200,
    "description": "Contract: Gaming after exercise rendered invalid",
    "tags": ["contracts", "notification"]
}
```

These events can be picked up by **Courier** to send notifications.

## Configuration

Sentinel processes are registered in `apps/contracts.py`:

```python
contracts_app.register_process(Sentinel, enabled=True)
contracts_app.register_process(SentinelOC, enabled=True, name="SentinelOC")
```

### Environment Variables

No specific environment variables required. Sentinel uses the contracts database connection defined in `.env`:

```bash
# Contracts DB (PostgreSQL)
CONTRACTS_DB_HOST=localhost
CONTRACTS_DB_PORT=5432
CONTRACTS_DB_NAME=contracts
CONTRACTS_DB_USER=postgres
CONTRACTS_DB_PASSWORD=yourpassword
```

## Usage Examples

### Creating a Contract via Web UI

1. Navigate to `http://your-pi-ip:5000/contracts`
2. Click "Create New Contract"
3. Fill in:
   - **Name**: "Gaming after exercise"
   - **Trigger Event**: `gaming:league_of_legends`
   - **Conditions**: `gaming:league_of_legends AFTER 2x exercise WITHIN 6h`
   - **Start/End Time**: Set validity period
   - **Frequency**: Leave empty for trigger-based

### Creating an Open Contract

1. **Name**: "Daily exercise reminder"
2. **Trigger Event**: Leave empty or set to `null`
3. **Conditions**: `health:check AFTER exercise`
4. **Frequency**: `daily`
5. **Next Run Date**: Set initial check time

## Monitoring

### Logs

Sentinel logs are available in the application logs:

```bash
tail -f logs/Sentinel.log
tail -f logs/SentinelOC.log
```

**Example log output:**
```
2025-01-15 14:32:10 - Sentinel - INFO - Contract Gaming after exercise remains valid
2025-01-15 18:45:22 - Sentinel - INFO - Contract Gaming after exercise was invalidated
2025-01-15 18:45:22 - Sentinel - INFO - Queued contract:invalidation event
```

### Queue Stats

Monitor Sentinel's queue processing via the `queuestats` table:

```sql
SELECT * FROM queuestats WHERE process_name LIKE 'Sentinel%';
```

## Troubleshooting

### Contract not being evaluated

**Check:**
1. Contract `start_time` and `end_time` are valid for current time
2. For trigger contracts: `trigger_event` matches incoming event type exactly
3. For open contracts: `next_run_date` is in the past and `trigger_event` is null
4. Process is enabled in `apps/contracts.py`

### Syntax errors in conditions

**Common issues:**
- Missing parentheses for complex conditions
- Incorrect time unit (use `s`, `m`, or `h`)
- Typo in event names (must match exactly)
- Missing `AFTER` keyword

**Valid:** `gaming AFTER (exercise WITHIN 2h) AND laundry`
**Invalid:** `gaming AFTER exercise WITHIN 2h AND laundry` (missing parentheses)

### Performance issues

If Sentinel is slow:
1. Add database indexes on `event_type` and `timestamp` columns
2. Reduce time windows in contracts
3. Archive old events
4. Increase SentinelOC sleep time in `sentinel.py` (line 22)

## Future Enhancements

Potential improvements (see `todo.md`):
- [ ] Enforce temporal conditions (time-of-day restrictions)
- [ ] Document frequency behavior more clearly
- [ ] Add contract templates for common patterns
- [ ] Support for contract priorities
- [ ] Contract dependency chains

## Related Components

- **Events App** (`apps/events.py`): Provides event storage
- **Courier** (`processes/courier/`): Sends notifications for contract violations
- **Contracts Service** (`services/contracts.py`): Database operations
- **Contract Model** (`model/contract.py`): Data structure definition

## License

See main project [license](../../license.md).