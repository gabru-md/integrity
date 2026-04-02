from datetime import datetime, timedelta
from flask import jsonify
from apps.user_docs import build_app_user_guidance
from gabru.auth import PermissionManager, write_access_required
from gabru.flask.app import App
from model.promise import Promise
from services.promises import PromiseService
from services.events import EventService
from services.recommendation_followups import RecommendationFollowUpService
from services.users import UserService
from processes.promise_processor import PromiseProcessor
from gabru.flask.util import render_flask_template

promise_service = PromiseService()
event_service = EventService()
user_service = UserService()
recommendation_followup_service = RecommendationFollowUpService(promise_service=promise_service)


def _should_filter_by_exact_event_type(promise: Promise) -> bool:
    return bool(promise.target_event_type and not promise.target_event_type.startswith("project:"))


def _event_matches_promise_filters(event, promise: Promise) -> bool:
    if promise.target_event_type:
        if promise.target_event_type.startswith("project:"):
            if not PromiseProcessor._event_matches_project_target(event, promise.target_event_type):
                return False
        elif event.event_type != promise.target_event_type:
            return False

    if promise.target_event_tag and promise.target_event_tag not in (event.tags or []):
        return False

    return True

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
            name="Promises",
            service=promise_service,
            model_class=Promise,
            home_template="promises.html",
            _process_model_data_func=process_promise_data,
            widget_type="kanban",
            widget_recent_limit=3,
            user_guidance=build_app_user_guidance("Promises")
        )
        self.register_process(PromiseProcessor, enabled=True)

    def setup_home_route(self):
        @self.blueprint.route('/home')
        def home():
            promises = self.service.get_all()
            recommendation_map = self._build_recommendation_map()
            # Calculate some stats for the dashboard
            stats = {
                "total": len(promises),
                "active": len([p for p in promises if p.status == 'active']),
                "fulfilled": len([p for p in promises if p.status == 'fulfilled']),
                "broken": len([p for p in promises if p.status == 'broken']),
            }
            return render_flask_template(self.home_template,
                                   model_class_attributes=self.model_class_attributes,
                                   model_class_name=self.model_class.__name__,
                                   app_name=self.name,
                                   user_guidance=self.user_guidance,
                                   promises=promises,
                                   promise_recommendations=recommendation_map,
                                   stats=stats)

        @self.blueprint.route('/<int:promise_id>/refresh', methods=['POST'])
        @write_access_required
        def refresh_stats(promise_id):
            promise = self.service.get_by_id(promise_id)
            if not promise:
                return jsonify({"error": "Promise not found"}), 404
            
            # Re-count events for current period
            end_time = datetime.now()
            last_check = promise.last_checked_at or promise.created_at
            
            # Simple window query
            from services.events import EventService
            ev_service = EventService()
            
            filters = {
                "user_id": promise.user_id,
                "timestamp": {"$gt": last_check, "$lt": end_time}
            }
            if _should_filter_by_exact_event_type(promise):
                filters["event_type"] = promise.target_event_type
            
            events = ev_service.find_all(filters=filters)
            count = sum(1 for e in events if _event_matches_promise_filters(e, promise))
            
            promise.current_count = count
            self.service.update(promise)
            
            return jsonify({
                "message": "Stats refreshed",
                "current_count": count
            }), 200

        @self.blueprint.route('/<int:promise_id>/history', methods=['GET'])
        def get_promise_history(promise_id):
            promise = self.service.get_by_id(promise_id)
            if not promise:
                return jsonify({"error": "Promise not found"}), 404
            
            # Fetch last 14 days of events
            end_time = datetime.now()
            start_time = end_time - timedelta(days=14)
            
            filters = {
                "user_id": promise.user_id,
                "timestamp": {"$gt": start_time, "$lt": end_time}
            }
            if _should_filter_by_exact_event_type(promise):
                filters["event_type"] = promise.target_event_type
            
            events = event_service.find_all(filters=filters)
            
            # Filter by tag if needed and format for chart
            history_data = []
            for e in events:
                if _event_matches_promise_filters(e, promise):
                    # Convert to hours (e.g., 14.5 for 2:30 PM)
                    ts = e.timestamp
                    hour_val = ts.hour + (ts.minute / 60)
                    history_data.append({
                        "x": ts.strftime("%Y-%m-%d"),
                        "y": round(hour_val, 2),
                        "time": ts.strftime("%H:%M")
                    })
            
            return jsonify({
                "promise_name": promise.name,
                "history": history_data
            })

    @staticmethod
    def _build_recommendation_map() -> dict[int, list[dict]]:
        user_id = PermissionManager.get_current_user_id()
        if not user_id:
            return {}

        user = user_service.get_by_id(user_id)
        recommendation_limit = 2
        if user:
            if not getattr(user, "recommendations_enabled", True):
                recommendation_limit = 0
            else:
                recommendation_limit = max(0, int(getattr(user, "recommendation_limit", 2) or 0))
        if recommendation_limit <= 0:
            return {}

        recommendation_map: dict[int, list[dict]] = {}
        recommendations = recommendation_followup_service.recommendation_engine.get_recommendations(
            user_id=user_id,
            app_name="Promises",
            limit=recommendation_limit,
        )
        for item in recommendations:
            if item.scope_id is None:
                continue
            recommendation_map.setdefault(item.scope_id, []).append(
                RecommendationFollowUpService._to_follow_up_payload(item)
            )
        return recommendation_map

promises_app = PromiseApp()
