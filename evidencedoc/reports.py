"""Private temporary, atomic JSON exports with bounded retention."""

import json
import logging
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path


def private_data_root() -> Path:
    root = Path(tempfile.gettempdir()) / f"evidencedoc-{os.getuid()}"
    root.mkdir(mode=0o700, exist_ok=True)
    if root.is_symlink() or root.stat().st_uid != os.getuid():
        raise OSError("The temporary storage directory ownership could not be verified.")
    root.chmod(0o700)
    return root


class ReportStore:
    def __init__(self, root=None, max_files=64, ttl_seconds=3600, cache_root=None):
        self.root = Path(root) if root is not None else private_data_root() / "reports"
        self.root.mkdir(parents=True, exist_ok=True)
        self.cache_root = Path(cache_root) if cache_root is not None else None
        self.max_files, self.ttl_seconds = max_files, ttl_seconds
        self._lock = threading.RLock()
        self._cleaner = None
        self.prune()

    def prune(self):
        with self._lock:
            now = time.time()
            for path in self.root.glob("*.json"):
                try:
                    if now - path.stat().st_mtime > self.ttl_seconds:
                        path.unlink(missing_ok=True)
                except FileNotFoundError:
                    pass
            if self.cache_root is not None:
                for path in self.cache_root.rglob("*"):
                    try:
                        if path.is_file() and now - path.stat().st_mtime > self.ttl_seconds:
                            path.unlink(missing_ok=True)
                    except FileNotFoundError:
                        pass

    def start_cleanup(self):
        """Run server-side retention even when no new reports arrive."""
        with self._lock:
            if self._cleaner is not None:
                return

            def clean_periodically():
                while True:
                    time.sleep(60)
                    try:
                        self.prune()
                    except OSError:
                        logging.exception("Could not clean expired report files")

            self._cleaner = threading.Thread(target=clean_periodically, daemon=True)
            self._cleaner.start()

    def write(self, report: dict) -> str:
        with self._lock:
            self.prune()
            path = self.root / f"evidencedoc-{uuid.uuid4().hex}.json"
            pending = path.with_suffix(".tmp")
            try:
                pending.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                pending.replace(path)
            finally:
                pending.unlink(missing_ok=True)
            files = sorted(
                self.root.glob("*.json"), key=lambda p: p.stat().st_mtime_ns, reverse=True
            )
            for old in files[self.max_files :]:
                old.unlink(missing_ok=True)
            return str(path)
