import os
import time
from dataclasses import dataclass
from typing import Optional

import libtorrent as lt

from services.media_items import VIDEO_EXTENSIONS


@dataclass
class TorrentVideoMetadata:
    torrent_name: str
    file_index: int
    file_name: str
    file_size_bytes: int


class TorrentMetadataResolver:
    def __init__(self, timeout_seconds: Optional[int] = None):
        timeout_seconds = timeout_seconds or int(os.getenv("RTV_METADATA_TIMEOUT_SECONDS", "120"))
        self.timeout_seconds = timeout_seconds

    def resolve_largest_video(self, magnet_uri: str) -> TorrentVideoMetadata:
        if not magnet_uri.startswith("magnet:"):
            raise ValueError("A valid magnet URI is required.")

        session = lt.session()
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
        params = lt.parse_magnet_uri(magnet_uri)
        params.save_path = "/tmp"
        handle = session.add_torrent(params)
        handle.force_reannounce()
        try:
            handle.force_dht_announce()
        except Exception:
            pass

        deadline = time.time() + self.timeout_seconds
        try:
            while not handle.has_metadata():
                if time.time() > deadline:
                    status = handle.status()
                    raise TimeoutError(
                        "Timed out waiting for torrent metadata "
                        f"after {self.timeout_seconds}s "
                        f"(peers={status.num_peers}, seeds={status.num_seeds}, "
                        f"download_rate_kbps={status.download_rate / 1000:.1f})."
                    )
                time.sleep(0.5)

            info = handle.get_torrent_info() if hasattr(handle, "get_torrent_info") else handle.torrent_info()
            selected = self._select_largest_video(info)
            if selected is None:
                raise ValueError("No movie-like video file found in torrent metadata.")
            return selected
        finally:
            session.pause()

    def probe_magnet(self, magnet_uri: str) -> dict:
        if not magnet_uri.startswith("magnet:"):
            raise ValueError("A valid magnet URI is required.")

        session = lt.session()
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

        params = lt.parse_magnet_uri(magnet_uri)
        params.save_path = "/tmp"
        handle = session.add_torrent(params)
        handle.force_reannounce()
        try:
            handle.force_dht_announce()
        except Exception:
            pass

        deadline = time.time() + self.timeout_seconds
        last_status = None
        try:
            while not handle.has_metadata():
                last_status = handle.status()
                if time.time() > deadline:
                    raise TimeoutError(
                        "Timed out waiting for torrent metadata "
                        f"after {self.timeout_seconds}s "
                        f"(peers={last_status.num_peers}, seeds={last_status.num_seeds}, "
                        f"downloading={last_status.download_rate / 1000:.1f} KB/s)."
                    )
                time.sleep(0.5)

            info = handle.get_torrent_info() if hasattr(handle, "get_torrent_info") else handle.torrent_info()
            selected = self._select_largest_video(info)
            return {
                "torrent_name": info.name(),
                "file_count": info.num_files(),
                "selected_file_index": None if selected is None else selected.file_index,
                "selected_file_name": None if selected is None else selected.file_name,
                "selected_file_size_bytes": None if selected is None else selected.file_size_bytes,
                "peers": handle.status().num_peers,
                "seeds": handle.status().num_seeds,
            }
        except Exception as exc:
            raise
        finally:
            session.pause()

    @staticmethod
    def _select_largest_video(info) -> Optional[TorrentVideoMetadata]:
        selected = None
        selected_size = 0
        for index, item in enumerate(info.files()):
            path = item.path
            size = item.size
            if path.lower().endswith(tuple(VIDEO_EXTENSIONS)) and size > selected_size:
                selected = TorrentVideoMetadata(
                    torrent_name=info.name(),
                    file_index=index,
                    file_name=path,
                    file_size_bytes=size,
                )
                selected_size = size
        return selected
