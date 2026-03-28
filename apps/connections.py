from datetime import datetime

from flask import jsonify, request

from apps.user_docs import build_app_user_guidance
from gabru.auth import write_access_required
from gabru.flask.app import App
from gabru.flask.util import render_flask_template
from model.connection import Connection
from model.connection_interaction import ConnectionInteraction
from services.connection_interactions import ConnectionInteractionService
from services.connections import ConnectionService


def process_connection_data(data):
    tags = data.get("tags", [])
    if isinstance(tags, str):
        data["tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
    elif tags is None:
        data["tags"] = []
    return data


class ConnectionsApp(App[Connection]):
    def __init__(self):
        self.connection_service = ConnectionService()
        self.connection_interaction_service = ConnectionInteractionService()
        super().__init__(
            "Connections",
            service=self.connection_service,
            model_class=Connection,
            home_template="connections.html",
            _process_model_data_func=process_connection_data,
            widget_type="kanban",
            widget_recent_limit=4,
            user_guidance=build_app_user_guidance("Connections")
        )

    def setup_home_route(self):
        @self.blueprint.route('/home')
        def home():
            connections = self.connection_service.get_all()
            overdue = self._overdue_connections(connections)
            recent_interactions = self.connection_interaction_service.get_recent_items(8)
            stats = {
                "total": len(connections),
                "active": len([item for item in connections if item.active]),
                "overdue": len(overdue),
                "recent_interactions": len(recent_interactions),
            }
            return render_flask_template(
                self.home_template,
                app_name=self.name,
                user_guidance=self.user_guidance,
                connections=connections,
                recent_interactions=recent_interactions,
                stats=stats,
            )

    @staticmethod
    def _overdue_connections(connections):
        now = datetime.now()
        overdue = []
        for item in connections:
            if not item.active:
                continue
            if item.last_contact_at is None:
                overdue.append(item)
                continue
            if (now - item.last_contact_at).days > item.cadence_days:
                overdue.append(item)
        return overdue


connections_app = ConnectionsApp()


def _process_interaction_data(data, connection_id=None):
    tags = data.get("tags", [])
    if isinstance(tags, str):
        data["tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
    elif tags is None:
        data["tags"] = []

    if not data.get("created_at"):
        data["created_at"] = datetime.now()

    safe_connection_id = int(connection_id or data.get("connection_id"))
    connection = connections_app.connection_service.get_by_id(safe_connection_id)
    if not connection:
        raise ValueError("connection_id must reference an existing connection")

    data["connection_id"] = safe_connection_id
    data["connection_name"] = connection.name
    data["user_id"] = connection.user_id
    return data


@connections_app.blueprint.route('/<int:connection_id>/ledger', methods=['GET'])
def get_connection_ledger(connection_id):
    items = connections_app.connection_interaction_service.get_by_connection_id(connection_id, limit=25)
    return jsonify([item.dict() for item in items]), 200


@connections_app.blueprint.route('/<int:connection_id>/ledger', methods=['POST'])
@write_access_required
def create_connection_ledger_item(connection_id):
    data = request.json or {}
    try:
        processed_data = _process_interaction_data(dict(data), connection_id=connection_id)
        new_item = ConnectionInteraction(**processed_data)
        new_id = connections_app.connection_interaction_service.create(new_item)
        if new_id:
            return jsonify({"message": "Interaction logged", "id": new_id}), 201
        return jsonify({"error": "Failed to create interaction"}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@connections_app.blueprint.route('/ledger/recent', methods=['GET'])
def get_recent_connection_ledger():
    items = connections_app.connection_interaction_service.get_recent_items(25)
    return jsonify([item.dict() for item in items]), 200


@connections_app.blueprint.route('/ledger/<int:interaction_id>', methods=['GET'])
def get_connection_interaction(interaction_id):
    item = connections_app.connection_interaction_service.get_by_id(interaction_id)
    if not item:
        return jsonify({"error": "Interaction not found"}), 404
    return jsonify(item.dict()), 200


@connections_app.blueprint.route('/ledger/<int:interaction_id>', methods=['PUT'])
@write_access_required
def update_connection_interaction(interaction_id):
    item = connections_app.connection_interaction_service.get_by_id(interaction_id)
    if not item:
        return jsonify({"error": "Interaction not found"}), 404

    data = request.json or {}
    try:
        processed_data = _process_interaction_data(dict(data), connection_id=item.connection_id)
        updated_item = ConnectionInteraction(id=interaction_id, **processed_data)
        if connections_app.connection_interaction_service.update(updated_item):
            return jsonify({"message": "Interaction updated"}), 200
        return jsonify({"error": "Failed to update interaction"}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@connections_app.blueprint.route('/ledger/<int:interaction_id>', methods=['DELETE'])
@write_access_required
def delete_connection_interaction(interaction_id):
    item = connections_app.connection_interaction_service.get_by_id(interaction_id)
    if not item:
        return jsonify({"error": "Interaction not found"}), 404
    if connections_app.connection_interaction_service.delete(interaction_id):
        return jsonify({"message": "Interaction deleted"}), 200
    return jsonify({"error": "Failed to delete interaction"}), 500
