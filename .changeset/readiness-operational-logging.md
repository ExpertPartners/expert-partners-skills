---
research-ops: patch
---

video-discovery: `video_discovery.py` and `probe_media.py` now write privacy-safe operational status events to stderr through a new `scripts/operational_logging.py` module. Each event is one JSON line holding only a fixed event name, a random run identifier, a success or failure outcome, a duration and bounded counts. Unknown fields are rejected, exception text and content are never logged, and nothing is written to files or sent over the network.
