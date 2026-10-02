"""Check linked resident/stream data and source action coverage, without encoding."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter"),
               str(ROOT / "soundwork/tad"), str(ROOT / "tools/rom_audit")]
import plan_action_residency
import rebuild
import aram_budget
import check_sfx_id_sync
import seal_runtime_audio
import s8_audio_scope
import generate_normal_audio
from pak_extract import extract
from production_sfx import canonical_wav


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("FAIL: " + message)


def verify_linked_data() -> set[str]:
    seal = json.loads(seal_runtime_audio.OUTPUT.read_text())
    require(seal["inputs_sha256"] == seal_runtime_audio.inputs(),
            "runtime authoring/compiled inputs changed; run seal_runtime_audio.py after rebuilding")
    baseline = rebuild.load_baseline()
    rebuild.verify_patched_toolchain(rebuild.find_compiler(None), baseline)
    rebuild.verify_generated_driver(rebuild.OUT_ASM, rebuild.OUT_BIN, baseline)
    rebuild.verify_data_table_metadata(rebuild.OUT_SYMS.read_text(), baseline)
    require(check_sfx_id_sync.main() == 0, "resident ID mismatch")
    require(aram_budget.main() == 0, "resident ARAM overflow")
    project = json.loads(rebuild.PROJECT_FILE.read_text())
    sample_paths = {str((rebuild.PROJECT_FILE.parent / s["source"]).resolve()) for s in project["samples"]}
    sources = []
    for path in sorted((ROOT / "assets/audio").glob("*.source.json")):
        row = json.loads(path.read_text())
        if row.get("canonical_path") and row.get("raw_sha256"):
            sources.append(row)
    available = set()
    for row in sources:
        sample = ROOT / row["canonical_path"]
        resident = row.get("project_sample_path") or row["canonical_path"]
        linked = str((ROOT / resident).resolve()) in sample_paths
        streamed = row.get("stream_brr_path")
        if not linked and not streamed:
            continue
        raw = extract(ROOT / row["source_pak"], row["asset"].split(":", 1)[1])
        require(hashlib.sha256(raw).hexdigest() == row["raw_sha256"], f"source drift: {row['asset']}")
        require(digest(sample) == row["canonical_sha256"], f"canonical sample drift: {row['asset']}")
        if linked:
            require(digest(ROOT / resident) == row["canonical_sha256"], f"resident sample drift: {row['asset']}")
        if streamed:
            require(digest(ROOT / streamed) == row["brr_sha256"], f"stream BRR drift: {row['asset']}")
        available.add(row["asset"])
    # BEAT1 and FOOTDIE predate the common provenance schema.
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text())
    families = {f["family"]: f for f in manifest["families"]}
    beat = extract(ROOT / families["bor-original"]["pak"], "DATA\\SOUNDS\\BEAT1.WAV")
    require(canonical_wav(beat)[0] == (rebuild.PROJECT_FILE.parent / "samples/beat1.wav").read_bytes(), "BEAT1 source drift")
    available.add("bor-original:DATA\\SOUNDS\\BEAT1.WAV")
    foot = json.loads((ROOT / "assets/audio/footdie.stream.json").read_text())
    raw = extract(ROOT / families["tmnt"]["pak"], "DATA\\SOUNDS\\FOOTDIE.WAV")
    require(hashlib.sha256(canonical_wav(raw)[0]).hexdigest() == foot["canonical_pcm_sha256"], "FOOTDIE source drift")
    require(digest(ROOT / "assets/audio/footdie.brr") == foot["brr_sha256"], "FOOTDIE BRR drift")
    available.add(foot["asset"])
    main = (ROOT / "src/main.pasm").read_text()
    host = (ROOT / "src/core/stage_timer_host.pasm").read_text()
    require('.incbin "../soundwork/tad/build/audio-data.bin"' in main, "resident blob not linked")
    require('.include "core/stage_timer_host.pasm"' in main, "Normal timer host not linked")
    require(re.search(r'^AUDIO_SEMANTIC_TIMEOVER\s*=\s*\$1D\b', main, re.M) is not None, "TIMEOVER semantic mismatch")
    semantics = re.findall(r'^AUDIO_SEMANTIC_\w+\s*=\s*\$([0-9A-Fa-f]+)', main, re.M)
    require(semantics.count("1D") == 1, "TIMEOVER semantic collides with another event")
    require('lda #AUDIO_SEMANTIC_TIMEOVER' in host and 'ldx #STAGE_TIMER_TIMEOVER_SFX_ID' in host
            and 'jsl Audio_QueueResidentSemantic' in host, "TIMEOVER host dispatch missing")
    require('cmp #3' in host, "TIMEOVER Normal campaign guard missing")
    require('lda #AUDIO_SEMANTIC_MONEY\n    ldx #SFX_MONEY_ID\n    jsl Audio_QueueResidentSemantic' in host,
            "Time reset item source get2 audio dispatch missing")
    require("bor-original:DATA\\SOUNDS\\TIMEOVER.WAV" in available, "TIMEOVER resident source absent")
    effect = rebuild.PROJECT_FILE.parent / "sound-effects.txt"
    require(re.search(r'=== sfx_timeover ===\s+set_instrument timeover\s+play_note 0 115\b', effect.read_text()) is not None,
            "TIMEOVER source effect or full duration changed")
    print(f"linked runtime data PASS: {len(project['sound_effects'])} resident effects; TIMEOVER source/ID/host verified")
    return available


def main() -> int:
    inventory_path = ROOT / "tools/audio/runtime_action_requirements.json"
    inventory = json.loads(inventory_path.read_text())
    # Re-derive instead of trusting manifest/roster/moveset summary hashes.
    with tempfile.TemporaryDirectory(prefix="s8-audio-check-") as tmp:
        fresh = Path(tmp) / "actions.json"
        plan_action_residency.main(True, fresh)
        require(json.loads(fresh.read_text()) == inventory, "runtime action inventory is stale")
    available = verify_linked_data()
    # Exact raw-source aliases may share a backend; filename similarity is
    # never evidence. The explicit legacy source adaptations remain separate.
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text())
    hashes = {f"{f['family']}:{a['source_path']}": a["source_hash"]
              for f in manifest["families"] for a in f["assets"] if a["kind"] == "sfx"}
    accepted = s8_audio_scope.accepted_inventory()
    normal = generate_normal_audio.bindings()
    require(generate_normal_audio.OUTPUT.read_text() == generate_normal_audio.render(normal), "stale Normal audio bindings")
    main_source = (ROOT / "src/main.pasm").read_text()
    require('.include "core/normal_audio_generated.pasm"' in main_source, "Normal audio tables not linked")
    runtime = (ROOT / "src/core/vm/vm_native_engine.pasm").read_text()
    for needle in ("cmp #AUDIO_NORMAL_ROSTER_COUNT", "lda.l AudioNormal_DiesoundByRoster,x",
                   "lda.l AudioNormal_DiesoundSourceByRoster,x", "AudioSemantic_EmitDiesound__normal_load:"):
        require(needle in runtime, "Normal diesound dispatch missing: " + needle)
    require("cmp #21" in runtime, "legacy diesound bound removed")
    owners_by_index = {i: m["family"] + ":" + m["identity"] for i, m in enumerate(inventory["models"])}
    scoped = {owners_by_index[i] for i in normal["normal_scope"]["roster_indices"]}
    accepted_models = {m["owner"]: m for m in accepted["models"]}
    globals = {(g["owner"], g["event"], g["asset"]) for g in accepted["globals"]}
    new_rows = {owners_by_index[r["roster_index"]]: r for r in normal["rows"]}
    classifications = []
    failures = []
    for row in inventory["requirements"]:
        if not row["assets"]:
            continue
        owner = row["owner"]
        if owner not in scoped and owner != "bor-original:engine":
            classification = "OUTSIDE_NORMAL_SCOPE"
        elif owner in accepted_models:
            classification = "ADAPTER_EQUIVALENT"
        elif all((owner, row["event"], a) in globals for a in row["assets"]):
            classification = "ADAPTER_EQUIVALENT"
        elif owner == "bor-original:engine" and row["event"] == "time-over" and row["assets"] == ["bor-original:DATA\\SOUNDS\\TIMEOVER.WAV"]:
            classification = "NEW_SOURCE_BOUND"
        elif (row["event"] == "diesound" and new_rows.get(owner, {}).get("classification") == "NEW_SOURCE_BOUND"
              and row["assets"] == [new_rows[owner]["asset"]] and all(a in available for a in row["assets"])):
            classification = "NEW_SOURCE_BOUND"
        else:
            classification = "FAIL_NEW_UNHANDLED"
            failures.append(row)
        classifications.append(dict(row, classification=classification))
    missing = sorted({a for r in failures for a in r["assets"]})
    owners = failures
    from normal_boss_music import receipt as boss_music_receipt
    report = {
        "verdict": "FAIL" if missing else "PASS",
        "scope": "S8 Normal ACCEPTED_COMPAT; established S7 mappings are not source-exact claims",
        "normal_scope": normal["normal_scope"],
        "normal_required_behaviors": [boss_music_receipt()],
        "accepted_baseline": accepted,
        "requirements": classifications,
        "new_model_bindings": [r for r in normal["rows"] if r["classification"] != "ADAPTER_EQUIVALENT"],
        "time_item_audio": {"classification": "NEW_SOURCE_BOUND", "event": "reset-timer get2",
                            "asset": "bor-original:DATA\\SOUNDS\\MONEY.WAV", "resident_id": 4},
        "linked_runtime_data": "PASS",
        "audio_blob_sha256": digest(rebuild.OUT_BIN),
        "action_inventory_sha256": digest(inventory_path),
        "uncovered_assets": missing,
        "affected_requirements": owners,
        "nonclaims": ["no ROM build or emulator run", "no audible acceptance",
                      "no simultaneous source-SFX playback proof"],
    }
    (ROOT / "tools/audio/runtime_audio_coverage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if missing:
        print("Uncovered source action/event assets:")
        for asset in missing:
            print("  " + asset)
        print(f"Affected requirements: {len(owners)}; no silence or substitute counted as coverage")
        raise SystemExit("FAIL: source action coverage exceeds linked runtime audio; encoding/dispatch work remains")
    print("S8 Normal audio gate PASS: pinned ADAPTER_EQUIVALENT mappings preserved; new source requirements bound")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
