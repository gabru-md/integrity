from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from gabru.flask.model import WidgetUIModel


MediaKind = Literal["movie"]
MediaSourceType = Literal["local_file", "magnet"]
MediaStatus = Literal["candidate", "queued", "downloading", "ready", "failed", "deleted"]
MediaCacheState = Literal["not_cached", "cached", "evicted"]


class MediaItem(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    user_id: Optional[int] = Field(default=None, edit_enabled=False, ui_enabled=False)
    title: str = Field(default="", widget_enabled=True, description="Movie title shown in rTV.")
    kind: MediaKind = Field(default="movie", widget_enabled=True, description="rTV v1 is movie-only.")
    source_type: MediaSourceType = Field(default="local_file", widget_enabled=True, description="Where this item came from.")
    status: MediaStatus = Field(default="candidate", widget_enabled=True, description="Whether the movie is ready to watch.")
    magnet_uri: Optional[str] = Field(default="", widget_enabled=False, description="Optional magnet URI for a candidate movie.")
    selected_file_index: Optional[int] = Field(default=None, widget_enabled=False, description="Selected video file index inside a torrent when known.")
    selected_file_name: Optional[str] = Field(default="", widget_enabled=True, description="Selected movie filename when known.")
    selected_file_size_bytes: int = Field(default=0, widget_enabled=True, description="Size of the selected movie file before or during download.")
    local_path: Optional[str] = Field(default="", widget_enabled=False, description="Local downloaded or scanned video path.")
    file_size_bytes: int = Field(default=0, widget_enabled=True, description="Size of the selected movie file.")
    cache_state: MediaCacheState = Field(default="not_cached", widget_enabled=True, description="Whether the movie file is currently stored in the rTV local cache.")
    download_progress: float = Field(default=0.0, widget_enabled=True, description="Current download progress from 0 to 100.")
    download_rate_kbps: float = Field(default=0.0, widget_enabled=True, description="Current download rate in KB/s.")
    download_peers: int = Field(default=0, widget_enabled=True, description="Connected peers for the active download.")
    last_error: Optional[str] = Field(default="", widget_enabled=False, description="Most recent download or metadata error.")
    poster_path: Optional[str] = Field(default="", widget_enabled=False, description="Optional poster image path or URL.")
    progress_seconds: int = Field(default=0, widget_enabled=True, description="Last watched position.")
    duration_seconds: int = Field(default=0, widget_enabled=True, description="Movie duration when known.")
    is_playing: bool = Field(default=False, widget_enabled=True, description="Whether rTV recently saw this item playing.")
    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False)
    download_started_at: Optional[datetime] = Field(default=None, edit_enabled=False)
    downloaded_at: Optional[datetime] = Field(default=None, edit_enabled=False)
    evicted_at: Optional[datetime] = Field(default=None, edit_enabled=False)
    playback_heartbeat_at: Optional[datetime] = Field(default=None, edit_enabled=False)
    last_watched_at: Optional[datetime] = Field(default=None, edit_enabled=False, widget_enabled=True)
    active: bool = Field(default=True, widget_enabled=True, description="Whether this item should appear in rTV.")
