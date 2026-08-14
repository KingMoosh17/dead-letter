"""Persistent settings, profile statistics, and safe-screen run saves for Dead Letter."""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

GAME_VERSION = "1.1.1"


def user_data_dir() -> Path:
    """Return a per-user writable data directory outside the install folder."""
    override = os.environ.get("DEADLETTER_DATA_DIR")
    if override:
        root = Path(override)
    elif os.name == "nt" and os.environ.get("APPDATA"):
        root = Path(os.environ["APPDATA"]) / "DeadLetter"
    else:
        root = Path.home() / ".dead_letter"
    root.mkdir(parents=True, exist_ok=True)
    return root


DEFAULT_SETTINGS = {
    "display_mode": "fullscreen",  # fullscreen, borderless, windowed
    "resolution": "1280x800",
    "sound_enabled": True,
    "reduced_motion": False,
    "telemetry_enabled": True,
    "tutorial_seen": False,
    "check_updates": True,
}

DEFAULT_STATS = {
    "runs_started": 0,
    "runs_finished": 0,
    "main_wins": 0,
    "endless_runs": 0,
    "words_solved": 0,
    "bosses_defeated": 0,
    "perfect_words": 0,
    "full_word_solves": 0,
    "total_points_earned": 0,
    "highest_chapter": 1,
    "longest_run_words": 0,
    "best_run_points": 0,
    "highest_complexity_solved": 0.0,
    "best_by_difficulty": {
        "easy": {"runs": 0, "wins": 0, "longest_words": 0, "best_points": 0},
        "medium": {"runs": 0, "wins": 0, "longest_words": 0, "best_points": 0},
        "hard": {"runs": 0, "wins": 0, "longest_words": 0, "best_points": 0},
    },
    "recorded_finished_runs": [],
    "recorded_win_runs": [],
}


def _merge_defaults(value: Any, default: Any):
    if isinstance(default, dict):
        out = deepcopy(default)
        if isinstance(value, dict):
            for key, val in value.items():
                if key in default:
                    out[key] = _merge_defaults(val, default[key])
                else:
                    out[key] = val
        return out
    return default if value is None else value


def _read_json(path: Path, default: dict) -> dict:
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return _merge_defaults(json.load(f), default)
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return deepcopy(default)


def _write_json(path: Path, data: dict) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


class Storage:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else user_data_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.root / "settings.json"
        self.stats_path = self.root / "player_stats.json"
        self.save_path = self.root / "continue_run.json"
        self.settings = _read_json(self.settings_path, DEFAULT_SETTINGS)
        self.stats = _read_json(self.stats_path, DEFAULT_STATS)

    @property
    def telemetry_dir(self) -> Path:
        path = self.root / "telemetry"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_settings(self) -> bool:
        return _write_json(self.settings_path, self.settings)

    def save_stats(self) -> bool:
        return _write_json(self.stats_path, self.stats)

    def has_run_save(self) -> bool:
        return self.save_path.exists() and self.save_path.stat().st_size > 0

    def save_run_payload(self, payload: dict) -> bool:
        wrapper = {
            "save_version": 1,
            "game_version": GAME_VERSION,
            "payload": payload,
        }
        return _write_json(self.save_path, wrapper)

    def load_run_payload(self) -> dict | None:
        try:
            with self.save_path.open("r", encoding="utf-8") as f:
                wrapper = json.load(f)
            if int(wrapper.get("save_version", 0)) != 1:
                return None
            payload = wrapper.get("payload")
            return payload if isinstance(payload, dict) else None
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None

    def delete_run_save(self):
        try:
            self.save_path.unlink(missing_ok=True)
        except OSError:
            pass

    def record_run_started(self, difficulty: str):
        self.stats["runs_started"] += 1
        bucket = self.stats["best_by_difficulty"].setdefault(
            difficulty, {"runs": 0, "wins": 0, "longest_words": 0, "best_points": 0}
        )
        bucket["runs"] += 1
        self.save_stats()

    def record_main_win(self, game):
        ids = self.stats["recorded_win_runs"]
        if game.run_id in ids:
            return
        ids.append(game.run_id)
        if len(ids) > 500:
            del ids[:-500]
        self.stats["main_wins"] += 1
        bucket = self.stats["best_by_difficulty"].setdefault(
            game.difficulty, {"runs": 0, "wins": 0, "longest_words": 0, "best_points": 0}
        )
        bucket["wins"] += 1
        self._merge_run_peaks(game)
        self.save_stats()

    def record_endless_entered(self, game):
        # A run can only enter Endless once, and main-win IDs provide a stable guard.
        key = f"endless:{game.run_id}"
        finished_ids = self.stats["recorded_finished_runs"]
        if key in finished_ids:
            return
        finished_ids.append(key)
        if len(finished_ids) > 1000:
            del finished_ids[:-1000]
        self.stats["endless_runs"] += 1
        self.save_stats()

    def finalize_run(self, game):
        marker = f"finished:{game.run_id}"
        ids = self.stats["recorded_finished_runs"]
        if marker in ids:
            self._merge_run_peaks(game)
            self.save_stats()
            return
        ids.append(marker)
        if len(ids) > 1000:
            del ids[:-1000]
        self.stats["runs_finished"] += 1
        rs = getattr(game, "run_stats", {})
        self.stats["words_solved"] += int(rs.get("words_solved", game.round_index))
        self.stats["bosses_defeated"] += int(rs.get("bosses_defeated", game.completed_chapters))
        self.stats["perfect_words"] += int(rs.get("perfect_words", 0))
        self.stats["full_word_solves"] += int(rs.get("full_word_solves", 0))
        self.stats["total_points_earned"] += int(game.total_earned)
        self._merge_run_peaks(game)
        self.save_stats()

    def _merge_run_peaks(self, game):
        rs = getattr(game, "run_stats", {})
        solved = int(rs.get("words_solved", game.round_index))
        self.stats["highest_chapter"] = max(int(self.stats["highest_chapter"]), int(game.chapter))
        self.stats["longest_run_words"] = max(int(self.stats["longest_run_words"]), solved)
        self.stats["best_run_points"] = max(int(self.stats["best_run_points"]), int(game.total_earned))
        self.stats["highest_complexity_solved"] = max(
            float(self.stats["highest_complexity_solved"]),
            float(rs.get("highest_complexity_solved", 0.0)),
        )
        bucket = self.stats["best_by_difficulty"].setdefault(
            game.difficulty, {"runs": 0, "wins": 0, "longest_words": 0, "best_points": 0}
        )
        bucket["longest_words"] = max(int(bucket["longest_words"]), solved)
        bucket["best_points"] = max(int(bucket["best_points"]), int(game.total_earned))
