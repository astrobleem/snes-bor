"""Validate the single shipped roster/stage source used by build and audio tools."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "audio"))
from shipped_content import PLAYABLE_ROSTER_COUNT, ROSTER_CONFIGS, ROSTER_PREFIXES, STAGE_CONFIGS  # noqa: E402


def main() -> int:
    prefixes = [entry["converted_prefix"] for entry in ROSTER_CONFIGS]
    sources = [(entry["family"], entry["source_character"].upper()) for entry in ROSTER_CONFIGS]
    if prefixes != ROSTER_PREFIXES:
        raise SystemExit("roster prefixes are not derived from ROSTER_CONFIGS")
    if len(prefixes) != len(set(prefixes)):
        raise SystemExit("duplicate converted roster prefix")
    if len(sources) != len(set(sources)):
        raise SystemExit("duplicate family/source roster identity")
    if any(entry["playable"] not in (True, False) for entry in ROSTER_CONFIGS):
        raise SystemExit("roster playable classification must be boolean")
    if sum(entry["playable"] for entry in ROSTER_CONFIGS) != PLAYABLE_ROSTER_COUNT:
        raise SystemExit("playable roster count is not derived from roster records")
    seen_non_playable = False
    for entry in ROSTER_CONFIGS:
        if not entry["playable"]:
            seen_non_playable = True
        elif seen_non_playable:
            raise SystemExit("playable roster entry appears after a non-playable entry")
    if len(STAGE_CONFIGS) != len({(s["family"], s["source_level"].upper()) for s in STAGE_CONFIGS}):
        raise SystemExit("duplicate shipped stage identity")
    print(f"shipped content: {len(ROSTER_CONFIGS)} roster entries, {PLAYABLE_ROSTER_COUNT} playable, {len(STAGE_CONFIGS)} stages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
