"""Trace the emitted live player-control initializer without an emulator."""
from pathlib import Path
import re
import os
import subprocess
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))

import source_foreign_state_layout as foreign_layout
import source_live_player_controls_native as controls


CONSUMERS = {
    "input_owner": "source_player_attack_native.py",
    "costmove_controls": "source_costmove_native.py",
    "combo_controls": "source_player_combo_native.py",
    "attack_chain_controls": "source_attack_chain_native.py",
    "run_tuple_controls": "source_run_tuple_native.py",
    "ground_controls": "source_player_ground_native.py",
    "ground_binding_controls": "source_player_ground_binding.py",
    "find_here_empty_controls": "source_find_here_empty_native.py",
    "ground_services_controls": "source_player_ground_services.py",
    "common_idle_controls": "source_common_idle_native.py",
    "run_cancel_controls": "source_player_run_native.py",
    "run_binding_controls": "source_player_run_binding.py",
    "special_controls": "source_player_special_native.py",
    "special_binding_controls": "source_player_special_binding.py",
    "special_services_controls": "source_player_special_services.py",
    "charge_services_controls": "source_player_charge_services.py",
    "pain_services_controls": "source_player_pain_services.py",
    "player_early_controls": "source_player_early_native.py",
    "player_fall_controls": "source_player_fall_native.py",
    "player_jump_controls": "source_player_jump_native.py",
    "player_lie_controls": "source_player_lie_absence_native.py",
    "player_directional_controls": "source_player_directional_native.py",
    "player_button_controls": "source_player_button_native.py",
    "player_release_controls": "source_player_release_native.py",
    "player_attack_controls": "source_player_attack_native.py",
    "tryjump_controls": "source_tryjump_native.py",
    "dojump_controls": "source_dojump_native.py",
    "player_jump_entry_controls": "source_player_jump_entry_native.py",
}


def _number(token):
    token = token.strip()
    if token.startswith("$"):
        return int(token[1:], 16)
    return int(token, 10)


def _trace(code, memory, *, a=0x1357, x=0x2468, p=0x01):
    """Execute just the emitted clear-loop instruction subset and trace stores."""
    labels = {}
    program = []
    for raw in code.splitlines():
        line = raw.strip()
        if not line or line.startswith("."):
            continue
        if line.endswith(":"):
            labels[line[:-1].lower()] = len(program)
        else:
            program.append(line)
    stack = []
    writes = []
    carry = bool(p & 1)
    m8, x8 = bool(p & 0x20), bool(p & 0x10)
    pc = 0
    steps = 0
    while pc < len(program):
        steps += 1
        assert steps < 50000, "trace loop did not terminate"
        ins = program[pc].lower().split()
        op = ins[0]
        arg = ins[1] if len(ins) > 1 else ""
        pc += 1
        if op == "php":
            stack.append(("p", (carry, m8, x8)))
        elif op == "rep":
            mask = _number(arg.removeprefix("#"))
            if mask & 0x20:
                m8 = False
            if mask & 0x10:
                x8 = False
        elif op == "sep":
            mask = _number(arg.removeprefix("#"))
            if mask & 0x20:
                m8 = True
            if mask & 0x10:
                x8 = True
        elif op == "phx":
            stack.append(("x8" if x8 else "x16", x & (0xFF if x8 else 0xFFFF)))
        elif op == "pha":
            stack.append(("a8" if m8 else "a16", a & (0xFF if m8 else 0xFFFF)))
        elif op == "pla":
            kind, value = stack.pop()
            assert kind in ("a8", "a16")
            a = value
        elif op == "plx":
            kind, value = stack.pop()
            assert kind in ("x8", "x16")
            x = value
        elif op == "plp":
            kind, value = stack.pop()
            assert kind == "p"
            carry, m8, x8 = value
        elif op == "lda":
            assert arg.startswith("#")
            a = _number(arg[1:]) & (0xFF if m8 else 0xFFFF)
        elif op == "ldx":
            assert arg.startswith("#")
            x = _number(arg[1:]) & (0xFF if x8 else 0xFFFF)
        elif op == "sta.l":
            match = re.fullmatch(r"\$([0-9a-f]+)(?:,x)?", arg)
            assert match, program[pc - 1]
            address = int(match.group(1), 16)
            if arg.endswith(",x"):
                address = (address + x) & 0xFFFFFF
            width = 1 if m8 else 2
            value = a & ((1 << (8 * width)) - 1)
            memory[address] = value & 0xFF
            if width == 2:
                memory[address + 1] = value >> 8
            writes.append((address, width, value))
        elif op == "inx":
            x = (x + 1) & (0xFF if x8 else 0xFFFF)
        elif op == "cpx":
            assert arg.startswith("#")
            carry = x >= _number(arg[1:])
        elif op == "bcc":
            if not carry:
                pc = labels[arg]
        elif op == "clc":
            carry = False
        elif op == "rtl":
            break
        else:
            raise AssertionError(f"unhandled emitted instruction: {program[pc - 1]}")
    assert not stack
    return memory, writes, a, x, (carry, m8, x8)


