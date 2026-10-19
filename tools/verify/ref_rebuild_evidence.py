"""Pinned READY control, exact ref writes, context and post-map timing evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fused_capture_evidence as capture
import ready_validate_evidence as ready

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / 'out/byor-motu-ready-validate-v1'
BASE_ROM_SHA256 = 'ad04ee314d72a45c5f8785ea749decf612ae974af0366c0eb9bf48e57f724c00'
BASE_RECEIPT = ROOT / 'docs/receipts/byor-motu-ready-validate.json'
BASE_RECEIPT_SHA256 = 'f7b43163ab668751afeb40bfb0d16bb07e9ddf780dcb6f6407f26255e2910346'
BASE_SEAL = capture.CaptureSeal(
    'bd889ec5ebcc8d68746c5fdf6e7975f3bdff0622077ef23352b9e3519e2f1e56',
    '45add5d4518d6400db57b5b239199e2b6b6e71a3d76cee4815248cbae2fa6591')
REGISTERS = ready.REGISTERS


def require(ok, code):
    if not ok:
        raise ValueError('REF_REBUILD:' + code)


def load_baseline(path=BASE_RECEIPT):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == BASE_RECEIPT_SHA256, 'BASE_RECEIPT_DIGEST')
    result = json.loads(raw)
    require(result['candidate_rom_sha256'] == BASE_ROM_SHA256, 'BASE_RECEIPT_ROM')
    return result


def postmap_intervals(path):
    """Use unchanged original NbMapsComplete and NbVisible exec callbacks."""
    starts, result = {}, {}
    for event in ready.events(path):
        data = event['data']
        if event['kind'] != 'PHASE' or data[0] not in ('NbMapsComplete', 'NbVisible'):
            continue
        require(len(data) >= 2, 'POSTMAP_RECORD')
        txn = data[1]
        if data[0] == 'NbMapsComplete':
            require(txn not in starts, 'POSTMAP_DUPLICATE_START')
            starts[txn] = event
        else:
            require(txn in starts and txn not in result, 'POSTMAP_INCOMPLETE')
            start = starts[txn]
            elapsed = event['clock'] - start['clock']
            require(elapsed > 0, 'POSTMAP_CLOCK_ORDER')
            result[txn] = dict(master_clocks=elapsed, start_clock=start['clock'],
                finish_clock=event['clock'], start_frame=start['frame'], finish_frame=event['frame'])
    require(bool(result) and set(result) == set(starts), 'POSTMAP_INCOMPLETE')
    return result


def _words(value, count):
    require(isinstance(value, str) and len(value) == count * 4, 'WORDS_LENGTH')
    try:
        raw = bytes.fromhex(value)
    except ValueError as error:
        raise ValueError('REF_REBUILD:WORDS_HEX') from error
    require(len(raw) == count * 2, 'WORDS_LENGTH')
    return [int.from_bytes(raw[i:i + 2], 'little') for i in range(0, len(raw), 2)]


def expected_rebuild(refs, maps):
    require(len(refs) == 768 and len(maps) == 1024 and all(0 <= x < 768 for x in maps),
            'INPUT_WORDS_OR_SLOTS')
    result = list(refs); trace = []
    def write(slot, value):
        result[slot] = value
        address = 0xd000 + 2 * slot
        trace.extend((f'{address:04x}{value & 255:02x}', f'{address + 1:04x}{value >> 8:02x}'))
    for slot in range(768):
        write(slot, result[slot] & 0x8000)
    for slot in maps:
        write(slot, result[slot] + 1)
    return result, ''.join(trace)


def native_rebuilds(path):
    intervals = postmap_intervals(path)
    entries, scans = {}, {}
    for event in ready.events(path):
        data = event['data']
        if event['kind'] == 'RF_ENTRY':
            require(len(data) == 11 and data[0] not in entries, 'ENTRY_RECORD')
            entries[data[0]] = (event, ready._registers(data[1:9]),
                               _words(data[9], 768), _words(data[10], 1024))
        elif event['kind'] == 'RF_SCAN':
            require(len(data) == 13 and data[0] in entries and data[0] not in scans,
                    'EXIT_RECORD')
            txn = data[0]; entry, before, refs, maps = entries[txn]
            after = ready._registers(data[2:10])
            output, output_map = _words(data[10], 768), _words(data[11], 1024)
            elapsed = int(data[1])
            require(elapsed == event['clock'] - entry['clock'] and elapsed > 0, 'SCAN_CLOCKS')
            require(before['d'] == after['d'] == 0x3400 and before['ps'] & 0x30 == 0,
                    'ENTRY_ABI')
            expected, trace = expected_rebuild(refs, maps)
            require(output == expected and output_map == maps, 'REFERENCE_TRANSFORM')
            require(data[12] == trace, 'ORDERED_BYTE_WRITE_TRACE')
            require(after['a'] == expected[maps[-1]] and after['x'] == 2 * maps[-1]
                    and after['y'] == 2048, 'EXIT_REGISTERS')
            require(all(after[k] == before[k] for k in ('d', 'dbr', 'sp', 'counter'))
                    and after['ps'] == ((before['ps'] & 0x7c) | 3), 'EXIT_CONTEXT')
            require(txn in intervals and intervals[txn]['start_clock'] < entry['clock']
                    < event['clock'] < intervals[txn]['finish_clock'], 'SCAN_PHASE_ORDER')
            scans[txn] = dict(master_clocks=elapsed, cleared_words=768, map_words=1024,
                byte_writes=3584, exact_reference_transform=True, ordered_write_trace=True,
                context_preserved=True)
    require(bool(scans) and set(scans) == set(entries) == set(intervals), 'SCAN_INVENTORY')
    return scans


def compare_intervals(current, baseline):
    require(set(current) == set(baseline), 'POSTMAP_TRANSACTION_DRIFT')
    result = {}
    for txn, old in baseline.items():
        new = current[txn]
        require(new['master_clocks'] < old['master_clocks'], 'POSTMAP_NOT_IMPROVED:' + txn)
        result[txn] = dict(before_clocks=old['master_clocks'], after_clocks=new['master_clocks'],
                           saved_clocks=old['master_clocks'] - new['master_clocks'])
    return result


def verify_timing(report, baseline):
    for epoch in ('epoch2', 'epoch3'):
        require(report[epoch]['fields'] <= baseline['candidate_' + epoch]['fields'] and
                report[epoch]['master_clocks'] < baseline['candidate_' + epoch]['master_clocks'],
                epoch.upper() + '_REGRESSION_OR_NO_GAIN')
