from gabru.flask.app import App
from model.contract import Contract
from processes.sentinel.sentinel import Sentinel, SentinelOC
from services.contracts import ContractService

contracts_app = App('Contracts', ContractService(), Contract)

contracts_app.register_process(Sentinel, enabled=True)

contracts_app.register_process(SentinelOC, enabled=True, name="SentinelOC")
