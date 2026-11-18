"""Source-faithful bounded selector lifecycle owner for a live preview.

This owner implements only the one-preview, no-PICK transition used by the
admitted He-Man selector profile. It reads the committed source clock and the
immutable port-0 ``newkeys`` snapshot; it never calls animation, retirement,
constructor, clock, or acknowledgement services. Handoff work is reported to
the caller as explicit pending statuses.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dialect_4086 import GAME_SPEED
from source_script_input import authority as input_authority


CONTROL = 0x7E79F0
CONTROL_BYTES = 14
MAGIC = 0xB6E3
STALL_TICKS = 2 * GAME_SPEED
EXIT_TICKS = GAME_SPEED

PHASE_WAIT_ACCEPT = 0
PHASE_READY_ONE = 1
PHASE_READY_TWO = 2
PHASE_RETIRE_PENDING = 3
PHASE_BIRTH_PENDING = 4

STATUS_WAIT_ACCEPT = 0
STATUS_READY_ONE_WAIT = 1
STATUS_READY_TWO_WAIT = 2
STATUS_RETIRE_PENDING = 3
STATUS_BIRTH_PENDING = 4
STATUS_NAVIGATION_PENDING = 5
STATUS_ESCAPE_PENDING = 6
STATUS_INPUT_UNAVAILABLE = 7
STATUS_FAULT = 0xFFFF

INPUT_ANIMATING = 1
INPUT_PREVIEW_LIVE = 2
INPUT_MASK = INPUT_ANIMATING | INPUT_PREVIEW_LIVE


def _key_masks():
    rows = input_authority()["keys"]
    return {row["name"]: int(row["mask"]) & 0xFFFF for row in rows}


def _required_symbols(symbols):
    names = ("SourceClock4086_TimeLo", "VmSourceInput_Ready",
             "VmSourceInput_Count", "VmSourceInput_Data")
    missing = [name for name in names if name not in symbols]
    if missing:
        raise ValueError("SELECTOR_SYMBOL_MISSING:" + ",".join(missing))
    return {name: int(symbols[name]) for name in names}


def validate_control(control=CONTROL, reserved=()):
    """Check one caller-leased block without guessing a different free range."""
    if not isinstance(control, int) or control < 0 or control + CONTROL_BYTES > 0x1000000:
        raise ValueError("SELECTOR_CONTROL_EXTENT")
    if control & 1:
        raise ValueError("SELECTOR_CONTROL_ALIGNMENT")
    if control != CONTROL:
        raise ValueError("SELECTOR_CONTROL_LEASE_REQUIRED")
    # The selected block is an explicit sublease in the retired-video arena.
    # Validate both intrinsic nearby owners and any caller-provided additions.
    protected = [
        (0x7E7A00, 0x7E7A80),  # player binding table
        (0x7E8080, 0x7E8100),  # flat movement/profile scratch
        (0x7FA000, 0x7FB900),  # fully allocated foreign work arena
        (0x7FB900, 0x7FC000),  # damage/audio/player source state and sentinel
        *reserved,
    ]
    for start, end in protected:
        if not (control + CONTROL_BYTES <= start or end <= control):
            raise ValueError("SELECTOR_CONTROL_OVERLAP")
    return control


def emit(symbols, *, control=CONTROL, reserved=(), pick_valid=False):
    """Emit the lifecycle entry points using real assembled symbol addresses.

    ABI (A16/X16): ``Init`` is called once after the real preview is born.
    ``Run`` takes A bits 0=preview animating, 1=preview alive, returns A=status
    with C clear, or A=$FFFF/C set on invalid state. The caller invokes Run
    once at each outer source selector/input-sampling boundary, before
    ``update(0,0)`` and its catch-up ticks, using committed SourceClock time
    and the freshly published physical SourceInput snapshot. Never call it
    once per catch-up logical tick: one immutable ``newkeys`` edge could then
    be consumed repeatedly. X/Y/DBR/DP/SP and P apart from carry are preserved.
    This narrow owner rejects profiles with PICK;
    those need the actual animation/frame-zero service before ready-one can
    proceed.
    """
    if pick_valid:
        raise ValueError("SELECTOR_PICK_PROVIDER_REQUIRED")
    sy = _required_symbols(symbols)
    control = validate_control(control, reserved)
    anybutton = _key_masks()["anybutton"]
    esc = _key_masks()["esc"]
    # selectplayer checks horizontal model cycling before its ANYBUTTON
    # acceptance branch. Direction bits are outside source ANYBUTTON.
    navigation = _key_masks()["moveleft"] | _key_masks()["moveright"]
    if anybutton != 0x1DC2 or esc != 1 or navigation != 0x0C:
        raise ValueError("SELECTOR_INPUT_AUTHORITY_CHANGED")

    c = control
    time_lo = sy["SourceClock4086_TimeLo"]
    time_hi = time_lo + 2
    input_ready = sy["VmSourceInput_Ready"]
    input_count = sy["VmSourceInput_Count"]
    input_new_lo = sy["VmSourceInput_Data"] + 4
    lines = [
        ".a16", ".i16",
        "; 14-byte caller-leased block: magic, phase, stall u32, exit u32, input flags.",
        f"SourceSelectorLifecycle_Control = ${c:06X}",
        f"SourceSelectorLifecycle_Phase = ${c+2:06X}",
        f"SourceSelectorLifecycle_StallLo = ${c+4:06X}",
        f"SourceSelectorLifecycle_StallHi = ${c+6:06X}",
        f"SourceSelectorLifecycle_ExitLo = ${c+8:06X}",
        f"SourceSelectorLifecycle_ExitHi = ${c+10:06X}",
        f"SourceSelectorLifecycle_InputFlags = ${c+12:06X}",
        "",
        "SourceSelectorLifecycle_Init:",
        " php", " rep #$38", " phx", " phy",
        " lda.l SourceSelectorLifecycle_Control",
        " beq SourceSelectorLifecycle_InitFresh",
        " jmp SourceSelectorLifecycle_FaultNoInput",
        "SourceSelectorLifecycle_InitFresh:",
        ".a16", ".i16",
        " lda #0", " sta.l SourceSelectorLifecycle_Phase",
        " sta.l SourceSelectorLifecycle_StallLo",
        " sta.l SourceSelectorLifecycle_StallHi",
        " sta.l SourceSelectorLifecycle_ExitLo",
        " sta.l SourceSelectorLifecycle_ExitHi",
        f" lda #${MAGIC:04X}",
        " sta.l SourceSelectorLifecycle_Control",
        " lda #0", " ply", " plx", " plp", " clc", " rtl",
        "",
        "SourceSelectorLifecycle_Run:",
        ".a16", ".i16", " php", " rep #$38", " phx", " phy", " pha",
        " lda.l SourceSelectorLifecycle_Control",
        f" cmp #${MAGIC:04X}",
        " beq SourceSelectorLifecycle_RunReady",
        " jmp SourceSelectorLifecycle_Fault",
        "SourceSelectorLifecycle_RunReady:",
        ".a16", ".i16",
        " pla", " sta.l SourceSelectorLifecycle_InputFlags",
        " and #$FFFC", " beq SourceSelectorLifecycle_FlagsGood",
        " jmp SourceSelectorLifecycle_FaultNoInput",
        "SourceSelectorLifecycle_FlagsGood:",
        ".a16", ".i16",
        f" lda.l SourceSelectorLifecycle_InputFlags\n and #${INPUT_PREVIEW_LIVE:04X}",
        " bne SourceSelectorLifecycle_PhaseLoad",
        " lda.l SourceSelectorLifecycle_Phase",
        f" cmp #${PHASE_RETIRE_PENDING:04X}",
        " beq SourceSelectorLifecycle_PhaseLoad",
        f" cmp #${PHASE_BIRTH_PENDING:04X}",
        " beq SourceSelectorLifecycle_PhaseLoad",
        " jmp SourceSelectorLifecycle_FaultNoInput",
        "SourceSelectorLifecycle_PhaseLoad:",
        ".a16", ".i16",
        " lda.l SourceSelectorLifecycle_Phase",
        " beq SourceSelectorLifecycle_WaitAccept",
        " cmp #1", " bne SourceSelectorLifecycle_CheckReadyTwo",
        " jmp SourceSelectorLifecycle_ReadyOne",
        "SourceSelectorLifecycle_CheckReadyTwo:",
        " cmp #2", " bne SourceSelectorLifecycle_CheckRetirePending",
        " jmp SourceSelectorLifecycle_ReadyTwo",
        "SourceSelectorLifecycle_CheckRetirePending:",
        " cmp #3", " bne SourceSelectorLifecycle_CheckBirthPending",
        " jmp SourceSelectorLifecycle_RetirePending",
        "SourceSelectorLifecycle_CheckBirthPending:",
        " cmp #4", " bne SourceSelectorLifecycle_InvalidPhase",
        " jmp SourceSelectorLifecycle_BirthPending",
        "SourceSelectorLifecycle_InvalidPhase:",
        " jmp SourceSelectorLifecycle_FaultNoInput",
        "",
        "SourceSelectorLifecycle_WaitAccept:",
        ".a16", ".i16",
        f" lda.l {input_ready}", " cmp #$B4C2",
        " beq SourceSelectorLifecycle_InputCount",
        " lda #0", " jmp SourceSelectorLifecycle_Return",
        "SourceSelectorLifecycle_InputCount:",
        ".a16", ".i16",
        f" lda.l {input_count}", " beq SourceSelectorLifecycle_InputMissing",
        " cmp #5", " bcc SourceSelectorLifecycle_ReadNewKeys",
        " jmp SourceSelectorLifecycle_FaultNoInput",
        "SourceSelectorLifecycle_InputMissing:",
        ".a16", ".i16", " lda #7", " jmp SourceSelectorLifecycle_Return",
        "SourceSelectorLifecycle_ReadNewKeys:",
        ".a16", ".i16",
        f" lda.l {input_new_lo}",
        f" and #${navigation:04X}",
        " beq SourceSelectorLifecycle_CheckEscape",
        " lda #5", " jmp SourceSelectorLifecycle_Return",
        "SourceSelectorLifecycle_CheckEscape:",
        ".a16", ".i16",
        f" lda.l {input_new_lo}", f" and #${esc:04X}",
        " beq SourceSelectorLifecycle_CheckAccept",
        " lda #6", " jmp SourceSelectorLifecycle_Return",
        "SourceSelectorLifecycle_CheckAccept:",
        ".a16", ".i16",
        f" lda.l {input_new_lo}", f" and #${anybutton:04X}",
        " bne SourceSelectorLifecycle_Accept",
        "SourceSelectorLifecycle_WaitAgain:",
        ".a16", ".i16", " lda #0", " jmp SourceSelectorLifecycle_Return",
        "SourceSelectorLifecycle_Accept:",
        ".a16", ".i16",
        f" lda.l {time_lo}", " clc", f" adc #{STALL_TICKS}",
        " sta.l SourceSelectorLifecycle_StallLo",
        f" lda.l {time_hi}", " adc #0",
        " sta.l SourceSelectorLifecycle_StallHi",
        f" lda #${PHASE_READY_ONE:04X}",
        " sta.l SourceSelectorLifecycle_Phase",
        " lda #1", " jmp SourceSelectorLifecycle_Return",
        "",
        "SourceSelectorLifecycle_ReadyOne:",
        ".a16", ".i16",
        f" lda.l SourceSelectorLifecycle_InputFlags\n and #${INPUT_ANIMATING:04X}",
        " beq SourceSelectorLifecycle_BecomeReadyTwo",
        f" lda.l {time_hi}", " cmp.l SourceSelectorLifecycle_StallHi",
        " bcc SourceSelectorLifecycle_ReadyOneWait",
        " bne SourceSelectorLifecycle_BecomeReadyTwo",
        f" lda.l {time_lo}", " cmp.l SourceSelectorLifecycle_StallLo",
        " bcc SourceSelectorLifecycle_ReadyOneWait",
        " beq SourceSelectorLifecycle_ReadyOneWait",
        "SourceSelectorLifecycle_BecomeReadyTwo:",
        ".a16", ".i16",
        f" lda.l {time_lo}", " clc", f" adc #{EXIT_TICKS}",
        " sta.l SourceSelectorLifecycle_ExitLo",
        f" lda.l {time_hi}", " adc #0",
        " sta.l SourceSelectorLifecycle_ExitHi",
        f" lda #${PHASE_READY_TWO:04X}",
        " sta.l SourceSelectorLifecycle_Phase",
        " lda #2", " jmp SourceSelectorLifecycle_Return",
        "SourceSelectorLifecycle_ReadyOneWait:",
        ".a16", ".i16", " lda #1", " jmp SourceSelectorLifecycle_Return",
        "",
        "SourceSelectorLifecycle_ReadyTwo:",
        ".a16", ".i16",
        f" lda.l {time_hi}", " cmp.l SourceSelectorLifecycle_ExitHi",
        " bcc SourceSelectorLifecycle_ReadyTwoWait",
        " bne SourceSelectorLifecycle_BecomeRetirePending",
        f" lda.l {time_lo}", " cmp.l SourceSelectorLifecycle_ExitLo",
        " bcc SourceSelectorLifecycle_ReadyTwoWait",
        " beq SourceSelectorLifecycle_ReadyTwoWait",
        "SourceSelectorLifecycle_BecomeRetirePending:",
        ".a16", ".i16",
        f" lda #${PHASE_RETIRE_PENDING:04X}",
        " sta.l SourceSelectorLifecycle_Phase",
        " lda #3", " jmp SourceSelectorLifecycle_Return",
        "SourceSelectorLifecycle_ReadyTwoWait:",
        ".a16", ".i16", " lda #2", " jmp SourceSelectorLifecycle_Return",
        "",
        "SourceSelectorLifecycle_RetirePending:",
        ".a16", ".i16",
        f" lda.l SourceSelectorLifecycle_InputFlags\n and #${INPUT_PREVIEW_LIVE:04X}",
        " bne SourceSelectorLifecycle_RetireWait",
        f" lda #${PHASE_BIRTH_PENDING:04X}",
        " sta.l SourceSelectorLifecycle_Phase",
        " lda #4", " jmp SourceSelectorLifecycle_Return",
        "SourceSelectorLifecycle_RetireWait:",
        ".a16", ".i16", " lda #3", " jmp SourceSelectorLifecycle_Return",
        "SourceSelectorLifecycle_BirthPending:",
        ".a16", ".i16", " lda #4", " jmp SourceSelectorLifecycle_Return",
        "",
        "SourceSelectorLifecycle_Return:",
        ".a16", ".i16", " ply", " plx", " plp", " clc", " rtl",
        "SourceSelectorLifecycle_Fault:",
        ".a16", ".i16", " pla", "SourceSelectorLifecycle_FaultNoInput:",
        ".a16", ".i16", " lda #$FFFF", " ply", " plx", " plp", " sec", " rtl",
    ]
    return "\n".join(lines) + "\n"


class Lifecycle:
    """Small reference state machine used by focused provider tests."""

    def __init__(self, pick_valid=False):
        if pick_valid:
            raise ValueError("SELECTOR_PICK_PROVIDER_REQUIRED")
        self.phase = None
        self.stalltime = 0
        self.exitdelay = 0

    def init(self):
        if self.phase is not None:
            return STATUS_FAULT
        self.phase = PHASE_WAIT_ACCEPT
        return STATUS_WAIT_ACCEPT

    def run(self, time, newkeys=0, *, input_ready=True, port_count=1,
            animating=False, preview_live=True):
        if self.phase is None or not 0 <= time <= 0xFFFFFFFF:
            return STATUS_FAULT
        if not isinstance(newkeys, int) or not 0 <= newkeys <= 0xFFFFFFFF:
            return STATUS_FAULT
        if not preview_live and self.phase < PHASE_RETIRE_PENDING:
            return STATUS_FAULT
        if self.phase == PHASE_WAIT_ACCEPT:
            if not input_ready:
                return STATUS_WAIT_ACCEPT
            if not isinstance(port_count, int) or not 0 <= port_count <= 4:
                return STATUS_FAULT
            if port_count == 0:
                return STATUS_INPUT_UNAVAILABLE
            masks = _key_masks()
            nav = masks["moveleft"] | masks["moveright"]
            if newkeys & nav:
                return STATUS_NAVIGATION_PENDING
            if newkeys & masks["esc"]:
                return STATUS_ESCAPE_PENDING
            if not newkeys & masks["anybutton"]:
                return STATUS_WAIT_ACCEPT
            self.stalltime = (time + STALL_TICKS) & 0xFFFFFFFF
            self.phase = PHASE_READY_ONE
            return STATUS_READY_ONE_WAIT
        if self.phase == PHASE_READY_ONE:
            if (not animating) or time > self.stalltime:
                self.exitdelay = (time + EXIT_TICKS) & 0xFFFFFFFF
                self.phase = PHASE_READY_TWO
                return STATUS_READY_TWO_WAIT
            return STATUS_READY_ONE_WAIT
        if self.phase == PHASE_READY_TWO:
            if time > self.exitdelay:
                self.phase = PHASE_RETIRE_PENDING
                return STATUS_RETIRE_PENDING
            return STATUS_READY_TWO_WAIT
        if self.phase == PHASE_RETIRE_PENDING:
            if not preview_live:
                self.phase = PHASE_BIRTH_PENDING
                return STATUS_BIRTH_PENDING
            return STATUS_RETIRE_PENDING
        if self.phase == PHASE_BIRTH_PENDING:
            return STATUS_BIRTH_PENDING
        return STATUS_FAULT


def main():
    import argparse
    import json
    import re
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    text = args.symbols.read_text(encoding="utf-8")
    sy = {}
    for name in ("SourceClock4086_TimeLo", "VmSourceInput_Ready",
                 "VmSourceInput_Count", "VmSourceInput_Data"):
        match = re.search(r"^([0-9A-Fa-f]+):([0-9A-Fa-f]+) " + re.escape(name) + r"$", text, re.M)
        if not match:
            raise SystemExit("SELECTOR_SYMBOL_MISSING:" + name)
        sy[name] = (int(match[1], 16) << 16) | int(match[2], 16)
    source = ".snes\n.bank 48\n.org $8000\n" + emit(sy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(source, encoding="utf-8")
    print("emitted source selector lifecycle ABI; controls=$%06X..$%06X" %
          (CONTROL, CONTROL + CONTROL_BYTES))


if __name__ == "__main__":
    main()
