# rTV Test Loop

rTV is the movie-only owned-media surface inside Rasbhari. V1 is intentionally simple: add a movie candidate, download it fully, then watch it from the TV-first interface once it is ready and cached locally.

## V1 Constraints

- Movie-only. TV shows, seasons, and multi-episode handling are out of scope for V1.
- Manual magnet add. rTV does not search public indexes or discover media automatically.
- Full download before playback. rTV does not live-stream incomplete torrent pieces.
- 3GB default cache cap. `RTV_MEDIA_CACHE_LIMIT_BYTES` controls the cap and defaults to 3GB.
- One active download. `MediaDownloadProcessor` downloads one selected movie at a time to stay Raspberry Pi-safe.
- No transcoding. Files are served as-is through the browser.
- Best playback support is MP4 with H264 video and AAC audio.
- Local files are owned media only. rTV is not a piracy search or streaming product.

## Prerequisites

- Rasbhari is running and you are logged in.
- The rTV app is enabled.
- `MediaDownloadProcessor` is running from the `Processes` surface if you want magnet downloads to progress.
- `RTV_MEDIA_DIR` points to the local media folder. If unset, Rasbhari uses `./media/rtv`.
- The browser or TV can reach the Rasbhari host over the local network.
- If the probe shows `127.0.0.1:6881`, set `RTV_LISTEN_INTERFACES` or `RTV_OUTGOING_INTERFACE` to the Pi LAN address, such as `192.168.1.184:6881`.

## Fastest Local-File Test

Use this loop when you already have a compatible movie file.

1. Put an owned `.mp4` file in the dedicated rTV media folder, or add a magnet candidate.
2. Open `/rtv/home`.
3. Confirm the movie appears as ready and cached once it has been imported or downloaded.
4. Open `/tv`.
5. Search or focus the movie card with remote arrow controls.
6. Start playback and use the rTV player controls for play/pause, seek, fullscreen, and back.
7. Stop and reopen the movie to confirm resume support.
8. Watch near the end to confirm watched detection.
9. Check Events for `media:watch_started`, milestone `media:watch_progressed`, and `media:watch_finished`.

This is the preferred smoke test because it validates the TV interface, local playback, range support, progress tracking, and event emission without depending on torrent swarm health.

## Magnet Download Test

Use this loop when validating the full candidate-to-ready path.

1. Open `/rtv/home`.
2. Paste an owned-media magnet link into the add form.
3. Save it as a candidate.
4. Click `Resolve` to fetch torrent metadata.
5. Confirm rTV selected the largest video file as the movie.
6. Click the download action.
7. Confirm the item moves to queued or downloading.
8. Keep `MediaDownloadProcessor` running.
9. Watch progress update on `/rtv/home`.
10. When the item becomes ready and cached, open `/tv`.
11. Play the movie and verify resume/progress events as in the local-file test.

## Expected State Flow

```text
candidate
  -> resolving metadata
  -> resolved with selected video file
  -> queued
  -> downloading
  -> ready + cached
  -> playable from /tv
```

If the file is later evicted by the cache manager, the media record remains but `local_file_path` and cached state are cleared. The movie can be downloaded again later.

## Troubleshooting

- `Timed out waiting for torrent metadata`: the magnet may have weak peers, blocked trackers, or no available DHT response. Use `testing.py` with the same magnet to compare resolver behavior.
- `Queued` but not downloading: start or inspect `MediaDownloadProcessor` in the `Processes` surface.
- Progress does not move: the torrent has metadata but not enough peers for the selected file.
- Movie is not visible on `/tv`: only ready cached movies appear on the TV surface.
- Playback starts but fails or has no audio: the browser likely cannot decode the file. Prefer MP4 H264 AAC for V1.
- A ready movie disappeared from the TV shelf: the cache manager may have evicted the local file to stay under the 3GB cap. The record should still exist on `/rtv/home`, and magnet-backed items can be queued again after metadata has been resolved.
- A thumbnail disappeared after deleting the movie file: generated posters should live under `RTV_MEDIA_DIR/posters` and survive local file deletion. Open the rTV edit dialog to set a manual thumbnail URL if you want to override the generated poster.

## What This Test Proves

- rTV can add and manage movie candidates.
- Torrent metadata resolution selects a single movie file.
- Downloads are explicit and complete before playback.
- The cache manager protects the configured disk cap.
- The TV surface only exposes ready playable movies.
- Playback updates Rasbhari through media events.
