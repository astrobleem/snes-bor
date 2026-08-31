#!/usr/bin/env python3
"""Derive executable action-level SFX requirements from source/moveset data.

This is an evidence planner, not a runtime loader. It deliberately maps only
animations selected by the converted role table; source animations which the
SNES runtime cannot select are not promoted into an action bank.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter")]
from pak_extract import extract, read_entries  # noqa: E402
from entity_parse import parse_entity  # noqa: E402
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS  # noqa: E402


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


def main() -> int:
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
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
        entity_path = source_entry(pak, identity)
        entity = parse_entity(extract(str(pak), entity_path).decode("latin1"))
        moveset_path = ROOT / (entry["converted_prefix"] + "_moveset.json")
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
            assets = []
            for frame in anim.get("frames", []):
                sound = frame.get("sound")
                if sound:
                    sound = norm(sound)
                    k = key(family, sound if sound.startswith("DATA\\") else "DATA\\" + sound)
                    if k in reachable:
                        assets.append(k)
            actions.append({"role": role, "animation": anim_name, "frame_sound_ids": sorted(set(assets))})
        die = entity.get("diesound")
        if die:
            die = norm(die)
            die_key = key(family, die if die.startswith("DATA\\") else "DATA\\" + die)
        else:
            die_key = None
        if die_key not in reachable:
            die_key = None
        models.append({"family": family, "identity": identity, "playable": entry["playable"], "source_file": norm(entity_path), "diesound": die_key, "actions": actions})
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

    def model_action_options(model):
        options = {tuple()}
        for action in model["actions"]:
            values = set(action["frame_sound_ids"])
            role = action["role"]
            if role in ("attack", "attack2", "attack3", "attack4", "upper", "grabattack"):
                values |= global_assets.get((model["family"], "attack-swing"), set())
            if role in ("jump", "jumpattack", "jumpattack2"):
                values |= global_assets.get((model["family"], "jump"), set())
            options.add(tuple(sorted(values)))
        return sorted(options)

    options_by_identity = {m["identity"]: model_action_options(m) for m in models}
    model_by_identity = {m["identity"]: m for m in models}
    combined = set()
    combined_users = {}
    transition = set()
    for stage in STAGE_CONFIGS:
        family = stage["family"]
        base = set()
        for event in ("pause-entry", "ui-beep", "ui-beep-secondary", "landed-hit"):
            base |= global_assets.get((family, event), set())
        for player in (m for m in models if m["playable"]):
            states = __import__("runtime_sfx_states").explore_stage(stage)
            state_contexts = set()
            for state in states:
                identities = tuple(slot["roster_index"] for slot in state["slots"] if slot["alive"])
                state_contexts.add(identities)
            for identities in state_contexts:
                slot_models = []
                for index in identities:
                    if 0 <= index < len(ROSTER_CONFIGS):
                        ident = ROSTER_CONFIGS[index]["source_character"].split("\\CHARS\\", 1)[1].upper()
                        slot_models.append(options_by_identity.get(ident, [tuple()]))
                player_options = options_by_identity.get(player["identity"], [tuple()])
                for choices in itertools.product(player_options, *(slot_models[:3])):
                    values = set(base)
                    for choice in choices:
                        values.update(choice)
                    signature = tuple(sorted(values))
                    combined.add(signature)
                    combined_users.setdefault(signature, {"stage": stage["source_level"], "player": player["identity"], "slot_identities": list(identities)})
                for index in identities:
                    if 0 <= index < len(ROSTER_CONFIGS):
                        ident = ROSTER_CONFIGS[index]["source_character"].split("\\CHARS\\", 1)[1].upper()
                        die = model_by_identity.get(ident, {}).get("diesound")
                        if die:
                            transition.add(tuple(sorted(base | {die})))
    output = {
        "schema_version": 2,
        "source": "authoritative entity parser plus converted moveset role table",
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
    raise SystemExit(main())
