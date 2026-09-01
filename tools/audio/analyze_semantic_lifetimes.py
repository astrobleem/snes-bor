"""Compile source-canonical SFX working sets by semantic lifetime."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter"), str(ROOT / "soundwork/tad")]
from entity_parse import parse_entity
from pak_extract import extract
from production_compile import compile_production_sfx_set
from shipped_content import STAGE_CONFIGS

CAPACITY = 60828
PLAYERS = [
    {"family": "bor-original", "name": "Kula", "path": r"DATA\CHARS\KULA\KULA.TXT", "runtime_represented": False},
    {"family": "bor-original", "name": "Max", "path": r"DATA\CHARS\MAXIMA\MAXIMA.TXT", "runtime_represented": False},
    {"family": "bor-original", "name": "Mandy", "path": r"DATA\CHARS\MARY\MARY.TXT", "runtime_represented": False},
    {"family": "bor-original", "name": "Mighty", "path": r"DATA\CHARS\MIGHTY\MIGHTY.TXT", "runtime_represented": False},
    {"family": "tmnt", "name": "Leo", "path": r"DATA\CHARS\LEO\LEO.TXT", "runtime_represented": True},
]
PAKS = {
    "bor-original": ROOT / "Beats of Rage Original [v.3.0 Build 4086].pak",
    "tmnt": ROOT / "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak",
}
ALWAYS_GLOBAL_EVENTS = {"landed-hit", "attack-swing", "jump", "fall"}
CONDITIONAL_GLOBAL_EVENTS = {"health-pickup", "score-pickup", "one-up"}
UI_GLOBAL_EVENTS = {"pause-entry", "ui-beep", "ui-beep-secondary"}
PLAYER_CONDITIONAL_ACTION_ANIMS = {"throw", "grabattack"}
PLAYER_PICKUP_ANIMS = {"get"}
HEALTH_ITEMS = {"APPLE", "MEAT", "PIZZA"}
SCORE_ITEMS = {"MONEY", "GOLD"}
ONEUP_ITEMS = {"1UP"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def norm_path(value):
    return value.replace("/", "\\").upper()


def asset_key(family, path):
    return f"{family}:{norm_path(path)}"


def parse_models(pak):
    rows = {}
    raw = extract(pak, r"DATA\MODELS.TXT").decode("latin1", "replace")
    for line in raw.splitlines():
        tokens = line.split()
        if tokens and not line.lstrip().startswith("#") and len(tokens) >= 3 and tokens[0].lower() in {"load", "know"}:
            rows[tokens[1].upper()] = tokens[2].replace("/", "\\")
    entities = {}
    aliases = {}
    for name, path in rows.items():
        try:
            entity = parse_entity(extract(pak, path).decode("latin1", "replace"))
        except KeyError:
            continue
        entities[name] = (path, entity)
        if entity.get("name"):
            aliases[str(entity["name"]).upper()] = name
    return rows, entities, aliases


def parse_level(pak, level_path, model_rows, aliases):
    text = extract(pak, level_path).decode("latin1", "replace")
    epochs = [[]]
    current = None
    unresolved = []
    for line_number, raw in enumerate(text.splitlines(), 1):
        tokens = raw.split()
        if not tokens or raw.lstrip().startswith("#"):
            continue
        directive = tokens[0].lower()
        if directive == "spawn" and len(tokens) > 1:
            source_name = tokens[1].upper()
            resolved = source_name if source_name in model_rows else aliases.get(source_name)
            if resolved is None and source_name.startswith("FOOT") and source_name[4:].isdigit():
                resolved = f"FOOT{int(source_name[4:]):02d}"
            current = {"source_name": source_name, "model_name": resolved, "boss": False, "item": None, "line": line_number}
            epochs[-1].append(current)
            if resolved is None:
                unresolved.append({"name": source_name, "line": line_number})
        elif directive == "boss" and current is not None and len(tokens) > 1:
            current["boss"] = int(tokens[1]) != 0
        elif directive == "item" and current is not None and len(tokens) > 1:
            current["item"] = tokens[1].upper()
        elif directive == "wait":
            epochs.append([])
            current = None
    return [epoch for epoch in epochs if epoch], unresolved


def main():
    manifest_path = ROOT / "tools/audio/audio_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_assets = {}
    requested = {}
    global_events = defaultdict(set)
    for family in manifest["families"]:
        fam = family["family"]
        for asset in family["assets"]:
            if asset["kind"] != "sfx":
                continue
            key = asset_key(fam, asset["source_path"])
            manifest_assets[key] = asset
            requested[(fam, norm_path(asset["source_path"]))] = key
            for ref in asset.get("references", []):
                req = ref.get("requested_source_path")
                if req:
                    requested[(fam, norm_path(req))] = key
                if ref.get("directive") == "engine-global-default":
                    global_events[(fam, ref.get("semantic_event"))].add(key)

    def resolve(family, path):
        key = requested.get((family, norm_path(path)))
        if key is None:
            raise KeyError(f"unresolved SFX {family}:{path}")
        return key

    set_cache = {}
    asset_metadata = {}

    def compile_set(values):
        signature = tuple(sorted(set(values)))
        if signature in set_cache:
            return set_cache[signature]
        if not signature:
            row = {"common_data_bytes": 0, "common_data_sha256": None, "sample_count": 0, "effect_count": 0, "brr_sample_bytes": 0, "non_sample_common_bytes": 0, "compiler_version": None, "assets": [], "margin": CAPACITY}
            set_cache[signature] = row
            return row
        try:
            result = compile_production_sfx_set(ROOT, signature, policy_name="baseline", allow_source_canonical=True)
            row = {k: result[k] for k in ("common_data_bytes", "common_data_sha256", "sample_count", "effect_count", "brr_sample_bytes", "non_sample_common_bytes", "compiler_version")}
            for effect in result["effects"]:
                asset_metadata[effect["asset"]] = effect
        except RuntimeError as exc:
            match = re.search(r"too large \((\d+) bytes, max: (\d+)\)", str(exc))
            if not match:
                raise
            for value in signature:
                if value not in asset_metadata:
                    compile_set([value])
            identities = {}
            effects = set()
            for value in signature:
                metadata = asset_metadata[value]
                identities.setdefault(metadata["sample_identity"], ((metadata["source_frames"] + 15) // 16) * 9)
                effects.add(metadata["effect_identity"])
            brr = sum(identities.values())
            total = int(match.group(1))
            row = {"common_data_bytes": total, "common_data_sha256": None, "sample_count": len(identities), "effect_count": len(effects), "brr_sample_bytes": brr, "non_sample_common_bytes": total - brr, "compiler_version": None, "compile_error": str(exc).strip()}
        row["assets"] = list(signature)
        row["margin"] = CAPACITY - row["common_data_bytes"]
        set_cache[signature] = row
        return row

    for key in manifest_assets:
        if manifest_assets[key].get("shipped_reachable"):
            compile_set([key])

    global_sets = {}
    for family in PAKS:
        global_sets[family] = {
            "always": set().union(*(global_events[(family, event)] for event in ALWAYS_GLOBAL_EVENTS)),
            "conditional": set().union(*(global_events[(family, event)] for event in CONDITIONAL_GLOBAL_EVENTS)),
            "ui": set().union(*(global_events[(family, event)] for event in UI_GLOBAL_EVENTS)),
        }

    player_rows = []
    player_sets = {}
    lifetime_rows = {}
    for player in PLAYERS:
        family = player["family"]
        entity = parse_entity(extract(PAKS[family], player["path"]).decode("latin1", "replace"))
        classes = {"always_unpredictable_combat": set(global_sets[family]["always"]), "conditional_action": set(), "conditional_pickup": set(global_sets[family]["conditional"]), "terminal": set(), "ui_global": set(global_sets[family]["ui"])}
        evidence = defaultdict(list)
        if entity.get("diesound"):
            key = resolve(family, entity["diesound"])
            classes["terminal"].add(key)
            evidence[key].append({"event": "player death", "lifetime": "terminal", "source": player["path"] + ":diesound", "precondition": "player HP reaches zero", "first_possible_use": "lethal player transition", "last_possible_use": "death transition completes"})
        for anim_name, anim in entity["animations"].items():
            for frame_index, frame in enumerate(anim["frames"]):
                if not frame.get("sound"):
                    continue
                key = resolve(family, frame["sound"])
                category = "conditional_pickup" if anim_name.lower() in PLAYER_PICKUP_ANIMS else ("conditional_action" if anim_name.lower() in PLAYER_CONDITIONAL_ACTION_ANIMS else "always_unpredictable_combat")
                event = f"player {anim_name} frame sound"
                precondition = "pickup/get state active" if category == "conditional_pickup" else ("grab/throw state active" if category == "conditional_action" else "source player action is executable")
                classes[category].add(key)
                evidence[key].append({"event": event, "lifetime": category, "source": f"{player['path']}:anim {anim_name} frame {frame_index}", "precondition": precondition, "first_possible_use": f"entry to {anim_name} sound frame", "last_possible_use": f"{anim_name} exits"})
        for category, values in global_sets[family].items():
            target = "always_unpredictable_combat" if category == "always" else ("ui_global" if category == "ui" else "conditional_pickup")
            for key in values:
                for event in sorted(e for (fam, e), assets in global_events.items() if fam == family and key in assets):
                    evidence[key].append({"event": event, "lifetime": target, "source": "OpenBOR engine global/default", "precondition": event, "first_possible_use": event, "last_possible_use": "event completes"})
        full = set().union(*classes.values())
        ordinary = classes["always_unpredictable_combat"] | classes["conditional_action"] | classes["ui_global"]
        rows = {
            "full_capability_union": compile_set(full),
            "ordinary_combat": compile_set(ordinary),
            "conditional_action_only": compile_set(classes["conditional_action"]),
            "conditional_pickup_only": compile_set(classes["conditional_pickup"]),
            "conditional_pickup_environment": compile_set(ordinary | classes["conditional_pickup"]),
            "terminal_only": compile_set(classes["terminal"]),
            "terminal_environment": compile_set(classes["ui_global"] | classes["terminal"]),
        }
        player_key = f"{family}:{player['name']}"
        player_sets[player_key] = {**classes, "full": full, "ordinary": ordinary}
        for key in full:
            metadata = asset_metadata.get(key)
            if metadata is None:
                compile_set([key])
                metadata = asset_metadata[key]
            lifetime_rows[(player_key, key)] = {"asset": key, "brr_bytes": ((metadata["source_frames"] + 15) // 16) * 9, "sample_rate_hz": metadata["sample_rate_hz"], "source_frames": metadata["source_frames"], "duration_seconds": metadata["duration_seconds"], "duration_ticks": metadata["duration_ticks"], "canonical_pcm_hash": metadata["canonical_pcm_hash"], "sample_identity": metadata["sample_identity"], "effect_identity": metadata["effect_identity"], "evidence": evidence[key]}
        player_rows.append({**player, "classes": {k: sorted(v) for k, v in classes.items()}, "assets": sorted((lifetime_rows[(player_key, key)] for key in full), key=lambda x: (-x["brr_bytes"], x["asset"])), "compiled_sets": rows})

    family_models = {family: parse_models(pak) for family, pak in PAKS.items()}
    contexts = []
    for stage in STAGE_CONFIGS:
        family = stage["family"]
        model_rows, entities, aliases = family_models[family]
        epochs, unresolved = parse_level(PAKS[family], stage["source_level"], model_rows, aliases)
        for player in [p for p in PLAYERS if p["family"] == family]:
            psets = player_sets[f"{family}:{player['name']}"]
            stage_all = set(psets["full"])
            stage_combat = set(psets["ordinary"])
            boss_terminal = set(global_sets[family]["ui"])
            conditional_world = set(psets["ordinary"])
            actor_rows = []
            epoch_sets = []
            for epoch_index, epoch in enumerate(epochs):
                epoch_combat = set(psets["ordinary"])
                epoch_conditional = set(psets["ordinary"])
                epoch_actors = []
                for spawn in epoch:
                    model_name = spawn["model_name"]
                    if model_name is None or model_name not in entities:
                        continue
                    path, entity = entities[model_name]
                    kind = str(entity.get("type") or "unknown").lower()
                    frame_assets = {resolve(family, frame["sound"]) for anim in entity["animations"].values() for frame in anim["frames"] if frame.get("sound")}
                    death_assets = {resolve(family, entity["diesound"])} if entity.get("diesound") else set()
                    stage_all |= frame_assets | death_assets
                    if kind == "enemy":
                        epoch_combat |= frame_assets
                        stage_combat |= frame_assets
                        if spawn["boss"]:
                            boss_terminal |= death_assets
                        else:
                            epoch_combat |= death_assets
                            stage_combat |= death_assets
                    elif kind in {"obstacle", "item", "panel", "none"}:
                        epoch_conditional |= frame_assets | death_assets
                        conditional_world |= frame_assets | death_assets
                    item = spawn.get("item")
                    pickup_kind = item or (spawn["source_name"] if kind == "item" else None)
                    if pickup_kind in HEALTH_ITEMS:
                        epoch_conditional |= global_events[(family, "health-pickup")]
                        epoch_conditional |= psets["conditional_pickup"]
                    elif pickup_kind in SCORE_ITEMS:
                        epoch_conditional |= global_events[(family, "score-pickup")]
                        epoch_conditional |= psets["conditional_pickup"]
                    elif pickup_kind in ONEUP_ITEMS:
                        epoch_conditional |= global_events[(family, "one-up")]
                        epoch_conditional |= psets["conditional_pickup"]
                    conditional_world |= epoch_conditional
                    epoch_actors.append({"source_name": spawn["source_name"], "model_name": model_name, "model_path": path, "type": kind, "boss": spawn["boss"], "item": item, "frame_assets": sorted(frame_assets), "frame_lifetime": "encounter-local active combat" if kind == "enemy" else "conditional object lifetime", "death_assets": sorted(death_assets), "death_lifetime": "terminal boss transition" if spawn["boss"] else ("encounter-local active combat" if kind == "enemy" else "conditional object lifetime")})
                    actor_rows.append(epoch_actors[-1])
                stage_all |= epoch_conditional
                epoch_sets.append({"epoch": epoch_index, "actors": epoch_actors, "ordinary_combat": compile_set(epoch_combat), "conditional_environment": compile_set(epoch_conditional)})
            full = compile_set(stage_all)
            combat = compile_set(stage_combat)
            boss = compile_set(boss_terminal)
            player_terminal = compile_set(global_sets[family]["ui"] | psets["terminal"])
            pickup = compile_set(conditional_world)
            all_epoch_combat_fit = all(row["ordinary_combat"]["margin"] >= 0 for row in epoch_sets)
            if full["margin"] >= 0:
                classification = "WHOLE-STAGE"
            elif combat["margin"] >= 0 and all_epoch_combat_fit:
                classification = "TERMINAL/PREFETCH COARSE"
            elif all_epoch_combat_fit:
                classification = "WAIT/ENCOUNTER COARSE"
            else:
                classification = "FINE SAMPLE RESIDENCY CANDIDATE"
            required_reloads = sum(a["ordinary_combat"]["assets"] != b["ordinary_combat"]["assets"] for a, b in zip(epoch_sets, epoch_sets[1:]))
            contexts.append({"family": family, "stage": stage["source_level"], "player": player["name"], "runtime_represented": player["runtime_represented"], "unresolved_source_spawns": unresolved, "actors": actor_rows, "full_source_capability": full, "ordinary_combat": combat, "boss_terminal": boss, "player_terminal": player_terminal, "conditional_world_environment": pickup, "epochs": epoch_sets, "required_wait_reload_count": required_reloads, "classification": classification})

    output = {
        "schema_version": 1,
        "policy": "baseline-policy capacity; semantic lifetime feasibility, not final shipping policy",
        "capacity_bytes": CAPACITY,
        "canonical_source_context_count": len(contexts),
        "runtime_represented_canonical_count": sum(row["runtime_represented"] for row in contexts),
        "source_only_canonical_count": sum(not row["runtime_represented"] for row in contexts),
        "bonus_easter_egg_context_count": 122,
        "manifest_hash": sha(manifest_path),
        "player_scope_hash": sha(ROOT / "tools/audio/player_scope_evidence.json"),
        "shipped_content_hash": sha(ROOT / "tools/audio/shipped_content.py"),
        "production_compiler_source_hash": sha(ROOT / "tools/audio/production_compile.py"),
        "lifetime_planner_hash": sha(__file__),
        "pak_hashes": {family: sha(path) for family, path in PAKS.items()},
        "players": player_rows,
        "asset_costs": sorted(({"asset": key, "brr_bytes": ((row["source_frames"] + 15) // 16) * 9, "sample_rate_hz": row["sample_rate_hz"], "source_frames": row["source_frames"], "duration_seconds": row["duration_seconds"], "duration_ticks": row["duration_ticks"], "canonical_pcm_hash": row["canonical_pcm_hash"], "sample_identity": row["sample_identity"], "effect_identity": row["effect_identity"]} for key, row in asset_metadata.items()), key=lambda row: (-row["brr_bytes"], row["asset"])),
        "contexts": contexts,
        "compile_cache_entries": len(set_cache),
    }
    out = ROOT / "tools/audio/semantic_lifetime_residency.json"
    out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"semantic lifetime residency: {len(contexts)} canonical source contexts; represented={output['runtime_represented_canonical_count']} source-only={output['source_only_canonical_count']}")
    for player in player_rows:
        sets = player["compiled_sets"]
        print(f"PLAYER {player['family']}:{player['name']}: full={sets['full_capability_union']['common_data_bytes']} ordinary={sets['ordinary_combat']['common_data_bytes']} conditional-action={sets['conditional_action_only']['common_data_bytes']} pickup={sets['conditional_pickup_only']['common_data_bytes']} terminal={sets['terminal_only']['common_data_bytes']}")
    for row in contexts:
        print(f"CONTEXT {row['family']}:{row['stage']}:{row['player']}: full={row['full_source_capability']['common_data_bytes']} combat={row['ordinary_combat']['common_data_bytes']} boss-terminal={row['boss_terminal']['common_data_bytes']} player-terminal={row['player_terminal']['common_data_bytes']} conditional={row['conditional_world_environment']['common_data_bytes']} class={row['classification']}")


if __name__ == "__main__":
    main()
