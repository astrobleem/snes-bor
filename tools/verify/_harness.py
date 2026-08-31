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


def roster():
    """Gate/test hygiene (notjustfreespecial.txt): the authoritative roster
    order/count/index, derived from build_rom.py's own ROSTER_PREFIXES
    rather than a hand-copied literal list duplicated across every gate
    file. A future roster addition then only requires editing build_rom.py
    -- every gate that calls this picks the change up automatically.
    Returns a list of lowercase names in real build/roster-select order,
    e.g. ['ralf', 'jhun', ..., 'leo']."""
    import importlib.util
    root = repo_root_from(__file__)
    spec = importlib.util.spec_from_file_location('build_rom', os.path.join(root, 'build_rom.py'))
    build_rom = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_rom)
    return [p.rsplit('/', 1)[-1] for p in build_rom.ROSTER_PREFIXES]


def playable_roster():
    """Same authoritative derivation as roster(), but sliced to build_rom.py's
    PLAYABLE_ROSTER_COUNT -- the real player-selectable subset char-select's
    own Left/Right wrap cycles through (props like out/apple are real roster
    members for Spawn_DoRosterReassign's purposes but are never player-
    selectable; see pack_msu_roster.py's playable_count header-byte comment
    for the real bug this distinction fixes). Use this, not roster()[-1],
    for any char-select-wrap ground truth."""
    import importlib.util
    root = repo_root_from(__file__)
    spec = importlib.util.spec_from_file_location('build_rom', os.path.join(root, 'build_rom.py'))
    build_rom = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_rom)
    return [p.rsplit('/', 1)[-1] for p in build_rom.ROSTER_PREFIXES[:build_rom.PLAYABLE_ROSTER_COUNT]]


def _free_tcp_port():
    """Ask the OS for an ephemeral port and immediately release it.

    Every gate previously connected on the same hardcoded default port
    (7350). In a long sequential run, if a prior session's Mesen.exe was
    slow to die (see McpSession.__exit__'s kill()-without-wait() fix in
    the Mesen2 repo), a new session on that same fixed port could either
    fail to bind or -- worse -- have its client socket's connect() land
    on the still-alive old process instead of the freshly spawned one,
    silently handing the new gate stale emulator state from the previous
    gate's run. A fresh OS-assigned port per session removes the
    possibility of that collision entirely, rather than papering over it
    with a longer wait."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def open_session(verify_script_file, boot_wait=2.0):
    return McpSession(
        rom=rom_path(verify_script_file),
        mesen=MESEN_EXE,
        boot_wait=boot_wait,
        port=_free_tcp_port(),
    )


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


def pasm_constant_in(relpath, name):
    """Same contract as pasm_constant(), for any .pasm file under the repo
    root -- e.g. pasm_constant_in('src/core/vm/vm_consts.pasm', 'VMSTAT_READY').
    Verification scripts must never hardcode engine layout values; see
    pasm_constant()'s docstring for the phase5.py incident that rule came from."""
    path = os.path.join(repo_root_from(None), *relpath.split('/'))
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


def read_snes_bus_block(m, addr, length=32):
    """Read CPU-bus space, including low MMIO addresses such as $2000."""
    assert length >= 32
    return m.read_memory('snesMemory', addr, length)


def read_msu_status(m):
    """Return MSU-1 status from CPU-bus $2000, never from write-only ports."""
    return read_snes_bus_block(m, 0x002000, 32)[0]


def exact_input_edge(m, buttons, frames, port=0):
    """Assert `buttons` for EXACTLY `frames` emulated frames, verified
    against the real emulator frame counter (Mesen's set_input is
    frame-exact as of the 2026-08-29 McpTools.cs fix -- it used to sleep a
    wall-clock estimate and hope, so a caller had no way to know the edge
    was actually delivered for the frame count it expected). Input is
    guaranteed released before this returns (set_input's own contract).
    Raises AssertionError if the emulator didn't actually advance exactly
    `frames` frames while the override was active -- never silently
    accepts a short/long delivery."""
    r = m.set_input(buttons, frames, port=port)
    advanced = r.get('framesAdvanced')
    assert advanced == frames and not r.get('timedOut'), (
        f'exact_input_edge: requested {frames} frame(s) of buttons={buttons:#x}, '
        f'emulator only advanced {advanced} (timedOut={r.get("timedOut")}) -- '
        f'the input edge was not reliably delivered for the requested duration')
    return r


def held_input_sampled(m, buttons, frames, port=0, sample_fn=None):
    """Hold `buttons` across `frames` emulated frames, one real frame at a
    time, calling `sample_fn(i)` (0-based) after each frame while the
    input is still logically held (each 1-frame slice re-asserts the same
    override, verified exact via set_input's own framesAdvanced -- see
    exact_input_edge). Use this instead of a single long set_input() call
    when a gate needs to inspect state on every frame of a held press
    (e.g. proving a rigid drag/follow tracks every sampled frame, not just
    the frame the caller happened to read). Input is released before this
    returns. Returns the list of sample_fn results (empty if sample_fn is
    None)."""
    results = []
    for i in range(frames):
        exact_input_edge(m, buttons, 1, port=port)
        if sample_fn is not None:
            results.append(sample_fn(i))
    return results


def run_frames_exact(m, count):
    """run_frames, but asserts the emulator actually advanced exactly
    `count` frames (Mesen's run_frames has been frame-exact -- polls the
    real frame counter to the target -- since before this fix; this just
    makes callers verify that instead of trusting it silently). Raises
    AssertionError on a stalled/hung emulator instead of letting a caller
    read stale state past a silent short-advance."""
    r = m.run_frames(count)
    assert r.get('framesAdvanced') == count and not r.get('timedOut'), (
        f'run_frames_exact: requested {count} frames, only advanced '
        f'{r.get("framesAdvanced")} (timedOut={r.get("timedOut")}) -- '
        f'emulator may be hung')
    return r


def poll_until(m, predicate, max_frames, step=1):
    """Poll predicate(m) -> bool, advancing `step` emulated frames between
    checks (each advance verified exact via run_frames_exact -- a
    stalled/hung emulator raises here rather than exhausting max_frames
    and returning a silent False). Returns True the frame predicate first
    reads true, False if max_frames elapses first. Replaces a fixed
    "wait N frames and hope the thing you're waiting for finished" pattern
    with a real state-based convergence check."""
    advanced = 0
    while advanced < max_frames:
        this_step = min(step, max_frames - advanced)
        run_frames_exact(m, this_step)
        advanced += this_step
        if predicate(m):
            return True
    return False


class Reporter:
    """Collects named PASS/FAIL assertions and prints the phase summary
    line every phaseN.py script must end with."""

    def __init__(self, phase_number, kind='PHASE'):
        # `kind` lets plan_vm.md's gate scripts print "GATE 0a: PASS" instead
        # of "PHASE 0a: PASS" (plan_vm.md 0.7's gate-line rule). It defaults to
        # 'PHASE', so every existing phaseN.py is unaffected.
        self.phase_number = phase_number
        self.kind = kind
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
        print(f'{self.kind} {self.phase_number}: {"PASS" if overall else "FAIL"}')
        if not overall:
            failed = [name for name, ok in self.results if not ok]
            print(f'  failed: {failed}')
        raise SystemExit(0 if overall else 1)
