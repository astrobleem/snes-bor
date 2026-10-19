"""Initialize the real scratch controls used by the native live player chain.

This routine only clears caller-owned scratch blocks and installs their native
control tags. It does not establish a player, input history, source descriptor,
clock, animation handle, callback, or module-tail lease. In particular, the
birth-owned rows and the generation-bound player-state/pending-jump controls
are deliberately outside this initializer.

Before ForeignAIRun_Begin/Continue, the caller still needs to install the
SourceWorld/SourceAI descriptors and canonical player input-history rows,
SourcePlayerState's generation-bound module-tail lease, pending-jump birth
storage, and the real SourceAnimationInit/idle/default-player descriptors and
tables used by the selected source. Actual callbacks, time, and input must come
from those owners at runtime.
"""
from collections.abc import Mapping


# These are scratch/work areas from source_foreign_state_layout.layout().
# Persistent source rows and birth-owned controls are intentionally excluded.
SCRATCH_REGIONS = (
    "input_scratch",
    "input_snapshot",
    "combo_sequence",
    "input_owner",
    "binding_controls",
    "costmove_controls",
    "combo_controls",
    "attack_chain_controls",
    "run_tuple_controls",
    "ground_controls",
    "ground_binding_controls",
    "find_here_empty_controls",
    "ground_services_controls",
    "common_idle_controls",
    "run_cancel_controls",
    "run_binding_controls",
    "special_controls",
    "special_binding_controls",
    "special_services_controls",
    "charge_services_controls",
    "pain_services_controls",
    "player_early_controls",
    "player_fall_controls",
    "player_jump_controls",
    "player_lie_controls",
    "player_directional_controls",
    "player_button_controls",
    "player_release_controls",
    "player_attack_controls",
    "tryjump_controls",
    "dojump_controls",
    "player_jump_entry_controls",
)

# Native readiness/control tags checked by the corresponding real emitters.
# Values are verified against their consumers and the generated Lua setup in
# tools/verify/m4_animation_callback_owner_native.py.
CONTROL_MAGICS = {
    "input_owner": 0xB674,
    "costmove_controls": 0xB670,
    "combo_controls": 0xB673,
    "attack_chain_controls": 0xB675,
    "run_tuple_controls": 0xB678,
    "ground_controls": 0xB679,
    "ground_binding_controls": 0xB67C,
    "find_here_empty_controls": 0xB67D,
    "ground_services_controls": 0xB67E,
    "common_idle_controls": 0xB680,
    "run_cancel_controls": 0xB677,
    "run_binding_controls": 0xB681,
    "special_controls": 0xB682,
    "special_binding_controls": 0xB684,
    "special_services_controls": 0xB685,
    "charge_services_controls": 0xB686,
    "pain_services_controls": 0xB687,
    "player_early_controls": 0xB688,
    "player_fall_controls": 0xB689,
    "player_jump_controls": 0xB68A,
    "player_lie_controls": 0xB68B,
    "player_directional_controls": 0xB68C,
    "player_button_controls": 0xB68D,
    "player_release_controls": 0xB68F,
    "player_attack_controls": 0xB690,
    "tryjump_controls": 0xB692,
    "dojump_controls": 0xB693,
    "player_jump_entry_controls": 0xB694,
}

# These are compile-time control defaults from the generated ground-owner
# setup. Other actor-dependent ground values are populated by the real owner.
CONTROL_DEFAULT_WORDS = (
    ("ground_controls", 20, 1),
    ("ground_controls", 76, 1),
    ("ground_controls", 80, 0),
    ("ground_controls", 82, 2),
)

PERSISTENT_OR_BIRTH_OWNED = (
    "input_history",
    "entity_movetime",
    "entity_combo_tail",
    "binding_shadow",
    "entity_combostyle",
    "entity_run_tuple",
    "player_state_controls",
    "pending_jump_controls",
    "attack_identity_sequence",
    "global_fall_speedup",
)


def _regions(arena):
    if not isinstance(arena, Mapping) or not isinstance(arena.get("regions"), list):
        raise ValueError("LIVE_PLAYER_CONTROLS_LAYOUT")
    found = {}
    spans = []
    for region in arena["regions"]:
        try:
            name = region["name"]
            start = region["address"]
            size = region["bytes"]
        except (KeyError, TypeError):
            raise ValueError("LIVE_PLAYER_CONTROLS_LAYOUT") from None
        if (not isinstance(name, str) or type(start) is not int or type(size) is not int
                or not 0 <= start <= 0xFFFFFF or size <= 0 or start + size > 0x1000000
                or name in found):
            raise ValueError("LIVE_PLAYER_CONTROLS_LAYOUT")
        found[name] = (start, size)
        spans.append((start, start + size, name))
    spans.sort()
    if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
        raise ValueError("LIVE_PLAYER_CONTROLS_LAYOUT_OVERLAP")
    for name in (*SCRATCH_REGIONS, *PERSISTENT_OR_BIRTH_OWNED):
        if name not in found:
            raise ValueError("LIVE_PLAYER_CONTROLS_REGION:" + name)
    for name, magic in CONTROL_MAGICS.items():
        if found[name][1] < 2 or magic > 0xFFFF:
            raise ValueError("LIVE_PLAYER_CONTROLS_MAGIC_EXTENT:" + name)
    for name, offset, _ in CONTROL_DEFAULT_WORDS:
        if offset + 2 > found[name][1]:
            raise ValueError("LIVE_PLAYER_CONTROLS_DEFAULT_EXTENT:" + name)
    return found


def emit(symbols, arena):
    """Return PASM for an ABI-preserving scratch initializer.

    ``symbols`` is accepted to match the live-world compile helpers; no
    external symbol is written or required. Arena is the real layout mapping
    produced by source_foreign_state_layout.layout().
    """
    if not isinstance(symbols, Mapping):
        raise ValueError("LIVE_PLAYER_CONTROLS_SYMBOLS")
    regions = _regions(arena)
    lines = [
        "LivePlayerControls_Initialize:",
        ".a16",
        ".i16",
        " php",
        " rep #$38",
        " phx",
        " pha",
        " lda #0",
    ]
    for index, name in enumerate(SCRATCH_REGIONS):
        address, size = regions[name]
        if size & 1:
            raise ValueError("LIVE_PLAYER_CONTROLS_ODD_EXTENT:" + name)
        loop = f"LivePlayerControls_Clear{index}"
        lines.extend((
            " ldx #0",
            loop + ":",
            ".a16",
            ".i16",
            f" sta.l ${address:06X},x",
            " inx",
            " inx",
            f" cpx #{size}",
            f" bcc {loop}",
        ))
    for name, magic in CONTROL_MAGICS.items():
        address, _ = regions[name]
        lines.extend((f" lda #${magic:04X}", f" sta.l ${address:06X}"))
    for name, offset, value in CONTROL_DEFAULT_WORDS:
        address, _ = regions[name]
        lines.extend((f" lda #{value}", f" sta.l ${address + offset:06X}"))
    lines.extend((" pla", " plx", " plp", " clc", " rtl"))
    return "\n".join(lines) + "\n"
