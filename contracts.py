from gabru.app import App
from model.contract import Contract
from services.contracts import ContractService

contracts_app = App('Contracts', ContractService(), Contract)
