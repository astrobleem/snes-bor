#!/usr/bin/env python3
"""Derive executable action-level SFX requirements from source/moveset data.

This is an evidence planner, not a runtime loader. It deliberately maps only
animations selected by the converted role table; source animations which the
SNES runtime cannot select are not promoted into an action bank.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter")]
from pak_extract import extract, read_entries  # noqa: E402
from entity_parse import parse_entity  # noqa: E402
from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS, source_character_identity  # noqa: E402


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
            if not isinstance(ordinal, int):
                continue
            anim_name = role_by_ordinal.get(ordinal)
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
    signatures = {}
    for model in models:
        for action in model["actions"]:
            values = set(action["frame_sound_ids"])
            if model["diesound"]:
                values.add(model["diesound"])
            signature = tuple(sorted(values))
            signatures.setdefault(signature, []).append({"identity": model["identity"], "role": action["role"]})
    output = {
        "schema_version": 1,
        "source": "authoritative entity parser plus converted moveset role table",
        "input_hash": hashlib.sha256(json.dumps(models, sort_keys=True).encode()).hexdigest(),
        "models": models,
        "required_signature_count": len(signatures),
        "signatures": [{"assets": list(s), "users": users} for s, users in sorted(signatures.items())],
    }
    path = ROOT / "tools/audio/action_residency.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"action residency: {len(models)} models, {len(signatures)} executable signatures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
