"""Measure canonical reachable-SFX PCM identity and TAD duplicate cost."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "audio"), str(ROOT / "tools" / "bor_converter"), str(ROOT / "soundwork" / "tad")]
from compile_reachable_sfx import canonical_wav  # noqa: E402
from pak_extract import extract  # noqa: E402
from rebuild import check_compiler_version, find_compiler  # noqa: E402


def compile_names(compiler, project_root: Path, names: list[str]) -> int:
    project_file = project_root / "02_coin.terrificaudio"
    project = json.loads(project_file.read_text(encoding="utf-8"))
    project["samples"] = [{"name": name, "source": f"samples/{name}.wav", "sample_rates": [11025], "loop": "none", "evaluator": "default", "ignore_gaussian_overflow": False, "envelope": "gain F127"} for name in names]
    project["sound_effects"] = [f"sfx_{name}" for name in names]
    project["high_priority_sound_effects"] = []
    project["low_priority_sound_effects"] = []
    project["sound_effect_file"] = "sound-effects.txt"
    project_file.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    effects = []
    for name in names:
        effects += [f"=== sfx_{name} ===", f"    set_instrument {name}", "    play_note 0 48", ""]
    (project_root / "sound-effects.txt").write_text("\n".join(effects), encoding="utf-8")
    out = project_root.parent / ("out_" + str(len(names)))
    out.mkdir()
    result = subprocess.run([str(compiler), "ca65-export", str(project_file), "-a", str(out / "audio-data.s"), "-b", str(out / "audio-data.bin"), "-i", str(out / "audio-enums.inc"), "-s", "AUDIO0", "--lorom"], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(result.stdout + result.stderr)
    blob = out / "audio-data.bin"
    return blob.stat().st_size - 116 - 3250 - 8 - 21


def main() -> int:
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    rows, groups = [], {}
    for family in manifest["families"]:
        for asset in family["assets"]:
            if asset["kind"] != "sfx" or not asset["shipped_reachable"]:
                continue
            raw = extract(ROOT / family["pak"], asset["source_path"])
            normalized, rate = canonical_wav(raw)
            digest = hashlib.sha256(normalized).hexdigest()
            label = family["family"] + ":" + asset["source_path"]
            rows.append({"asset": label, "canonical_pcm_hash": digest, "sample_rate_hz": rate})
            groups.setdefault(digest, []).append(label)
    compiler = find_compiler(None)
    version = check_compiler_version(compiler)
    with tempfile.TemporaryDirectory(prefix="bor-sfx-dedup-") as tmp:
        root = Path(tmp) / "project"
        shutil.copytree(ROOT / "soundwork/tad/project", root)
        normalized, _ = canonical_wav(extract(ROOT / "Beats of Rage Original [v.3.0 Build 4086].pak", r"DATA\SOUNDS\BEAT1.WAV"))
        (root / "samples").mkdir(exist_ok=True)
        (root / "samples/a.wav").write_bytes(normalized)
        (root / "samples/b.wav").write_bytes(normalized)
        one = compile_names(compiler, root, ["a"])
        two = compile_names(compiler, root, ["a", "b"])
    output = {"schema_version": 1, "compiler": str(compiler), "compiler_version": version, "reachable_asset_count": len(rows), "canonical_assets": rows, "identical_groups": [items for items in groups.values() if len(items) > 1], "tad_one_sample_common_bytes": one, "tad_duplicate_sample_common_bytes": two, "tad_duplicate_delta_bytes": two - one}
    (ROOT / "tools/audio/sfx_pcm_dedup.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"canonical reachable SFX: {len(rows)} assets; identical groups: {len(output['identical_groups'])}")
    print(f"TAD duplicate experiment: one={one} bytes, duplicate={two} bytes, delta={two - one}")


if __name__ == "__main__":
    raise SystemExit(main())
