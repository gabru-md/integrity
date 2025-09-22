from contracts import contracts_app
from events import events_app
from gabru.server import Server

if __name__ == '__main__':
    server = Server("Rasbhari")
    server.register_app(contracts_app)
    server.register_app(events_app)
    server.run()
