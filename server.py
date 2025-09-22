import os

from flask import Flask

from apps.contracts import contracts_app
from apps.events import events_app

app = Flask(__name__)

app.register_blueprint(contracts_app, url_prefix='/contracts')
app.register_blueprint(events_app, url_prefix='/events')

if __name__ == '__main__':
    app.run(
        debug=os.getenv("SERVER_DEBUG", False),
        host='0.0.0.0',
        port=os.getenv("SERVER_PORT", 5000)
    )
