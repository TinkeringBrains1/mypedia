"""Transient audio conversion for Gemini-compatible voice understanding."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import os
from functools import lru_cache
from pathlib import Path


class AudioConversionError(RuntimeError):
    """Raised when a browser recording cannot be converted safely."""


_INPUT_EXTENSIONS = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
}


def convert_for_gemini(audio_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """Convert a short browser recording to 16 kHz mono WAV without persisting it.

    Gemini's Interactions API does not accept WebM containers even when they
    contain Opus audio. WAV is explicitly supported and avoids relying on a
    browser to produce an OGG/MP4 container.
    """
    executable = _find_ffmpeg()
    if executable is None:
        raise AudioConversionError("FFmpeg is required to process voice recordings.")
    suffix = _INPUT_EXTENSIONS.get(mime_type)
    if suffix is None:
        raise AudioConversionError("Unsupported browser recording format.")

    with tempfile.TemporaryDirectory(prefix="mypedia_voice_") as temporary_directory:
        directory = Path(temporary_directory)
        source = directory / f"recording{suffix}"
        converted = directory / "recording.wav"
        source.write_bytes(audio_bytes)
        try:
            completed = subprocess.run(
                [
                    executable,
                    "-y",
                    "-v",
                    "error",
                    "-i",
                    str(source),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(converted),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AudioConversionError("Voice recording conversion failed.") from exc
        if completed.returncode != 0 or not converted.exists():
            raise AudioConversionError("Voice recording could not be read.")
        return converted.read_bytes(), "audio/wav"


@lru_cache(maxsize=1)
def _find_ffmpeg() -> str | None:
    """Resolve FFmpeg from PATH, an explicit deployment setting, or WinGet."""
    configured = os.getenv("FFMPEG_PATH")
    if configured and Path(configured).is_file():
        return configured
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if packages.is_dir():
            for installation in packages.glob("*FFmpeg*"):
                for candidate in installation.glob("**/bin/ffmpeg.exe"):
                    if candidate.is_file():
                        return str(candidate)
        winget_link = Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"
        if winget_link.is_file():
            return str(winget_link)
    return None
