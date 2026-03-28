from flask import Blueprint, request, jsonify, abort, redirect
from typing import TypeVar, Generic, Optional

from gabru.log import Logger
from gabru.db.service import CRUDService
from gabru.auth import PermissionManager, write_access_required, Role
from gabru.flask.util import render_flask_template

T = TypeVar('T')


class App(Generic[T]):
    """
    A generic application blueprint for a Flask server that provides
    standard RESTful API endpoints (CRUD) for a given data model.

    This class simplifies the creation of a full-featured API by handling
    common operations like creating, retrieving, updating, and deleting
    entities in the database via a provided service.
    """

    def __init__(self, name: str, service: CRUDService[T], model_class: type, get_recent_limit=10,
                 widget_recent_limit=3, _process_model_data_func=None, home_template="crud.html",
                 widget_enabled=True, widget_type="basic", widget_config: Optional[dict] = None,
                 user_guidance: Optional[dict] = None):
        self.name = name
        self.log = Logger.get_log(f"{self.name.capitalize()}")
        self.blueprint = Blueprint(self.name, __name__)
        self.service = service
        self.get_recent_limit = get_recent_limit
        self.widget_recent_limit = widget_recent_limit
        self.model_class = model_class
        self.model_class_attributes = self.get_model_class_attributes()
        self.user_guidance = self.build_user_guidance(user_guidance)
        self._process_model_data_func = _process_model_data_func
        self.setup_default_routes()
        self.setup_home_route()
        self.processes = []
        self.home_template = home_template
        self.widget_enabled = widget_enabled
        self.widget_type = widget_type # basic, count, timeline, kanban, progress_ring
        self.widget_config = widget_config or {}
        self.server_instance = None

    def setup_default_routes(self):

        @self.blueprint.before_request
        def check_access():
            if not PermissionManager.is_authenticated():
                if request.method == "GET":
                    next_path = request.full_path if request.query_string else request.path
                    return redirect(f"/login?next={next_path}")
                return abort(401)
            if not PermissionManager.can_view_app(self.name):
                return abort(403)

        @self.blueprint.route('/', methods=['POST'])
        @write_access_required
        def create():
            """ Create a new entity """
            data = request.json
            data = dict(data)
            try:
                data = self.process_model_data(data)
                new_entity = self.model_class(**data)
                new_entity_id = self.service.create(new_entity)
                if new_entity_id:
                    return jsonify({"message": f"{self.name.capitalize()} created successfully"}), 200
                else:
                    return jsonify({"error": f"Failed to create {self.name.lower()}"}), 500
            except Exception as e:
                self.log.exception(e)
                return jsonify({"error": str(e)}), 400

        @self.blueprint.route('/', methods=['GET'])
        def get_recent():
            """ Get the N most recent entities"""
            entities = self.service.get_recent_items(self.get_recent_limit)
            return jsonify([e.dict() for e in entities])

        @self.blueprint.route('/<int:entity_id>', methods=['GET'])
        def get(entity_id):
            """ Get an entity by entity_id """
            entity = self.service.get_by_id(entity_id)
            if entity:
                return jsonify(entity.dict()), 200
            else:
                return jsonify({"error": f"{self.name.capitalize()} not found"}), 404

        @self.blueprint.route('/<int:entity_id>', methods=['PUT'])
        @write_access_required
        def update(entity_id):
            """ Update an entity """
            data = request.json
            data = dict(data)
            try:
                existing_entity = self.service.get_by_id(entity_id)
                if not existing_entity:
                    return jsonify({"error": f"{self.name.capitalize()} not found or failed to update"}), 404

                existing_data = existing_entity.dict()
                existing_data.update(data)
                existing_data["id"] = entity_id
                processed_data = self.process_model_data(existing_data)
                updated_entity = self.model_class(**processed_data)
                if self.service.update(updated_entity):
                    return jsonify({"message": f"{self.name.capitalize()} updated successfully"}), 200
                else:
                    return jsonify({"error": f"{self.name.capitalize()} not found or failed to update"}), 404
            except Exception as e:
                self.log.exception(e)
                return jsonify({"error": str(e)}), 400

        @self.blueprint.route('/<int:entity_id>', methods=['DELETE'])
        @write_access_required
        def delete(entity_id):
            """ Delete an entity """
            if self.service.delete(entity_id):
                return jsonify({"message": f"{self.name.capitalize()} deleted successfully"})
            else:
                return jsonify({"error": f"{self.name.capitalize()} not found"})

        @self.blueprint.route('/widget/<action>', methods=['POST'])
        @write_access_required
        def toggle_widget(action):
            if action == 'enable':
                success = self.set_widget_enabled(True)
                if success:
                    return jsonify({"message": f"Widget for {self.name} enabled successfully"}), 200
                else:
                    return jsonify({"message": f"Widget for {self.name} was already enabled"}), 200
            elif action == 'disable':
                success = self.set_widget_enabled(False)
                if success:
                    return jsonify({"message": f"Widget for {self.name} disabled successfully"}), 200
                else:
                    return jsonify({"message": f"Widget for {self.name} was already disabled"}), 200


    def get_model_class_attributes(self):
        clazz = self.model_class
        attributes = []

        for name, field in clazz.model_fields.items():
            attr_type = str(field.annotation)
            is_required = field.is_required()

            # Clean up type string
            attr_type_str = attr_type.lower().replace("<class '", "").replace("'>", "").replace(
                "typing.optional[", "").replace("]", "").replace("typing.list[", "list-")

            extra = field.json_schema_extra or {}
            edit_enabled = extra.get("edit_enabled", True)
            download_enabled = extra.get("download_enabled", False)
            widget_enabled = extra.get("widget_enabled", False)
            ui_enabled = extra.get("ui_enabled", edit_enabled or widget_enabled)
            label = name.replace("_", " ").title()
            description = getattr(field, "description", None) or ""

            attributes.append({
                "name": name,
                "label": label,
                "type": attr_type_str,
                "description": description,
                "required": is_required,
                "edit_enabled": edit_enabled,
                "widget_enabled": widget_enabled,
                "download_enabled": download_enabled,
                "ui_enabled": ui_enabled
            })
        return attributes

    def build_user_guidance(self, guidance: Optional[dict] = None):
        guidance = guidance or {}
        described_fields = []
        for attr in self.model_class_attributes:
            if attr["description"] and attr["name"] != "id":
                described_fields.append({
                    "name": attr["name"],
                    "label": attr["label"],
                    "description": attr["description"],
                    "required": attr["required"],
                    "edit_enabled": attr["edit_enabled"],
                    "ui_enabled": attr["ui_enabled"],
                })

        return {
            "overview": guidance.get("overview", ""),
            "how_to_use": guidance.get("how_to_use", []),
            "glossary": guidance.get("glossary", []),
            "examples": guidance.get("examples", []),
            "fields": guidance.get("fields", described_fields),
        }

    def setup_home_route(self):

        @self.blueprint.route('/home')
        def home():
            """ Renders the home page """
            return render_flask_template(self.home_template,
                                   model_class_attributes=self.model_class_attributes,
                                   model_class_name=self.model_class.__name__,
                                   app_name=self.name,
                                   user_guidance=self.user_guidance)

    def process_model_data(self, data):
        if self._process_model_data_func:
            return self._process_model_data_func(data)
        return data

    def register_process(self, process_class: type, *args, **kwargs):
        """Registers a process class and its arguments for later instantiation."""
        if process_class:
            self.processes.append((process_class, args, kwargs))

    def get_processes(self):
        return self.processes

    def widget_data(self):
        if not self.widget_enabled:
            return None, None
        
        data = None
        if self.widget_type == "count":
            data = self.service.count()
        elif self.widget_type == "timeline":
            entities = self.service.get_recent_items(self.widget_recent_limit)
            data = self._filter_entities(entities)
        elif self.widget_type == "kanban":
             entities = self.service.get_recent_items(self.widget_recent_limit)
             data = self._filter_entities(entities)
        elif self.widget_type == "progress_ring":
             # Placeholder for progress ring data (maybe use a specific field or count)
             data = self.service.count() 
        else: # basic
            entities = self.service.get_recent_items(self.widget_recent_limit)
            data = self._filter_entities(entities)
            
        return data, self.model_class_attributes

    def _filter_entities(self, entities):
        filtered_entities_data = []
        for entity in entities:
            entity_dict = entity.dict()
            filtered_item = {}
            for attr in self.model_class_attributes:
                if attr["widget_enabled"] and attr["name"] in entity_dict:
                    filtered_item[attr["name"]] = entity_dict[attr["name"]]
            if "id" in entity_dict:
                 filtered_item["id"] = entity_dict["id"]
            filtered_entities_data.append(filtered_item)
        return filtered_entities_data

    def set_widget_enabled(self, enabled: bool) -> bool:
        if self.widget_enabled != enabled:
            self.widget_enabled = enabled
            self.log.info(f"Widget for '{self.name.capitalize()}' set to {'Enabled' if enabled else 'Disabled'}")
            return True
        return False

    def get_running_process(self, process_class: type):
        if not self.server_instance or not self.server_instance.process_manager:
            self.log.error(f"Cannot get running process: Process Manager is not initialized.")
            return None

        process_manager = self.server_instance.process_manager

        # The process name is defined in Heimdall's __init__ (default is class name)
        process_name = process_class.__name__

        running_thread = process_manager.running_process_threads.get(process_name)

        if running_thread:
            #    If the thread is running, look up the actual instance object
            #    from the all_processes_map. This is the instance that holds the buffers.
            #    (We must use all_processes_map for the instance object, as running_process_threads
            #    holds the thread, which is also the instance itself since Process inherits Thread).
            return process_manager.all_processes_map.get(process_name)
        else:
            # Process is registered but not enabled/running.
            self.log.warning(f"Process {process_name} is not currently running.")
            return None
