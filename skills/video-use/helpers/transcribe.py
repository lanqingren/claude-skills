"""Transcribe a video locally with OpenAI Whisper.

Extracts mono 16kHz audio via ffmpeg, runs Whisper locally, and writes a
Scribe-compatible transcript JSON to <edit_dir>/transcripts/<video_stem>.json.

Cached: if the output file already exists, transcription is skipped.

Usage:
    python helpers/transcribe.py <video_path>
    python helpers/transcribe.py <video_path> --edit-dir /custom/edit
    python helpers/transcribe.py <video_path> --language en
    python helpers/transcribe.py <video_path> --model small
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def load_api_key() -> str:
    """Compatibility shim for transcribe_batch.py.

    The original helper required ELEVENLABS_API_KEY. Local Whisper does not use
    any API key, but transcribe_batch imports and calls this function.
    """
    return ""


def extract_audio(video_path: Path, dest: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def whisper_word_entries(result: dict) -> list[dict]:
    """Convert Whisper verbose output to the word list expected downstream."""
    entries: list[dict] = []
    prev_end: float | None = None

    for segment in result.get("segments", []):
        words = segment.get("words") or []
        if words:
            for word in words:
                start = float(word.get("start", segment.get("start", 0.0)))
                end = float(word.get("end", start))
                text = str(word.get("word", "")).strip()
                if not text:
                    continue
                if prev_end is not None and start > prev_end:
                    entries.append({
                        "type": "spacing",
                        "text": " ",
                        "start": prev_end,
                        "end": start,
                    })
                entries.append({
                    "type": "word",
                    "text": text,
                    "start": start,
                    "end": end,
                    "speaker_id": "speaker_0",
                })
                prev_end = end
            continue

        # Fallback for Whisper versions without word timestamps.
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        if prev_end is not None and start > prev_end:
            entries.append({
                "type": "spacing",
                "text": " ",
                "start": prev_end,
                "end": start,
            })
        entries.append({
            "type": "word",
            "text": text,
            "start": start,
            "end": end,
            "speaker_id": "speaker_0",
        })
        prev_end = end

    return entries


def call_whisper(
    audio_path: Path,
    language: str | None = None,
    model_name: str = "small",
) -> dict:
    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI Whisper is not installed. Install it with: pip install -U openai-whisper"
        ) from exc

    model = whisper.load_model(model_name)
    options: dict[str, object] = {
        "fp16": False,
        "verbose": False,
        "word_timestamps": True,
    }
    if language:
        options["language"] = language

    result = model.transcribe(str(audio_path), **options)
    words = whisper_word_entries(result)
    return {
        "text": result.get("text", ""),
        "language_code": result.get("language"),
        "words": words,
        "source": "openai-whisper-local",
        "model": model_name,
    }


def transcribe_one(
    video: Path,
    edit_dir: Path,
    api_key: str = "",
    language: str | None = None,
    num_speakers: int | None = None,
    verbose: bool = True,
    model_name: str = "small",
) -> Path:
    """Transcribe a single video. Returns path to transcript JSON.

    Cached: returns existing path immediately if the transcript already exists.
    api_key and num_speakers are accepted for compatibility with the original
    ElevenLabs helper, but local Whisper does not use them.
    """
    del api_key, num_speakers

    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{video.stem}.json"

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path

    if verbose:
        print(f"  extracting audio from {video.name}", flush=True)

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio)
        size_mb = audio.stat().st_size / (1024 * 1024)
        if verbose:
            print(f"  transcribing locally with Whisper {model_name} ({size_mb:.1f} MB)", flush=True)
        payload = call_whisper(audio, language=language, model_name=model_name)

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    dt = time.time() - t0

    if verbose:
        kb = out_path.stat().st_size / 1024
        print(f"  saved: {out_path.name} ({kb:.1f} KB) in {dt:.1f}s")
        print(f"    words: {len(payload.get('words', []))}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe a video locally with OpenAI Whisper")
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument(
        "--edit-dir",
        type=Path,
        default=None,
        help="Edit output directory (default: <video_parent>/edit)",
    )
    ap.add_argument(
        "--language",
        type=str,
        default=None,
        help="Optional ISO language code (e.g., 'en', 'zh'). Omit to auto-detect.",
    )
    ap.add_argument(
        "--num-speakers",
        type=int,
        default=None,
        help="Accepted for compatibility; local Whisper does not do speaker diarization.",
    )
    ap.add_argument(
        "--model",
        type=str,
        default="small",
        choices=["tiny", "base", "small", "medium", "large", "turbo"],
        help="Whisper model to use (default: small).",
    )
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or (video.parent / "edit")).resolve()

    transcribe_one(
        video=video,
        edit_dir=edit_dir,
        language=args.language,
        num_speakers=args.num_speakers,
        model_name=args.model,
    )


if __name__ == "__main__":
    main()
