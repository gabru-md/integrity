import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from model.media_item import MediaItem
from services.media_items import MediaItemService


DEFAULT_CACHE_LIMIT_BYTES = 3 * 1024 * 1024 * 1024


@dataclass
class MediaCacheEvictionResult:
    evicted_items: List[MediaItem] = field(default_factory=list)
    freed_bytes: int = 0
    total_before_bytes: int = 0
    total_after_bytes: int = 0


class MediaCacheManager:
    def __init__(self, media_service: Optional[MediaItemService] = None):
        self.media_service = media_service or MediaItemService()
        self.cache_limit_bytes = int(os.getenv("RTV_MEDIA_CACHE_LIMIT_BYTES", str(DEFAULT_CACHE_LIMIT_BYTES)))

    def ensure_space_for(self, incoming_size_bytes: int, protected_item_ids=None) -> MediaCacheEvictionResult:
        protected = {int(item_id) for item_id in (protected_item_ids or []) if item_id is not None}
        cached_items = self._cached_items()
        total_before = self._total_size(cached_items)
        result = MediaCacheEvictionResult(total_before_bytes=total_before, total_after_bytes=total_before)

        target_total = max(0, self.cache_limit_bytes - int(incoming_size_bytes or 0))
        if total_before <= target_total:
            return result

        for item in self._lru_candidates(cached_items, protected):
            if result.total_after_bytes <= target_total:
                break
            freed = self._evict_item_file(item)
            if freed <= 0:
                continue
            if self.media_service.mark_evicted(item.id):
                result.evicted_items.append(item)
                result.freed_bytes += freed
                result.total_after_bytes -= freed

        if result.total_after_bytes + int(incoming_size_bytes or 0) > self.cache_limit_bytes:
            raise RuntimeError("Not enough rTV cache space and no safe movies are available to evict.")
        return result

    def _cached_items(self) -> List[MediaItem]:
        return self.media_service.find_all(filters={"status": "ready", "cache_state": "cached", "active": True})

    @staticmethod
    def _total_size(items: List[MediaItem]) -> int:
        return sum(int(item.file_size_bytes or 0) for item in items)

    @staticmethod
    def _lru_candidates(items: List[MediaItem], protected_item_ids: set[int]) -> List[MediaItem]:
        candidates = [
            item for item in items
            if item.id not in protected_item_ids
            and not item.is_playing
            and item.status not in {"queued", "downloading"}
        ]
        return sorted(candidates, key=lambda item: item.last_watched_at or item.downloaded_at or item.created_at)

    @staticmethod
    def _evict_item_file(item: MediaItem) -> int:
        if not item.local_path:
            return 0
        path = Path(item.local_path).expanduser().resolve()
        if not path.exists():
            return int(item.file_size_bytes or 0)
        size = path.stat().st_size if path.is_file() else int(item.file_size_bytes or 0)
        if path.is_file():
            path.unlink()
            parent = path.parent
            try:
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                pass
        elif path.is_dir():
            shutil.rmtree(path)
        return size
