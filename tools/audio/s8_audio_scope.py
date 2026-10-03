"""Source Normal closure and mechanically pinned S7 ACCEPTED_COMPAT audio."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S7 = "c8cbd71b200cab869d3f953bdd07352c172577ed"


@lru_cache(None)
def baseline(path: str) -> bytes:
    return subprocess.run(["git", "show", f"{S7}:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def roster() -> list[dict]:
    tree = ast.parse(baseline("tools/audio/shipped_content.py"))
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "ROSTER_CONFIGS" for t in n.targets))


def normal_scope() -> dict:
    from shipped_content import STAGE_CONFIGS, ROSTER_CONFIGS, normal_player_entries
    from production_campaign import Source, stage, model_catalog, key
    selected = [s for s in STAGE_CONFIGS if s.get("source_set_id") == 1 and s["family"] == "bor-original"]
    if not selected:
        raise SystemExit("FAIL: no source Normal stages")
    source = Source(selected[0]["pak"])
    catalog = model_catalog(source)
    used = {i for i, _ in normal_player_entries("bor-original")}
    stages = []
    for cfg in selected:
        parsed = stage(source, cfg["source_level"])
        names = sorted({name.casefold() for e in parsed.queue for name in (e.character, e.item) if name})
        for name in names:
            path = key(catalog[name]["source_path"])
            matches = [i for i, r in enumerate(ROSTER_CONFIGS) if r["family"] == "bor-original"
                       and 1 in r.get("runtime_binding_sets", (0, 1))
                       and (key(r["source_character"]) == path.rsplit("/", 1)[0]
                            or key(r["source_character"]) == path.removesuffix(".txt"))]
            if len(matches) != 1:
                raise SystemExit(f"FAIL: Normal audio model binding {name}: {matches}")
            used.add(matches[0])
        stages.append({"source": cfg["source_level"], "models": names,
                       "sha256": digest(source.read(cfg["source_level"]))})
    return {"campaign": "Normal", "source_set_id": 1, "stages": stages,
            "roster_indices": sorted(used)}


def accepted_inventory() -> dict:
    from shipped_content import ROSTER_CONFIGS
    old_roster = roster()
    old_manifest = json.loads(baseline("tools/audio/audio_manifest.json"))
    current_manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text())
    old_paks = {f["family"]: f["pak_hash"] for f in old_manifest["families"]}
    for family in current_manifest["families"]:
        if digest((ROOT / family["pak"]).read_bytes()) != old_paks[family["family"]]:
            raise SystemExit(f"FAIL: S7 source PAK changed: {family['family']}")
    # These are actual runtime inputs, not the obsolete explorer/bank report.
    pinned_paths = ["tools/audio/batch_b_audio.json", "src/core/vm/audio_batch_b_generated.pasm",
                    "src/audio_batch_b_stream_sources.pasm"]
    for path in pinned_paths:
        if (ROOT / path).read_bytes().replace(b"\r\n", b"\n") != baseline(path).replace(b"\r\n", b"\n"):
            raise SystemExit(f"FAIL: accepted audio adapter changed: {path}")
    seal = json.loads(baseline("soundwork/tad/driver_baseline.json"))
    blob = baseline("soundwork/tad/build/audio-data.bin")
    if digest(blob) != seal["runtime_graph"]["audio_data_sha256_after_patch"]:
        raise SystemExit("FAIL: S7 resident blob does not match its own driver seal")
    project_path = "soundwork/tad/project/02_coin.terrificaudio"
    old_project = json.loads(baseline(project_path))
    current_project = json.loads((ROOT / project_path).read_text())
    for field in ("samples", "sound_effects"):
        if current_project[field][:len(old_project[field])] != old_project[field]:
            raise SystemExit(f"FAIL: S7 resident {field} changed")
    for sample in old_project["samples"]:
        path = "soundwork/tad/project/" + sample["source"]
        if (ROOT / path).read_bytes() != baseline(path):
            raise SystemExit(f"FAIL: S7 resident source sample changed: {path}")
    effects = "soundwork/tad/project/sound-effects.txt"
    if not (ROOT / effects).read_text().startswith(baseline(effects).decode().replace("\r\n", "\n")):
        raise SystemExit("FAIL: S7 resident effects changed")
    # The death selector is extended below; the shared queue, frame dispatch,
    # and serialized stream policy themselves must remain the S7 adapter.
    runtime_path = "src/core/vm/vm_native_engine.pasm"
    old_runtime = baseline(runtime_path).decode().replace("\r\n", "\n")
    current_runtime = (ROOT / runtime_path).read_text()
    for start, end in (("Audio_QueueResidentSemantic:", "AudioSemantic_EmitDiesound:"),
                       ("AudioSemantic_StreamBackendPolicy:", "Game_State_TickExtraActorTimers:")):
        if current_runtime.split(start, 1)[1].split(end, 1)[0] != old_runtime.split(start, 1)[1].split(end, 1)[0]:
            raise SystemExit(f"FAIL: unclassified S7 runtime audio change: {start}")
    spec = json.loads(baseline("tools/audio/batch_b_audio.json"))
    accepted = []
    for i, old in enumerate(old_roster):
        if i >= len(ROSTER_CONFIGS) or any(ROSTER_CONFIGS[i][k] != old[k] for k in ("family", "source_character", "converted_prefix")):
            raise SystemExit(f"FAIL: S7 roster identity moved at {i}")
        path = old["converted_prefix"] + "_moveset.json"
        if json.loads((ROOT / path).read_text()) != json.loads(baseline(path)):
            raise SystemExit(f"FAIL: unclassified action change in S7 model {old['source_character']}")
        die = spec["diesounds"].get(str(i)) if i < 21 else None
        accepted.append({"roster_index": i, "owner": old["family"] + ":" + old["source_character"].split("\\CHARS\\", 1)[1],
                         "classification": "ADAPTER_EQUIVALENT", "moveset_sha256": digest(baseline(path)),
                         "legacy_diesound": die,
                         "legacy_diesound_policy": "table dispatch" if i < 21 else "S7 >=21 excluded; preserved adapter",
                         "legacy_frame_records": [r for r in spec["frame_sounds"] if r["roster"] == i]})
    globals = [{"owner": f["family"] + ":engine", "event": r["semantic_event"],
                "asset": f["family"] + ":" + a["source_path"]}
               for f in old_manifest["families"] for a in f["assets"] for r in a["references"]
               if r.get("directive") == "engine-global-default" and r.get("snes_reachable")]
    return {"baseline": S7, "resident_blob_sha256": digest(blob), "globals": globals,
            "runtime_input_hashes": {p: digest(baseline(p)) for p in pinned_paths}, "models": accepted}
