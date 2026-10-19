"""Reusable native dispatcher for SourceWorldTick4086 service phases."""
import re
from collections.abc import Mapping


_LABEL = re.compile(r"[A-Za-z_]\w*\Z")


def emit(symbols, providers):
    """Emit a resumable dispatcher. ``providers`` maps phase 1..12 to JSL labels.

    The caller owns Begin and Commit. A provider returns C=1 on fault, A=0 on
    completion, or A=1 while pending. Providers preserve M/X, DBR/DP under the
    native calling convention, and return a 16-bit status. The dispatcher
    rejects mode violations, restores the caller's outer registers, and
    acknowledges only the statically dispatched phase after completion.
    """
    if not isinstance(providers, Mapping):
        raise ValueError("LIVE_WORLD_PROVIDERS")
    for phase, label in providers.items():
        if isinstance(phase, bool) or not isinstance(phase, int) or not 1 <= phase <= 12:
            raise ValueError("LIVE_WORLD_PHASE")
        if not isinstance(label, str) or not _LABEL.fullmatch(label):
            raise ValueError("LIVE_WORLD_PROVIDER_LABEL")
    for name in ("SourceWorldTick4086_Poll", "SourceWorldTick4086_Ack", "SourceWorldTick4086_Phase"):
        if not isinstance(symbols, Mapping) or name not in symbols:
            raise ValueError("LIVE_WORLD_SYMBOL_" + name)

    code = ["""LiveWorldDispatch_Run:
.a16
.i16
    php
    phb
    phd
    rep #$38
    phx
    phy
LiveWorldDispatch_Poll:
.a16
.i16
    jsl SourceWorldTick4086_Poll
    rep #$38
    bcs LiveWorldDispatch_Fault
    cmp #0
    beq LiveWorldDispatch_Complete
    cmp #13
    bcs LiveWorldDispatch_Fault
"""]
    for phase in sorted(providers):
        code.append(f"""    cmp #{phase}
    beq LiveWorldDispatch_Call_{phase}
""")
    code.append("""    ; A nonzero phase with no bound provider remains outstanding.
    lda.l SourceWorldTick4086_Phase
    jmp LiveWorldDispatch_ReturnPending
""")
    for phase, label in sorted(providers.items()):
        code.append(f"""LiveWorldDispatch_Call_{phase}:
.a16
.i16
    ; Stack layout after PHP/PHB/PHD/PHX/PHY: X=3,s and Y=1,s.
    lda 3,s
    tax
    lda 1,s
    tay
    jsl {label}
    php
    rep #$38
    tax
    lda 1,s
    and #$31
    beq LiveWorldDispatch_ProviderAbiValid_{phase}
    sep #$20
    pla
    rep #$38
    jmp LiveWorldDispatch_Fault
LiveWorldDispatch_ProviderAbiValid_{phase}:
.a16
.i16
    sep #$20
    pla
    rep #$38
    txa
    cmp #0
    beq LiveWorldDispatch_Ack_{phase}
    cmp #1
    beq LiveWorldDispatch_ProviderPending
    jmp LiveWorldDispatch_Fault
LiveWorldDispatch_Ack_{phase}:
.a16
.i16
    lda #{phase}
    jsl SourceWorldTick4086_Ack
    rep #$38
    bcs LiveWorldDispatch_Fault
    jmp LiveWorldDispatch_Poll
""")
    code.append("""LiveWorldDispatch_Complete:
.a16
.i16
    lda #0
    jmp LiveWorldDispatch_ReturnGood
LiveWorldDispatch_ProviderPending:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
LiveWorldDispatch_ReturnPending:
.a16
.i16
LiveWorldDispatch_ReturnGood:
.a16
.i16
    ply
    plx
    pld
    plb
    plp
    clc
    rtl
LiveWorldDispatch_Fault:
.a16
.i16
    ply
    plx
    pld
    plb
    plp
    sec
    rtl
""")
    text = "".join(code)

    # Convert all conditionals to a short inverse branch over an absolute JMP;
    # this keeps the emitted fragment valid regardless of caller placement.
    serial = [0]
    def relax(match):
        serial[0] += 1
        branch, target = match.groups()
        guard = f"LiveWorldDispatch_Guard{serial[0]}"
        inverse = {"beq": "bne", "bne": "beq", "bcs": "bcc"}[branch]
        return f"    {inverse} {guard}\n    jmp {target}\n{guard}:\n.a16\n.i16"
    text = re.sub(r"^    (beq|bne|bcs) (LiveWorldDispatch_\w+)$", relax, text, flags=re.M)

    for name in sorted((k for k in symbols if isinstance(k, str)), key=len, reverse=True):
        if name.startswith("SourceWorldTick4086_"):
            text = re.sub(r"\b" + re.escape(name) + r"\b", str(symbols[name]), text)
    return text