@pytest.fixture
def arena():
    return foreign_layout.layout(0x7E0000, 0x10000)


def _region_map(arena):
    return {r["name"]: (r["address"], r["bytes"]) for r in arena["regions"]}


def test_trace_zeros_scratch_and_writes_real_control_tags_only(arena):
    code = controls.emit({}, arena)
    regions = _region_map(arena)
    memory = {address: 0xA5 for address in range(arena["base"], arena["base"] + arena["bytes"])}
    original_protected = {
        name: bytes(memory[address] for address in range(at, at + size))
        for name in controls.PERSISTENT_OR_BIRTH_OWNED
        for at, size in (regions[name],)
    }
    final, writes, a, x, status = _trace(code, memory)

    allowed = {
        address
        for name in controls.SCRATCH_REGIONS
        for address in range(regions[name][0], regions[name][0] + regions[name][1])
    }
    assert writes
    assert all(at in allowed and at + width - 1 in allowed for at, width, _ in writes)
    for name in controls.SCRATCH_REGIONS:
        at, size = regions[name]
        expected = bytearray(size)
        if name in controls.CONTROL_MAGICS:
            value = controls.CONTROL_MAGICS[name]
            expected[0:2] = value.to_bytes(2, "little")
        for block, offset, value in controls.CONTROL_DEFAULT_WORDS:
            if block == name:
                expected[offset:offset + 2] = value.to_bytes(2, "little")
        assert bytes(final[address] for address in range(at, at + size)) == bytes(expected), name
    for name, before in original_protected.items():
        at, size = regions[name]
        assert bytes(final[address] for address in range(at, at + size)) == before, name
    assert (a, x, status) == (0x1357, 0x2468, (False, False, False))


def test_control_tags_match_live_owner_consumers_and_fixture_producer(arena):
    compile_root = ROOT / "tools" / "bor_compile"
    fixture_source = (ROOT / "tools" / "verify" / "m4_animation_callback_owner_native.py").read_text(encoding="utf-8")
    for name, magic in controls.CONTROL_MAGICS.items():
        consumer = (compile_root / CONSUMERS[name]).read_text(encoding="utf-8").lower()
        assert f"{magic:04x}" in consumer, name
        # The generated Lua fixtures use these same actual control tags.
        assert re.search(rf"0x0*{magic:04x}\b", fixture_source.lower()), name

    code = controls.emit({}, arena)
    regions = _region_map(arena)
    memory = {address: 0 for address in range(arena["base"], arena["base"] + arena["bytes"])}
    final, _, _, _, _ = _trace(code, memory)
    for name, magic in controls.CONTROL_MAGICS.items():
        at, _ = regions[name]
        assert final[at] | final[at + 1] << 8 == magic
    for name, offset, value in controls.CONTROL_DEFAULT_WORDS:
        at, _ = regions[name]
        assert final[at + offset] | final[at + offset + 1] << 8 == value


def test_layout_rejects_missing_regions_and_overlaps(arena):
    missing = dict(arena, regions=[r for r in arena["regions"] if r["name"] != "run_binding_controls"])
    with pytest.raises(ValueError, match="REGION:run_binding_controls"):
        controls.emit({}, missing)

    overlaps = dict(arena, regions=[dict(r) for r in arena["regions"]])
    by_name = {r["name"]: r for r in overlaps["regions"]}
    by_name["ground_controls"]["address"] = by_name["ground_binding_controls"]["address"]
    with pytest.raises(ValueError, match="LAYOUT_OVERLAP"):
        controls.emit({}, overlaps)


def test_birth_owned_rows_and_state_leases_are_not_initializer_targets(arena):
    code = controls.emit({}, arena)
    regions = _region_map(arena)
    for name in controls.PERSISTENT_OR_BIRTH_OWNED:
        address, _ = regions[name]
        assert f"${address:06X}" not in code

    # Source-owned readiness globals and descriptor tables are prerequisites,
    # not silently initialized memory targets.
    assert "SourceDefaultPlayer4086_Ready" not in code
    assert "SourceIdle4086_Ready" not in code
    assert "SourcePlayerState_Init" not in code


def test_emitted_initializer_assembles_with_poppy(arena):
    from m4_live_world_native import assembler_command
    try:
        command = assembler_command()
    except ValueError:
        pytest.skip("Configure DOTNET/PATH and POPPY_DLL to test assembly")
    with tempfile.TemporaryDirectory(prefix="live_player_controls_") as tmp:
        source = Path(tmp) / "controls.pasm"
        binary = Path(tmp) / "controls.bin"
        source.write_text(
            ".snes\n.bank 1\n.org $8000\n" + controls.emit({}, arena),
            encoding="utf-8",
        )
        run = subprocess.run(
            [*command, str(source), "-o", str(binary)],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert run.returncode == 0, run.stdout + run.stderr
        assert binary.is_file() and binary.stat().st_size > 0
