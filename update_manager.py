"""GitHub Releases update checker/downloader for Dead Letter.

Player data lives outside the install directory, so replacing application files
preserves settings, statistics, and local telemetry.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    asset_url: str
    asset_name: str
    release_url: str
    notes: str = ""


def _version_tuple(text: str) -> tuple[int, ...]:
    text = (text or "").strip().lower().lstrip("v")
    parts = []
    for token in text.split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts or [0])


class UpdateManager:
    def __init__(self, install_dir: str | Path, current_version: str):
        self.install_dir = Path(install_dir).resolve()
        self.current_version = current_version
        self.config_path = self.install_dir / "update_config.json"
        self.last_error = ""

    def config(self) -> dict:
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return {}

    def configured(self) -> bool:
        repo = str(self.config().get("repository", "")).strip()
        return bool(repo and "/" in repo)

    def _api_lookup(self, repo: str, preferred: str, timeout: float) -> UpdateInfo | None:
        api = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(
            api,
            headers={
                "User-Agent": f"DeadLetter/{self.current_version}",
                "Accept": "application/vnd.github+json",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))

        latest = str(data.get("tag_name") or data.get("name") or "").strip().lstrip("v")
        if not latest or _version_tuple(latest) <= _version_tuple(self.current_version):
            return None

        assets = data.get("assets") or []
        candidates = [a for a in assets if str(a.get("name", "")).lower().endswith(".zip")]
        asset = next((a for a in candidates if str(a.get("name", "")).startswith(preferred)), None)
        if asset is None and candidates:
            asset = candidates[0]
        if not asset:
            raise ValueError("The latest GitHub release has no ZIP asset.")

        url = str(asset.get("browser_download_url") or "")
        if not url:
            raise ValueError("The latest GitHub release ZIP has no download URL.")
        return UpdateInfo(
            version=latest,
            asset_url=url,
            asset_name=str(asset.get("name") or f"Dead_Letter_v{latest}.zip"),
            release_url=str(data.get("html_url") or ""),
            notes=str(data.get("body") or "")[:1200],
        )

    def _redirect_lookup(self, repo: str, preferred: str, timeout: float) -> UpdateInfo | None:
        """Fallback that avoids GitHub's API rate limit entirely.

        Public /releases/latest redirects to the newest release tag. Since Dead
        Letter controls its asset naming convention, the ZIP URL can then be
        constructed directly from the tag.
        """
        latest_url = f"https://github.com/{repo}/releases/latest"
        req = urllib.request.Request(
            latest_url,
            headers={
                "User-Agent": f"DeadLetter/{self.current_version}",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            final_url = response.geturl()

        marker = "/releases/tag/"
        if marker not in final_url:
            raise ValueError("GitHub did not redirect to a release tag.")
        tag = urllib.parse.unquote(final_url.split(marker, 1)[1].split("?", 1)[0].split("#", 1)[0]).strip("/")
        latest = tag.lstrip("v")
        if not latest or _version_tuple(latest) <= _version_tuple(self.current_version):
            return None

        asset_name = f"{preferred}{latest}.zip"
        asset_url = (
            f"https://github.com/{repo}/releases/download/"
            f"{urllib.parse.quote(tag, safe='')}/{urllib.parse.quote(asset_name, safe='')}"
        )
        return UpdateInfo(
            version=latest,
            asset_url=asset_url,
            asset_name=asset_name,
            release_url=final_url,
            notes="",
        )

    def check_latest(self, timeout: float = 5.0) -> UpdateInfo | None:
        self.last_error = ""
        cfg = self.config()
        repo = str(cfg.get("repository", "")).strip()
        if not repo or "/" not in repo:
            self.last_error = "The update repository is not configured."
            return None
        preferred = str(cfg.get("asset_prefix", "Dead_Letter_v"))

        api_error = ""
        try:
            return self._api_lookup(repo, preferred, timeout)
        except Exception as exc:
            api_error = f"GitHub API: {exc}"

        try:
            info = self._redirect_lookup(repo, preferred, timeout)
            self.last_error = ""
            return info
        except Exception as exc:
            self.last_error = f"{api_error}; public release fallback: {exc}"
            return None

    def stage_update(self, info: UpdateInfo, timeout: float = 45.0) -> Path:
        temp_root = Path(tempfile.mkdtemp(prefix="dead_letter_update_"))
        archive = temp_root / info.asset_name
        req = urllib.request.Request(info.asset_url, headers={"User-Agent": f"DeadLetter/{self.current_version}"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response, archive.open("wb") as out:
                shutil.copyfileobj(response, out)
            extract = temp_root / "extract"
            extract.mkdir()
            with zipfile.ZipFile(archive) as zf:
                for member in zf.infolist():
                    dest = (extract / member.filename).resolve()
                    if extract.resolve() not in dest.parents and dest != extract.resolve():
                        raise ValueError("Update archive contains an unsafe path.")
                zf.extractall(extract)
        except Exception:
            shutil.rmtree(temp_root, ignore_errors=True)
            raise

        roots = [extract] + [p for p in extract.iterdir() if p.is_dir()]
        source = next((r for r in roots if (r / "VERSION.txt").exists() and ((r / "DeadLetter.exe").exists() or (r / "main.py").exists())), None)
        if source is None:
            shutil.rmtree(temp_root, ignore_errors=True)
            raise ValueError("The release ZIP is not a valid Dead Letter package.")
        staged_version = (source / "VERSION.txt").read_text(encoding="utf-8").strip()
        if _version_tuple(staged_version) < _version_tuple(info.version):
            shutil.rmtree(temp_root, ignore_errors=True)
            raise ValueError("Release version does not match the downloaded package.")
        return source

    def launch_installer(self, staged_source: str | Path):
        staged_source = Path(staged_source).resolve()
        common_args = ["--pid", str(os.getpid()), "--source", str(staged_source), "--target", str(self.install_dir)]
        staged_exe = staged_source / "DeadLetterUpdater.exe"
        if os.name == "nt" and staged_exe.exists():
            args = [str(staged_exe), *common_args]
        else:
            updater = self.install_dir / "updater.py"
            if not updater.exists():
                raise FileNotFoundError("DeadLetterUpdater.exe/updater.py is missing.")
            args = [sys.executable, str(updater), *common_args]
        flags = 0
        if os.name == "nt":
            flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        subprocess.Popen(args, cwd=str(staged_source), close_fds=(os.name != "nt"), creationflags=flags)
