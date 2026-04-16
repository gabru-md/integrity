from flask import Blueprint, jsonify, request

from gabru.auth import PermissionManager, write_access_required
from services.agent_runs import AgentRunService


agent_runs_blueprint = Blueprint("agent_runs", __name__, url_prefix="/agent-runs")
agent_run_service = AgentRunService()


def _current_user_id():
    user_id = PermissionManager.get_current_user_id()
    if not user_id:
        return None
    return int(user_id)


@agent_runs_blueprint.route("/ticket/<int:ticket_id>/queue", methods=["POST"])
@write_access_required
def queue_ticket_run(ticket_id):
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"error": "Login required"}), 401
    data = request.get_json(silent=True) or {}
    run_id = agent_run_service.queue_for_ticket(
        user_id=user_id,
        ticket_id=ticket_id,
        workspace_key=data.get("workspace_key") or "integrity",
        agent_kind=data.get("agent_kind") or "dry-run",
    )
    if not run_id:
        return jsonify({"error": "Ticket not found or agent run could not be queued"}), 404
    run = agent_run_service.get_by_id(run_id)
    return jsonify(agent_run_service.to_payload(run) if run else {"id": run_id}), 202


@agent_runs_blueprint.route("/next", methods=["GET"])
@write_access_required
def next_run():
    run = agent_run_service.next_queued(
        workspace_key=(request.args.get("workspace_key") or "").strip() or None,
        agent_kind=(request.args.get("agent_kind") or "").strip() or None,
    )
    if not run:
        return jsonify({"run": None}), 200
    return jsonify({"run": agent_run_service.to_payload(run, include_prompt=True)}), 200


@agent_runs_blueprint.route("/<int:run_id>/claim", methods=["POST"])
@write_access_required
def claim_run(run_id):
    data = request.get_json(silent=True) or {}
    run = agent_run_service.claim(run_id, data.get("worker_name") or data.get("worker") or "unknown-worker")
    if not run:
        return jsonify({"error": "Run is not claimable"}), 409
    return jsonify(agent_run_service.to_payload(run, include_prompt=True)), 200


@agent_runs_blueprint.route("/<int:run_id>/start", methods=["POST"])
@write_access_required
def start_run(run_id):
    run = agent_run_service.start(run_id)
    if not run:
        return jsonify({"error": "Run cannot be started"}), 409
    return jsonify(agent_run_service.to_payload(run, include_prompt=True)), 200


@agent_runs_blueprint.route("/<int:run_id>/complete", methods=["POST"])
@write_access_required
def complete_run(run_id):
    data = request.get_json(silent=True) or {}
    run = agent_run_service.complete(
        run_id,
        result_summary=data.get("result_summary") or data.get("summary") or "",
        changed_files=data.get("changed_files") or [],
    )
    if not run:
        return jsonify({"error": "Run cannot be completed"}), 409
    return jsonify(agent_run_service.to_payload(run)), 200


@agent_runs_blueprint.route("/<int:run_id>/fail", methods=["POST"])
@write_access_required
def fail_run(run_id):
    data = request.get_json(silent=True) or {}
    run = agent_run_service.fail(run_id, error_message=data.get("error_message") or data.get("error") or "")
    if not run:
        return jsonify({"error": "Run cannot be failed"}), 409
    return jsonify(agent_run_service.to_payload(run)), 200


@agent_runs_blueprint.route("/<int:run_id>/cancel", methods=["POST"])
@write_access_required
def cancel_run(run_id):
    run = agent_run_service.cancel(run_id)
    if not run:
        return jsonify({"error": "Run cannot be cancelled"}), 409
    return jsonify(agent_run_service.to_payload(run)), 200
