from datetime import datetime

from flask import jsonify, request

from apps.user_docs import build_app_user_guidance
from gabru.auth import write_access_required
from gabru.flask.app import App
from model.kanban_ticket import KanbanTicket
from services.kanban_tickets import KanbanTicketService


ticket_service = KanbanTicketService()


def process_ticket_data(data):
    now = datetime.now()
    data["project_id"] = int(data.get("project_id") or 0)
    data["title"] = (data.get("title") or "").strip()
    data["description"] = (data.get("description") or "").strip()
    data["state"] = (data.get("state") or "backlog").strip().lower().replace("-", "_")
    data["is_archived"] = bool(data.get("is_archived", False))
    data["updated_at"] = now
    if not data.get("created_at"):
        data["created_at"] = now
    if not data.get("state_changed_at"):
        data["state_changed_at"] = now
    return data


kanban_tickets_app = App(
    "KanbanTickets",
    service=ticket_service,
    model_class=KanbanTicket,
    _process_model_data_func=process_ticket_data,
    widget_enabled=False,
    user_guidance=build_app_user_guidance("KanbanTickets"),
)


@kanban_tickets_app.blueprint.route("/project/<int:project_id>", methods=["GET"])
def list_by_project(project_id):
    items = kanban_tickets_app.service.get_by_project_id(project_id)
    return jsonify([item.dict() for item in items]), 200


@kanban_tickets_app.blueprint.route("/<int:ticket_id>/move", methods=["POST"])
@write_access_required
def move_ticket(ticket_id):
    data = request.get_json(silent=True) or {}
    requested_state = data.get("state")
    if not requested_state:
        ticket = kanban_tickets_app.service.get_by_id(ticket_id)
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
        requested_state = kanban_tickets_app.service.next_state(ticket.state.value if hasattr(ticket.state, "value") else ticket.state)
    try:
        ticket = kanban_tickets_app.service.move_ticket(ticket_id, requested_state)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    return jsonify(ticket.dict()), 200


@kanban_tickets_app.blueprint.route("/<int:ticket_id>/archive", methods=["POST"])
@write_access_required
def archive_ticket(ticket_id):
    ticket = kanban_tickets_app.service.archive_ticket(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    return jsonify(ticket.dict()), 200


@kanban_tickets_app.blueprint.route("/<int:ticket_id>/board-edit", methods=["POST"])
@write_access_required
def board_edit_ticket(ticket_id):
    ticket = kanban_tickets_app.service.get_by_id(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    ticket.title = title
    ticket.description = description
    ticket.updated_at = datetime.now()
    if not kanban_tickets_app.service.update(ticket):
        return jsonify({"error": "Failed to update ticket"}), 500
    return jsonify(ticket.dict()), 200


@kanban_tickets_app.blueprint.route("/<int:ticket_id>/dependencies", methods=["POST"])
@write_access_required
def update_ticket_dependencies(ticket_id):
    data = request.get_json(silent=True) or {}
    dependency_ticket_ids = data.get("dependency_ticket_ids") or []
    try:
        ticket = kanban_tickets_app.service.update_dependencies(ticket_id, dependency_ticket_ids)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    return jsonify(ticket.dict()), 200
