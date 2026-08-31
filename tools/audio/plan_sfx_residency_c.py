"""Plan and compile bounded active-entity SFX residency candidates.

This is a measurement tool only. It does not select or load a runtime bank.
Candidates are derived from contiguous source spawn events and the identities
that the current packed spawn/runtime path actually represents.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools" / "audio"), str(ROOT / "tools" / "bg_converter"), str(ROOT / "tools" / "bor_converter")]
from pak_extract import extract  # noqa: E402
from spawn_parse import SpawnEvent, parse_spawns  # noqa: E402
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS  # noqa: E402


def key(family: str, path: str) -> str:
    return f"{family}:{path.upper()}"


def main() -> int:
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    all_assets = {
        (family["family"], asset["source_path"]): asset
        for family in manifest["families"]
        for asset in family["assets"]
        if asset["kind"] == "sfx"
    }
    global_by_event: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for (family, path), asset in all_assets.items():
        if not asset["shipped_reachable"]:
            continue
        for ref in asset["references"]:
            if ref.get("directive") == "engine-global-default" and ref.get("snes_reachable"):
                global_by_event.setdefault((family, ref["semantic_event"]), set()).add((family, path))

    represented = {}
    for entry in ROSTER_CONFIGS:
        identity = entry["source_character"].split("\\CHARS\\", 1)[1].upper().strip("\\")
        represented[(entry["family"], identity.rsplit("\\", 1)[-1])] = identity

    def runtime_identity(family: str, name: str) -> str | None:
        return represented.get((family, name.upper().strip("\\").rsplit("\\", 1)[-1]))

    def model_assets(family: str, identity: str) -> tuple[set[tuple[str, str]], dict[str, str]]:
        marker = "DATA\\CHARS\\" + identity.upper().strip("\\") + "\\"
        assets, reasons = set(), {}
        for (owner, path), asset in all_assets.items():
            if owner != family or not asset["shipped_reachable"]:
                continue
            if any(marker in ref.get("source_file", "").upper() and ref.get("reachability") == "shipped-reachable" for ref in asset["references"]):
                assets.add((owner, path))
                reasons[key(owner, path)] = f"represented-model:{identity}"
        return assets, reasons

    def parse_stage(stage: dict) -> tuple[list[SpawnEvent], str]:
        text = extract(ROOT / stage["pak"], stage["source_level"]).decode("latin1")
        return [event for event in parse_spawns(text) if isinstance(event, SpawnEvent)], stage["source_level"]

    def stage_static(stage: dict, events: list[SpawnEvent]) -> tuple[set[tuple[str, str]], dict[str, str]]:
        family = stage["family"]
        assets, reasons = set(), {}

        def add(values: set[tuple[str, str]], reason: str) -> None:
            for item in values:
                assets.add(item)
                reasons.setdefault(key(*item), reason)

        for event_name in ("pause-entry", "ui-beep", "ui-beep-secondary"):
            add(global_by_event.get((family, event_name), set()), f"always-available-ui:{event_name}")
        names = {name.upper() for event in events for name in (event.character, event.item) if name}
        if names & {"MONEY", "GOLD"}:
            add(global_by_event.get((family, "score-pickup"), set()), "stage-global:score-pickup")
        if names & {"APPLE", "MEAT", "PIZZA"}:
            add(global_by_event.get((family, "health-pickup"), set()), "stage-global:health-pickup")
        if "1UP" in names:
            add(global_by_event.get((family, "one-up"), set()), "stage-global:one-up")
        level = stage["source_level"].upper()
        for (owner, path), asset in all_assets.items():
            if owner == family and asset["shipped_reachable"] and any(level in ref.get("source_file", "").upper() for ref in asset["references"]):
                add({(owner, path)}, "stage-global:level-directive")
        return assets, reasons

    players = []
    for entry in ROSTER_CONFIGS:
        if not entry["playable"]:
            continue
        identity = entry["source_character"].split("\\CHARS\\", 1)[1]
        local, reasons = model_assets(entry["family"], identity)
        moveset = ROOT / (entry["converted_prefix"] + "_moveset.json")
        jump = moveset.exists() and json.loads(moveset.read_text(encoding="utf-8")).get("roles", {}).get("jump") is not None
        players.append({"prefix": entry["converted_prefix"], "family": entry["family"], "identity": identity, "local": local, "reasons": reasons, "jump": jump})

    def global_player(stage_family: str, player: dict) -> tuple[set[tuple[str, str]], dict[str, str]]:
        values, reasons = set(), {}
        for event_name in ("landed-hit", "attack-swing", "ui-beep", "ui-beep-secondary"):
            for item in global_by_event.get((stage_family, event_name), set()):
                values.add(item)
                reasons[key(*item)] = f"active-player-global:{event_name}:stage-family"
        if player["jump"]:
            for item in global_by_event.get((stage_family, "jump"), set()):
                values.add(item)
                reasons[key(*item)] = "active-player-global:jump:stage-family"
        return values, reasons

    candidates = []
    for stage in STAGE_CONFIGS:
        events, source_level = parse_stage(stage)
        static, static_reasons = stage_static(stage, events)
        represented_events = []
        for event in events:
            identities = []
            for name in (event.character, event.item):
                if name and (identity := runtime_identity(stage["family"], name)):
                    identities.append(identity)
            represented_events.append((event, identities))
        windows = {(): []}
        for index in range(len(represented_events)):
            for width in (1, 2, 3):
                window = represented_events[index:index + width]
                identities = tuple(sorted({identity for _, names in window for identity in names}))
                if identities:
                    windows[identities] = window
        for player in players:
            player_globals, player_global_reasons = global_player(stage["family"], player)
            for identities, window in windows.items():
                assets = set(static) | player["local"] | player_globals
                reasons = dict(static_reasons) | player["reasons"] | player_global_reasons
                for identity in identities:
                    model, model_reasons = model_assets(stage["family"], identity)
                    assets |= model
                    reasons.update({asset: f"active-entity:{identity}:model-local" for asset in model_reasons})
                users = [{"stage": stage["family"] + ":" + source_level, "player": player["prefix"], "entities": list(identities)}]
                candidates.append({"strategy": "C", "users": users, "assets": sorted(key(*item) for item in assets), "asset_reasons": reasons})

    unique = {}
    for candidate in candidates:
        signature = tuple(candidate["assets"])
        record = unique.setdefault(signature, {**candidate, "users": []})
        record["users"].extend(candidate["users"])

    results = []
    for signature, candidate in unique.items():
        cmd = [sys.executable, str(ROOT / "tools/audio/compile_reachable_sfx.py")]
        for asset in signature:
            cmd += ["--asset", asset]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        common = next((int(line.split()[2]) for line in output.splitlines() if line.startswith("compiled common-data:")), None)
        overflow = None
        match = re.search(r"common audio data is too large \((\d+) bytes, max: (\d+) bytes\)", output)
        if match:
            overflow = {"required_common_bytes": int(match.group(1)), "max_common_bytes": int(match.group(2))}
        results.append({**candidate, "compile_pass": result.returncode == 0, "compiled_common_bytes": common, "overflow": overflow, "compile_diagnostic": output[-700:] if result.returncode else None})

    out = {"schema_version": 1, "strategy": "C", "candidate_count": len(candidates), "unique_set_count": len(results), "results": results}
    (ROOT / "tools/audio/sfx_residency_c.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    passing = [row["compiled_common_bytes"] for row in results if row["compile_pass"]]
    print(f"Strategy C candidates: {len(candidates)} configurations, {len(results)} unique sets")
    print(f"compiled passing sets: {len(passing)}")
    if passing:
        print(f"common-data range: {min(passing)}..{max(passing)} bytes; smallest margin: {60828 - max(passing)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
