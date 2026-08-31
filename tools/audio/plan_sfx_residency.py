"""Generate residency evidence from packed runtime states."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "audio"))
from runtime_sfx_states import explore_stage, roster_identity  # noqa: E402
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS  # noqa: E402

CAPACITY = 60828
PICKUP_EVENTS = {1: "health-pickup", 2: "health-pickup", 3: "score-pickup", 4: "one-up", 5: "score-pickup"}


def asset_key(family: str, path: str) -> str:
    return f"{family}:{path.upper()}"


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ab-only", action="store_true", help="compile A/B candidates without the expensive exhaustive C compile")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    assets = {(family["family"], asset["source_path"]): asset for family in manifest["families"] for asset in family["assets"] if asset["kind"] == "sfx"}
    roster = {index: entry for index, entry in enumerate(ROSTER_CONFIGS)}
    global_by_event = {}
    for (family, path), asset in assets.items():
        if not asset["shipped_reachable"]:
            continue
        for ref in asset["references"]:
            if ref.get("directive") == "engine-global-default" and ref.get("snes_reachable"):
                global_by_event.setdefault((family, ref["semantic_event"]), set()).add((family, path))

    def model_assets(index: int):
        entry = roster[index]
        marker = "DATA\\CHARS\\" + roster_identity(entry) + "\\"
        return {(owner, path) for (owner, path), asset in assets.items() if owner == entry["family"] and asset["shipped_reachable"] and any(marker in ref.get("source_file", "").upper() and ref.get("reachability") == "shipped-reachable" for ref in asset["references"])}

    def add(values, reasons, items, reason):
        for item in items:
            values.add(item)
            reasons.setdefault(asset_key(*item), reason)

    def stage_directives(stage):
        level = stage["source_level"].upper()
        return {(owner, path) for (owner, path), asset in assets.items() if owner == stage["family"] and asset["shipped_reachable"] and any(level in ref.get("source_file", "").upper() for ref in asset["references"])}

    def jump_capable(entry):
        path = ROOT / (entry["converted_prefix"] + "_moveset.json")
        return path.exists() and json.loads(path.read_text(encoding="utf-8")).get("roles", {}).get("jump") is not None

    def state_set(stage, player_index, state):
        family = stage["family"]
        values, reasons = set(), {}
        add(values, reasons, stage_directives(stage), "stage-global:level-directive")
        for event in ("pause-entry", "ui-beep", "ui-beep-secondary", "landed-hit", "attack-swing"):
            add(values, reasons, global_by_event.get((family, event), set()), "global:" + event)
        player = roster[player_index]
        add(values, reasons, model_assets(player_index), "player:" + roster_identity(player) + ":model-local")
        if jump_capable(player):
            add(values, reasons, global_by_event.get((family, "jump"), set()), "global:jump")
        for slot_number, slot in enumerate(state["slots"], 1):
            if not slot["alive"]:
                continue
            entry = roster.get(slot["roster_index"])
            if entry is not None:
                add(values, reasons, model_assets(slot["roster_index"]), f"slot{slot_number}:{roster_identity(entry)}:model-local")
            event = PICKUP_EVENTS.get(slot["pickup_type"])
            if event:
                add(values, reasons, global_by_event.get((family, event), set()), "pending-transition:" + event)
        return values, reasons

    candidates, exact_states = {}, []
    for stage in STAGE_CONFIGS:
        stage_key = stage["family"] + ":" + stage["source_level"]
        states = explore_stage(stage)
        per_player = []
        for player_index, player in roster.items():
            if not player["playable"]:
                continue
            signatures = set()
            reason_union = {}
            for state_index, state in enumerate(states):
                values, reasons = state_set(stage, player_index, state)
                signature = tuple(sorted(asset_key(*item) for item in values))
                signatures.add(signature)
                reason_union.update(reasons)
                exact_states.append({"stage": stage_key, "player": player["converted_prefix"], "state_index": state_index, "assets": list(signature), "asset_reasons": reasons})
            per_player.append(set().union(*(set(signature) for signature in signatures)))
            candidates[f"B:{stage_key}:{player['converted_prefix']}"] = {"strategy": "B", "stages": [stage_key], "players": [player["converted_prefix"]], "combinations": [{"stage": stage_key, "player": player["converted_prefix"]}], "assets": sorted(set().union(*(set(signature) for signature in signatures))), "asset_reasons": reason_union}
        a_assets = set().union(*per_player) if per_player else set()
        a_reasons = {}
        for row in candidates.values():
            if row["stages"] == [stage_key]:
                a_reasons.update(row.get("asset_reasons", {}))
        candidates[f"A:{stage_key}"] = {"strategy": "A", "stages": [stage_key], "players": ["all"], "combinations": [{"stage": stage_key, "player": "all"}], "assets": sorted(a_assets), "asset_reasons": a_reasons}
    expected = len(STAGE_CONFIGS) * (1 + sum(entry["playable"] for entry in ROSTER_CONFIGS))
    if len(candidates) != expected:
        raise SystemExit(f"runtime-derived A/B candidate formula mismatch: {len(candidates)} != {expected}")

    def dedupe(rows):
        unique = {}
        for row in rows:
            signature = tuple(row["assets"])
            record = unique.setdefault(signature, {**row, "stages": [], "players": [], "combinations": []})
            record["stages"] = sorted(set(record["stages"] + row.get("stages", [])))
            record["players"] = sorted(set(record["players"] + row.get("players", [])))
            record["combinations"].extend(row.get("combinations", []))
        return list(unique.values())

    def compile_one(row):
        command = [sys.executable, str(ROOT / "tools/audio/compile_reachable_sfx.py")]
        for item in row["assets"]:
            command += ["--asset", item]
        result = subprocess.run(command, capture_output=True, text=True)
        output = result.stdout + result.stderr
        common = next((int(line.split()[2]) for line in output.splitlines() if line.startswith("compiled common-data:")), None)
        overflow = None
        if "too large" in output:
            numbers = re.findall(r"\d+", output.split("too large", 1)[1])
            if len(numbers) >= 2:
                overflow = {"required_common_bytes": int(numbers[0]), "max_common_bytes": int(numbers[1])}
        return {"compile_pass": result.returncode == 0, "compiled_common_bytes": common, "overflow": overflow, "compile_diagnostic": output[-700:] if result.returncode else None}

    ab_rows = dedupe(candidates.values())
    c_unique = {}
    for row in exact_states:
        signature = tuple(row["assets"])
        record = c_unique.setdefault(signature, {**row, "user_count": 0, "example_users": []})
        record["user_count"] += 1
        if len(record["example_users"]) < 3:
            record["example_users"].append({"stage": row["stage"], "player": row["player"], "state_index": row["state_index"]})
    ab_results = [{**row, **compile_one(row)} for row in ab_rows]
    c_results = [] if args.ab_only else [{**row, **compile_one(row)} for row in c_unique.values()]
    output = {"schema_version": 5, "source": "committed packed 10-byte spawn tables and runtime lifecycle model", "candidate_count": len(candidates), "unique_set_count": len(ab_results), "strategy_a_count": len(STAGE_CONFIGS), "strategy_b_count": len(candidates) - len(STAGE_CONFIGS), "strategy_a_b_results": ab_results, "strategy_c_state_count": len(exact_states), "strategy_c_unique_set_count": len(c_results), "strategy_c_results": c_results, "strategy_c_compile_skipped": args.ab_only, "max_non_player_slots": 3}
    (ROOT / "tools/audio/sfx_residency.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    passed = [row["compiled_common_bytes"] for row in ab_results if row["compile_pass"]]
    cpassed = [row["compiled_common_bytes"] for row in c_results if row["compile_pass"]]
    print(f"runtime residency: {len(candidates)} A/B combinations, {len(ab_results)} unique sets; A/B passing {len(passed)}")
    print(f"runtime states: {len(exact_states)} exact states, {len(c_results)} unique signatures; C passing {len(cpassed)}")
    if cpassed:
        print(f"C common-data range: {min(cpassed)}..{max(cpassed)} bytes; smallest margin: {CAPACITY - max(cpassed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
