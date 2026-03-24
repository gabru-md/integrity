from datetime import datetime, timedelta
from flask import render_template
from gabru.flask.app import App
from model.promise import Promise
from services.promises import PromiseService
from processes.promise_processor import PromiseProcessor

promise_service = PromiseService()

def process_promise_data(data):
    # Initialize next_check_at if not provided
    if not data.get('next_check_at'):
        now = datetime.now()
        freq = data.get('frequency', 'daily')
        if freq == 'daily':
            data['next_check_at'] = now + timedelta(days=1)
        elif freq == 'weekly':
            data['next_check_at'] = now + timedelta(weeks=1)
        elif freq == 'monthly':
            data['next_check_at'] = now + timedelta(days=30)
        else: # once
            data['next_check_at'] = now + timedelta(days=1) # check after 24h by default for once?
    return data

class PromiseApp(App[Promise]):
    def __init__(self):
        super().__init__(
            name="promises",
            service=promise_service,
            model_class=Promise,
            home_template="promises.html",
            _process_model_data_func=process_promise_data
        )
        self.register_process(PromiseProcessor, enabled=True)

    def setup_home_route(self):
        @self.blueprint.route('/home')
        def home():
            promises = self.service.get_all()
            # Calculate some stats for the dashboard
            stats = {
                "total": len(promises),
                "active": len([p for p in promises if p.status == 'active']),
                "fulfilled": len([p for p in promises if p.status == 'fulfilled']),
                "broken": len([p for p in promises if p.status == 'broken']),
            }
            return render_template(self.home_template,
                                   model_class_attributes=self.model_class_attributes,
                                   model_class_name=self.model_class.__name__,
                                   app_name=self.name,
                                   promises=promises,
                                   stats=stats)

promises_app = PromiseApp()
