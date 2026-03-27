# Gabru Flask Layer

The Flask layer turns models and services into usable web apps with very little boilerplate.

## Components

### `Server`

`gabru.flask.server.Server` owns:

- the Flask app
- app registration
- process manager startup
- dashboard routes
- process control routes

Built-in routes include:

- `/`
- `/apps`
- `/processes`
- `/enable_process/<name>`
- `/disable_process/<name>`
- `/start_process/<name>`
- `/stop_process/<name>`
- `/process_logs/<name>`
- `/download/<filename>`

The current Rasbhari dashboard also injects:

- `widgets_data`
- `reliability_data`
- `universal_timeline`

into the `home.html` template.

### `App`

`gabru.flask.app.App` is the standard CRUD app abstraction.

Constructor knobs that matter in the current codebase:

- `name`
- `service`
- `model_class`
- `get_recent_limit`
- `widget_recent_limit`
- `_process_model_data_func`
- `home_template`
- `widget_enabled`
- `widget_type`
- `widget_config`

Default routes:

| Method | Endpoint |
|---|---|
| `POST` | `/{app}/` |
| `GET` | `/{app}/` |
| `GET` | `/{app}/<id>` |
| `PUT` | `/{app}/<id>` |
| `DELETE` | `/{app}/<id>` |
| `GET` | `/{app}/home` |
| `POST` | `/{app}/widget/enable` |
| `POST` | `/{app}/widget/disable` |

### `UIModel` / `WidgetUIModel`

These models allow the framework to infer what should appear:

- in forms
- in tables
- in widgets

Typical field metadata:

```python
name: str = Field(default="", widget_enabled=True)
id: Optional[int] = Field(default=None, edit_enabled=False)
```

## Widget Notes

The framework exposes generic widget types such as:

- `basic`
- `count`
- `timeline`
- `kanban`
- `progress_ring`

The current Rasbhari dashboard also adds a custom `skill_tree` rendering path inside `templates/home.html`.

## Current Dashboard Capabilities

The project-specific `home.html` currently supports:

- reliability cards
- pinned widgets
- local drag reordering
- collapsed widgets
- action-first buttons
- universal timeline filters

That behavior lives at the template layer rather than in generic Gabru framework code.

## Current Rasbhari Apps Built on This Layer

- `Blogs`
- `Promises`
- `Events`
- `Thoughts`
- `Devices`
- `Projects`
- `Activities`
- `Skills`

See [apps/README.md](/Users/manish/PycharmProjects/integrity/apps/README.md).
