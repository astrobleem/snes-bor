"""Derive normal-player scope from the shipped PAK model configuration."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/bor_converter"), str(ROOT / "tools/audio")]
from pak_extract import extract
from shipped_content import ROSTER_CONFIGS, SOURCE_PLAYER_SELECTION

PAKS = {
    "bor-original": ROOT / "Beats of Rage Original [v.3.0 Build 4086].pak",
    "tmnt": ROOT / "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak",
}


def parse_models(pak: Path):
    raw = extract(pak, "DATA\\MODELS.TXT")
    text = raw.decode("latin1").replace("\r", "")
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        if len(fields) >= 3 and fields[0].lower() in {"load", "know"}:
            rows.append({"directive": fields[0].lower(), "name": fields[1], "path": fields[2]})
    return raw, rows


def model_type(pak: Path, path: str):
    raw = extract(pak, path.replace("/", "\\"))
    match = re.search(rb"(?mi)^\s*type\s+(\S+)", raw)
    return match.group(1).decode("latin1").lower() if match else None


def main():
    families = []
    for family, pak in PAKS.items():
        raw, models = parse_models(pak)
        normal = SOURCE_PLAYER_SELECTION[family]["normal"]
        source_names = SOURCE_PLAYER_SELECTION[family].get("source_names", {})
        source_rows = []
        for row in models:
            source_rows.append({
                **row,
                "model_type": model_type(pak, row["path"]),
                "normal_player": row["directive"] == "load" and source_names.get(row["name"].upper(), row["name"].upper()) in normal,
            })
        runtime = []
        for entry in ROSTER_CONFIGS:
            if entry["family"] != family:
                continue
            identity = entry["source_character"].split("\\CHARS\\", 1)[1].upper()
            source = next((x for x in source_rows if x["name"].upper() == identity), None)
            runtime.append({
                "character": identity,
                "runtime_roster_member": entry["runtime_roster_member"],
                "ai_spawnable": entry["ai_spawnable"],
                "normal_player": entry["normal_player_selectable"],
                "optional_bonus_player": entry["optional_bonus_player"],
                "source_model": source,
            })
        families.append({
            "family": family,
            "pak": pak.name,
            "pak_sha256": hashlib.sha256(pak.read_bytes()).hexdigest(),
            "models_path": "DATA\\MODELS.TXT",
            "models_sha256": hashlib.sha256(raw).hexdigest(),
            "source_rows": source_rows,
            "runtime_rows": runtime,
        })
    output = {
        "schema_version": 1,
        "source_of_truth": "PAK DATA\\MODELS.TXT and referenced model type directives",
        "families": families,
    }
    out = ROOT / "tools/audio/player_scope_evidence.json"
    out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for family in families:
        print(f"{family['family']}: normal source players = " + ", ".join(x["name"] for x in family["source_rows"] if x["normal_player"]))
        for row in family["runtime_rows"]:
            print(f"  {row['character']}: normal={row['normal_player']} ai={row['ai_spawnable']} bonus={row['optional_bonus_player']}")


if __name__ == "__main__":
    main()
