"""Record runtime audio inputs only after the pinned TAD rebuild check passes."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "tools/audio/runtime_audio_inputs.json"


def inputs() -> dict[str, str]:
    project_path = ROOT / "soundwork/tad/project/02_coin.terrificaudio"
    project = json.loads(project_path.read_text())
    paths = {project_path, project_path.parent / project["sound_effect_file"]}
    paths.update(project_path.parent / s["source"] for s in project["samples"])
    paths.update(project_path.parent / s["source"] for s in project["songs"])
    paths.update(ROOT / "soundwork/tad/build" / name for name in
                 ("audio-data.bin", "audio-data.s", "audio-enums.inc", "tad_blob_syms.pasm"))
    # Text hashes use repository LF semantics; binary/sample hashes stay raw.
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(
        p.read_bytes().replace(b"\r\n", b"\n") if p.suffix in (".txt", ".mml", ".s", ".inc", ".pasm", ".terrificaudio")
        else p.read_bytes()).hexdigest() for p in sorted(paths)}


def main() -> int:
    subprocess.run([sys.executable, str(ROOT / "soundwork/tad/rebuild.py"), "--check"], cwd=ROOT, check=True)
    OUTPUT.write_text(json.dumps({"schema_version": 1, "inputs_sha256": inputs()}, indent=2) + "\n", encoding="utf-8")
    print("runtime audio source/output seal recorded after reproducible compiler check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
