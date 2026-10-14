"""Experimental opt-in direct pair DMA for the BYOR MOTU warm component renderer.

Replace both call sites to WarmStage with a pair of channel-7 DMA transfers
straight from the already-computed $42D680/$42D6C0 scratch buffers. This is
ONLY valid after OnlineBlank has made the PPU safe for arbitrarily timed DMA.

Target: snes-bor feat/byor-motu 7e582347..., generated 65816 assembly after
warm residency + occupancy + tile fusion transforms. Not tested on Mesen here.

Rationale: profiler measured 539,680 master clocks/25.127961 ms executing the
scratch->stage MVNs in epoch 17. Direct DMA removes those two MVNs but increases
VRAM DMA descriptor count, so native timing/correctness must decide whether to
keep it. Existing renderer remains available without this opt-in transform.
"""
from __future__ import annotations

from collections.abc import Sequence

class DirectDMAContractError(ValueError):
    pass

BANK57_START = '.org $D400'


def _emit_byte_write(reg: int, value: int) -> list[str]:
    assert 0 <= reg <= 0xFFFFFF and 0 <= value <= 255
    return [f' lda #${value:02X}', f' sta.l ${reg:06X}']


def _dma_fields(source_low: int) -> list[str]:
    """Set each register explicitly: SNES DMA hardware may mutate A1T/size."""
    result = []
    for reg, value in [
        (0x004370, 1),       # DMA mode 1: low and high $2118/$2119
        (0x004371, 0x18),    # BBAD $18 = $2118
        (0x004372, source_low),
        (0x004373, 0xD6),
        (0x004374, 0x42),     # BW-RAM bank 42
    ]:
        result += _emit_byte_write(reg, value)
    return result


def emit_direct_pair_asm() -> list[str]:
    """Both DMA sources and VRAM destinations are the existing leased pairs.

    Input: DP $2C = physical pair slot 0..767; A16/I16, D=$3400.
    Scratch HIGH at $42D680 length 64; LOW at $42D6C0 length 16.
    No X, Y, D, DBR, or stack changes; returns A16 with X/Y untouched.
    Preconditions: forced blank, channel 7 exclusively owned, $2115 word
    increment-by-one, completed scratch output, VRAM slot leased and checked.
    """
    lines = [BANK57_START, 'WarmDirectPair:', '.a16', '.i16']
    # Destination word index: HIGH = slot*32, LOW = $6000 + slot*8.
    lines += [' lda $2C', *([' asl a'] * 5), ' sta.l $002116',
              ' lda #64', ' sta.l $004375', ' sep #$20', '.a8']
    lines += _dma_fields(0x80)
    lines += _emit_byte_write(0x00420B, 0x80)  # start DMA channel 7
    # Observer expects the same post-DMA marker convention as WarmFlush.
    lines += ['OnlineDmaDone8:', ' rep #$20', '.a16',
              ' lda $2C', *([' asl a'] * 3), ' clc', ' adc #$6000',
              ' sta.l $002116', ' lda #16', ' sta.l $004375',
              ' sep #$20', '.a8']
    lines += _dma_fields(0xC0)
    lines += _emit_byte_write(0x00420B, 0x80)
    lines += ['OnlineDmaDone9:', ' rep #$20', '.a16', ' rts']
    return lines


def transform(lines: Sequence[str]) -> list[str]:
    """Fail-closed generated-assembly splice; old warm emitter is preserved.

    Inject into known unused $D400..$DFFF bank-57 range, checked by Sol's
    native symbol/byte map before acceptance. Two existing callers are after
    OnlineBlank and before OnlineComplete. The original WarmStage/WarmFlush
    code remains present and selectable when the opt-in switch is absent.
    """
    a = list(lines)
    required = ['OnlineBlank:', 'WarmRestore:', 'OnlineTransfer:',
                'WarmStage:', 'WarmFlush:', 'OnlineComplete:',
                '.org $E000', '.org $E200', '.org $F000',
                'OnlineDmaDone5:', 'OnlineDmaDone6:', 'OnlineDmaDone7:']
    for label in required:
        if a.count(label) != 1:
            raise DirectDMAContractError(f'DIRECT_PAIR_LABEL_DRIFT:{label}')
    if a.count(' jsr WarmStage') != 2:
        raise DirectDMAContractError('DIRECT_PAIR_STAGE_CALLSITE_DRIFT')
    if 'WarmDirectPair:' in a or 'OnlineDmaDone8:' in a or BANK57_START in a:
        raise DirectDMAContractError('DIRECT_PAIR_ALREADY_PRESENT')
    if not (a.index('OnlineBlank:') < a.index('WarmRestore:') < a.index('OnlineTransfer:')
            < a.index('OnlineComplete:')):
        raise DirectDMAContractError('DIRECT_PAIR_PUBLICATION_ORDER_DRIFT')
    calls = [i for i, s in enumerate(a) if s == ' jsr WarmStage']
    if not (a.index('WarmRestore:') < calls[0] < a.index('OnlineTransfer:')
            < calls[1] < a.index('OnlineComplete:')):
        raise DirectDMAContractError('DIRECT_PAIR_CALLSITE_ORDER_DRIFT')
    for i in calls:
        a[i] = ' jsr WarmDirectPair'
    # Last routine before the standard E000 atlas kernel / E200 fusion.
    at = a.index('.org $E000')
    a[at:at] = emit_direct_pair_asm()
    return a


def packet(slot: int, high: bytes, low: bytes) -> tuple[tuple[int, bytes], tuple[int, bytes]]:
    """Independent reference packet semantics; addresses are byte offsets."""
    if not 0 <= slot < 768 or len(high) != 64 or len(low) != 16:
        raise ValueError('DIRECT_PAIR_PACKET_DOMAIN')
    return ((slot * 64, high), (49152 + slot * 16, low))
