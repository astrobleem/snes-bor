#!/usr/bin/env python3
"""Derive executable action-level SFX requirements from source/moveset data.

This is an evidence planner, not a runtime loader. It deliberately maps only
animations selected by the converted role table; source animations which the
SNES runtime cannot select are not promoted into an action bank.
"""
from __future__ import annotations

import hashlib
import argparse
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter")]
from pak_extract import extract, read_entries  # noqa: E402
from entity_parse import parse_entity  # noqa: E402
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS  # noqa: E402
from generate_audio_manifest import PAK_ALIASES  # noqa: E402


def norm(value: str) -> str:
    return value.replace("/", "\\").upper()


def key(family: str, path: str) -> str:
    return f"{family}:{norm(path)}"


def source_entry(pak: Path, identity: str) -> str:
    target = "DATA\\CHARS\\" + identity.upper()
    names = [e.name for e in read_entries(str(pak))]
    exact = target + ".TXT"
    for name in names:
        if norm(name) == exact:
            return name
    for name in names:
        if norm(name).startswith(target + "\\") and norm(name).endswith(".TXT"):
            return name
    raise ValueError(f"no entity source for {pak.name}:{identity}")


def main(runtime_actions: bool = False, output_path: Path | None = None) -> int:
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    manifest_hash = hashlib.sha256((ROOT / "tools/audio/audio_manifest.json").read_bytes()).hexdigest()
    global_ids_path = ROOT / "tools/audio/sfx_global_ids.json"
    runtime_summary_path = ROOT / "tools/audio/runtime_sfx_states.json"
    reachable = {}
    for family in manifest["families"]:
        for asset in family["assets"]:
            if asset["kind"] == "sfx" and asset["shipped_reachable"]:
                reachable[key(family["family"], asset["source_path"])] = asset
    models = []
    for entry in ROSTER_CONFIGS:
        family = entry["family"]
        identity = entry["source_character"].split("\\CHARS\\", 1)[1].upper()
        pak = ROOT / next(s["pak"] for s in STAGE_CONFIGS if s["family"] == family)
        entity_path = entry.get("source_definition") or source_entry(pak, identity)
        entity = parse_entity(extract(str(pak), entity_path).decode("latin1"))
        moveset_path = ROOT / (entry["converted_prefix"] + "_moveset.json")
        if runtime_actions and not moveset_path.exists():
            raise SystemExit(f"FAIL: missing action input {moveset_path}")
        moveset = json.loads(moveset_path.read_text(encoding="utf-8")) if moveset_path.exists() else {"roles": {}}
        role_by_ordinal = {a["ordinal"]: a["name"] for a in moveset.get("animations", [])}
        actions = []
        for role, ordinal in moveset.get("roles", {}).items():
            # bool is an int subclass, but attack2_is_grab and similar fields
            # are metadata, never animation ordinals.
            if type(ordinal) is not int:
                continue
            anim_name = role_by_ordinal.get(ordinal)
            if anim_name is None:
                raise ValueError(f"{identity}: role {role} references absent animation ordinal {ordinal}")
            anim = entity["animations"].get(anim_name, {})
            if runtime_actions and anim_name not in entity["animations"]:
                # convert_prop.py copies the real idle animation to satisfy
                # the packed role ABI; these names are not source animations.
                if identity.startswith("MISC\\") and anim_name in ("walk", "attack", "fall", "rise"):
                    anim = entity["animations"]["idle"]
                else:
                    raise SystemExit(f"FAIL: {identity}: selected animation {anim_name} absent from source")
            assets = []
            for frame in anim.get("frames", []):
                sound = frame.get("sound")
                if sound:
                    sound = norm(sound)
                    sound = sound if sound.startswith("DATA\\") else "DATA\\" + sound
                    k = key(family, PAK_ALIASES.get((family, sound), sound))
                    if runtime_actions and k not in reachable:
                        raise SystemExit(f"FAIL: {identity}/{role}: required sound absent from reachable manifest: {k}")
                    if k in reachable:
                        assets.append(k)
            actions.append({"role": role, "animation": anim_name, "frame_sound_ids": sorted(set(assets))})
        die = entity.get("diesound")
        if die:
            die = norm(die)
            die = die if die.startswith("DATA\\") else "DATA\\" + die
            die_key = key(family, PAK_ALIASES.get((family, die), die))
        else:
            die_key = None
        if runtime_actions and die_key and die_key not in reachable:
            raise SystemExit(f"FAIL: {identity}: diesound absent from reachable manifest: {die_key}")
        if die_key not in reachable:
            die_key = None
        models.append({"family": family, "identity": identity, "playable": entry["normal_player_selectable"] if runtime_actions else entry["playable"], "source_file": norm(entity_path), "diesound": die_key, "actions": actions})
    # The diesound is a transition requirement, not an ordinary action
    # requirement. Keep both inventories so an idle/attack bank is not
    # needlessly charged for a future death transition.
    action_signatures = {}
    transition_signatures = {}
    for model in models:
        for action in model["actions"]:
            values = set(action["frame_sound_ids"])
            signature = tuple(sorted(values))
            action_signatures.setdefault(signature, []).append({"identity": model["identity"], "role": action["role"]})
        if model["diesound"]:
            transition_signatures.setdefault((model["diesound"],), []).append({"identity": model["identity"], "transition": "lethal"})

    # Family-owned immediate globals are included in combined requirements.
    # Attack/jump globals are action-specific and are added only to matching
    # roles; this avoids double-counting explicit frame sounds as a second
    # event while retaining source-backed engine semantics.
    global_assets = {}
    for family in manifest["families"]:
        for asset in family["assets"]:
            if not asset["shipped_reachable"]:
                continue
            for ref in asset["references"]:
                if ref.get("directive") == "engine-global-default" and ref.get("snes_reachable"):
                    global_assets.setdefault((family["family"], ref["semantic_event"]), set()).add(key(family["family"], asset["source_path"]))

    if runtime_actions:
        # This inventory is independent of spawn order and slot count. It owns
        # individual action/event coverage, never concurrent bank residency.
        requirements = []
        for model in models:
            owner = model["family"] + ":" + model["identity"]
            for action in model["actions"]:
                requirements.append({"owner": owner, "event": action["role"],
                                     "assets": action["frame_sound_ids"]})
            if model["diesound"]:
                requirements.append({"owner": owner, "event": "diesound",
                                     "assets": [model["diesound"]]})
        for (family, event), assets in sorted(global_assets.items()):
            requirements.append({"owner": family + ":engine", "event": event,
                                 "assets": sorted(assets)})
        required = sorted({asset for row in requirements for asset in row["assets"]})
        output = {
            "schema_version": 1,
            "scope": "source action/event coverage; no concurrent residency claim",
            "manifest_hash": manifest_hash,
            "global_ids_hash": hashlib.sha256(global_ids_path.read_bytes()).hexdigest(),
            "models": models,
            "requirements": requirements,
            "source_hashes": {asset: reachable[asset]["source_hash"] for asset in required},
        }
        path = output_path or ROOT / "tools/audio/runtime_action_requirements.json"
        path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        print(f"runtime action inventory: {len(models)} models, {len(requirements)} requirements, {len(required)} assets; no explorer dependency")
        return 0

    def model_action_options(model, context_family):
        options = {tuple()}
        for action in model["actions"]:
            values = set(action["frame_sound_ids"])
            role = action["role"]
            if role in ("attack", "attack2", "attack3", "attack4", "upper", "grabattack"):
                values |= global_assets.get((context_family, "attack-swing"), set())
            if role in ("jump", "jumpattack", "jumpattack2"):
                values |= global_assets.get((context_family, "jump"), set())
            options.add(tuple(sorted(values)))
        return sorted(options)

    model_by_identity = {m["identity"]: m for m in models}
    combined = set()
    combined_users = {}
    transition = set()
    states_by_stage = {
        stage["family"] + ":" + stage["source_level"]: __import__("runtime_sfx_states").explore_stage(stage)
        for stage in STAGE_CONFIGS
    }
    projected_by_stage = {}
    for stage in STAGE_CONFIGS:
        stage_key = stage["family"] + ":" + stage["source_level"]
        projected_by_stage[stage_key] = {
            tuple((slot["alive"], slot["roster_index"], slot["prop"],
                   slot["pickup_type"], slot["contained_item_roster_index"])
                  for slot in state["slots"])
            for state in states_by_stage[stage_key]
        }
    for stage in STAGE_CONFIGS:
        family = stage["family"]
        options_by_identity = {m["identity"]: model_action_options(m, family) for m in models}
        always_resident_global_requirements = set()
        for event in ("pause-entry", "ui-beep", "ui-beep-secondary", "landed-hit"):
            always_resident_global_requirements |= global_assets.get((family, event), set())
        stage_key = stage["family"] + ":" + stage["source_level"]
        state_contexts = projected_by_stage[stage_key]
        for player in (m for m in models if m["playable"]):
            for context in state_contexts:
                identities = [slot[1] for slot in context if slot[0]]
                slot_models = []
                for index in identities:
                    if 0 <= index < len(ROSTER_CONFIGS):
                        ident = ROSTER_CONFIGS[index]["source_character"].split("\\CHARS\\", 1)[1].upper()
                        slot_models.append(options_by_identity.get(ident, [tuple()]))
                player_options = options_by_identity.get(player["identity"], [tuple()])
                for choices in itertools.product(player_options, *(slot_models[:3])):
                    values = set(always_resident_global_requirements)
                    for choice in choices:
                        values.update(choice)
                    signature = tuple(sorted(values))
                    combined.add(signature)
                    combined_users.setdefault(signature, {"stage": stage["source_level"], "player": player["identity"], "slot_identities": list(identities)})
                    # Every transition overlays the complete concurrent action
                    # requirement; it is never reduced to base + event.
                    transition.add(tuple(sorted(values | global_assets.get((family, "landed-hit"), set()))))
                    for ident in [player["identity"]] + [ROSTER_CONFIGS[index]["source_character"].split("\\CHARS\\", 1)[1].upper() for index in identities if 0 <= index < len(ROSTER_CONFIGS)]:
                        die = model_by_identity.get(ident, {}).get("diesound")
                        if die:
                            transition.add(tuple(sorted(values | {die})))
                    for alive, roster_index, prop, pickup_type, contained in context:
                        if not alive or not prop or not pickup_type:
                            continue
                        pickup_event = {1: "health-pickup", 2: "health-pickup", 3: "score-pickup", 4: "one-up", 5: "score-pickup"}.get(pickup_type)
                        if pickup_event:
                            transition.add(tuple(sorted(values | global_assets.get((family, pickup_event), set()))))
                    # FALL is a landing/bounce transition, not an animation role.
                    transition.add(tuple(sorted(values | global_assets.get((family, "fall"), set()))))
    output = {
        "schema_version": 2,
        "source": "authoritative entity parser plus converted moveset role table",
        "manifest_hash": manifest_hash,
        "global_ids_hash": hashlib.sha256(global_ids_path.read_bytes()).hexdigest() if global_ids_path.exists() else None,
        "runtime_summary_hash": hashlib.sha256(runtime_summary_path.read_bytes()).hexdigest(),
        "input_hash": hashlib.sha256(json.dumps(models, sort_keys=True).encode()).hexdigest(),
        "models": models,
        "action_signature_count": len(action_signatures),
        "action_signatures": [{"assets": list(s), "users": users} for s, users in sorted(action_signatures.items())],
        "transition_signature_count": len(transition_signatures),
        "transition_signatures": [{"assets": list(s), "users": users} for s, users in sorted(transition_signatures.items())],
        "combined_context_count": len(combined_users),
        "combined_signatures": [{"assets": list(s), "example": combined_users[s]} for s in sorted(combined)],
        "combined_signature_count": len(combined),
        "combined_transition_signatures": [{"assets": list(s)} for s in sorted(transition)],
    }
    path = ROOT / "tools/audio/action_residency.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"action residency: {len(models)} models, {len(action_signatures)} action signatures, {len(combined)} combined signatures, {len(transition)} transition signatures")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-actions", action="store_true",
                        help="inventory current source actions/events without legacy state exploration")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and not args.runtime_actions:
        parser.error("--output requires --runtime-actions")
    raise SystemExit(main(args.runtime_actions, args.output))
