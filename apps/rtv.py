import os
from datetime import datetime
from pathlib import Path

from flask import jsonify, request, send_file

from apps.user_docs import build_app_user_guidance
from gabru.auth import PermissionManager, write_access_required
from gabru.flask.app import App
from gabru.flask.util import render_flask_template
from model.event import Event
from model.media_item import MediaItem
from processes.media_download_processor import MediaDownloadProcessor
from services.events import EventService
from services.media_cache import DEFAULT_CACHE_LIMIT_BYTES
from services.media_items import MediaItemService
from services.media_torrents import TorrentMetadataResolver


def _media_root() -> Path:
    return Path(os.getenv("RTV_MEDIA_DIR", "./media/rtv")).expanduser().resolve()


def _safe_media_file(local_path: str) -> Path:
    path = Path(local_path).expanduser().resolve()
    try:
        path.relative_to(_media_root())
    except ValueError:
        raise ValueError("Movie path is outside RTV_MEDIA_DIR.")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("Movie file not found.")
    return path


def _process_media_item_data(data):
    if not data.get("title") and data.get("local_path"):
        data["title"] = MediaItemService.title_from_path(Path(data["local_path"]))
    data.setdefault("kind", "movie")
    data.setdefault("source_type", "magnet" if data.get("magnet_uri") else "local_file")
    data.setdefault("status", "candidate")
    return data


class RTVApp(App[MediaItem]):
    def __init__(self):
        self.media_service = MediaItemService()
        self.event_service = EventService()
        self.torrent_resolver = TorrentMetadataResolver()
        super().__init__(
            "rTV",
            service=self.media_service,
            model_class=MediaItem,
            home_template="rtv_home.html",
            _process_model_data_func=_process_media_item_data,
            widget_type="kanban",
            widget_recent_limit=4,
            user_guidance=build_app_user_guidance("rTV"),
        )

    def setup_home_route(self):
        @self.blueprint.route('/home')
        def home():
            items = self.media_service.find_all(sort_by={"created_at": "DESC"})
            stats = {
                "total": len(items),
                "ready": len([item for item in items if item.status == "ready"]),
                "candidates": len([item for item in items if item.status == "candidate"]),
                "downloaded_gb": round(sum(item.file_size_bytes for item in items if item.status == "ready") / 1024 / 1024 / 1024, 2),
                "cache_limit_gb": round(int(os.getenv("RTV_MEDIA_CACHE_LIMIT_BYTES", str(DEFAULT_CACHE_LIMIT_BYTES))) / 1024 / 1024 / 1024, 2),
                "media_root": str(_media_root()),
            }
            return render_flask_template(
                self.home_template,
                app_name=self.name,
                user_guidance=self.user_guidance,
                items=items,
                stats=stats,
            )

    def emit_media_event(self, event_type: str, item: MediaItem, description: str, payload=None):
        try:
            self.event_service.create(Event(
                user_id=item.user_id or PermissionManager.get_current_user_id(),
                event_type=event_type,
                timestamp=datetime.now(),
                description=description,
                tags=["media", "rtv", "movie"],
                payload={
                    "media_item_id": item.id,
                    "title": item.title,
                    "status": item.status,
                    **(payload or {}),
                },
            ))
        except Exception as exc:
            self.log.warning("Failed to emit rTV media event: %s", exc)


rtv_app = RTVApp()
rtv_app.register_process(MediaDownloadProcessor, enabled=True)


@rtv_app.blueprint.route('/tv')
def tv_home():
    ready_items = rtv_app.media_service.get_ready_movies()
    continue_items = [item for item in ready_items if item.progress_seconds > 0]
    recent_items = sorted(ready_items, key=lambda item: item.downloaded_at or item.created_at, reverse=True)
    return render_flask_template(
        "rtv_tv.html",
        app_name=rtv_app.name,
        ready_items=ready_items,
        continue_items=continue_items,
        recent_items=recent_items,
    )


