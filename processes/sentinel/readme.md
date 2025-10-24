# Sentinel

**Sentinel** is a contract validation system that monitors events and enforces behavioral rules (contracts) on your Raspberry Pi. It acts as a guardian that ensures specific conditions are met based on the events happening in your system.

## Overview

Sentinel consists of two independent processes:

* **Sentinel**: Event-driven contract validator (triggered by specific events)

* **SentinelOC**: Open contract validator (runs periodically on a schedule)

## What are Contracts?

Contracts are rules that define expected behaviors or conditions. They can:

* Be triggered by specific events (e.g., "gaming should only happen after exercise")

* Run periodically without triggers (e.g., "check every hour if exercise happened today")

* Support complex conditions with logical operators (AND, OR, NOT)

* Include time windows (e.g., "within the last 2 hours")

---

## Sentinel Contract Language (SCL) Syntax

The Sentinel Contract Language (SCL) is a Domain-Specific Language designed for expressing complex temporal and historical conditions efficiently. All contracts follow the structure: **`{TRIGGER_EVENT} AFTER {CONDITION_BLOCK}`**.

### 1. Event Count and Time Window Checks

This syntax checks for the historical occurrence and frequency of other events relative to the moment the trigger fires.

| Syntax | Description | Example |
| :--- | :--- | :--- |
| `[NUMBER]x EVENT` | Checks if the event occurred at least **`[NUMBER]`** times in the entire history before the trigger. (E.g., `2x lunch`) | `login AFTER 1x lunch` |
| `EVENT WITHIN [NUMBER][UNIT]` | Checks if the event occurred at least once within the specified time window before the trigger. | `gaming AFTER reading WITHIN 3h` |
| `[NUMBER]x EVENT WITHIN [NUMBER][UNIT]` | Combines count and time window logic. | `payment AFTER 3x error WITHIN 10m` |
| `NOT EVENT` | Checks if the event has **not** occurred at all before the trigger. | `sleep AFTER NOT coffee` |

*Units can be: **s** (seconds), **m** (minutes), **h** (hours).*

### 2. Historical Sequence Checks (The `SINCE` Keyword)

The **`SINCE`** keyword creates a specific time window defined by the *last* occurrence of a boundary event. This is highly efficient for checking state resets.

| Syntax | Description | Example |
| :--- | :--- | :--- |
| `EVENT_A SINCE EVENT_B` | Checks if **EVENT_A** occurred at least once in the period between the *last* **EVENT_B** and the `TRIGGER_EVENT`. | `alert AFTER error SINCE status:reset` |

### 3. Temporal Clock Checks

This syntax checks the absolute time of day the `TRIGGER_EVENT` occurred. Clock values must be four digits (**HHMM**), based on the local time of the Sentinel server.

| Syntax | Meaning | Example |
| :--- | :--- | :--- |
| `CLOCK(HHMM) AFTER` | Trigger must occur **after** the specified time. | `gaming AFTER CLOCK(2100) AFTER` |
| `CLOCK(HHMM) BEFORE` | Trigger must occur **before** the specified time. | `coffee AFTER CLOCK(1100) BEFORE` |
| `CLOCK(HHMM1) BETWEEN CLOCK(HHMM2)` | Trigger must occur **between** the two specified times. | `entry AFTER CLOCK(0800) BETWEEN CLOCK(1800)` |
| `NOT CLOCK(HHMM) AFTER` | Trigger must **not** occur after the time (i.e., must occur before). | `sleep AFTER NOT CLOCK(2300) AFTER` |

### 4. Boolean Logic

Conditions can be nested using parentheses and combined with logical operators. **Parentheses are mandatory for combining terms.**

| Operator | Rule | Example |
| :--- | :--- | :--- |
| `AND` | Both conditions must be true. | `A AND (B WITHIN 1h)` |
| `OR` | At least one condition must be true. | `A OR B` |
| `NOT` | Negates the following term or grouped condition. | `NOT (A AND B)` |

---

### SCL Real-World Examples

| Contract Name | SCL Contract String | Explanation |
| :--- | :--- | :--- |
| **Work Hour Check** | `work:slack_message AFTER CLOCK(0900) AFTER AND CLOCK(1700) BEFORE` | A work message must only be sent between **09:00** and **17:00**. |
| **Exercise Routine** | `dinner AFTER (1x exercise WITHIN 10h) OR (cooking_dinner WITHIN 30m)` | Dinner can happen if you either exercised today (last 10h) **OR** if you started cooking in the last 30 minutes. |
| **Billing Reset** | `transaction AFTER transaction:failed SINCE monthly:billing_reset` | A transaction fail notification should only trigger if a failure has occurred **since** the last monthly billing cycle was reset. |
| **No Late Gaming** | `gaming:start AFTER NOT CLOCK(2200) AFTER AND NOT (1x sleep WITHIN 24h)` | Gaming must **not** start after **22:00** **AND** you must have slept at least once in the last day. |

---

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
│  SentinelOC   │
│  (Scheduled)  │
└─────────────────┘

```

## Troubleshooting

### Contract not running

1.  Check contract `is_valid` flag in the database
2.  For open contracts: check if `start_time` and `end_time` are valid for current time
3.  For trigger contracts: `trigger_event` matches incoming event type exactly
4.  For open contracts: `next_run_date` is in the past and `trigger_event` is null
5.  Process is enabled in `apps/contracts.py`

### Syntax errors in conditions

**Common issues:**

* Missing parentheses for complex conditions
* Incorrect time unit (use `s`, `m`, or `h`)
* Typo in event names (must match exactly)
* Missing `AFTER` keyword

**Valid:** `gaming AFTER (exercise WITHIN 2h) AND laundry`
**Invalid:** `gaming AFTER exercise WITHIN 2h AND laundry` (missing parentheses)

### Performance issues

If Sentinel is slow:

1.  Add database indexes on `event_type` and `timestamp` columns
2.  Reduce time windows in contracts
3.  Archive old events
4.  Increase SentinelOC sleep time in `sentinel.py` (line 22)

## Future Enhancements

Potential improvements (see `todo.md`):

* \[ \] Enforce temporal conditions (time-of-day restrictions)

* \[ \] Document frequency behavior more clearly

* \[ \] Add contract templates for common patterns

* \[ \] Support for contract priorities

* \[ \] Contract dependency chains

## Related Components

* **Events App** (`apps/events.py`): Provides event storage

* **Courier** (`processes/courier/`): Sends notifications for contract violations

* **Contracts Service** (`services/contracts.py`): Database operations

* **Contract Model** (`model/contract.py`): Data structure definition

## License

See main project [license](../../license.md).