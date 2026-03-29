from flask import request, jsonify
from gabru.auth import write_access_required
from gabru.flask.app import App
from apps.user_docs import build_app_user_guidance
from model.blog import BlogPost
from services.blogs import BlogService
from services.eventing import emit_event_safely
from datetime import datetime
from gabru.flask.util import render_flask_template

blog_service = BlogService()

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
            _process_model_data_func=process_blog_data,
            widget_type="timeline",
            user_guidance=build_app_user_guidance("Blogs"),
        )

    def setup_home_route(self):
        @self.blueprint.route('/home')
        def home():
            posts = self.service.get_all()
            return render_flask_template(self.home_template, 
                                   posts=posts, 
                                   app_name=self.name,
                                   user_guidance=self.user_guidance)

        @self.blueprint.route('/p/<slug>')
        def view_post(slug):
            post = self.service.get_by_slug(slug)
            if not post:
                return "Post not found", 404
            return render_flask_template('blog_post.html', post=post)

        @self.blueprint.route('/', methods=['POST'])
        @write_access_required
        def create_post():
            data = request.json
            try:
                processed_data = self.process_model_data(data)
                new_post = self.model_class(**processed_data)
                new_id = self.service.create(new_post)
                
                if new_id:
                    emit_event_safely(
                        self.log,
                        user_id=new_post.user_id,
                        event_type="blog:posted",
                        timestamp=datetime.now(),
                        description=f"New blog post: {new_post.title}",
                        tags=["blog", "content"],
                    )
                    return jsonify({"message": "Blog post created", "id": new_id}), 201
                return jsonify({"error": "Failed to create post"}), 500
            except Exception as e:
                self.log.exception(e)
                return jsonify({"error": str(e)}), 400

blog_app = BlogApp()
