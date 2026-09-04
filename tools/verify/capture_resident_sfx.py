#!/usr/bin/env python3
"""Capture one generated resident SFX through the normal TAD queue path.

This is a backend/content control.  The caller supplies the generated local
effect ID and the physical voice to observe; no BOR semantic or DSP state is
written by this runner.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "distribution" / "bor.sfc"
NAME = os.environ.get("RESIDENT_SFX_NAME", "resident")
LOCAL_ID = int(os.environ.get("RESIDENT_LOCAL_ID", "0"), 0)
VOICE = int(os.environ.get("MESEN_VOICE_CAPTURE_VOICE", "6"), 0)
CAPTURE = Path(os.environ.get("MESEN_VOICE_CAPTURE_PATH", str(ROOT / "out" / f"{NAME}-direct.raw"))).resolve()
ARM = Path(os.environ.get("MESEN_VOICE_CAPTURE_ARM_FILE", str(CAPTURE) + ".arm")).resolve()
STDERR = Path(os.environ.get("MESEN_VOICE_CAPTURE_STDERR", str(CAPTURE) + ".stderr.log")).resolve()
ENV = {
    "MESEN_VOICE_CAPTURE_PATH": str(CAPTURE),
    "MESEN_VOICE_CAPTURE_VOICE": str(VOICE),
    "MESEN_VOICE_CAPTURE_ARM_FILE": str(ARM),
}

sys.path.insert(0, str(ROOT / "tools" / "verify"))
from _harness import open_session  # noqa: E402
import audio_semantic_diesound as semantic  # noqa: E402

QUEUE_SFX = 0x7E0020
QUEUE_PAN = 0x7E0021
PLAY_SFX_HANDLER_PC = int(os.environ.get("RESIDENT_SFX_HANDLER_PC", "0x08C1"), 0)


def remove_stale() -> None:
    CAPTURE.parent.mkdir(parents=True, exist_ok=True)
    for path in (CAPTURE, Path(str(CAPTURE) + ".json"), Path(str(CAPTURE) + ".report.json"), ARM):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    if not 0 <= VOICE <= 7:
        raise SystemExit("FAIL: physical voice must be in 0..7")
    if not 0 <= LOCAL_ID <= 255:
        raise SystemExit("FAIL: local resident SFX ID must fit in one byte")
    remove_stale()
    with open_session(__file__, env=ENV, stderr_log=str(STDERR)) as m:
        semantic.boot(m)
        # A direct backend control must not race a lower-ID gameplay request
        # from any live AI entity.  Keep the player/runtime lifecycle real,
        # but remove all non-player combat sources before queueing the chosen
        # resident ID.
        for base in semantic.ENTITY_BASES[1:]:
            semantic.w8(m, base + semantic.CHAR_HP, 0)
        for _ in range(30):
            m.run_frames(1)
            m.pause()
        Path(ARM).touch()
        handler_hook = m.add_exec_hook(PLAY_SFX_HANDLER_PC, PLAY_SFX_HANDLER_PC, cpu_type="Spc")
        m.write_memory("snesMemory", QUEUE_PAN, "40")
        m.write_memory("snesMemory", QUEUE_SFX, f"{LOCAL_ID:02X}")
        handler_result = m.run_until(60, handler_hook)
        m.remove_hook(handler_hook)
        m.run_frames(180)
        m.pause()
        state = m.get_audio_state()
    raw = CAPTURE.read_bytes() if CAPTURE.exists() else b""
    sidecar_path = Path(str(CAPTURE) + ".json")
    sidecar = {}
    if sidecar_path.exists():
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8").splitlines()[0])
    report = {
        **sidecar,
        "fixture": "direct-resident-sfx",
        "name": NAME,
        "local_id": LOCAL_ID,
        "voice": VOICE,
        "rom_sha256": hashlib.sha256(ROM.read_bytes()).hexdigest(),
        "capture_sha256": hashlib.sha256(raw).hexdigest(),
        "capture_bytes": len(raw),
        "audio_state": state,
        "capture_path": str(CAPTURE),
        "spc_handler_pc": PLAY_SFX_HANDLER_PC,
        "spc_handler_result": handler_result,
    }
    Path(str(CAPTURE) + ".report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if raw else 1


if __name__ == "__main__":
    raise SystemExit(main())
