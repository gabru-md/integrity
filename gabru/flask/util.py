import os
import subprocess
from functools import lru_cache

from flask import render_template

from apps.user_docs import build_rasbhari_mental_model, build_rasbhari_tutorial


@lru_cache(maxsize=1)
def get_build_info():
    version = (
        os.getenv("RASBHARI_VERSION")
        or os.getenv("GIT_COMMIT_SHA")
        or os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("FLY_IMAGE_REF")
    )

    if not version:
        try:
            version = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except Exception:
            version = None

    if version and ":" in version:
        version = version.rsplit(":", 1)[-1]
    if version and len(version) > 12:
        version = version[:12]

    return {
        "label": f"Build {version}" if version else "Build unknown",
        "commit": version,
    }


def render_flask_template(template_name, **context):
    open_webui_url = os.getenv('OPEN_WEBUI_URL')
    return render_template(
        template_name,
        open_webui_url=open_webui_url,
        build_info=get_build_info(),
        rasbhari_mental_model=build_rasbhari_mental_model(),
        rasbhari_tutorial=build_rasbhari_tutorial(),
        **context,
    )
