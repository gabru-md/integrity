import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Response, jsonify, request, send_file

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


SUBTITLE_EXTENSIONS = {".vtt", ".srt"}
TEXT_SUBTITLE_CODECS = {"subrip", "srt", "ass", "ssa", "webvtt", "mov_text"}


def _subtitle_label(path: Path) -> str:
    suffix = path.suffix.lower()
    stem = path.stem
    parts = stem.replace(".", " ").replace("_", " ").split()
    if parts and parts[-1].lower() in {"en", "eng", "english"}:
        return "English"
    if len(parts) >= 2 and parts[-2].lower() == "embedded" and parts[-1].isdigit():
        return "Embedded"
    if parts and len(parts[-1]) in {2, 3}:
        return parts[-1].upper()
    return "Subtitles"


def _subtitle_candidates(video_path: Path) -> list[Path]:
    candidates = []
    for child in video_path.parent.iterdir():
        if not child.is_file() or child.suffix.lower() not in SUBTITLE_EXTENSIONS:
            continue
        if child.stem == video_path.stem or child.stem.startswith(f"{video_path.stem}.") or child.stem.startswith(f"{video_path.stem}_"):
            candidates.append(child)
    return sorted(candidates, key=lambda path: (path.suffix.lower() != ".vtt", path.name.lower()))


def _extracted_subtitle_path(video_path: Path, stream_index: int, language: str = "") -> Path:
    suffix = f".embedded.{language}" if language else ".embedded"
    return video_path.with_name(f"{video_path.stem}{suffix}.{stream_index}.vtt")


def _probe_embedded_text_subtitles(video_path: Path) -> list[dict]:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "s",
                "-show_entries",
                "stream=index,codec_name:stream_tags=language,title",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return []
    streams = []
    for stream in payload.get("streams", []):
        codec = str(stream.get("codec_name") or "").lower()
        if codec not in TEXT_SUBTITLE_CODECS:
            continue
        tags = stream.get("tags") or {}
        streams.append({
            "index": stream.get("index"),
            "codec": codec,
            "language": str(tags.get("language") or "").lower(),
            "title": tags.get("title") or "",
        })
    return [stream for stream in streams if stream.get("index") is not None]


def _ensure_embedded_subtitles(video_path: Path) -> list[Path]:
    existing = _subtitle_candidates(video_path)
    if existing:
        return existing
    extracted_paths = []
    for stream in _probe_embedded_text_subtitles(video_path):
        output_path = _extracted_subtitle_path(video_path, int(stream["index"]), stream.get("language") or "")
        if not output_path.exists():
            try:
                result = subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(video_path),
                        "-map",
                        f"0:{stream['index']}",
                        "-c:s",
                        "webvtt",
                        str(output_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=90,
                    check=False,
                )
            except (FileNotFoundError, subprocess.SubprocessError):
                continue
            if result.returncode != 0 or not output_path.exists():
                output_path.unlink(missing_ok=True)
                continue
        extracted_paths.append(output_path)
    return _subtitle_candidates(video_path) or extracted_paths


def _discover_subtitles(item: MediaItem) -> list[dict]:
    if not item.local_path:
        return []
    try:
        video_path = _safe_media_file(item.local_path)
    except (ValueError, FileNotFoundError):
        return []
    subtitles = []
    for index, path in enumerate(_ensure_embedded_subtitles(video_path)):
        subtitles.append({
            "index": index,
            "label": _subtitle_label(path),
            "url": f"/rtv/subtitles/{item.id}/{index}",
            "srclang": "en" if _subtitle_label(path) == "English" else "und",
        })
    return subtitles


