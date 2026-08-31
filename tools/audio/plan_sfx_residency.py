"""Generate and compile context-correct Strategy A/B SFX residency sets."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "audio"))
sys.path.insert(0, str(ROOT / "tools" / "bg_converter"))
sys.path.insert(0, str(ROOT / "tools" / "bor_converter"))
from engine_audio_semantics import ENGINE_GLOBAL_AUDIO  # noqa: E402
from pak_extract import extract  # noqa: E402
from spawn_parse import parse_spawns, SpawnEvent  # noqa: E402
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS  # noqa: E402


def key(family: str, path: str) -> str:
    return f"{family}:{path.upper()}"


def main() -> int:
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    all_assets = {(f["family"], a["source_path"]): a for f in manifest["families"] for a in f["assets"] if a["kind"] == "sfx"}
    global_by_event = {}
    for family, path in all_assets:
        for ref in all_assets[(family, path)]["references"]:
            if ref.get("directive") == "engine-global-default" and ref.get("snes_reachable"):
                global_by_event.setdefault((family, ref["semantic_event"]), set()).add((family, path))

    def model_assets(family: str, identity: str) -> set[tuple[str, str]]:
        marker = "DATA\\CHARS\\" + identity.upper().strip("\\") + "\\"
        return {(f, p) for (f, p), a in all_assets.items() if f == family and any(marker in r.get("source_file", "").upper() and r.get("reachability") == "shipped-reachable" for r in a["references"])}

    represented = {(e["family"], e["source_character"].split("\\CHARS\\", 1)[1].upper().strip("\\")) for e in ROSTER_CONFIGS}

    def represented_identity(family: str, name: str) -> str | None:
        name = name.upper().strip("\\")
        for owner, identity in represented:
            if owner == family and identity.rsplit("\\", 1)[-1] == name.rsplit("\\", 1)[-1]:
                return identity
        return None

    def stage_entities(stage: dict) -> tuple[set[str], set[str]]:
        text = extract(ROOT / stage["pak"], stage["source_level"]).decode("latin1")
        entities, items = set(), set()
        for event in parse_spawns(text):
            if isinstance(event, SpawnEvent):
                entities.add(event.character)
                if event.item:
                    items.add(event.item)
        return entities, items

    def stage_base(stage: dict) -> tuple[set[tuple[str, str]], dict]:
        family = stage["family"]
        entities, items = stage_entities(stage)
        represented_entities = {resolved for name in entities | items if (resolved := represented_identity(family, name))}
        base = set().union(*(model_assets(family, n) for n in represented_entities)) if represented_entities else set()
        level = stage["source_level"].upper()
        base |= {(f, p) for (f, p), a in all_assets.items() if f == family and any(level in r.get("source_file", "").upper() for r in a["references"])}
        names = {n.upper() for n in entities | items}
        if names & {"MONEY", "GOLD", "APPLE", "MEAT"}:
            base |= global_by_event.get((family, "score-pickup"), set()) | global_by_event.get((family, "health-pickup"), set())
        if "1UP" in names:
            base |= global_by_event.get((family, "one-up"), set())
        return base, {"spawnable_entities": sorted(entities), "contained_or_standalone_items": sorted(items)}

    player_sets = {}
    for entry in ROSTER_CONFIGS:
        if entry["playable"]:
            identity = entry["source_character"].split("\\CHARS\\", 1)[1]
            player_sets[entry["converted_prefix"]] = model_assets(entry["family"], identity)

    candidates, stage_reports = {}, {}
    for stage in STAGE_CONFIGS:
        stage_key = stage["family"] + ":" + stage["source_level"]
        base, report = stage_base(stage)
        stage_global = base & set().union(*(global_by_event.get((stage["family"], event), set()) for event in ("score-pickup", "one-up", "health-pickup", "pause-entry", "ui-beep", "ui-beep-secondary")))
        stage_reports[stage_key] = {**report, "required_stage_global_sfx": sorted(key(*x) for x in stage_global), "model_local_sfx": sorted(key(*x) for x in base - stage_global), "stage_base_sfx": sorted(key(*x) for x in base)}
        player_global = global_by_event.get((stage["family"], "landed-hit"), set()) | global_by_event.get((stage["family"], "attack-swing"), set()) | global_by_event.get((stage["family"], "ui-beep"), set()) | global_by_event.get((stage["family"], "ui-beep-secondary"), set())
        all_local = set().union(*player_sets.values()) if player_sets else set()
        reasons = {key(*item): "stage-content:represented-model-or-directive" for item in base}
        reasons.update({key(*item): "all-selectable-player:model-local" for item in all_local})
        reasons.update({key(*item): "active-player-global:ordinary-attack-or-ui:stage-family" for item in player_global})
        candidates["A:" + stage_key] = {"strategy": "A", "stages": [stage_key], "players": ["all"], "combinations": [{"stage": stage_key, "player": "all"}], "assets": sorted(key(*x) for x in base | all_local | player_global), "asset_reasons": reasons}
        for prefix, local in player_sets.items():
            selected = base | local | player_global
            moveset = ROOT / (prefix + "_moveset.json")
            jump_capable = moveset.exists() and json.loads(moveset.read_text(encoding="utf-8")).get("roles", {}).get("jump") is not None
            if jump_capable:
                selected |= global_by_event.get((stage["family"], "jump"), set())
            reasons = {key(*item): "stage-content:represented-model-or-directive" for item in base}
            reasons.update({key(*item): f"selected-player:{prefix}:model-local" for item in local})
            reasons.update({key(*item): "active-player-global:ordinary-attack-or-ui:stage-family" for item in player_global})
            if jump_capable:
                reasons.update({key(*item): "active-player-global:jump:stage-family" for item in global_by_event.get((stage["family"], "jump"), set())})
            candidates["B:" + stage_key + ":" + prefix] = {"strategy": "B", "stages": [stage_key], "players": [prefix], "combinations": [{"stage": stage_key, "player": prefix}], "assets": sorted(key(*x) for x in selected), "asset_reasons": reasons}
    expected = len(STAGE_CONFIGS) * (1 + sum(e["playable"] for e in ROSTER_CONFIGS))
    if len(candidates) != expected:
        raise SystemExit(f"candidate formula mismatch: generated {len(candidates)}, expected {expected}")
    unique = {}
    for candidate in candidates.values():
        signature = tuple(candidate["assets"])
        record = unique.setdefault(signature, {**candidate, "stages": [], "players": [], "combinations": []})
        record["stages"] = sorted(set(record["stages"] + candidate["stages"]))
        record["players"] = sorted(set(record["players"] + candidate["players"]))
        record["combinations"].extend(candidate["combinations"])
    results = []
    for signature, candidate in unique.items():
        cmd = [sys.executable, str(ROOT / "tools/audio/compile_reachable_sfx.py")]
        for asset in signature:
            cmd += ["--asset", asset]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        size = next((int(line.split()[2]) for line in output.splitlines() if line.startswith("compiled audio-data.bin:")), None)
        common = next((int(line.split()[2]) for line in output.splitlines() if line.startswith("compiled common-data:")), None)
        overflow = None
        if "common audio data is too large" in output:
            import re
            match = re.search(r"common audio data is too large \((\d+) bytes, max: (\d+) bytes\)", output)
            if match:
                overflow = {"required_common_bytes": int(match.group(1)), "max_common_bytes": int(match.group(2))}
        results.append({**candidate, "compile_pass": result.returncode == 0, "compiled_blob_bytes": size, "compiled_common_bytes": common, "overflow": overflow, "compile_diagnostic": output[-700:] if result.returncode else None})
    out = {"schema_version": 3, "candidate_count": len(candidates), "unique_set_count": len(results), "stage_reports": stage_reports, "candidates": results}
    (ROOT / "tools/audio/sfx_residency.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"residency candidates: {len(candidates)} combinations, {len(results)} unique sets")
    print(f"compiled passing sets: {sum(r['compile_pass'] for r in results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
