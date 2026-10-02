"""Exact static-common witnesses and sustained-bandwidth evidence for long SFX."""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter"), str(ROOT / "soundwork/tad")]
from production_compile import compile_production_sfx_set

SOURCE = ROOT / "tools/audio/semantic_lifetime_residency.json"
OUTPUT = ROOT / "tools/audio/streaming_witnesses.json"
CAPACITY = 60828
SOURCE_DEFENSIBLE_LONG = {
    "bor-original:DATA\\SOUNDS\\EEK.WAV",
    "bor-original:DATA\\SOUNDS\\KULABLOW.WAV",
    "bor-original:DATA\\SOUNDS\\MAXBOOM.WAV",
    "bor-original:DATA\\SOUNDS\\MAXROCKT.WAV",
    "tmnt:DATA\\SOUNDS\\FOOTDIE.WAV",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compile_set(assets):
    try:
        result = compile_production_sfx_set(
            ROOT, assets, policy_name="baseline", allow_source_canonical=True
        )
        return {
            "common_data_bytes": result["common_data_bytes"],
            "brr_sample_bytes": result["brr_sample_bytes"],
            "non_sample_common_bytes": result["non_sample_common_bytes"],
            "sample_count": result["sample_count"],
            "effect_count": result["effect_count"],
            "margin": CAPACITY - result["common_data_bytes"],
            "common_data_sha256": result["common_data_sha256"],
        }
    except RuntimeError as exc:
        match = re.search(r"too large \((\d+) bytes, max: (\d+)\)", str(exc))
        if not match:
            raise
        total = int(match.group(1))
        return {"common_data_bytes": total, "margin": CAPACITY - total, "compile_error": str(exc).strip()}


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    costs = {row["asset"]: row for row in source["asset_costs"]}
    failures = []
    for context in source["contexts"]:
        if context["classification"] != "FINE SAMPLE RESIDENCY CANDIDATE":
            continue
        failing = [e for e in context["epochs"] if e["ordinary_combat"]["margin"] < 0]
        if not failing:
            continue
        worst = max(failing, key=lambda e: e["ordinary_combat"]["common_data_bytes"])
        assets = worst["ordinary_combat"]["assets"]
        candidates = [
            a for a in assets
            if a in SOURCE_DEFENSIBLE_LONG
        ]
        fitting = []
        trials = []
        for count in range(1, len(candidates) + 1):
            for removed in itertools.combinations(candidates, count):
                result = compile_set(sorted(set(assets) - set(removed)))
                trials.append({"assets": list(removed), "result": result})
                if result["margin"] >= 0:
                    fitting.append((removed, result))
            if fitting:
                break
        fitting.sort(key=lambda row: (sum(costs[a]["brr_bytes"] for a in row[0]), row[0]))
        removed, result = fitting[0] if fitting else ((), None)
        failures.append({
            "family": context["family"],
            "stage": context["stage"],
            "player": context["player"],
            "epoch": worst["epoch"],
            "original": worst["ordinary_combat"],
            "samples": [costs[a] for a in sorted(assets, key=lambda a: (-costs[a]["brr_bytes"], a))],
            "source_defensible_candidates": candidates,
            "exact_recompile_trials": trials,
            "minimum_nonresident_witness": {
                "assets": list(removed),
                "removed_brr_bytes": sum(costs[a]["brr_bytes"] for a in removed),
                "recompiled": result,
            },
        })

    bandwidth_assets = {
        "tmnt:DATA\\SOUNDS\\FOOTDIE.WAV",
        "tmnt:DATA\\SOUNDS\\BEBOPDIE.WAV",
        "tmnt:DATA\\SOUNDS\\ROCKDIE.WAV",
        "tmnt:DATA\\SOUNDS\\TURTLE~1.WAV",
        "tmnt:DATA\\SOUNDS\\PIZZA1.WAV",
    }
    for row in failures:
        bandwidth_assets.update(row["minimum_nonresident_witness"]["assets"])
    bandwidth = []
    for asset in sorted(bandwidth_assets):
        row = dict(costs[asset])
        row["average_brr_bytes_per_second"] = row["brr_bytes"] / row["duration_seconds"]
        row["average_brr_bytes_per_60hz_frame"] = row["average_brr_bytes_per_second"] / 60
        row["average_brr_blocks_per_60hz_frame"] = row["average_brr_bytes_per_60hz_frame"] / 9
        bandwidth.append(row)
    output = {
        "schema_version": 1,
        "capacity_bytes": CAPACITY,
        "semantic_lifetime_parent_hash": sha(SOURCE),
        "production_compiler_hash": sha(ROOT / "tools/audio/production_compile.py"),
        "analyzer_hash": sha(__file__),
        "failures": failures,
        "stream_bandwidth": bandwidth,
    }
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for row in failures:
        witness = row["minimum_nonresident_witness"]
        print(row["family"], row["stage"], row["player"], row["original"]["common_data_bytes"], witness["assets"], witness["recompiled"]["common_data_bytes"] if witness["recompiled"] else "NO FIT")


if __name__ == "__main__":
    main()
