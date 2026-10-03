"""Extract the Normal timer's real BOR TIMEOVER sample at resident-bank rate."""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter")]
from pak_extract import extract

ASSET = "DATA\\SOUNDS\\TIMEOVER.WAV"
RAW_HASH = "b2b70433a077412a3e3f6d0fd8c9f1a31ad9f6047dc6901e21201d967ee20018"


def main() -> int:
    pak = ROOT / "Beats of Rage Original [v.3.0 Build 4086].pak"
    raw = extract(pak, ASSET)
    if hashlib.sha256(raw).hexdigest() != RAW_HASH:
        raise SystemExit("FAIL: TIMEOVER source changed")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("FAIL: ffmpeg required for TIMEOVER source resampling")
    pcm = subprocess.run(
        [ffmpeg, "-v", "error", "-i", "pipe:0", "-ac", "1", "-ar", "11025",
         "-acodec", "pcm_u8", "-f", "u8", "pipe:1"],
        input=raw, capture_output=True, check=True).stdout
    if len(pcm) != 10080 or len(set(pcm)) < 2:
        raise SystemExit("FAIL: TIMEOVER resampling lost duration or signal")
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setparams((1, 1, 11025, 0, "NONE", "not compressed"))
        wav.writeframes(pcm)
    canonical = output.getvalue()
    path = ROOT / "soundwork/tad/project/samples/timeover.wav"
    path.write_bytes(canonical)
    record = {
        "asset": "bor-original:" + ASSET,
        "source_pak": pak.name,
        "source_pak_sha256": hashlib.sha256(pak.read_bytes()).hexdigest(),
        "raw_sha256": RAW_HASH,
        "raw_frames": 20160, "raw_sample_rate_hz": 22050,
        "canonical_path": path.relative_to(ROOT).as_posix(),
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_frames": len(pcm), "canonical_rate_hz": 11025,
        "duration_ticks": 115, "brr_bytes": 5670,
        "resampler": "ffmpeg mono PCM u8 22050 to 11025; full duration, original pitch",
        "resampler_sha256": hashlib.sha256(Path(ffmpeg).read_bytes()).hexdigest(),
        "backend": "resident_tad_sfx", "effect": "sfx_timeover",
        "scope": "BOR Normal campaign timer expiration only",
    }
    (ROOT / "assets/audio/timeover.source.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
