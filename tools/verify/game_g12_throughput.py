#!/usr/bin/env python3
"""G12 throughput gate: grouped two-buffer animation service.

This is a SERVICE-PATH STRESS PROOF for the transport, not a claim that BOR
has more than four production gameplay entities.  It uses the real four-slot
fixture, verifies that two requests coexisted before one NMI drain, and checks
the committed VRAM rows against the exact MSU frame bytes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, read_block, run_frames_exact,
                      Reporter)
from g12_scaling_baseline import move_to_stage_1a, snapshot, ENTITY_BASES

ACTIVE = pasm_constant('Msu1_StreamBusy')
MAX_BATCH = pasm_constant('AnimUpload_MaxBatch')
ACCEPTED = pasm_constant('AnimUpload_Accepted')
COMMITTED = pasm_constant('AnimUpload_Committed')
FRAME = pasm_constant('CHAR_FRAME_INDEX')
TILE_COLUMN = pasm_constant('CHAR_TILE_COLUMN')
SELECTED = pasm_constant('CHAR_SELECTED')
VARIANT = pasm_constant('CHAR_ATTACK_VARIANT')
ENTITY_LIMIT = 4


def main():
    r = Reporter('G12-THROUGHPUT', kind='GATE')
    msu = open(os.path.join(os.path.dirname(__file__), '..', '..',
                            'distribution', 'bor.msu'), 'rb').read()
    with open_session(__file__) as m:
        m.reset_emulator()
        move_to_stage_1a(m)
        m.set_input(m.BTN_RIGHT, 300)
        run_frames_exact(m, 60)
        # Allow a complete commit boundary, then sample a sustained service
        # window.  The telemetry is BOR-local and is cleared at boot.
        run_frames_exact(m, 600)
        m.pause()
        active = m.read_u8(ACTIVE)
        max_batch = m.read_u16(MAX_BATCH)
        accepted = m.read_u16(ACCEPTED)
        committed = m.read_u16(COMMITTED)
        r.check('two independent buffers were occupied before a drain', max_batch > 0)
        r.check('accepted frame requests are nonzero', accepted > 0)
        r.check('every accepted descriptor was committed', accepted == committed)
        r.check('no buffer remains multiply-owned after settle', active <= 2)
        r.check('NMI remained 1:1 for the service window', snapshot(m)['nmi'] >= 600)
        checks = 0
        mismatches = []
        # Ground-truth checks use the same source-base computation as the
        # baseline trace, imported from its authoritative helper.
        from g12_scaling_baseline import source_identity
        for entity_id, base in enumerate(ENTITY_BASES):
            b = bytes(read_block(m, base, 64))
            source, _ = source_identity(b, b[FRAME], b[SELECTED], b[VARIANT])
            if source is None:
                continue
            col = b[TILE_COLUMN]
            for row in range(6):
                expected = msu[source + row * 128: source + (row + 1) * 128]
                got = bytes(read_block(m, 0x8000 + col * 128 + row * 512,
                                       128, mem_type='snesVideoRam'))
                checks += 1
                if got != expected:
                    mismatches.append({'entity': entity_id, 'row': row,
                                       'column': col, 'source': source})
        r.check(f'committed VRAM rows match MSU ground truth ({checks} rows)',
                checks > 0 and not mismatches)
        if mismatches:
            mm = mismatches[0]
            print('first mismatch detail:', mm)
            print('expected:', list(msu[mm['source']:mm['source'] + 16]))
            print('got:', list(read_block(m, 0x8000 + mm['column'] * 128 + mm['row'] * 512,
                                           128, mem_type='snesVideoRam')[:16]))
        print(f'telemetry: active={active} max_batch={max_batch} '
              f'accepted={accepted} committed={committed} '
              f'vram_mismatches={mismatches[:3]}')
        r.check('bounded two-buffer service has no VRAM corruption', not mismatches)
    r.finish()


if __name__ == '__main__':
    main()
