from flask import Blueprint, request, jsonify, render_template
from typing import TypeVar, Generic
from gabru.log import Logger
from gabru.service import CRUDService

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
                 widget_recent_limit=3, _process_data_func=None):
        self.name = name
        self.log = Logger.get_log(f"{self.name.capitalize()}")
        self.blueprint = Blueprint(self.name, __name__)
        self.service = service
        self.get_recent_limit = get_recent_limit
        self.widget_recent_limit = widget_recent_limit
        self.model_class = model_class
        self._process_data_func = _process_data_func
        self.setup_default_routes()

        self.setup_home_route()

    def setup_default_routes(self):

        @self.blueprint.route('/', methods=['POST'])
        def create():
            """ Create a new entity """
            data = request.json
            try:
                data = self._process_data(data)
                new_entity = self.model_class(**data)
                new_entity_id = self.service.create(new_entity)
                if new_entity_id:
                    return jsonify(
                        {"id": new_entity_id, "message": f"{self.name.capitalize()} created successfully"}), 201
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

        @self.blueprint.route('/int:entity_id>', methods=['PUT'])
        def update(entity_id):
            """ Update an entity """
            data = request.json
            try:
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

    def setup_home_route(self):

        @self.blueprint.route('/home')
        def home():
            """ Renders the home page """
            print(f"Main app templates path: {self.blueprint.template_folder}")
            return render_template(f"{self.name.lower()}/home.html")

    def _process_data(self, data):
        if self._process_data_func:
            return self._process_data_func(data)
        return data

    def widget_data(self):
        entities = self.service.get_recent_items(self.widget_recent_limit)
        return [e.dict() for e in entities]
