"""Pinned baseline and independent native evidence for READY map validation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fused_capture_evidence as capture

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / 'out/byor-motu-fused-coverage-certified-v1'
BASE_ROM_SHA256 = '695e623a3eb5dab69feada4a3a72ff6d233227214cacbcfb570eb385dfec36f0'
BASE_RECEIPT = ROOT / 'docs/receipts/byor-motu-fused-coverage.json'
BASE_RECEIPT_SHA256 = '50e6675c7637e1574018222515893d4479deccc230cfbbffa6d3c2d64a5d7bb2'
REGISTERS = ('a', 'x', 'y', 'd', 'dbr', 'sp', 'ps', 'counter')


def require(ok, code):
    if not ok:
        raise ValueError('READY_VALIDATE:' + code)


def load_baseline(path=BASE_RECEIPT):
    path = Path(path)
    require(path.is_file(), 'BASE_RECEIPT_FILE')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == BASE_RECEIPT_SHA256, 'BASE_RECEIPT_DIGEST')
    result = json.loads(raw)
    require(isinstance(result, dict) and result.get('candidate_rom_sha256') == BASE_ROM_SHA256,
            'BASE_RECEIPT_ROM')
    return result


def verify_initial_sram(manifest):
    """Bind the declared capture input to the independently pinned f9 receipt."""
    rows = [row for row in load_baseline()['preservation']['checks']
            if row['group'] == 'emulator-input' and Path(row['path']).name == 'bor.srm']
    require(len(rows) == 1, 'INITIAL_SRAM_AUTHORITY')
    authority = rows[0]
    source = Path(authority['path']).resolve()
    seed = manifest.get('initial_sram')
    require(isinstance(seed, dict) and isinstance(seed.get('source'), str),
            'INITIAL_SRAM_MANIFEST')
    require(Path(seed['source']).resolve() == source, 'INITIAL_SRAM_SOURCE_PATH')
    require(seed.get('sha256') == authority['expected'], 'INITIAL_SRAM_DECLARED_DIGEST')
    require(type(seed.get('bytes')) is int and seed['bytes'] > 0, 'INITIAL_SRAM_SIZE')
    raw = source.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == authority['expected'], 'INITIAL_SRAM_INPUT_DIGEST')
    require(len(raw) == seed['bytes'], 'INITIAL_SRAM_SIZE')
    return dict(source=str(source), sha256=authority['expected'], bytes=len(raw),
                authority_receipt_sha256=BASE_RECEIPT_SHA256)


def runtime_initial_sram(root):
    path = Path(root) / 'capture-runtime/capture-runtime.json'
    raw = path.read_bytes()
    result = verify_initial_sram(json.loads(raw))
    return dict(result, manifest_sha256=hashlib.sha256(raw).hexdigest())


def events(path):
    result = []
    for line in Path(path).read_text(errors='replace').splitlines():
        require('callback_owner.lua:' not in line, 'LUA_ERROR')
        if 'NB_' not in line:
            continue
        row = line[line.index('NB_'):].split('|')
        require(len(row) >= 5 and row[0] != 'NB_FAULT', 'NATIVE_FAULT_OR_RECORD')
        result.append(dict(kind=row[0][3:], clock=int(row[1]), frame=int(row[2]), data=row[4:]))
    return result


def ready_intervals(path):
    """Reuse existing unmodified drain/READY markers, with no baseline rerun."""
    drains, intervals = {}, {}
    for event in events(path):
        data = event['data']
        if event['kind'] == 'BATCH' and data[0] == 'NbQueueDrainDone':
            require(len(data) >= 2, 'DRAIN_RECORD')
            drains[data[1]] = event
        if event['kind'] == 'PHASE' and data[0] == 'NbReady':
            require(len(data) >= 2 and data[1] in drains and data[1] not in intervals,
                    'READY_WITHOUT_UNIQUE_DRAIN')
            txn = data[1]; drain = drains[txn]
            elapsed = event['clock'] - drain['clock']
            require(elapsed > 0, 'READY_CLOCK_ORDER')
            intervals[txn] = dict(master_clocks=elapsed, drain_clock=drain['clock'],
                                  ready_clock=event['clock'], drain_frame=drain['frame'],
                                  ready_frame=event['frame'])
    require(bool(intervals), 'READY_INTERVALS_MISSING')
    return intervals


def _registers(values):
    require(len(values) == len(REGISTERS), 'REGISTER_RECORD')
    return dict(zip(REGISTERS, map(int, values)))


def _map(value):
    require(len(value) == 4096, 'MAP_LENGTH')
    try:
        data = bytes.fromhex(value)
    except ValueError as error:
        raise ValueError('READY_VALIDATE:MAP_HEX') from error
    require(len(data) == 2048, 'MAP_LENGTH')
    return [int.from_bytes(data[i:i + 2], 'little') for i in range(0, 2048, 2)]


def _ready_successes(rows):
    result = {}
    for event in rows:
        data = event['data']
        if event['kind'] == 'BH_COST' and data[0] == 'BhReadyOK':
            require(len(data) == 2 and data[1] not in result, 'SCAN_EXPECTED_RECORD')
            result[data[1]] = event['clock']
    require(bool(result), 'SCAN_EXPECTED_MISSING')
    return result


def ready_successes(path):
    """Original borrowing-validation success markers require a following scan."""
    return _ready_successes(events(path))


def native_scans(path):
    rows = events(path); expected = _ready_successes(rows)
    entries, scans = {}, {}
    for event in rows:
        data = event['data']
        if event['kind'] == 'RV_ENTRY':
            require(len(data) == 10 and data[0] not in entries, 'SCAN_ENTRY_RECORD')
            entries[data[0]] = (event, _registers(data[1:9]), _map(data[9]))
        elif event['kind'] == 'RV_SCAN':
            require(len(data) == 11 and data[0] in entries and data[0] not in scans,
                    'SCAN_EXIT_RECORD')
            txn = data[0]; entry, before, words = entries[txn]
            after = _registers(data[2:10]); result = _map(data[10])
            elapsed = int(data[1])
            require(elapsed == event['clock'] - entry['clock'] and elapsed > 0,
                    'SCAN_CLOCKS')
            require(before['d'] == after['d'] == 0x3400 and before['counter'] == 0 and
                    before['ps'] & 0x30 == 0, 'SCAN_ENTRY_ABI')
            require(after['a'] == 2048 and after['x'] == 2046 and after['counter'] == 2048,
                    'SCAN_EXIT_INDEX')
            require(all(before[key] == after[key] for key in ('y', 'd', 'dbr', 'sp')) and
                    after['ps'] == ((before['ps'] & 0x7c) | 3), 'SCAN_CONTEXT')
            require(all(not (word & 0x8000) and (word & 0x3fff) < 768 for word in words),
                    'SCAN_INPUT_REJECTABLE')
            require(result == [word & 0x3fff for word in words], 'SCAN_MAP_SEMANTICS')
            scans[txn] = dict(master_clocks=elapsed, words=1024, context_preserved=True,
                              exact_map_transform=True)
    require(bool(scans) and set(scans) == set(entries) == set(expected), 'SCAN_INCOMPLETE_INVENTORY')
    require(all(entries[txn][0]['clock'] > expected[txn] for txn in entries),
            'SCAN_BEFORE_ORIGINAL_READY_SUCCESS')
    return scans


def compare_intervals(current, baseline):
    require(set(current) == set(baseline), 'READY_TRANSACTION_DRIFT')
    result = {}
    for txn, old in baseline.items():
        new = current[txn]
        require(new['master_clocks'] < old['master_clocks'], 'READY_CPU_NOT_IMPROVED:' + txn)
        result[txn] = dict(before_clocks=old['master_clocks'], after_clocks=new['master_clocks'],
                           saved_clocks=old['master_clocks'] - new['master_clocks'])
    return result


def verify_timing(report, baseline):
    require(report['epoch2']['fields'] <= baseline['candidate_epoch2']['fields'] and
            report['epoch2']['master_clocks'] <= baseline['candidate_epoch2']['master_clocks'],
            'EPOCH2_REGRESSION')
    require(report['epoch3']['fields'] < baseline['candidate_epoch3']['fields'] and
            report['epoch3']['master_clocks'] < baseline['candidate_epoch3']['master_clocks'],
            'EPOCH3_NOT_IMPROVED')
