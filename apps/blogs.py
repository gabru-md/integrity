from flask import render_template, request, jsonify
from gabru.flask.app import App
from model.blog import BlogPost
from services.blogs import BlogService
from services.events import EventService
from model.event import Event
from datetime import datetime

blog_service = BlogService()
event_service = EventService()

def process_blog_data(data):
    # Ensure tags is a list
    tags = data.get('tags', [])
    if isinstance(tags, str):
        data['tags'] = [t.strip() for t in tags.split(',') if t.strip()]
    
    # Generate slug from title if not present
    if not data.get('slug') and data.get('title'):
        data['slug'] = data['title'].lower().replace(' ', '-')
    
    data['updated_at'] = datetime.now()
    return data

class BlogApp(App[BlogPost]):
    def __init__(self):
        super().__init__(
            name="Blogs",
            service=blog_service,
            model_class=BlogPost,
            home_template="blog.html",
            _process_model_data_func=process_blog_data
        )

    def setup_home_route(self):
        @self.blueprint.route('/home')
        def home():
            posts = self.service.get_all()
            return render_template(self.home_template, 
                                   posts=posts, 
                                   app_name=self.name)

        @self.blueprint.route('/p/<slug>')
        def view_post(slug):
            post = self.service.get_by_slug(slug)
            if not post:
                return "Post not found", 404
            return render_template('blog_post.html', post=post)

        @self.blueprint.route('/', methods=['POST'])
        def create_post():
            data = request.json
            try:
                processed_data = self.process_model_data(data)
                new_post = self.model_class(**processed_data)
                new_id = self.service.create(new_post)
                
                if new_id:
                    # Trigger event
                    event = Event(
                        event_type="blog:posted",
                        timestamp=datetime.now(),
                        description=f"New blog post: {new_post.title}",
                        tags=["blog", "content"]
                    )
                    event_service.create(event)
                    return jsonify({"message": "Blog post created", "id": new_id}), 201
                return jsonify({"error": "Failed to create post"}), 500
            except Exception as e:
                return jsonify({"error": str(e)}), 400

blog_app = BlogApp()
