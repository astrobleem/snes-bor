"""Read-only S7 Easy data audit. No build, encoder, assembly, or emulator.

Only --out writes a compact JSON report under out/. Run from any directory.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
S7 = "c8cbd71b200cab869d3f953bdd07352c172577ed"
sys.path[:0] = [str(ROOT / "tools/bor_compile"), str(ROOT / "tools/audio")]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args, **kwargs):
    return subprocess.check_output(["git", *args], cwd=ROOT, **kwargs)


def old(path):
    return git("show", f"{S7}:{path}")


def classification(before, after):
    if before == after:
        return "BYTE_IDENTICAL"
    if before.replace(b"\r\n", b"\n") == after.replace(b"\r\n", b"\n"):
        return "LINE_ENDINGS_ONLY"
    return "CONTENT_CHANGED"


def table(text, label):
    match = re.search(re.escape(label) + r":\s*\.db ([^\r\n]+)", text)
    return [v.strip() for v in match[1].split(",")] if match else None


def queue_from_msu(data, slot):
    if len(data) < 16:
        raise ValueError("truncated MSU header")
    directory = struct.unpack_from("<I", data, 12)[0]
    record = directory + slot * 40
    if directory < 16 or record + 40 > len(data):
        raise ValueError("invalid MSU stage directory extent")
    offset, count = struct.unpack_from("<IH", data, record + 32)
    if offset + count * 10 > len(data):
        raise ValueError("invalid MSU queue extent")
    return data[offset:offset + count * 10]


def media_comparison(selected):
    """Batch raw Git blobs; git archive can apply export/line-ending filters."""
    payload = git("cat-file", "--batch", input="".join(
        f"{S7}:{p}\n" for p in selected).encode())
    cursor = 0
    counts = Counter()
    differences = []
    inventory = hashlib.sha256()
    for path in selected:
        end = payload.index(b"\n", cursor)
        size = int(payload[cursor:end].split()[-1])
        before = payload[end + 1:end + 1 + size]
        cursor = end + size + 2
        target = ROOT / path
        after = target.read_bytes() if target.is_file() else None
        kind = "MISSING" if after is None else classification(before, after)
        counts[kind] += 1
        # Compact reproducible inventory of every selected file, not copies.
        inventory.update((path + "\0" + sha(before) + "\0" +
                          (sha(after) if after is not None else "MISSING") + "\n").encode())
        if kind not in ("BYTE_IDENTICAL", "LINE_ENDINGS_ONLY"):
            differences.append(dict(path=path, classification=kind))
    return dict(files=len(selected), counts=dict(counts),
                inventory_sha256=inventory.hexdigest(), differences=differences,
                passed=bool(selected) and not differences)


def audit(msu_paths):
    import compiler
    import production_campaign
    import shipped_content as current
    import s8_audio_scope

    baseline, _ = compiler.baseline(S7)
    checks = {}
    report = dict(schema=1, baseline=S7, scope="EASY_S7_DATA_PRESERVATION",
                  classification="ACCEPTED_COMPAT", checks=checks)
    ids = current.LEGACY_BOR_STAGE_IDS["Easy"]
    configs = [current.STAGE_CONFIGS[i] for i in ids]
    checks["easy_physical_bindings"] = len(configs) == 14 and all(
        all(cfg.get(k) == baseline["STAGE_CONFIGS"][slot].get(k)
            for k in ("family", "pak", "source_level", "bg", "frontpanel", "spawn"))
        and cfg.get("scroll_direction", "right") == baseline["STAGE_CONFIGS"][slot].get("scroll_direction", "right")
        for slot, cfg in zip(ids, configs))
    queues = production_campaign.compile_queues(configs, current.ROSTER_CONFIGS)
    rows = []
    for slot, cfg in zip(ids, configs):
        generated = queues[cfg["spawn"]]
        pinned = old(cfg["spawn"])
        disk = (ROOT / cfg["spawn"]).read_bytes()
        rows.append(dict(slot=slot, source=cfg["source_level"], path=cfg["spawn"],
                         records=len(generated) // 10, sha256=sha(generated),
                         s7_sha256=sha(pinned), disk_sha256=sha(disk),
                         s7_equal=generated == pinned, disk_equal=generated == disk))
    report["queues"] = rows
    checks["queues"] = len(rows) == 14 and all(r["s7_equal"] and r["disk_equal"] for r in rows)
    report["msu"] = []
    for path in msu_paths:
        data = path.read_bytes()
        matches = [queue_from_msu(data, slot) == queues[cfg["spawn"]]
                   for slot, cfg in zip(ids, configs)]
        report["msu"].append(dict(path=str(path), sha256=sha(data),
                                  easy_queue_matches=matches, passed=all(matches)))
    checks["packed_queues"] = bool(msu_paths) and all(r["passed"] for r in report["msu"])
    previous = baseline["CAMPAIGN_CONFIGS"]["BOR_ORIGINAL"]
    selected = current.CAMPAIGN_CONFIGS["BOR_ORIGINAL"]
    def identity(entry):
        return (entry["kind"], compiler.key(entry["source_level"])
                if entry["kind"] == "stage" else entry["scene_id"])
    checks["easy_entry_identity_order"] = list(map(identity, previous["entries"])) == list(map(identity, selected["entries"]))
    before_text = old("tools/audio/campaign_config.pasm").decode()
    after_text = (ROOT / "tools/audio/campaign_config.pasm").read_text()
    report["campaign_tables"] = {}
    for label in ("Campaign_Bor_EntryKinds", "Campaign_Bor_EntryValues", "Campaign_Bor_StageMap"):
        a, b = table(before_text, label), table(after_text, label)
        report["campaign_tables"][label] = dict(s7=a, current=b)
        checks[label] = a is not None and a == b
    expected_next = [str(int(e["next_after"])) for e in selected["entries"]]
    actual_next = table(after_text, "Campaign_Bor_NextFlags")
    report["next_flags_difference"] = dict(
        s7=table(before_text, "Campaign_Bor_NextFlags"), current=actual_next,
        source_expected=expected_next,
        classification="SOURCE_DERIVED_ADDITION_NOT_RUNTIME_EQUIVALENCE",
        note="S7 lacked this table. Completion/runtime behavior is not proven unchanged.")
    checks["next_flags_source_match"] = actual_next == expected_next
    old_roster = baseline["ROSTER_CONFIGS"]
    checks["roster_prefix"] = current.ROSTER_CONFIGS[:len(old_roster)] == old_roster
    report["roster"] = dict(s7_count=len(old_roster), current_count=len(current.ROSTER_CONFIGS),
                             appended=current.ROSTER_CONFIGS[len(old_roster):])
    roots = {c[k] for c in configs for k in ("bg", "frontpanel") if c.get(k)}
    prefixes = [r["converted_prefix"] for r in old_roster]
    paths = git("ls-tree", "-r", "--name-only", S7, "out").decode().splitlines()
    report["media"] = {}
    for name, paths_in_scope in (
        ("easy", [p for p in paths if any(p.startswith(r + "/") for r in roots)]),
        ("s7_roster", [p for p in paths if any(p.startswith(r + "_") for r in prefixes)])):
        result = media_comparison(paths_in_scope)
        report["media"][name] = result
        checks[name + "_media"] = result["passed"]
    checks["scene_config"] = current.SCENE_CONFIGS == baseline["SCENE_CONFIGS"]
    checks["scene_metadata_bytes"] = (ROOT / "src/generated/scene_sequence_meta.pasm").read_bytes() == old("src/generated/scene_sequence_meta.pasm")
    catalog = json.loads((ROOT / "tools/audio/music_catalog.json").read_text())
    checks["music_catalog"] = catalog == json.loads(old("tools/audio/music_catalog.json"))
    report["music"] = []
    for track in catalog["tracks"]:
        actual = sha((ROOT / track["msu_pcm_path"]).read_bytes())
        report["music"].append(dict(track_id=track["track_id"], path=track["msu_pcm_path"],
                                   expected_sha256=track["msu_pcm_hash"], actual_sha256=actual,
                                   passed=actual == track["msu_pcm_hash"]))
    checks["music_pcm"] = bool(report["music"]) and all(t["passed"] for t in report["music"])
    inventory = s8_audio_scope.accepted_inventory()
    checks["s7_audio_adapters"] = len(inventory["models"]) == len(old_roster)
    report["audio_adapters"] = dict(count=len(inventory["models"]), classification="ADAPTER_EQUIVALENT")
    # Inspect the actual default gate without executing its file-writing generator.
    tree = ast.parse((ROOT / "build_rom.py").read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "write_campaign_include")
    default = dict(zip([a.arg for a in function.args.args][-len(function.args.defaults):], function.args.defaults))
    assignment = next(n for n in function.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "available" for t in n.targets))
    expression = compile(ast.Expression(assignment.value), "availability", "eval")
    availability = [eval(expression, {"__builtins__": {}, "bool": bool}, {"normal_candidate": flag}) for flag in (False, True)]
    checks["production_default_gate"] = ast.literal_eval(default["normal_candidate"]) is False and availability == [
        dict(Easy=True, Normal=False, Hard=False, Bonus=False),
        dict(Easy=True, Normal=True, Hard=False, Bonus=False)]
    report["availability"] = dict(default=availability[0], explicit_candidate=availability[1],
                                  current_generated=table(after_text, "BorSet_ContentAvailable"),
                                  note="Shared generated availability can belong to a candidate; not default release evidence.")
    report["nonclaims"] = [
        "No build, assembly, encoding, emulator or native-route execution.",
        "No pixel, packed visual-payload, timing, gameplay or whole-ROM/MSU equivalence.",
        "Existing actors/audio remain ACCEPTED_COMPAT/ADAPTER_EQUIVALENT, not SOURCE_CERTIFIED.",
        "Shared runtime changes, expanded roster and TIMEOVER blob are not byte-preserved S7 runtime.",
        "Native3 Easy route PASS (out/s8_scene_edge_easy.json) is separate evidence, not a pixel claim; not revalidated here.",
        "Media inventory covers S7-tracked binding files; newly added files and final packed visuals are not certified."]
    report["status"] = "PASS" if all(checks.values()) else "FAIL"
    report["audit_tool_sha256"] = sha(Path(__file__).read_bytes())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--msu", action="append", type=Path,
                        help="MSU to check; repeatable. Default: distribution and s8_candidate.")
    parser.add_argument("--out", type=Path, help="Optional JSON report path confined to repository out/.")
    args = parser.parse_args()
    target = None
    if args.out:
        target = (ROOT / args.out).resolve()
        if not target.is_relative_to((ROOT / "out").resolve()) or target.suffix != ".json":
            parser.error("--out must be a .json report under repository out/")
    os.chdir(ROOT)
    paths = [(ROOT / p).resolve() for p in (args.msu or [Path("distribution/bor.msu"), Path("build/s8_candidate/bor.msu")])]
    try:
        report = audit(paths)
    except (Exception, SystemExit) as error:
        report = dict(schema=1, baseline=S7, status="FAIL", error=str(error),
                      scope="EASY_S7_DATA_PRESERVATION", nonclaim="Incomplete audit is not PASS.")
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(encoded, encoding="utf-8")
        print(json.dumps(dict(status=report["status"], report=str(target), error=report.get("error"))))
    else:
        print(encoded, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
