"""Acceptance gates and reproducible handoff for the native bitmap experiment.

Consumes the eight serial runs certified by m4_home_borrow_bitmap_native.
Does not manufacture snapshots, render pictures, or change a historical auditor.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

MS = 21477.270
NAMES = ('success', 'valid', 'early', 'ready', 'partial', 'stale', 'insufficient', 'right')
VERSIONS = dict(early='v7', ready='v8', partial='v8', stale='v8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError('BITMAP_ACCEPTANCE:' + message)


def map_completion_margins(folder):
    events = []
    for line in (folder / 'native/mesen.log').read_text(errors='replace').splitlines():
        if 'NB_' in line:
            p = line[line.index('NB_'):].split('|')
            events.append((p[0][3:], int(p[1]), p[4:]))
    result = []
    for kind, clock, data in events:
        if kind == 'PHASE' and data[0] == 'NbMapsComplete':
            end = next(t for k, t, _ in events if k == 'VBLANK_END' and t > clock)
            result.append(dict(transaction=int(data[1]), completion_clock=clock,
                               active_display_resumes=end, margin_clocks=end-clock))
    return result


def collect(root, output):
    baseline_path = Path('docs/receipts/byor-motu-home-borrow.json')
    baseline = json.loads(baseline_path.read_text())
    cases = {}
    for name in NAMES:
        folder = root / name
        result_path = folder / 'bitmap-result.json'
        r = json.loads(result_path.read_text())
        # Re-run the new bitmap trace checker, including unfiltered fault logs.
        from m4_home_borrow_bitmap_native import bitmap_evidence
        require(r['bitmap'] == bitmap_evidence(folder), name + ': bitmap trace drift')
        require(r['pixel_mismatches'] == r['resource_faults'] == r['unsafe_ppu_operations'] == 0,
                name + ': correctness')
        require(r['min_batch_margin_clocks'] >= 10000, name + ': VBlank margin')
        old_name = 'right_control' if name == 'right' else name
        old = baseline['cases'][old_name]
        old_folder = Path('out/byor-motu-home-borrow-' + name + '-' + VERSIONS.get(name, 'v5'))
        snapshots = {}
        for path in (folder / 'native').glob('*world.bin'):
            previous = old_folder / 'native' / path.name
            require(previous.exists() and path.read_bytes() == previous.read_bytes(),
                    name + ': source snapshot changed: ' + path.name)
            snapshots[path.name] = sha(path)
        require(bool(snapshots), name + ': no source snapshots')
        if name == 'right':
            require(r['classification'] == 'BYOR_MOTU_SOURCE_SAFEPOINT_PASS', 'RIGHT control')
            require(not r['bitmap']['plans'], 'RIGHT performed bitmap work')
            require(r['transition_fields'] == old['transition_fields'], 'RIGHT gained a field')
            require(r['transaction_costs'] == old['transaction_costs'], 'RIGHT timing changed')
        else:
            require(r['classification'] == 'BYOR_MOTU_HOME_BORROW_BITMAP_NATIVE_CORRECT', name)
            historic = json.loads((folder / 'certified.json').read_text())
            expected = ('HOME_BORROW_TWO_PICTURES_CERTIFIED' if name in ('success', 'valid')
                        else 'HOME_BORROW_ROLLBACK_CERTIFIED')
            require(historic['classification'] == expected, name + ': missing outcome')
            require(len(r['bitmap']['plans']) == 1 and
                    r['bitmap']['plans'][0]['transaction'] == 3, name + ': bitmap fast-path violation')
            require(all(p['map_words_per_input'] == 1024 for p in r['bitmap']['plans']),
                    name + ': map pass count')
            require(r['source_pixel_difference'] == 1816, name + ': changed source pixels')
            require(r['transactions'][0] == old['transactions'][0], name + ': first publication changed')
        for suffix in ('committed', 'pending', 'refs', 'cgram'):
            for file in (folder / 'native').glob(f'*-{suffix}.bin'):
                previous = old_folder / 'native' / file.name
                require(previous.exists() and file.read_bytes() == previous.read_bytes(),
                        name + ': physical/control identity: ' + file.name)
        # Power-on VRAM residue is not deterministic across emulator instances.
        # Each strict certifier replays ALL 64 KiB from that run's captured base.
        # Cross-run equality applies to maps and referenced physical CHR storage.
        physical_comparisons = []
        for file in (folder / 'native').glob('*-vram.bin'):
            if file.name in ('initial-vram.bin', 'handoff-vram.bin'):
                continue
            a = file.read_bytes()
            b = (old_folder / 'native' / file.name).read_bytes()
            require(len(a) == len(b) == 65536 and a[61440:] == b[61440:], name + ': displayed maps')
            slots = set(int(w) & 1023 for w in np.frombuffer(a[61440:], dtype='<u2'))
            for slot in slots:
                require(slot < 768 and a[64*slot:64*(slot+1)] == b[64*slot:64*(slot+1)] and
                        a[49152+16*slot:49152+16*(slot+1)] == b[49152+16*slot:49152+16*(slot+1)],
                        name + ': referenced HIGH/LOW CHR changed')
            physical_comparisons.append(dict(checkpoint=file.name, referenced_slots=len(slots),
                                            unused_byte_differences=sum(x != y for x, y in zip(a, b))))
        keep = ('rom_sha256', 'audit', 'observed_fields', 'verified_pixels', 'pixel_mismatches',
                'resource_faults', 'unsafe_ppu_operations', 'bitmap', 'transactions',
                'transaction_costs', 'transition_fields', 'pools', 'transfers', 'batches',
                'dma_fences', 'min_batch_margin_clocks', 'helper_costs', 'ready_residency_checks',
                'backdrop_restorations', 'validity_clear_events', 'full_physical_replay',
                'source_events', 'timing_uncertainty', 'source_pixel_difference')
        cases[name] = {k: r[k] for k in keep if k in r}
        cases[name].update(evidence_folder=str(folder), native_result_sha256=sha(result_path),
                           fields_receipt_sha256=sha(folder / 'fields.json'),
                           map_commit_completion_margins=map_completion_margins(folder),
                           baseline_physical_comparisons=physical_comparisons,
                           source_snapshots_byte_identical=snapshots)

    success = cases['success']
    old_success = baseline['cases']['success']
    require(success['pools']['3']['homes'] == old_success['pools']['3']['homes'], 'allocation order')
    require(not success['pools']['3']['original_valid'], 'default new invalidations')
    plan = next(p for p in success['ready_residency_checks'] if p['transaction'] == 3)
    require((plan['actor_tiles'], len(plan['restoration_homes']), plan['tail_reservations'],
             plan['borrowed_reservations']) == (95, 10, 64, 41), '105 physical reservations')
    refs = np.frombuffer((root / 'success/native/after-second-refs.bin').read_bytes(), dtype='<u2')
    require(np.count_nonzero(refs & 0x3fff) == 639, '639 final referenced slots')
    transfer = next(t for t in success['transfers'] if t['transaction'] == 3)
    require((transfer['chr_pairs'], transfer['chr_bytes'], transfer['map_bytes'], transfer['descriptors'])
            == (105, 8400, 4096, 212), 'epoch-3 transfer workload')
    require(len([b for b in success['batches'] if b['transaction'] == 3]) == 18, '18 preload batches')
    full = next(t for t in success['helper_costs'] if t['routine'] == 'BhPrepare' and t['transaction'] == 3)
    require(full['elapsed_clocks'] < 17991078, 'BhPrepare did not improve')
    first, second = success['transactions'][:2]
    require(first['fields'] <= 32, 'first publication >32 fields')
    require(second['master_clocks'] < 33833446 and second['fields'] < 94, 'second publication did not improve')
    valid = cases['valid']
    require(valid['pools']['3']['original_valid'] == [204], 'valid-home case')
    require(any(p['transaction'] == 4 and p['home'] == 204 and p['destination'] == 634 and not p['rollback']
                for p in valid['backdrop_restorations']), 'source-owned later IDLE restoration')
    for name in ('early', 'ready', 'partial', 'stale'):
        require(bool(cases[name]['validity_clear_events']), name + ': no rollback validity fence')
    require(next(t for t in cases['insufficient']['transfers'] if t['transaction'] == 3)['descriptors'] == 0,
            'insufficient budget did DMA')

    before_path = Path('out/byor-motu-home-bitmap-package-v1/dirty-before.json')
    fingerprints = json.loads(before_path.read_text())
    require(len(fingerprints) == 29 and all(sha(Path(x['path'])) == x['sha256'] for x in fingerprints),
            'inherited dirty bytes changed')
    require(not Path('SNES-BOR-Engine-Prompt.md').exists(), 'unrelated deletion changed')
    controls = {}
    for label, dirname, expected in (
        ('original_home', 'original', '061c574cb37a0d8dfabe731bb1fb8685610a091ec3b7d48fdb46ed9aabf38fda'),
        ('disabled_safe_point', 'disabled-sp', '7cf213a9aaa467c7c1248dc0e40d35027f8dbd56a6ac3e9f81d373d216cc431b'),
        ('disabled_conditional', 'disabled-conditional', '9ccbb5310ceb73f97ba6bdcfddfeeedb98f0378c448c8c0e98f543581c6ddeea')):
        path = Path(f'out/byor-motu-home-bitmap-{dirname}-v1/native/bor.sfc')
        require(sha(path) == expected, label + ': original build identity')
        controls[label] = dict(path=str(path), sha256=expected, byte_identical=True)

    bitmap = success['bitmap']['plans'][0]
    tests = {}
    for name, count in (('supplied', 22), ('inherited', 162)):
        path = Path('out/byor-motu-home-bitmap-package-v1') / f'{name}-tests.log'
        log = path.read_text()
        require(f'Ran {count} tests' in log and log.rstrip().endswith('OK'), name + ': test results')
        tests[name] = dict(passed=count, log=str(path), sha256=sha(path))
    report = dict(classification='BYOR_MOTU_HOME_BORROW_BITMAP_PASS',
        starting_commit='836e8a9c8ad1dec108d68c29bdab6fd62bcc04cc',
        baseline_receipt_sha256=sha(baseline_path), cases=cases, original_controls=controls,
        verified_fields=sum(c['observed_fields'] for c in cases.values()),
        verified_pixels=sum(c['verified_pixels'] for c in cases.values()),
        pixel_mismatches=0, resource_faults=0, unsafe_ppu_operations=0,
        focused_tests=tests,
        supplied_archive_sha256='945f83323a8658ebed6f962a4de392b8508b479a40fa2e287c6fa2f013db9472',
        timing=dict(full_bh_prepare=full, bitmap_build_clocks=bitmap['build_clocks'],
                    bitmap_build_ms=bitmap['build_clocks']/MS, publications=success['transactions'],
                    overlapping_intervals_not_additive=True),
        bitmap_timing_boundary='BhBitmapLeaseBegin to BhBitmapBuilt: initialization plus one pass per map; entry guards and final return are outside this subinterval but included in BhPrepare/publication.',
        default_final_referenced_slots=639, inherited_dirty_files_preserved=fingerprints,
        unrelated_prompt_deletion_preserved=True,
        implementation_changes_from_package=['Native adapter bootstrap marker corrected from ONLINE_OBSERVER_BEGIN to retained NONBLANK_OBSERVER_BEGIN; algorithm unchanged.'],
        nonclaims=['30 FPS', '200-Hz scheduling', 'SA-1 coexecution', 'audio', 'HUD', 'combat', 'MOTU Demo'])
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(report['classification'], report['verified_fields'], report['verified_pixels'])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=Path('out/byor-motu-home-bitmap-v2'))
    parser.add_argument('--receipt', type=Path, default=Path('docs/receipts/byor-motu-home-bitmap.json'))
    args = parser.parse_args()
    collect(args.output_root, args.receipt)
