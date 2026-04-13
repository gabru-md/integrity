from datetime import datetime
from pathlib import Path
from typing import List, Optional

from gabru.db.db import DB
from gabru.db.service import CRUDService
from model.media_item import MediaItem


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}


class MediaItemService(CRUDService[MediaItem]):
    def __init__(self):
        super().__init__("media_items", DB("rasbhari"), user_scoped=True)

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS media_items (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        kind VARCHAR(32) NOT NULL DEFAULT 'movie',
                        source_type VARCHAR(32) NOT NULL DEFAULT 'local_file',
                        status VARCHAR(32) NOT NULL DEFAULT 'candidate',
                        magnet_uri TEXT DEFAULT '',
                        selected_file_index INTEGER,
                        selected_file_name TEXT DEFAULT '',
                        selected_file_size_bytes BIGINT NOT NULL DEFAULT 0,
                        local_path TEXT DEFAULT '',
                        file_size_bytes BIGINT NOT NULL DEFAULT 0,
                        cache_state VARCHAR(32) NOT NULL DEFAULT 'not_cached',
                        download_progress DOUBLE PRECISION NOT NULL DEFAULT 0,
                        download_rate_kbps DOUBLE PRECISION NOT NULL DEFAULT 0,
                        download_peers INTEGER NOT NULL DEFAULT 0,
                        last_error TEXT DEFAULT '',
                        poster_path TEXT DEFAULT '',
                        progress_seconds INTEGER NOT NULL DEFAULT 0,
                        duration_seconds INTEGER NOT NULL DEFAULT 0,
                        is_playing BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        download_started_at TIMESTAMP,
                        downloaded_at TIMESTAMP,
                        evicted_at TIMESTAMP,
                        playback_heartbeat_at TIMESTAMP,
                        last_watched_at TIMESTAMP,
                        active BOOLEAN NOT NULL DEFAULT TRUE
                    )
                """)
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS magnet_uri TEXT DEFAULT ''")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS selected_file_index INTEGER")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS selected_file_name TEXT DEFAULT ''")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS selected_file_size_bytes BIGINT NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS local_path TEXT DEFAULT ''")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS cache_state VARCHAR(32) NOT NULL DEFAULT 'not_cached'")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS download_progress DOUBLE PRECISION NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS download_rate_kbps DOUBLE PRECISION NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS download_peers INTEGER NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS last_error TEXT DEFAULT ''")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS poster_path TEXT DEFAULT ''")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS progress_seconds INTEGER NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS duration_seconds INTEGER NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS is_playing BOOLEAN NOT NULL DEFAULT FALSE")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS download_started_at TIMESTAMP")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS downloaded_at TIMESTAMP")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS evicted_at TIMESTAMP")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS playback_heartbeat_at TIMESTAMP")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS last_watched_at TIMESTAMP")
                cursor.execute("ALTER TABLE media_items ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE")
                self.db.conn.commit()

    def _to_tuple(self, item: MediaItem) -> tuple:
        return (
            item.user_id,
            item.title,
            item.kind,
            item.source_type,
            item.status,
            item.magnet_uri or "",
            item.selected_file_index,
            item.selected_file_name or "",
            item.selected_file_size_bytes or 0,
            item.local_path or "",
            item.file_size_bytes or 0,
            item.cache_state,
            item.download_progress or 0,
            item.download_rate_kbps or 0,
            item.download_peers or 0,
            item.last_error or "",
            item.poster_path or "",
            item.progress_seconds or 0,
            item.duration_seconds or 0,
            item.is_playing,
            item.created_at,
            item.download_started_at,
            item.downloaded_at,
            item.evicted_at,
            item.playback_heartbeat_at,
            item.last_watched_at,
            item.active,
        )

    def _to_object(self, row: tuple) -> MediaItem:
        return MediaItem(
            id=row[0],
            user_id=row[1],
            title=row[2],
            kind=row[3],
            source_type=row[4],
            status=row[5],
            magnet_uri=row[6] or "",
            selected_file_index=row[7],
            selected_file_name=row[8] or "",
            selected_file_size_bytes=row[9] or 0,
            local_path=row[10] or "",
            file_size_bytes=row[11] or 0,
            cache_state=row[12] or "not_cached",
            download_progress=row[13] or 0,
            download_rate_kbps=row[14] or 0,
            download_peers=row[15] or 0,
            last_error=row[16] or "",
            poster_path=row[17] or "",
            progress_seconds=row[18] or 0,
            duration_seconds=row[19] or 0,
            is_playing=row[20],
            created_at=row[21],
            download_started_at=row[22],
            downloaded_at=row[23],
            evicted_at=row[24],
            playback_heartbeat_at=row[25],
            last_watched_at=row[26],
            active=row[27],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return [
            "user_id",
            "title",
            "kind",
            "source_type",
            "status",
            "magnet_uri",
            "selected_file_index",
            "selected_file_name",
            "selected_file_size_bytes",
            "local_path",
            "file_size_bytes",
            "cache_state",
            "download_progress",
            "download_rate_kbps",
            "download_peers",
            "last_error",
            "poster_path",
            "progress_seconds",
            "duration_seconds",
            "is_playing",
            "created_at",
            "download_started_at",
            "downloaded_at",
            "evicted_at",
            "playback_heartbeat_at",
            "last_watched_at",
            "active",
        ]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return ["id", *self._get_columns_for_insert()]

    def get_ready_movies(self) -> List[MediaItem]:
        return self.find_all(filters={"status": "ready", "cache_state": "cached", "active": True}, sort_by={"last_watched_at": "DESC", "created_at": "DESC"})

    def find_by_local_path(self, local_path: str) -> Optional[MediaItem]:
        return self.find_one_by_field("local_path", local_path)

    def update_watch_progress(self, item_id: int, progress_seconds: int, duration_seconds: int = 0, is_playing: bool = True) -> bool:
        item = self.get_by_id(item_id)
        if not item:
            return False
        item.progress_seconds = max(0, int(progress_seconds or 0))
        item.duration_seconds = max(item.duration_seconds or 0, int(duration_seconds or 0))
        item.is_playing = bool(is_playing)
        item.playback_heartbeat_at = datetime.now()
        item.last_watched_at = datetime.now()
        return self.update(item)

    def mark_watch_started(self, item_id: int, restart: bool = False) -> Optional[MediaItem]:
        item = self.get_by_id(item_id)
        if not item:
            return None
        if restart:
            item.progress_seconds = 0
        item.is_playing = True
        item.playback_heartbeat_at = datetime.now()
        item.last_watched_at = datetime.now()
        return item if self.update(item) else None

    def mark_playback_stopped(self, item_id: int) -> bool:
        item = self.get_by_id(item_id)
        if not item:
            return False
        item.is_playing = False
        item.playback_heartbeat_at = datetime.now()
        return self.update(item)

    def mark_ready_from_local_file(self, item: MediaItem, path: Path) -> MediaItem:
        item.source_type = item.source_type or "local_file"
        item.status = "ready"
        item.cache_state = "cached"
        item.local_path = str(path)
        item.selected_file_name = path.name
        item.file_size_bytes = path.stat().st_size
        item.selected_file_size_bytes = item.file_size_bytes
        item.downloaded_at = item.downloaded_at or datetime.now()
        item.evicted_at = None
        return item

    def apply_torrent_metadata(self, item: MediaItem, file_index: int, file_name: str, file_size_bytes: int, torrent_name: str = "") -> MediaItem:
        if not item.title or item.title == "Untitled Movie":
            item.title = self.title_from_path(Path(torrent_name or file_name))
        item.source_type = "magnet"
        item.status = "candidate"
        item.selected_file_index = file_index
        item.selected_file_name = file_name
        item.selected_file_size_bytes = file_size_bytes
        item.cache_state = "not_cached"
        return item

    def queue_download(self, item_id: int) -> bool:
        item = self.get_by_id(item_id)
        if not item or item.source_type != "magnet" or not item.magnet_uri:
            return False
        if item.selected_file_index is None or not item.selected_file_name:
            return False
        item.status = "queued"
        item.cache_state = "not_cached"
        item.download_progress = 0
        item.download_rate_kbps = 0
        item.download_peers = 0
        item.last_error = ""
        return self.update(item)

    def get_next_queued_download(self) -> Optional[MediaItem]:
        items = self.find_all(filters={"status": "queued"}, sort_by={"created_at": "ASC"})
        return items[0] if items else None

    def mark_download_started(self, item_id: int) -> Optional[MediaItem]:
        item = self.get_by_id(item_id)
        if not item:
            return None
        item.status = "downloading"
        item.cache_state = "not_cached"
        item.download_progress = 0
        item.download_rate_kbps = 0
        item.download_peers = 0
        item.last_error = ""
        item.download_started_at = datetime.now()
        return item if self.update(item) else None

    def update_download_progress(self, item_id: int, progress: float, rate_kbps: float, peers: int) -> bool:
        item = self.get_by_id(item_id)
        if not item:
            return False
        item.download_progress = max(0, min(100, float(progress or 0)))
        item.download_rate_kbps = max(0, float(rate_kbps or 0))
        item.download_peers = max(0, int(peers or 0))
        return self.update(item)

    def mark_download_ready(self, item_id: int, local_path: Path) -> Optional[MediaItem]:
        item = self.get_by_id(item_id)
        if not item:
            return None
        item = self.mark_ready_from_local_file(item, local_path)
        item.source_type = "magnet"
        item.download_progress = 100
        item.download_rate_kbps = 0
        item.download_peers = 0
        item.last_error = ""
        return item if self.update(item) else None

    def mark_download_failed(self, item_id: int, error: str) -> Optional[MediaItem]:
        item = self.get_by_id(item_id)
        if not item:
            return None
        item.status = "failed"
        item.download_rate_kbps = 0
        item.download_peers = 0
        item.last_error = error
        return item if self.update(item) else None

    def mark_download_cancelled(self, item_id: int, reason: str = "Cancelled by user") -> Optional[MediaItem]:
        item = self.get_by_id(item_id)
        if not item:
            return None
        item.status = "cancelled"
        item.download_rate_kbps = 0
        item.download_peers = 0
        item.last_error = reason
        item.is_playing = False
        return item if self.update(item) else None

    def mark_evicted(self, item_id: int) -> bool:
        item = self.get_by_id(item_id)
        if not item:
            return False
        item.status = "deleted"
        item.cache_state = "evicted"
        item.local_path = ""
        item.file_size_bytes = 0
        item.evicted_at = datetime.now()
        return self.update(item)

    @staticmethod
    def discover_video_files(media_dir: Path) -> List[Path]:
        if not media_dir.exists():
            return []
        return sorted(
            [path for path in media_dir.rglob("*") if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS],
            key=lambda path: path.name.lower(),
        )

    @staticmethod
    def title_from_path(path: Path) -> str:
        title = path.stem.replace(".", " ").replace("_", " ").replace("-", " ")
        return " ".join(title.split()).strip().title() or path.name
