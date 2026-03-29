from apps.user_docs import build_app_user_guidance
from gabru.flask.app import App
from model.network_signature import NetworkSignature
from services.network_signatures import NetworkSignatureService
from processes.network_sniffer import NetworkSniffer

def process_data(json_data):
    # Split comma-separated tags into a list
    tags = json_data.get("tags", "")
    if isinstance(tags, str):
        json_data["tags"] = [t.strip() for t in tags.split(',') if t.strip()]
    return json_data

network_signatures_app = App(
    name="Network-Signatures",
    service=NetworkSignatureService(),
    model_class=NetworkSignature,
    _process_model_data_func=process_data,
    home_template="crud.html",
    user_guidance=build_app_user_guidance("NetworkSignatures")
)

# Register the sniffer process
network_signatures_app.register_process(NetworkSniffer)