@rtv_app.blueprint.route('/play/<int:item_id>')
def play(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item or item.status != "ready" or item.cache_state != "cached":
        return "Movie not found or not ready.", 404
    restart = request.args.get("restart") in {"1", "true", "yes"}
    return render_flask_template("rtv_player.html", app_name=rtv_app.name, item=item, restart=restart)


@rtv_app.blueprint.route('/stream/<int:item_id>')
def stream(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item or item.status != "ready" or item.cache_state != "cached" or not item.local_path:
        return "Movie not found or not ready.", 404
    try:
        path = _safe_media_file(item.local_path)
    except ValueError as exc:
        return str(exc), 403
    except FileNotFoundError as exc:
        return str(exc), 404
    return send_file(path, conditional=True)


@rtv_app.blueprint.route('/scan', methods=['POST'])
@write_access_required
def scan_media_root():
    media_root = _media_root()
    media_root.mkdir(parents=True, exist_ok=True)
    created = 0
    skipped = 0
    for path in rtv_app.media_service.discover_video_files(media_root):
        existing = rtv_app.media_service.find_by_local_path(str(path))
        if existing:
            skipped += 1
            continue
        item = MediaItem(
            title=rtv_app.media_service.title_from_path(path),
            source_type="local_file",
        )
        item = rtv_app.media_service.mark_ready_from_local_file(item, path)
        item_id = rtv_app.media_service.create(item)
        if item_id:
            item.id = item_id
            rtv_app.emit_media_event("media:item_indexed", item, f"Indexed rTV movie {item.title}")
            created += 1
    return jsonify({"created": created, "skipped": skipped, "media_root": str(media_root)}), 200


@rtv_app.blueprint.route('/candidate', methods=['POST'])
@write_access_required
def add_candidate():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Untitled Movie").strip()
    magnet_uri = (data.get("magnet_uri") or "").strip()
    if not magnet_uri.startswith("magnet:"):
        return jsonify({"error": "A magnet URI is required for candidate media."}), 400
    item = MediaItem(title=title, source_type="magnet", status="candidate", magnet_uri=magnet_uri)
    item_id = rtv_app.media_service.create(item)
    if not item_id:
        return jsonify({"error": "Failed to add media candidate."}), 500
    item.id = item_id
    rtv_app.emit_media_event("media:candidate_added", item, f"Added rTV candidate {item.title}")
    return jsonify({"id": item_id, "message": "Candidate added"}), 201


@rtv_app.blueprint.route('/<int:item_id>/resolve-metadata', methods=['POST'])
@write_access_required
def resolve_metadata(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item:
        return jsonify({"error": "Movie candidate not found."}), 404
    if item.source_type != "magnet" or not item.magnet_uri:
        return jsonify({"error": "Only magnet candidates can resolve torrent metadata."}), 400

    try:
        metadata = rtv_app.torrent_resolver.resolve_largest_video(item.magnet_uri)
    except Exception as exc:
        item.status = "failed"
        rtv_app.media_service.update(item)
        rtv_app.emit_media_event("media:metadata_failed", item, f"Failed to resolve rTV metadata for {item.title}", {"error": str(exc)})
        return jsonify({"error": str(exc)}), 400

    item = rtv_app.media_service.apply_torrent_metadata(
        item,
        file_index=metadata.file_index,
        file_name=metadata.file_name,
        file_size_bytes=metadata.file_size_bytes,
        torrent_name=metadata.torrent_name,
    )
    if not rtv_app.media_service.update(item):
        return jsonify({"error": "Failed to update movie metadata."}), 500
    rtv_app.emit_media_event("media:metadata_ready", item, f"Resolved rTV metadata for {item.title}", {
        "selected_file_index": item.selected_file_index,
        "selected_file_name": item.selected_file_name,
        "selected_file_size_bytes": item.selected_file_size_bytes,
    })
    return jsonify({
        "id": item.id,
        "title": item.title,
        "selected_file_index": item.selected_file_index,
        "selected_file_name": item.selected_file_name,
        "selected_file_size_bytes": item.selected_file_size_bytes,
        "message": "Metadata resolved",
    }), 200


@rtv_app.blueprint.route('/<int:item_id>/queue-download', methods=['POST'])
@write_access_required
def queue_download(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item:
        return jsonify({"error": "Movie candidate not found."}), 404
    if item.selected_file_index is None or not item.selected_file_name:
        return jsonify({"error": "Resolve metadata before queueing download."}), 400
    if not rtv_app.media_service.queue_download(item_id):
        return jsonify({"error": "Failed to queue download."}), 500
    item = rtv_app.media_service.get_by_id(item_id)
    rtv_app.emit_media_event("media:download_queued", item, f"Queued rTV download for {item.title}", {
        "selected_file_index": item.selected_file_index,
        "selected_file_name": item.selected_file_name,
        "selected_file_size_bytes": item.selected_file_size_bytes,
    })
    return jsonify({"id": item_id, "message": "Download queued"}), 200


@rtv_app.blueprint.route('/<int:item_id>/title', methods=['POST'])
@write_access_required
def update_title(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item:
        return jsonify({"error": "Movie not found."}), 404
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required."}), 400
    item.title = title
    if not rtv_app.media_service.update(item):
        return jsonify({"error": "Failed to update title."}), 500
    return jsonify({"id": item_id, "title": title, "message": "Title updated"}), 200


@rtv_app.blueprint.route('/<int:item_id>/retry', methods=['POST'])
@write_access_required
def retry_item(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item:
        return jsonify({"error": "Movie not found."}), 404
    if item.status != "failed":
        return jsonify({"error": "Only failed movies can be retried."}), 400
    item.status = "candidate" if item.selected_file_index is None else "queued"
    item.download_progress = 0
    item.download_rate_kbps = 0
    item.download_peers = 0
    item.last_error = ""
    if not rtv_app.media_service.update(item):
        return jsonify({"error": "Failed to retry movie."}), 500
    event_type = "media:metadata_retry" if item.status == "candidate" else "media:download_retried"
    rtv_app.emit_media_event(event_type, item, f"Retried rTV movie {item.title}")
    return jsonify({"id": item_id, "status": item.status, "message": "Retry queued"}), 200


@rtv_app.blueprint.route('/<int:item_id>/delete-local', methods=['POST'])
@write_access_required
def delete_local_file(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item:
        return jsonify({"error": "Movie not found."}), 404
    if item.status in {"queued", "downloading"} or item.is_playing:
        return jsonify({"error": "Cannot delete a queued, downloading, or currently playing movie."}), 400
    path = Path(item.local_path).expanduser().resolve() if item.local_path else None
    if path and path.exists() and path.is_file():
        path.unlink()
    if not rtv_app.media_service.mark_evicted(item_id):
        return jsonify({"error": "Failed to update movie cache state."}), 500
    evicted_item = rtv_app.media_service.get_by_id(item_id) or item
    rtv_app.emit_media_event("media:file_deleted", evicted_item, f"Deleted local rTV file for {item.title}", {
        "previous_local_path": item.local_path,
        "previous_file_size_bytes": item.file_size_bytes,
    })
    return jsonify({"id": item_id, "message": "Local file deleted"}), 200


@rtv_app.blueprint.route('/<int:item_id>/delete-record', methods=['POST'])
@write_access_required
def delete_record(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item:
        return jsonify({"error": "Movie not found."}), 404
    if item.status in {"queued", "downloading"} or item.is_playing:
        return jsonify({"error": "Cannot delete a queued, downloading, or currently playing movie."}), 400
    path = Path(item.local_path).expanduser().resolve() if item.local_path else None
    if path and path.exists() and path.is_file():
        path.unlink()
    if not rtv_app.media_service.delete(item_id):
        return jsonify({"error": "Failed to delete movie record."}), 500
    rtv_app.emit_media_event("media:record_deleted", item, f"Deleted rTV record for {item.title}", {
        "previous_local_path": item.local_path,
        "previous_file_size_bytes": item.file_size_bytes,
    })
    return jsonify({"id": item_id, "message": "Movie record deleted"}), 200


@rtv_app.blueprint.route('/progress/<int:item_id>', methods=['POST'])
@write_access_required
def update_progress(item_id):
    data = request.get_json(silent=True) or {}
    progress = int(float(data.get("progress_seconds") or 0))
    duration = int(float(data.get("duration_seconds") or 0))
    is_playing = bool(data.get("is_playing", True))
    previous_item = rtv_app.media_service.get_by_id(item_id)
    previous_ratio = 0
    if previous_item and previous_item.duration_seconds:
        previous_ratio = previous_item.progress_seconds / previous_item.duration_seconds
    if not rtv_app.media_service.update_watch_progress(item_id, progress, duration, is_playing=is_playing):
        return jsonify({"error": "Movie not found"}), 404
    item = rtv_app.media_service.get_by_id(item_id)
    if item:
        ratio = (progress / duration) if duration else 0
        event_type = "media:watch_finished" if duration and ratio >= 0.9 and previous_ratio < 0.9 else "media:watch_progressed"
        rtv_app.emit_media_event(event_type, item, f"Updated watch progress for {item.title}", {
            "progress_seconds": progress,
            "duration_seconds": duration,
            "completion_ratio": round(ratio, 3) if duration else 0,
        })
    return jsonify({"ok": True}), 200


@rtv_app.blueprint.route('/watch-started/<int:item_id>', methods=['POST'])
@write_access_required
def watch_started(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item or item.status != "ready" or item.cache_state != "cached":
        return jsonify({"error": "Movie not found or not ready."}), 404
    data = request.get_json(silent=True) or {}
    restart = bool(data.get("restart", False))
    updated_item = rtv_app.media_service.mark_watch_started(item_id, restart=restart)
    if not updated_item:
        return jsonify({"error": "Failed to mark watch started."}), 500
    rtv_app.emit_media_event("media:watch_started", updated_item, f"Started watching {updated_item.title}", {
        "restart": restart,
        "progress_seconds": updated_item.progress_seconds,
        "duration_seconds": updated_item.duration_seconds,
    })
    return jsonify({"ok": True}), 200
