from flask import Blueprint, jsonify, render_template, request

from gabru.log import Logger
from model.contract import Contract
from services.contracts import ContractService

contracts_app = Blueprint('contracts', __name__)

contracts_service = ContractService()

log = Logger.get_log('Contracts')


@contracts_app.route('/', methods=['POST'])
def create_contract():
    """Create a new contract."""
    data = request.json
    try:
        new_contract = Contract(**data)
        contract_id = contracts_service.create(new_contract)
        if contract_id:
            return jsonify({"id": contract_id, "message": "Contract created successfully"}), 201
        else:
            return jsonify({"error": "Failed to create contract"}), 500
    except Exception as e:
        log.exception(e)
        return jsonify({"error": str(e)}), 400


@contracts_app.route('/', methods=['GET'])
def get_all_contracts():
    """Retrieve all contracts."""
    contracts = contracts_service.get_recent_items(5)
    return jsonify([c.dict() for c in contracts]), 200


@contracts_app.route('/<int:contract_id>', methods=['GET'])
def get_contract(contract_id):
    """Retrieve a single contract by ID."""
    contract = contracts_service.get_by_id(contract_id)
    if contract:
        return jsonify(contract.dict()), 200
    else:
        return jsonify({"error": "Contract not found"}), 404


@contracts_app.route('/<int:contract_id>', methods=['PUT'])
def update_contract(contract_id):
    """Update an existing contract."""
    data = request.json
    try:
        updated_contract = Contract(id=contract_id, **data)
        if contracts_service.update(updated_contract):
            return jsonify({"message": "Contract updated successfully"}), 200
        else:
            return jsonify({"error": "Contract not found or failed to update"}), 404
    except Exception as e:
        log.exception(e)
        return jsonify({"error": str(e)}), 400


@contracts_app.route('/<int:contract_id>', methods=['DELETE'])
def delete_contract(contract_id):
    """Delete a contract by ID."""
    if contracts_service.delete(contract_id):
        return jsonify({"message": "Contract deleted successfully"}), 200
    else:
        return jsonify({"error": "Contract not found"}), 404


@contracts_app.route('/home')
def home():
    return render_template('contracts_home.html')