def _srt_to_vtt(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = ["WEBVTT", ""]
    for line in normalized.split("\n"):
        if "-->" in line:
            line = line.replace(",", ".")
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def _process_media_item_data(data):
    if not data.get("title") and data.get("local_path"):
        data["title"] = MediaItemService.title_from_path(Path(data["local_path"]))
    data.setdefault("kind", "movie")
    data.setdefault("source_type", "magnet" if data.get("magnet_uri") else "local_file")
    data.setdefault("status", "candidate")
    return data


def _cancel_active_download(item_id: int, reason: str = "Cancelled by user"):
    processor = rtv_app.get_running_process(MediaDownloadProcessor)
    if processor and hasattr(processor, "request_cancel"):
        processor.request_cancel(item_id, reason=reason)


def _cleanup_download_artifacts(item: MediaItem):
    if not item or not item.local_path:
        return
    path = Path(item.local_path).expanduser().resolve()
    if path.exists() and path.is_file():
        path.unlink()

    download_root = path.parent if path.parent.name == f"item-{item.id}" else None
    if download_root and download_root.exists() and download_root.is_dir():
        try:
            for child in download_root.iterdir():
                if child.is_file():
                    child.unlink()
            download_root.rmdir()
        except Exception:
            pass


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
            query = (request.args.get("q") or "").strip().lower()
            raw_items = self.media_service.find_all(sort_by={"created_at": "DESC"})
            if query:
                raw_items = [
                    item for item in raw_items
                    if query in (item.title or "").lower()
                    or query in (item.magnet_uri or "").lower()
                    or query in (item.local_path or "").lower()
                    or query in (item.status or "").lower()
                    or query in (item.source_type or "").lower()
                ]
            media_root = _media_root()
            items = []
            for item in raw_items:
                display_local_path = ""
                if item.local_path:
                    try:
                        relative_path = Path(item.local_path).expanduser().resolve().relative_to(media_root)
                        display_local_path = relative_path.as_posix()
                    except Exception:
                        display_local_path = Path(item.local_path).name
                item_data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
                item_data["display_local_path"] = display_local_path
                items.append(item_data)
            stats = {
                "total": len(items),
                "ready": len([item for item in items if item.get("status") == "ready"]),
                "candidates": len([item for item in items if item.get("status") == "candidate"]),
                "downloaded_gb": round(sum(item.get("file_size_bytes", 0) for item in items if item.get("status") == "ready") / 1024 / 1024 / 1024, 2),
                "cache_limit_gb": round(int(os.getenv("RTV_MEDIA_CACHE_LIMIT_BYTES", str(DEFAULT_CACHE_LIMIT_BYTES))) / 1024 / 1024 / 1024, 2),
                "media_root": str(media_root),
                "query": query,
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
    return render_flask_template(
        "rtv_player.html",
        app_name=rtv_app.name,
        item=item,
        restart=restart,
        subtitles=_discover_subtitles(item),
    )


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


@rtv_app.blueprint.route('/subtitles/<int:item_id>/<int:subtitle_index>')
def subtitles(item_id, subtitle_index):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item or item.status != "ready" or item.cache_state != "cached":
        return "Movie not found or not ready.", 404
    if subtitle_index < 0:
        return "Subtitle not found.", 404
    try:
        video_path = _safe_media_file(item.local_path)
        candidates = _subtitle_candidates(video_path)
        subtitle_path = candidates[subtitle_index]
        subtitle_path.relative_to(_media_root())
    except (IndexError, ValueError, FileNotFoundError):
        return "Subtitle not found.", 404

    if subtitle_path.suffix.lower() == ".vtt":
        return send_file(subtitle_path, mimetype="text/vtt", conditional=True)

    content = subtitle_path.read_text(encoding="utf-8", errors="replace")
    return Response(_srt_to_vtt(content), mimetype="text/vtt")


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
        rtv_app.log.info(
            "Resolving rTV metadata id=%s title=%s source=%s",
            item.id,
            item.title,
            item.magnet_uri[:80],
        )
        metadata = rtv_app.torrent_resolver.resolve_largest_video(item.magnet_uri)
    except Exception as exc:
        rtv_app.log.exception("rTV metadata resolution failed id=%s title=%s", item.id, item.title)
        item.status = "failed"
        item.last_error = str(exc)
        rtv_app.media_service.update(item)
        rtv_app.emit_media_event("media:metadata_failed", item, f"Failed to resolve rTV metadata for {item.title}", {"error": str(exc)})
        return jsonify({
            "error": str(exc),
            "error_type": exc.__class__.__name__,
            "item_id": item.id,
            "title": item.title,
            "status": item.status,
            "last_error": item.last_error,
        }), 400

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
        "torrent_name": metadata.torrent_name,
        "message": "Metadata resolved",
    }), 200


