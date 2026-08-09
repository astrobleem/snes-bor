"""Shared helpers for this project's committed Mesen2 verification scripts.

See plan.md Part Two, section 2.2 ("Tool B") for why these conventions
exist and are mandatory, not stylistic:
  - ROM path is always derived from THIS repo root, never hardcoded --
    inside a git worktree, a hardcoded E:\\gh\\snes-bor\\distribution\\bor.sfc
    silently points at the main checkout's stale ROM instead of the one
    this worktree actually built. An entire session was lost to exactly
    this once.
  - Reads are always >=32 bytes, sliced locally -- smaller reads have
    returned stale data in this harness before.
  - Full $7Exxxx addresses only -- a bare offset silently misreads instead
    of erroring.
  - Assertions run 3x and take the majority, since this harness has a
    documented false-failure rate on some checks (notably audio).
"""
import os
import re
import sys

MESEN_PYTHON_PATH = r'E:\gh\Mesen2\python'
MESEN_EXE = r'E:\gh\Mesen2\bin\win-x64\Release\Mesen.exe'

if MESEN_PYTHON_PATH not in sys.path:
    sys.path.append(MESEN_PYTHON_PATH)

from mesen_mcp.session import McpSession  # noqa: E402


def repo_root_from(verify_script_file):
    """Pass __file__ from the calling phaseN.py -- this file lives at
    <repo_root>/tools/verify/_harness.py, so repo root is two levels up
    from THIS file, not from the caller (works the same either way here,
    but anchoring to this file is what actually matches the stated rule:
    never derive it from a hardcoded literal)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, '..', '..'))


def rom_path(verify_script_file):
    return os.path.join(repo_root_from(verify_script_file), 'distribution', 'bor.sfc')


def open_session(verify_script_file, boot_wait=2.0):
    return McpSession(rom=rom_path(verify_script_file), mesen=MESEN_EXE, boot_wait=boot_wait)


def pasm_constant(name):
    """Read a plain integer constant out of src/main.pasm by name.

    Verification scripts must never hardcode engine layout values. phase5.py
    originally wrote the four entity bases as literal +35/+70/+105 and began
    silently reading entities 1-3 at the wrong addresses the moment Phase 6
    added CHAR_HP and grew CHAR_ZP_LEN to 36 -- the assertions still ran, they
    just examined the wrong memory. Deriving from source makes that class of
    drift impossible.

    Handles `NAME = 36`, `NAME = $24`, and trailing comments.
    """
    path = os.path.join(repo_root_from(None), 'src', 'main.pasm')
    pattern = re.compile(r'^\s*' + re.escape(name) + r'\s*=\s*(\$?[0-9A-Fa-f]+)\s*(?:;.*)?$')
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = pattern.match(line)
            if m:
                raw = m.group(1)
                return int(raw[1:], 16) if raw.startswith('$') else int(raw, 10)
    raise KeyError(f'constant {name!r} not found in {path}')


def read_block(m, addr, length=32, mem_type='snesMemory'):
    """For mem_type='snesMemory' (WRAM), addr must be a full $7Exxxx/$00xxxx
    -style address -- a bare offset silently misreads in this harness. That
    rule doesn't apply to the other memory types (snesCgRam, snesVideoRam,
    snesSpriteRam), which are addressed as plain offsets into their own
    small space. length must always be >= 32."""
    if mem_type == 'snesMemory':
        assert addr >= 0x7E0000 or addr >= 0x008000, \
            f'read_block: {hex(addr)} does not look like a full WRAM address'
    assert length >= 32, 'read_block: reads under 32 bytes can be stale in this harness'
    return m.read_memory(mem_type, addr, length)


class Reporter:
    """Collects named PASS/FAIL assertions and prints the phase summary
    line every phaseN.py script must end with."""

    def __init__(self, phase_number):
        self.phase_number = phase_number
        self.results = []

    def check(self, name, condition):
        status = 'PASS' if condition else 'FAIL'
        print(f'{name}: {status}')
        self.results.append((name, bool(condition)))
        return bool(condition)

    def majority_of_3(self, name, fn):
        """fn() -> bool, called 3x; majority wins. Use for anything that has
        shown flakiness in this harness (audio checks especially)."""
        outcomes = [bool(fn()) for _ in range(3)]
        passed = sum(outcomes) >= 2
        print(f'{name}: {outcomes} -> {"PASS" if passed else "FAIL"}')
        self.results.append((name, passed))
        return passed

    def finish(self):
        overall = all(ok for _, ok in self.results)
        print()
        print(f'PHASE {self.phase_number}: {"PASS" if overall else "FAIL"}')
        if not overall:
            failed = [name for name, ok in self.results if not ok]
            print(f'  failed: {failed}')
        raise SystemExit(0 if overall else 1)
