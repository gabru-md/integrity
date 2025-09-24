from gabru.app import App
from model.contract import Contract
from processes.sentinel import Sentinel
from services.contracts import ContractService

def process_data(json_data):
    json_data['is_valid'] = True
    return json_data


contracts_app = App('Contracts', ContractService(), Contract, _process_data_func=process_data)

contracts_app.register_process(Sentinel(daemon=True))
