import os

from flask import render_template


def render_flask_template(template_name, **context):
    open_webui_url = os.getenv('OPEN_WEBUI_URL')
    return render_template(template_name, open_webui_url=open_webui_url, **context)
