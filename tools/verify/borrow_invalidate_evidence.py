"""Pinned reference-rebuild baseline and original invalidation leaf semantics."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fused_capture_evidence as capture
import ready_validate_evidence as ready

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / 'out/byor-motu-ref-rebuild-v2'
BASE_ROM_SHA256 = '41c505ad5f821bc7a6c458524cfd61f5212362f976d01a3f107a2d14381b9941'
BASE_RECEIPT = ROOT / 'docs/receipts/byor-motu-ref-rebuild.json'
BASE_RECEIPT_SHA256 = '4907309e52e6e47f8e0d60536051c63a8a93b836a56eafde6e008448c830b39f'
BASE_SEAL = capture.CaptureSeal(
    'f1597aefea2a14cdf684185cdf099d4807cff4927fb6a9c50f3ccba4ac4bbb6f',
    'c946fd6639cbcf95cea495bd7bfbbab92bec33629086c4f4dadb0e016bd279fa')
REGISTERS = ready.REGISTERS
RETURN_REFERENCED, RETURN_OK, RETURN_BAD = 0x39B509, 0x39B526, 0x39B528
CALLER_JSR, CALLER_RETURN = 0x39A1A6, 0x39A1A9
CONTROL_MANIFEST = 'control-raw-inputs.json'


def require(ok, code):
    if not ok:
        raise ValueError('BORROW_INVALIDATE:' + code)


def load_baseline(path=BASE_RECEIPT):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == BASE_RECEIPT_SHA256, 'BASE_RECEIPT_DIGEST')
    result = json.loads(raw)
    require(result['candidate_rom_sha256'] == BASE_ROM_SHA256, 'BASE_RECEIPT_ROM')
    return result


def load_native_baseline(receipt):
    pin = receipt['retained_full_native_receipt']
    path = capture._path(pin['path'],ROOT)
    capture._inside(path,BASELINE,'BASE_NATIVE_RECEIPT_ESCAPE')
    result = capture._pinned_json(path,pin['sha256'],'BASE_NATIVE_RECEIPT')
    require(result['classification'] == 'BYOR_MOTU_REF_REBUILD_PASS'
            and result['cases']['success']['rom_sha256'] == BASE_ROM_SHA256,
            'BASE_NATIVE_RECEIPT_IDENTITY')
    return result


def compare_case_timings(current, baseline):
    """No recorded publication, abort, transition or field inventory may regress."""
    require(set(current['cases']) == set(baseline['cases']) == set(capture.CASES),
            'CASE_TIMING_INVENTORY')
    comparisons = {}
    for name in capture.CASES:
        new,old = current['cases'][name],baseline['cases'][name]
        require(new['observed_fields'] <= old['observed_fields'], 'CASE_FIELD_REGRESSION:'+name)
        row = dict(before_observed_fields=old['observed_fields'],after_observed_fields=new['observed_fields'],transactions=[])
        before,after = old.get('transactions',[]),new.get('transactions',[])
        require(len(before) == len(after), 'CASE_TRANSACTION_INVENTORY:'+name)
        for was,now in zip(before,after):
            txn = str(was['transaction'])
            require((was['transaction'],was['committed']) == (now['transaction'],now['committed']),
                    'CASE_TRANSACTION_IDENTITY:'+name+':'+txn)
            require(now['fields'] <= was['fields'], 'CASE_TRANSACTION_FIELD_REGRESSION:'+name+':'+txn)
            require(now['master_clocks'] <= was['master_clocks'],
                    'CASE_TRANSACTION_CLOCK_REGRESSION:'+name+':'+txn)
            row['transactions'].append(dict(transaction=was['transaction'],committed=was['committed'],
                before_clocks=was['master_clocks'],after_clocks=now['master_clocks'],
                before_fields=was['fields'],after_fields=now['fields']))
        if 'transition_fields' in old:
            require(new['transition_fields'] <= old['transition_fields'], 'CASE_TRANSITION_FIELD_REGRESSION:'+name)
            row.update(before_transition_fields=old['transition_fields'],after_transition_fields=new['transition_fields'])
        comparisons[name] = row
    return comparisons


def words(value, count):
    require(isinstance(value, str) and len(value) == count * 4, 'WORDS_LENGTH')
    try:
        raw = bytes.fromhex(value)
    except ValueError as error:
        raise ValueError('BORROW_INVALIDATE:WORDS_HEX') from error
    require(len(raw) == count * 2, 'WORDS_LENGTH')
    return [int.from_bytes(raw[i:i+2], 'little') for i in range(0,len(raw),2)]


def nz(ps, value):
    value &= 65535
    return (ps & ~0x82) | (0x80 if value & 0x8000 else 0) | (2 if value == 0 else 0)


def compare(ps, left, right):
    return (nz(ps, left-right) & ~1) | int(left >= right)


def original_leaf(before, home, count, prepared, refs, table):
    """Independent original leaf model, including precise return flags/writes."""
    require(len(refs) == 768 and len(table) == 596, 'MODEL_WORD_INVENTORY')
    require(0 <= home <= 65535 and 0 <= count <= 65535 and 0 <= prepared <= 65535,
            'MODEL_INPUT_WORD')
    s = dict(before); refs, table = list(refs), list(table); trace = []
    s['a'] = home; s['ps'] = compare(s['ps'],home,596)
    if home >= 596:
        s['ps'] &= ~1
        return s,refs,table,'',RETURN_OK
    s['a'] = prepared; s['ps'] = compare(s['ps'],prepared,1)
    if prepared != 1:
        s['ps'] |= 1
        return s,refs,table,'',RETURN_BAD
    require(count <= 596, 'MODEL_CAPTURE_TABLE_BOUND')
    s['x'] = 0
    for index in range(count+1):
        s['a'] = index; s['ps'] = compare(s['ps'],index,count)
        if index == count:
            s['ps'] |= 1
            return s,refs,table,'',RETURN_BAD
        s['a'] = table[index] & 0x3fff
        s['ps'] = compare(s['ps'],s['a'],home)
        s['x'] = 2*index
        if s['a'] != home:
            s['x'] += 2
            continue
        s['a'] = refs[home] & 0x3fff
        s['ps'] = nz(s['ps'],s['a']) & ~1  # original ASL(home) clears C
        if s['a']:
            s['ps'] = nz(s['ps'],s['x']) | 1  # PLX, SEC
            return s,refs,table,'',RETURN_REFERENCED
        table[index] |= 0x4000; refs[home] |= 0x8000
        for address,value in ((0xd710+2*index,table[index]),(0xd000+2*home,refs[home])):
            trace.extend((f'{address:04x}{value&255:02x}',f'{address+1:04x}{value>>8:02x}'))
        s['a'] = refs[home]; s['x'] = 2*home
        s['ps'] = nz(s['ps'],s['a']) & ~1
        return s,refs,table,''.join(trace),RETURN_OK
    raise AssertionError('unreachable')


def native_calls(path):
    rows = ready.events(path)
    expected_entries = [(row['clock'],row['data'][1]) for row in rows
                        if row['kind'] == 'BH_COST' and row['data'][0] == 'BhInvalidate']
    entries, bodies, calls = {}, {}, []
    for event in rows:
        data = event['data']
        if event['kind'] == 'BI_ENTRY':
            require(len(data) == 16, 'ENTRY_RECORD')
            seq,txn = int(data[0]),data[1]
            require(seq == len(entries)+1 and seq not in entries, 'ENTRY_SEQUENCE')
            before = ready._registers(data[2:10])
            require(before['d'] == 0x3400 and before['ps'] & 0x30 == 0, 'ENTRY_ABI')
            home,count,prepared = map(int,data[10:13])
            require(int(data[15]) == CALLER_RETURN, 'ENTRY_CALLER_RETURN')
            entries[seq] = (event,txn,before,home,count,prepared,words(data[13],768),words(data[14],596))
        elif event['kind'] == 'BI_RTS':
            require(len(data) == 17, 'RTS_RECORD')
            seq,txn,pc = int(data[0]),data[1],int(data[2])
            require(seq == len(bodies)+1 and seq in entries and seq not in bodies, 'RTS_SEQUENCE')
            entry,oldtxn,before,home,count,prepared,refs,table = entries[seq]
            require(txn == oldtxn and event['clock'] > entry['clock'], 'RTS_CLOCKS_OR_TRANSACTION')
            expected,outrefs,outtable,trace,ret = original_leaf(before,home,count,prepared,refs,table)
            require(ready._registers(data[3:11]) == expected and pc == ret, 'RTS_CPU_CONTEXT_OR_RETURN')
            require(tuple(map(int,data[11:14])) == (home,count,prepared), 'RTS_MUTABLE_INPUT')
            require(words(data[14],768) == outrefs and words(data[15],596) == outtable,
                    'RTS_REFERENCE_OR_TABLE_STATE')
            require(data[16] == trace, 'RTS_ORDERED_BYTE_WRITES')
            bodies[seq] = (event,expected,outrefs,outtable,trace,ret)
        elif event['kind'] == 'BI_EXIT':
            require(len(data) == 18, 'EXIT_RECORD')
            seq,txn,elapsed,pc = int(data[0]),data[1],int(data[2]),int(data[3])
            require(seq == len(calls)+1 and seq in entries and seq in bodies, 'EXIT_SEQUENCE')
            entry,oldtxn,before,home,count,prepared,refs,table = entries[seq]
            body,expected,outrefs,outtable,trace,ret = bodies[seq]
            require(txn == oldtxn and elapsed == event['clock']-entry['clock'] and elapsed > 0,
                    'CALL_CLOCKS_OR_TRANSACTION')
            require(event['clock'] > body['clock'], 'RETURN_CLOCK_ORDER')
            after = ready._registers(data[4:12])
            require(tuple(map(int,data[12:15])) == (home,count,prepared), 'CALL_MUTABLE_INPUT')
            returned = dict(expected,sp=(expected['sp']+2)&65535)
            require(after == returned and pc == CALLER_RETURN, 'CALL_CPU_CONTEXT_OR_RETURN')
            require(words(data[15],768) == outrefs and words(data[16],596) == outtable,
                    'CALL_REFERENCE_OR_TABLE_STATE')
            require(data[17] == trace, 'CALL_ORDERED_BYTE_WRITES')
            calls.append(dict(sequence=seq,transaction=txn,home=home,count=count,prepared=prepared,
                master_clocks=elapsed,entry_clock=entry['clock'],return_pc=ret,caller_return_pc=pc,
                input_sha256=hashlib.sha256(('|'.join(data[12:15])+'|'+entries[seq][0]['data'][13]+'|'+entries[seq][0]['data'][14]).encode()).hexdigest(),
                exact_cpu_context=True,exact_reference_and_table_state=True,ordered_write_trace=True))
    require(bool(calls) and len(calls) == len(entries) == len(bodies), 'CALL_INCOMPLETE_INVENTORY')
    require([(row[0]['clock'],row[1]) for row in entries.values()] == expected_entries,
            'ORIGINAL_ENTRY_INVENTORY')
    return calls


def compare_calls(current, control):
    require(len(current) == len(control), 'CONTROL_CALL_COUNT')
    totals = {}
    for new,old in zip(current,control):
        require(all(new[key] == old[key] for key in
            ('sequence','transaction','home','count','prepared','input_sha256','return_pc','caller_return_pc')),
            'CONTROL_CALL_INPUT_DRIFT')
        txn = old['transaction']
        row = totals.setdefault(txn,dict(calls=0,before_clocks=0,after_clocks=0))
        row['calls'] += 1; row['before_clocks'] += old['master_clocks']; row['after_clocks'] += new['master_clocks']
    require('3' in totals, 'CONTROL_EPOCH3_MISSING')
    for txn,row in totals.items():
        require(row['after_clocks'] <= row['before_clocks'], 'LEAF_CPU_REGRESSION:'+txn)
        row['saved_clocks'] = row['before_clocks']-row['after_clocks']
    require(totals['3']['after_clocks']*5 <= totals['3']['before_clocks']*4,
            'LEAF_CPU_GAIN_BELOW_20_PERCENT')
    return totals


def verify_timing(report, baseline):
    for epoch in ('epoch2','epoch3'):
        require(report[epoch]['fields'] <= baseline['candidate_'+epoch]['fields'] and
                report[epoch]['master_clocks'] <= baseline['candidate_'+epoch]['master_clocks'],
                epoch.upper()+'_REGRESSION')


def control_paths(root):
    root = Path(root).resolve(); capture._inside(root,ROOT,'CONTROL_ROOT_ESCAPE')
    folder = root/'success'
    require(folder.is_dir() and not folder.is_symlink(),'CONTROL_CASE_DIRECTORY')
    paths = {folder/'fields.json',folder/'contract.json',root/'capture-runtime/capture-runtime.json'}
    for path in (folder/'native').rglob('*'):
        require(not path.is_symlink(), 'CONTROL_SYMLINK')
        if path.is_file() and path != folder/'native/bor.msu': paths.add(path)
    require(all(path.is_file() and not path.is_symlink() for path in paths), 'CONTROL_RAW_FILE')
    return {p.resolve() for p in paths}


def seal_control(root):
    root = Path(root).resolve(); path = root/CONTROL_MANIFEST
    capture._inside(root,ROOT,'CONTROL_ROOT_ESCAPE')
    require(not path.exists(), 'CONTROL_SEAL_ALREADY_EXISTS')
    capture.verify_field_inventory(root/'success'); capture._verify_msu(root/'success',capture.MSU_SHA256)
    ready.runtime_initial_sram(root)
    rows = [dict(path=p.relative_to(ROOT).as_posix(),sha256=capture.sha(p)) for p in sorted(control_paths(root))]
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(dict(case='success',rom_sha256=BASE_ROM_SHA256,files=rows),indent=2)+'\n')
    return capture.sha(path)


def verify_control(root, digest):
    root = Path(root).resolve()
    capture._inside(root,ROOT,'CONTROL_ROOT_ESCAPE')
    manifest = capture._pinned_json(root/CONTROL_MANIFEST,digest,'CONTROL_MANIFEST')
    require(set(manifest) == {'case','rom_sha256','files'} and manifest['case'] == 'success'
            and manifest['rom_sha256'] == BASE_ROM_SHA256, 'CONTROL_DECLARATION')
    require(isinstance(manifest['files'],list) and bool(manifest['files']), 'CONTROL_MANIFEST_FILES')
    declared = {}
    for row in manifest['files']:
        require(isinstance(row,dict) and set(row) == {'path','sha256'} and capture._digest(row['sha256']),
                'CONTROL_MANIFEST_ROW')
        path = capture._path(row['path'],ROOT); capture._inside(path,root,'CONTROL_PATH_ESCAPE')
        require(path not in declared and capture.sha(path) == row['sha256'], 'CONTROL_HASH_OR_DUPLICATE')
        declared[path] = row['sha256']
    require(set(declared) == control_paths(root), 'CONTROL_RAW_INVENTORY')
    require(capture.sha(root/'success/native/bor.sfc') == BASE_ROM_SHA256, 'CONTROL_ROM_DIGEST')
    coverage = capture.verify_field_inventory(root/'success')
    capture._verify_msu(root/'success',capture.MSU_SHA256); seed = ready.runtime_initial_sram(root)
    return dict(manifest_sha256=digest,raw_inputs=len(declared),coverage=coverage,
                rom_sha256=BASE_ROM_SHA256,initial_sram=seed,immutable_msu_sha256=capture.MSU_SHA256)