@rtv_app.blueprint.route('/<int:item_id>/debug-metadata', methods=['POST'])
@write_access_required
def debug_metadata(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item:
        return jsonify({"error": "Movie candidate not found."}), 404
    if item.source_type != "magnet" or not item.magnet_uri:
        return jsonify({"error": "Only magnet candidates can be probed."}), 400

    try:
        rtv_app.log.info("Probing rTV magnet id=%s title=%s", item.id, item.title)
        probe = rtv_app.torrent_resolver.probe_magnet(item.magnet_uri)
    except Exception as exc:
        rtv_app.log.exception("rTV magnet probe failed id=%s title=%s", item.id, item.title)
        return jsonify({
            "ok": False,
            "error": str(exc),
            "error_type": exc.__class__.__name__,
            "timeout_seconds": rtv_app.torrent_resolver.timeout_seconds,
        }), 400

    return jsonify({
        "ok": True,
        "item_id": item.id,
        "title": item.title,
        "timeout_seconds": rtv_app.torrent_resolver.timeout_seconds,
        "probe": probe,
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


@rtv_app.blueprint.route('/<int:item_id>/magnet', methods=['POST'])
@write_access_required
def update_magnet(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item:
        return jsonify({"error": "Movie not found."}), 404
    if item.source_type != "magnet":
        return jsonify({"error": "Only magnet candidates can update their magnet URI."}), 400
    data = request.get_json(silent=True) or {}
    magnet_uri = (data.get("magnet_uri") or "").strip()
    if not magnet_uri.startswith("magnet:"):
        return jsonify({"error": "A valid magnet URI is required."}), 400
    item.magnet_uri = magnet_uri
    if item.status in {"queued", "downloading", "failed"} and item.selected_file_index is None:
        item.status = "candidate"
    if not rtv_app.media_service.update(item):
        return jsonify({"error": "Failed to update magnet URI."}), 500
    return jsonify({"id": item_id, "magnet_uri": magnet_uri, "message": "Magnet updated"}), 200


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
    if item.status in {"queued", "downloading"}:
        _cancel_active_download(item.id, reason="Cancelled before local file deletion")
        item = rtv_app.media_service.get_by_id(item_id) or item
        if item.status == "downloading":
            return jsonify({"error": "Download cancellation requested. Try delete again in a moment."}), 409
    if item.is_playing:
        return jsonify({"error": "Cannot delete a currently playing movie."}), 400
    _cleanup_download_artifacts(item)
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
    if item.status in {"queued", "downloading"}:
        _cancel_active_download(item.id, reason="Cancelled before record deletion")
        item = rtv_app.media_service.get_by_id(item_id) or item
        if item.status == "downloading":
            return jsonify({"error": "Download cancellation requested. Try delete again in a moment."}), 409
    if item.is_playing:
        return jsonify({"error": "Cannot delete a currently playing movie."}), 400
    _cleanup_download_artifacts(item)
    if not rtv_app.media_service.delete(item_id):
        return jsonify({"error": "Failed to delete movie record."}), 500
    rtv_app.emit_media_event("media:record_deleted", item, f"Deleted rTV record for {item.title}", {
        "previous_local_path": item.local_path,
        "previous_file_size_bytes": item.file_size_bytes,
    })
    return jsonify({"id": item_id, "message": "Movie record deleted"}), 200


@rtv_app.blueprint.route('/<int:item_id>/cancel-download', methods=['POST'])
@write_access_required
def cancel_download(item_id):
    item = rtv_app.media_service.get_by_id(item_id)
    if not item:
        return jsonify({"error": "Movie not found."}), 404
    if item.status not in {"queued", "downloading"}:
        return jsonify({"error": "Only queued or downloading movies can be cancelled."}), 400

    _cancel_active_download(item.id, reason="Cancelled by user")
    cancelled_item = rtv_app.media_service.mark_download_cancelled(item.id, "Cancelled by user")
    if not cancelled_item:
        return jsonify({"error": "Failed to cancel movie download."}), 500
    rtv_app.emit_media_event("media:download_cancelled", cancelled_item, f"Cancelled rTV download for {cancelled_item.title}", {
        "status": cancelled_item.status,
    })
    return jsonify({"id": item_id, "status": cancelled_item.status, "message": "Download cancelled"}), 200


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
