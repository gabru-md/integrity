import os
import time
from datetime import datetime
from pathlib import Path

import libtorrent as lt

from gabru.process import Process
from model.event import Event
from model.media_item import MediaItem
from services.events import EventService
from services.media_cache import MediaCacheManager
from services.media_items import MediaItemService


class MediaDownloadProcessor(Process):
    def __init__(self, **kwargs):
        super().__init__(name=kwargs.get("name", self.__class__.__name__), enabled=kwargs.get("enabled", False), daemon=True)
        self.media_service = MediaItemService()
        self.cache_manager = MediaCacheManager(self.media_service)
        self.event_service = EventService()
        self.sleep_time_sec = int(os.getenv("RTV_DOWNLOAD_PROCESSOR_SLEEP_SEC", "10"))
        self.media_root = Path(os.getenv("RTV_MEDIA_DIR", "./media/rtv")).expanduser().resolve()

    def process(self):
        while self.running:
            queued_item = self.media_service.get_next_queued_download()
            if not queued_item:
                self.log.info("No rTV downloads queued, waiting for %ss", self.sleep_time_sec)
                time.sleep(self.sleep_time_sec)
                continue
            self._download_item(queued_item)

    def _download_item(self, item: MediaItem):
        started_item = self.media_service.mark_download_started(item.id)
        if not started_item:
            self.log.warning("Could not mark rTV item %s as downloading", item.id)
            return

        self.log.info(
            "Starting rTV download id=%s title=%s selected_file=%s size_mb=%.1f",
            started_item.id,
            started_item.title,
            started_item.selected_file_name,
            (started_item.selected_file_size_bytes or 0) / 1024 / 1024,
        )
        self._emit_event("media:download_started", started_item, f"Started rTV download for {started_item.title}")
        session = lt.session()
        try:
            self.media_root.mkdir(parents=True, exist_ok=True)
            download_root = self.media_root / f"item-{started_item.id}"
            download_root.mkdir(parents=True, exist_ok=True)
            eviction_result = self.cache_manager.ensure_space_for(
                started_item.selected_file_size_bytes,
                protected_item_ids=[started_item.id],
            )
            for evicted_item in eviction_result.evicted_items:
                self.log.info("Evicted rTV cached movie id=%s title=%s", evicted_item.id, evicted_item.title)
                self._emit_event("media:file_evicted", evicted_item, f"Evicted rTV movie {evicted_item.title}", {
                    "reason": "cache_limit",
                    "freed_bytes": evicted_item.file_size_bytes,
                })

            session.apply_settings({
                "listen_interfaces": "0.0.0.0:6881",
                "enable_dht": True,
                "enable_lsd": True,
                "enable_upnp": True,
                "enable_natpmp": True,
                "download_rate_limit": 0,
                "upload_rate_limit": 0,
                "connection_speed": 50,
            })
            try:
                session.start_dht()
            except Exception:
                pass

            params = lt.parse_magnet_uri(started_item.magnet_uri)
            params.save_path = str(download_root)
            params.storage_mode = lt.storage_mode_t.storage_mode_sparse
            handle = session.add_torrent(params)
            handle.force_reannounce()
            try:
                handle.force_dht_announce()
            except Exception:
                pass

            self._wait_for_metadata(handle)
            self.log.info("rTV metadata ready for id=%s title=%s", started_item.id, started_item.title)
            info = self._get_torrent_info(handle)
            self._prioritize_selected_file(handle, info, started_item.selected_file_index)

            selected_path = download_root / started_item.selected_file_name
            last_progress_update = 0
            while self.running and not handle.status().is_seeding:
                progress = self._selected_file_progress(handle, started_item.selected_file_index, started_item.selected_file_size_bytes)
                status = handle.status()
                now = time.time()
                if now - last_progress_update >= 5:
                    self.media_service.update_download_progress(
                        started_item.id,
                        progress=progress,
                        rate_kbps=status.download_rate / 1000,
                        peers=status.num_peers,
                    )
                    self.log.info(
                        "rTV download progress id=%s title=%s progress=%.1f%% peers=%s speed_kbps=%.1f",
                        started_item.id,
                        started_item.title,
                        progress,
                        status.num_peers,
                        status.download_rate / 1000,
                    )
                    last_progress_update = now
                if progress >= 100:
                    break
                time.sleep(1)

            ready_item = self.media_service.mark_download_ready(started_item.id, selected_path)
            if ready_item:
                self.log.info("Finished rTV download id=%s title=%s path=%s", ready_item.id, ready_item.title, ready_item.local_path)
                self._emit_event("media:download_finished", ready_item, f"Finished rTV download for {ready_item.title}", {
                    "local_path": ready_item.local_path,
                    "file_size_bytes": ready_item.file_size_bytes,
                })
        except Exception as exc:
            self.log.error("Failed rTV download id=%s title=%s error=%s", started_item.id, started_item.title, exc)
            failed_item = self.media_service.mark_download_failed(started_item.id, str(exc))
            self._emit_event(
                "media:download_failed",
                failed_item or started_item,
                f"Failed rTV download for {started_item.title}",
                {"error": str(exc)},
            )
            self.log.exception(exc)
        finally:
            session.pause()

    def _wait_for_metadata(self, handle, timeout_seconds=120):
        deadline = time.time() + timeout_seconds
        while self.running and not handle.has_metadata():
            if time.time() > deadline:
                raise TimeoutError("Timed out waiting for torrent metadata.")
            time.sleep(0.5)

    @staticmethod
    def _get_torrent_info(handle):
        if hasattr(handle, "get_torrent_info"):
            return handle.get_torrent_info()
        return handle.torrent_info()

    @staticmethod
    def _prioritize_selected_file(handle, info, selected_file_index):
        if selected_file_index is None:
            raise ValueError("Queued rTV item is missing selected_file_index.")
        priorities = [0] * info.num_files()
        priorities[int(selected_file_index)] = 7
        handle.prioritize_files(priorities)
        handle.set_sequential_download(True)

    @staticmethod
    def _selected_file_progress(handle, selected_file_index, selected_file_size_bytes) -> float:
        if not selected_file_size_bytes:
            return 0
        progress = handle.file_progress()
        downloaded = progress[int(selected_file_index)] if int(selected_file_index) < len(progress) else 0
        return min(100, (downloaded / selected_file_size_bytes) * 100)

    def _emit_event(self, event_type: str, item: MediaItem, description: str, payload=None):
        try:
            self.event_service.create(Event(
                user_id=item.user_id,
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
            self.log.warning("Failed to emit rTV download event: %s", exc)
