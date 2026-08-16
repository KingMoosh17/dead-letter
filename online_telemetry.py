"""Opt-in anonymous telemetry upload for Dead Letter.

Local CSV telemetry remains the source of truth. When a player explicitly opts
in, newly recorded local events are copied into a small persistent JSONL queue
and uploaded to Supabase on a daemon thread. Network failures never interrupt
or block gameplay and queued events are retried on a later event/startup.
"""
from __future__ import annotations

import csv
import json
import threading
import uuid
from pathlib import Path
from urllib import error, request

SUPABASE_URL = "https://qlodkitflnklidbrwjkc.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_z9PMNiTgyNZPw1W1BPr1iA_n_oN-eoL"
SCHEMA_VERSION = 1
CONSENT_VERSION = 1
MAX_QUEUE_EVENTS = 2000
BATCH_SIZE = 25
MAX_BATCHES_PER_FLUSH = 8

_lock = threading.Lock()
_worker_lock = threading.Lock()
_worker_running = False


def _settings_path(data_dir: Path) -> Path:
    return Path(data_dir) / "settings.json"


def sharing_enabled(data_dir: Path | None) -> bool:
    if data_dir is None:
        return False
    try:
        data = json.loads(_settings_path(Path(data_dir)).read_text(encoding="utf-8"))
        return (
            int(data.get("telemetry_consent_version", 0)) == CONSENT_VERSION
            and bool(data.get("remote_telemetry_enabled", False))
            and bool(data.get("telemetry_enabled", True))
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def _queue_path(data_dir: Path) -> Path:
    path = Path(data_dir) / "telemetry"
    path.mkdir(parents=True, exist_ok=True)
    return path / "upload_queue.jsonl"


def discard_queue(data_dir: Path | None) -> None:
    """Delete unsent online telemetry when the player opts out."""
    if data_dir is None:
        return
    try:
        path = Path(data_dir) / "telemetry" / "upload_queue.jsonl"
        with _lock:
            path.unlink(missing_ok=True)
            path.with_suffix(".tmp").unlink(missing_ok=True)
    except OSError:
        pass


def _read_last_csv_row(path: Path) -> dict | None:
    try:
        with Path(path).open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return rows[-1] if rows else None
    except (OSError, csv.Error):
        return None


def enqueue_csv_event(data_dir: Path | None, event_type: str, csv_path: Path | None) -> None:
    if data_dir is None or csv_path is None or not sharing_enabled(data_dir):
        return
    row = _read_last_csv_row(Path(csv_path))
    if not row:
        return
    enqueue_event(Path(data_dir), event_type, row)


def enqueue_event(data_dir: Path, event_type: str, payload: dict) -> None:
    if event_type not in {"round", "decision", "run_event"}:
        return
    run_id = str(payload.get("run_id", "")).strip()
    game_version = str(payload.get("game_version", "")).strip()
    if not run_id or not game_version:
        return
    event = {
        "event_id": str(uuid.uuid4()),
        "run_id": run_id[:96],
        "schema_version": SCHEMA_VERSION,
        "game_version": game_version[:32],
        "event_type": event_type,
        "client_time": payload.get("timestamp") or None,
        "payload": payload,
    }
    path = _queue_path(data_dir)
    try:
        with _lock:
            existing = []
            if path.exists():
                existing = path.read_text(encoding="utf-8").splitlines()
            existing = existing[-(MAX_QUEUE_EVENTS - 1):]
            existing.append(json.dumps(event, separators=(",", ":"), ensure_ascii=True))
            tmp = path.with_suffix(".tmp")
            tmp.write_text("\n".join(existing) + "\n", encoding="utf-8")
            tmp.replace(path)
    except OSError:
        return
    start_flush(data_dir)


def _load_batch(path: Path) -> list[dict]:
    try:
        with _lock:
            lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        batch = []
        for line in lines:
            if len(batch) >= BATCH_SIZE:
                break
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(event, dict) and event.get("event_id"):
                batch.append(event)
        return batch
    except OSError:
        return []


def _remove_uploaded(path: Path, uploaded: list[dict]) -> None:
    """Remove only events confirmed uploaded, preserving events appended meanwhile."""
    uploaded_ids = {str(event.get("event_id")) for event in uploaded if event.get("event_id")}
    if not uploaded_ids:
        return
    try:
        with _lock:
            current = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
            kept = []
            for line in current:
                try:
                    event = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    # Drop malformed queue records during normal cleanup.
                    continue
                if str(event.get("event_id", "")) not in uploaded_ids:
                    kept.append(json.dumps(event, separators=(",", ":"), ensure_ascii=True))
            tmp = path.with_suffix(".tmp")
            tmp.write_text(("\n".join(kept) + "\n") if kept else "", encoding="utf-8")
            tmp.replace(path)
    except OSError:
        pass


def _post_batch(batch: list[dict]) -> bool:
    if not batch:
        return True
    body = json.dumps(batch, separators=(",", ":")).encode("utf-8")
    req = request.Request(
        f"{SUPABASE_URL}/rest/v1/telemetry_events",
        data=body,
        method="POST",
        headers={
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    try:
        with request.urlopen(req, timeout=4.0) as response:
            return 200 <= int(response.status) < 300
    except (error.URLError, error.HTTPError, TimeoutError, OSError, ValueError):
        return False


def flush_once(data_dir: Path) -> None:
    if not sharing_enabled(data_dir):
        return
    path = _queue_path(data_dir)
    for _ in range(MAX_BATCHES_PER_FLUSH):
        if not sharing_enabled(data_dir):
            return
        batch = _load_batch(path)
        if not batch:
            return
        if not _post_batch(batch):
            return
        _remove_uploaded(path, batch)
        if len(batch) < BATCH_SIZE:
            return


def start_flush(data_dir: Path | None) -> None:
    global _worker_running
    if data_dir is None or not sharing_enabled(data_dir):
        return
    data_dir = Path(data_dir)
    with _worker_lock:
        if _worker_running:
            return
        _worker_running = True

    def worker():
        global _worker_running
        try:
            flush_once(data_dir)
        finally:
            with _worker_lock:
                _worker_running = False

    threading.Thread(target=worker, name="dead-letter-telemetry", daemon=True).start()
