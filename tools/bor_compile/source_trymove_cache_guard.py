"""ROM- and source-anchored replacement for FlatTrymove's cache-size guard.

The old guard reads RowBytes, scratch that is populated only inside the normal
animation-copy Apply call. The accepted flat try-move path instead compares
the stable Bytes control against the admitted model count times the source
row width. This module returns an exact patch description; it never edits a
ROM or input artifact.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib


SCHEMA = "BYOR_FLAT_TRYMOVE_CACHE_GUARD_PATCH_V1"
GUARD_BEGIN = "FlatTrymove_Guard54"
GUARD_END = "FlatTrymove_Guard55"
FAULT_LABEL = "FlatTrymove_Bad"
ROW_BYTES = 336
MAX_MODELS = 16
PATCH_BYTES = 12


def _symbol(symbols: Mapping, name: str) -> int:
    value = symbols.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFF:
        raise ValueError("TRYMOVE_CACHE_GUARD_SYMBOL:" + name)
    return value


def _lorom_offset(address: int) -> int:
    if isinstance(address, bool) or not isinstance(address, int) or not 0 <= address <= 0xFFFFFF:
        raise ValueError("TRYMOVE_CACHE_GUARD_ADDRESS_DOMAIN")
    if (address & 0xFFFF) < 0x8000:
        raise ValueError("TRYMOVE_CACHE_GUARD_NOT_ROM_WINDOW")
    return ((address >> 16) & 0x7F) * 0x8000 + (address & 0x7FFF)


def _source_guard_lines(pasm_text: str, *, row_bytes: int) -> tuple[str, ...]:
    if not isinstance(pasm_text, str):
        raise ValueError("TRYMOVE_CACHE_GUARD_PASM_REQUIRED")
    lines = [line.strip() for line in pasm_text.splitlines()]
    try:
        start = lines.index(GUARD_BEGIN + ":")
        end = lines.index(GUARD_END + ":", start + 1)
    except ValueError as exc:
        raise ValueError("TRYMOVE_CACHE_GUARD_SOURCE_LABELS") from exc
    body = tuple(line for line in lines[start + 1:end] if line and not line.startswith((";", ".")))
    expected_old = (
        f"lda.l {row_bytes}",
        f"cmp #{ROW_BYTES}",
        f"beq {GUARD_END}",
        f"jmp {FAULT_LABEL}",
    )
    if body != expected_old:
        raise ValueError("TRYMOVE_CACHE_GUARD_SOURCE_BLOCK")
    return body


def derive_patch_plan(contract: Mapping, rom_bytes: bytes, *, model_count: int,
                      pasm_text: str) -> dict:
    """Validate the accepted guard and describe its same-width 12-byte edit.

    `contract` must be the linked symbol contract for the same ROM, and
    `pasm_text` its accepted assembled live-world listing. The returned plan
    may be reviewed/applied by a separately authorized builder; this function
    itself remains read-only.
    """
    if not isinstance(contract, Mapping):
        raise ValueError("TRYMOVE_CACHE_GUARD_CONTRACT")
    if not isinstance(rom_bytes, bytes) or not rom_bytes:
        raise ValueError("TRYMOVE_CACHE_GUARD_ROM")
    symbols = contract.get("symbols")
    if not isinstance(symbols, Mapping):
        raise ValueError("TRYMOVE_CACHE_GUARD_SYMBOL_MAP")
    digest = hashlib.sha256(rom_bytes).hexdigest()
    if not isinstance(contract.get("rom_sha256"), str) or contract["rom_sha256"] != digest:
        raise ValueError("TRYMOVE_CACHE_GUARD_ROM_SHA256")
    if isinstance(model_count, bool) or not isinstance(model_count, int) or not 1 <= model_count <= MAX_MODELS:
        raise ValueError("TRYMOVE_CACHE_GUARD_MODEL_COUNT")
    expected_bytes = model_count * ROW_BYTES
    if expected_bytes > 0xFFFF:
        raise ValueError("TRYMOVE_CACHE_GUARD_EXPECTED_BYTES")

    begin = _symbol(symbols, GUARD_BEGIN)
    end = _symbol(symbols, GUARD_END)
    bad = _symbol(symbols, FAULT_LABEL)
    row_bytes = _symbol(symbols, "SourceModelAnimationCopy4086_RowBytes")
    stable_bytes = _symbol(symbols, "SourceModelAnimationCopy4086_Bytes")
    models_address = _symbol(symbols, "SourceModelAnimationCopy4086_Models")
    if (end - begin != PATCH_BYTES or begin >> 16 != end >> 16 or
            begin >> 16 != bad >> 16):
        raise ValueError("TRYMOVE_CACHE_GUARD_LABEL_EXTENT")
    if row_bytes != 0x7FFC64 or stable_bytes != 0x7FFC56 or models_address != 0x7FFC52:
        raise ValueError("TRYMOVE_CACHE_GUARD_SOURCE_FIELDS")
    _source_guard_lines(pasm_text, row_bytes=row_bytes)

    rom_offset = _lorom_offset(begin)
    if rom_offset + PATCH_BYTES > len(rom_bytes):
        raise ValueError("TRYMOVE_CACHE_GUARD_ROM_EXTENT")
    old_bytes = bytes((
        0xAF, row_bytes & 0xFF, (row_bytes >> 8) & 0xFF, (row_bytes >> 16) & 0xFF,
        0xC9, ROW_BYTES & 0xFF, ROW_BYTES >> 8,
        0xF0, 0x03,
        0x4C, bad & 0xFF, (bad >> 8) & 0xFF,
    ))
    actual = rom_bytes[rom_offset:rom_offset + PATCH_BYTES]
    if actual != old_bytes:
        raise ValueError("TRYMOVE_CACHE_GUARD_ROM_BYTES")
    new_bytes = bytes((
        0xAF, stable_bytes & 0xFF, (stable_bytes >> 8) & 0xFF, (stable_bytes >> 16) & 0xFF,
        0xC9, expected_bytes & 0xFF, expected_bytes >> 8,
        0xF0, 0x03,
        0x4C, bad & 0xFF, (bad >> 8) & 0xFF,
    ))
    replacement = (
        f"lda.l {stable_bytes}\n cmp #{expected_bytes}\n"
        f"beq {GUARD_END}\n jmp {FAULT_LABEL}"
    )
    # The assembler listing must describe the currently accepted pre-patch
    # block; the output replacement is provided separately for the opt-in build.
    return {
        "schema": SCHEMA,
        "enabled": True,
        "rom_sha256": digest,
        "site": begin,
        "site_hex": f"{begin:06X}",
        "rom_offset": rom_offset,
        "length": PATCH_BYTES,
        "labels": {"begin": GUARD_BEGIN, "end": GUARD_END, "fault": FAULT_LABEL},
        "model_count": model_count,
        "row_bytes": ROW_BYTES,
        "expected_bytes": expected_bytes,
        "old_control": {"name": "SourceModelAnimationCopy4086_RowBytes", "address": row_bytes},
        "new_control": {"name": "SourceModelAnimationCopy4086_Bytes", "address": stable_bytes},
        "source_field": {"name": "SourceModelAnimationCopy4086_Models", "address": models_address},
        "old_bytes_hex": old_bytes.hex(),
        "new_bytes_hex": new_bytes.hex(),
        "replacement_pasm": replacement,
        "source_anchor": "FlatTrymove_Guard54..FlatTrymove_Guard55; lda long, cmp immediate, beq +3, jmp Bad",
        "source_reference": "src/core/vm/vm_source_model_animation_copy.pasm:8-16,78-91,126-128",
        "read_only_plan": True,
        "writes_emitted": False,
        "instruction_widths_preserved": True,
        "branch_bytes_preserved": old_bytes[7:] == new_bytes[7:],
    }
