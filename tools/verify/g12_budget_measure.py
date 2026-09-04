#!/usr/bin/env python3
"""Measure the accepted G12 baseline NMI budget at real Mesen boundaries.

This is measurement only.  It does not alter WRAM, enqueue extra transfers,
or apply the rejected G12A residency candidate.  Each sample stops at the
existing Core_Nmi_Play entry and completion labels, then reads the real SNES
CPU cycle counter.  DMA payload accounting is reported separately because
the proposed grouped queue is not present in the baseline ROM.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import pasm_constant_in


def sym(name):
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'main.sym')
    with open(path, encoding='utf-8') as f:
        for line in f:
            m = re.match(r'([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+' + re.escape(name) + r'$', line.strip())
            if m:
                return (int(m.group(1), 16) << 16) | int(m.group(2), 16)
    raise KeyError(name)


def main():
    trace_path = os.path.join(os.path.dirname(__file__), '..', '..',
                              'out', 'g12', 'baseline_600.json')
    with open(trace_path, encoding='utf-8') as f:
        trace = json.load(f)
    # SNES DMA uses 8 master cycles per byte in the normal 2-register word
    # mode used by frame/OAM transfers.  Keep this arithmetic explicit and
    # separate from the observed CPU span.
    payload = {'oam': 544, 'one_frame': 768, 'two_frames': 1536,
               'hud_max': 256}
    master_per_byte = 8
    result = {
        'rom_scope': 'accepted distribution/bor.sfc; measurement only',
        'symbols': {'entry': sym('Core_Nmi_Play'), 'done': sym('Core_Nmi_Play__done')},
        'accepted_trace': {'sample_frames': trace['summary']['sample_frames'],
                           'nmi_delta': trace['summary']['nmi_delta'],
                           'nmi_over_samples': trace['summary']['nmi_over_samples'],
                           'max_dma_active_at_sample_boundary': trace['summary']['max_dma_active_at_sample_boundary'],
                           'max_dma_budget_at_sample_boundary': trace['summary']['max_dma_budget_at_sample_boundary']},
        'dma_payload_bytes': payload,
        'dma_payload_cycles': {k: v * master_per_byte for k, v in payload.items()},
        'budget_cap_bytes': pasm_constant_in('src/core/dma.pasm', 'DMA_TRANSFER_MAX_BYTES'),
        'proposed_two_frame_plus_oam_plus_hud_bytes':
            payload['two_frames'] + payload['oam'] + payload['hud_max'],
        'proposed_two_frame_plus_oam_plus_hud_headroom_bytes':
            0x0B00 - payload['two_frames'] - payload['oam'] - payload['hud_max'],
        'cpu_cycle_measurement': 'UNAVAILABLE: installed MCP endpoint rejects get_cpu_state',
        'note': 'Current ROM has no grouped queue; two-frame CPU/NMI behavior is not claimed here.',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
