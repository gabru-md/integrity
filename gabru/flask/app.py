import threading

from flask import Blueprint, request, jsonify, render_template, redirect
from typing import TypeVar, Generic, Optional

from gabru.log import Logger
from gabru.db.service import CRUDService

T = TypeVar('T')


class App(Generic[T]):
    """
    A generic application blueprint for a Flask server that provides
    standard RESTful API endpoints (CRUD) for a given data model.

    This class simplifies the creation of a full-featured API by handling
    common operations like creating, retrieving, updating, and deleting
    entities in the database via a provided service.
    """

    def __init__(self, name: str, service: CRUDService[T], model_class: type, get_recent_limit=5,
                 widget_recent_limit=3, _process_model_data_func=None, home_template="crud.html", widget_enabled=True):
        self.name = name
        self.log = Logger.get_log(f"{self.name.capitalize()}")
        self.blueprint = Blueprint(self.name, __name__)
        self.service = service
        self.get_recent_limit = get_recent_limit
        self.widget_recent_limit = widget_recent_limit
        self.model_class = model_class
        self.model_class_attributes = self.get_model_class_attributes()
        self._process_model_data_func = _process_model_data_func
        self.setup_default_routes()
        self.setup_home_route()
        self.processes = []
        self.home_template = home_template
        self.widget_enabled = widget_enabled

    def setup_default_routes(self):

        @self.blueprint.route('/', methods=['POST'])
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
        def update(entity_id):
            """ Update an entity """
            data = request.json
            data = dict(data)
            try:
                data = self.process_model_data(data)
                updated_entity = self.model_class(id=entity_id, **data)
                if self.service.update(updated_entity):
                    return jsonify({"message": f"{self.name.capitalize()} updated successfully"}), 200
                else:
                    return jsonify({"error": f"{self.name.capitalize()} not found or failed to update"}), 404
            except Exception as e:
                self.log.exception(e)
                return jsonify({"error": str(e)}), 400

        @self.blueprint.route('/<int:entity_id>', methods=['DELETE'])
        def delete(entity_id):
            """ Delete an entity """
            if self.service.delete(entity_id):
                return jsonify({"message": f"{self.name.capitalize()} deleted successfully"})
            else:
                return jsonify({"error": f"{self.name.capitalize()} not found"})

        @self.blueprint.route('/widget/<action>', methods=['POST'])
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

            attributes.append({
                "name": name,
                "type": attr_type_str,
                "required": is_required,
                "edit_enabled": edit_enabled,
                "widget_enabled": widget_enabled,
                "download_enabled": download_enabled,
                "ui_enabled": ui_enabled
            })
        return attributes

    def setup_home_route(self):

        @self.blueprint.route('/home')
        def home():
            """ Renders the home page """
            return render_template(self.home_template,
                                   model_class_attributes=self.model_class_attributes,
                                   model_class_name=self.model_class.__name__,
                                   app_name=self.name)

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
            return [], None
        entities = self.service.get_recent_items(self.widget_recent_limit)
        return [e.dict() for e in entities], self.model_class_attributes

    def set_widget_enabled(self, enabled: bool) -> bool:
        if self.widget_enabled != enabled:
            self.widget_enabled = enabled
            self.log.info(f"Widget for '{self.name.capitalize()}' set to {'Enabled' if enabled else 'Disabled'}")
            return True
        return False
