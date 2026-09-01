"""Fast fail-closed parent verification for semantic lifetime evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    artifact = json.loads((ROOT / "tools/audio/semantic_lifetime_residency.json").read_text(encoding="utf-8"))
    expected = {
        "manifest_hash": digest(ROOT / "tools/audio/audio_manifest.json"),
        "player_scope_hash": digest(ROOT / "tools/audio/player_scope_evidence.json"),
        "shipped_content_hash": digest(ROOT / "tools/audio/shipped_content.py"),
        "production_compiler_source_hash": digest(ROOT / "tools/audio/production_compile.py"),
        "lifetime_planner_hash": digest(ROOT / "tools/audio/analyze_semantic_lifetimes.py"),
    }
    for field, value in expected.items():
        if artifact.get(field) != value:
            raise SystemExit(f"FAIL: semantic lifetime evidence stale: {field}")
    pak_paths = {
        "bor-original": ROOT / "Beats of Rage Original [v.3.0 Build 4086].pak",
        "tmnt": ROOT / "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak",
    }
    for family, path in pak_paths.items():
        if artifact.get("pak_hashes", {}).get(family) != digest(path):
            raise SystemExit(f"FAIL: semantic lifetime evidence stale: {family} PAK")
    if artifact.get("canonical_source_context_count") != 16:
        raise SystemExit("FAIL: semantic lifetime canonical context count")
    print("semantic lifetime residency: PASS (all direct parents current)")


if __name__ == "__main__":
    main()
