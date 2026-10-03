"""Build-only organic NONE+WALK fixture; never launches an emulator.

This is an experimental integration fixture, not a compiler profile or a
SOURCE_EXACT/ACCEPTED_COMPAT permission. All full actor certificates stay BLOCKED.
"""
from __future__ import annotations

import argparse
import contextlib
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
for folder in ('bor_converter', 'bg_converter', 'bor_compile'):
    sys.path.insert(0, str(ROOT / 'tools' / folder))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def symbols(path):
    result = {}
    for bank, addr, name in re.findall(r'(?m)^([\da-fA-F]{2}):([\da-fA-F]{4,6}) (\S+)$',
                                      Path(path).read_text()):
        result[name] = (int(bank, 16) << 16) + int(addr, 16)
    return result


def offset(address):
    assert (address & 65535) >= 0x8000 and address < 0x400000
    return (address >> 16) * 0x8000 + (address & 65535) - 0x8000


def zero_flag_contract(asm_path, sym_path):
    """Static dominance/write-set proof, NOT CPU execution or a live PASS.

    Reject changed guard shapes so the reviewed write-set argument cannot
    silently survive source edits. Accepted domain: modes 0..6, flags all zero.
    A is caller-dead at these hooks; P/X/Y/D/DBR preservation is explicit.
    """
    source = (ROOT / 'src/core/actor_behavior.pasm').read_text()
    syms = symbols(sym_path)
    binary = Path(asm_path).read_bytes()
    for label, size in [('ModelFlags', 256), ('ModelSpeed', 1024),
                        ('ModelHealth', 512), ('SpawnCount', 2), ('SpawnRecords', 256)]:
        p = offset(syms['ActorBehavior_' + label])
        assert binary[p:p + size] == bytes(size), label
    constants = {'ClockLongNumerator': 357368 * 200,
                 'ClockShortNumerator': 357364 * 200, 'ClockDenominator': 21477270}
    for label, value in constants.items():
        assert struct.unpack_from('<I', binary, offset(syms['ActorBehavior_' + label]))[0] == value

    def body(start, end):
        return source.split(start + ':', 1)[1].split(end + ':', 1)[0]

    capture = body('ActorBehavior_CaptureRoster', 'ActorBehavior_CaptureRoster__done')
    guard = 'beq ActorBehavior_CaptureRoster__done'
    assert 'lda.l ActorBehavior_ModelFlags,x' in capture.split(guard)[0]
    assert not re.search(r'(?m)^\s*(?:sta|stz|jsl|jsr)\b', capture.split(guard)[0])
    restore = body('ActorBehavior_RestoreCompat', 'ActorBehavior_RestoreCompat__done')
    guard = 'beq ActorBehavior_RestoreCompat__done'
    prefix = restore.split(guard)[0]
    assert prefix.count('lda.l ActorBehavior_ModelFlags,x') == 2
    assert 'bne ActorBehavior_RestoreCompat__done' in prefix
    assert not re.search(r'(?m)^\s*(?:sta|stz|jsl|jsr)\b', prefix)
    bind = body('ActorBehavior_Bind', 'ActorBehavior_Bind__exact')
    writes = re.findall(r'(?m)^\s*sta\.l\s+([^\s,]+)', bind)
    assert set(writes) == {'ActorBehavior_Alive', 'ActorBehavior_Fault',
                           'ActorBehavior_Samples', 'ActorBehavior_SourceHealth'}
    assert 'bne ActorBehavior_Bind__exact' in bind and 'brl ActorBehavior_Return' in bind
    assert not re.search(r'(?m)^\s*(?:stz|jsl|jsr)\b', bind)
    preserve = body('ActorBehavior_PreserveRoster', 'ActorBehavior_RestoreRoster')
    restore_reset = body('ActorBehavior_RestoreRoster', 'ActorBehavior_RestoreCompat')
    assert re.findall(r'(?m)^\s*sta(?:\.l)?\s+([^\n;]+)', preserve) == ['$18E8,y']
    assert re.findall(r'(?m)^\s*sta(?:\.l)?\s+([^\n;]+)', restore_reset) == ['ActorBehavior_CompatRoster,x']
    assert 'cmp #CHAR_INPUT_DRIVEN_NONCOMBAT' in preserve
    assert 'lda #0\n    bra ActorBehavior_PreserveRoster__store' in preserve
    assert 'cpx #CHAR_ZP_LEN*6' in preserve and 'cpx #CHAR_ZP_LEN*6' in restore_reset
    for label, end, pops in [
        ('ActorBehavior_CaptureRoster__done', 'ActorBehavior_PreserveRoster', ('plx', 'plp')),
        ('ActorBehavior_RestoreCompat__done', 'ActorBehavior_Bind', ('ply', 'plx', 'plp')),
    ]:
        tail = body(label, end)
        for pop in pops:
            assert re.search(r'(?m)^\s*' + pop + r'\s*$', tail)
    # All reset/zero-binding writes are outside the immutable actor DP windows
    # and outside each row's accepted base/alias bytes 0..5.
    for row in range(6):
        for name in writes + ['ActorBehavior_CompatRoster']:
            address = syms[name] + row * 133
            assert 0x7E550F + row * 133 + 6 <= address
            assert address + 1 < 0x7E550F + (row + 1) * 133
    source_main = (ROOT / 'src/main.pasm').read_text()
    source_spawn = (ROOT / 'src/core/spawn.pasm').read_text()
    source_env = (ROOT / 'src/core/stage_environment.pasm').read_text()
    assert 'jsl ActorBehavior_AnimationAlive\n    bne Anim_Play__not_dead' in source_main
    assert 'jsl ActorBehavior_RenderAlive\n    bne Character_PlayFrame__not_dead_hide' in source_main
    assert 'jsl ActorBehavior_CaptureRoster\n    lda.l CharSelect_Index' in source_spawn
    assert 'jsl ActorBehavior_RestoreCompat\n    rep #$20' in source_env
    assert 'jsl ActorBehavior_Bind\n    rep #$30' in source_env
    for mode in range(7):
        for hp in range(256):
            assert (mode < 2 or hp != 0) == (True if mode < 2 else bool(hp))
            assert (mode < 1 or hp != 0) == (True if mode < 1 else bool(hp))
    return {
        'status': 'PASS_STATIC_ZERO_FLAG_CONTRACT', 'live_compatibility_pass': False,
        'domain': 'fresh accepted modes 0..6, all 256 flags zero; includes stage reset/new run and reassign',
        'capture_roster': 'first zero-table guard dominates all writes and calls; original reassign continues',
        'restore_compat': 'both table reads zero; exit precedes any reload or actor write',
        'reset': 'accepted modes produce six zero backups; existing reset clears rows; only reserved backup words restored',
        'bind': 'only four new parallel-state words cleared; no legacy actor fields or RNG written',
        'register_contract': 'P/X/Y/D/DBR preserved; A caller-dead before original next load',
        'limits': 'static guard/write-set proof, not machine execution, DMA/cadence or visual equivalence',
        'asm_sha256': sha(binary), 'actor_source_sha256': sha(source.encode()),
    }


def fixture_queue(model_name, slot):
    from spawn_parse import SpawnEvent, WaitEvent
    from build_spawn_table import convert_events, SCALE
    assert SCALE == 4 / 5
    events = []
    # Both headings oppose authored flip, proving facing is not the velocity input.
    for x, flip in [(20, 0), (300, 1)]:
        e = SpawnEvent(model_name, 0)
        e.coords, e.flip = (x, 187), flip
        events.append(e)
    # A future source queue record keeps this bounded scene loaded after both
    # non-enemies retire; no forced HP/enemy-clear state is used.
    events.append(WaitEvent(10000))
    count, queue = convert_events(events, {model_name: 'none'}, {model_name: slot})
    assert count == 3 and len(queue) == 30
    rows = [struct.unpack_from('<HHBBBBBB', queue, i * 10) for i in range(count)]
    assert [r[1] for r in rows[:2]] == [16, 240]
    assert [r[3] & 1 for r in rows[:2]] == [1, 0]
    assert all((r[4] & 7) == 1 and r[7] == slot for r in rows[:2])
    assert rows[2][0] == 8000 and (rows[2][4] & 7) == 2
    return queue, rows


def build(args):
    from compiler import Source
    from analyze import scoped_id
    from convert_character import convert_character
    from pack_msu_roster import pack_character_blob, build_record, RECORD_SIZE, BG_RECORD_SIZE
    assert RECORD_SIZE == 50 and BG_RECORD_SIZE == 40
    # Completed output required. Refuse stale/mismatched assembly before writing.
    syms = symbols(args.sym)
    asm = args.asm.read_bytes()
    rom = bytearray(args.rom.read_bytes())
    begin, end = (offset(syms['ActorBehavior_' + k]) for k in ('Start', 'End'))
    assert rom[begin:end] == asm[begin:end], 'production ROM does not match completed assembly'
    contract = zero_flag_contract(args.asm, args.sym)
    model = json.loads(args.report.read_text())['models'][args.model.casefold()]
    assert model['behavior']['driver'] == 'noncombat_horizontal_drift'
    assert model['behavior']['type'] == 'none' and model['roles']['walk'] > 0
    speed = Fraction(model['behavior']['source_speed']) * 2560
    assert speed.denominator == 1
    health = int(model['stats']['health'])
    assert 0 <= health <= 65535
    assert scoped_id(Source(args.pak)) == model['identity'][0], 'canonical source/report identity mismatch'
    with args.msu.open('rb') as f:
        header = f.read(16)
    count, playable = header[9], header[11]
    slot = count - 1 if args.slot is None else args.slot
    assert playable <= slot < count, 'fixture may only repurpose a non-player catalog slot'
    assert 0 <= args.stage < header[10]
    queue, rows = fixture_queue(args.model.casefold(), slot)
    bg_base = struct.unpack_from('<I', header, 12)[0]
    directory_offset = 16 + slot * 50
    with args.msu.open('rb') as f:
        f.seek(directory_offset)
        replaced_record = f.read(50)
        old_actor_offset = struct.unpack_from('<I', replaced_record, 8)[0]
        if slot + 1 < count:
            f.seek(directory_offset + 50 + 8)
            old_actor_end = struct.unpack('<I', f.read(4))[0]
        else:
            old_actor_end = bg_base
    assert old_actor_offset < old_actor_end
    out = args.output.resolve()
    assert not out.exists(), 'preserve existing fixture: choose a new output directory'
    assert ROOT in out.parents and out not in (ROOT / 'build', ROOT / 'distribution')
    out.mkdir(parents=True)
    prefix = out / 'assets' / 'actor'
    prefix.parent.mkdir()
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        convert_character(str(args.pak), model['source_path'], str(prefix))
        blob, info = pack_character_blob(str(prefix), extended_maps=True)
    assert info['idle_frame_count'] == model['roles']['idle']
    assert info['walk_frame_count'] == model['roles']['walk']
    assert info['attack_frame_count'] == 0
    assert sha(blob) == model['encoding_probe']['sha256'], 'fresh source raster differs from shadow encoding'
    (out / 'encoding.log').write_text(log.getvalue())
    (out / 'actor.bin').write_bytes(blob)
    (out / 'spawn_table.bin').write_bytes(queue)
    # Retain the fresh native source assets under a distinct fixture project.
    project = 's5-organic-noncombat-experiment-v1'
    identity = [sha(project.encode()), model['source_path'].replace('\\', '/').lower()]
    assert identity != model['identity']
    msu_before = file_sha(args.msu)
    shutil.copyfile(args.msu, out / 'bor.msu')
    with (out / 'bor.msu').open('r+b') as f:
        f.seek(0, 2)
        old_length = f.tell()
        actor_offset = old_length if args.layout == 'append' else old_actor_offset
        if args.layout == 'catalog-payload':
            assert actor_offset + len(blob) + len(queue) <= old_actor_end, 'repurposed slot payload too small'
        assert actor_offset + len(blob) + len(queue) < 0x1000000, 'actor AND queue loaders are 24-bit'
        f.seek(actor_offset)
        f.write(blob)
        queue_offset = f.tell()
        f.write(queue)
        f.seek(directory_offset)
        f.write(build_record(info, actor_offset))
        stage_queue_fields = bg_base + args.stage * 40 + 32
        f.seek(stage_queue_fields)
        replaced_queue_fields = f.read(6)
        f.seek(stage_queue_fields)
        f.write(struct.pack('<IH', queue_offset, 3))
    patched = []
    def patch(label, index, data):
        p = offset(syms[label]) + index
        old = bytes(rom[p:p + len(data)])
        rom[p:p + len(data)] = data
        patched.append({'label': label, 'index': index, 'offset': p,
                        'before': old.hex(), 'after': data.hex()})
    patch('ActorBehavior_ModelFlags', slot, b'\x01')
    patch('ActorBehavior_ModelSpeed', slot * 4, struct.pack('<I', int(speed)))
    patch('ActorBehavior_ModelHealth', slot * 2, struct.pack('<H', health))
    patch('ActorBehavior_SpawnCount', 0, struct.pack('<H', 2))
    patch('ActorBehavior_SpawnRecords', 0,
          struct.pack('<BBhBBh', args.stage, 0, 20, args.stage, 1, 300))
    patch('StageEnv_ModelMapCounts', slot, b'\x00')
    # Header checksum is the only non-table ROM mutation; no boot, force-spawn,
    # actor creation, CPU-state injection or stage-loader call is patched.
    rom[0x7FDC:0x7FE0] = b'\xff\xff\x00\x00'
    checksum = sum(rom) & 65535
    struct.pack_into('<HH', rom, 0x7FDC, checksum ^ 65535, checksum)
    (out / 'bor.sfc').write_bytes(rom)
    shutil.copyfile(args.sym, out / 'bor.sym')
    from pcm_runtime import link_immutable_pcm
    link_immutable_pcm(args.rom.parent, out, prefix=args.rom.stem + '-')
    # Verify every old MSU byte except precisely the catalog entry and stage
    # queue pointer/count. No pre-existing asset offset or payload moves.
    exceptions = [(directory_offset, directory_offset + 50),
                  (stage_queue_fields, stage_queue_fields + 6)]
    if args.layout == 'catalog-payload':
        exceptions.append((actor_offset, queue_offset + len(queue)))
    with args.msu.open('rb') as a, (out / 'bor.msu').open('rb') as b:
        cursor = 0
        while cursor < old_length:
            n = min(1024 * 1024, old_length - cursor)
            left, right = bytearray(a.read(n)), bytearray(b.read(n))
            for lo, hi in exceptions:
                x, y = max(lo - cursor, 0), min(hi - cursor, n)
                if x < y:
                    left[x:y] = right[x:y]
            assert left == right, 'unexpected old MSU byte changed'
            cursor += n
    assert file_sha(args.msu) == msu_before
    manifest = {
        'status': 'BUILD_ONLY_READY_RUNTIME_PENDING', 'project': project,
        'identity': identity, 'source_identity': model['identity'], 'catalog_slot': slot,
        'stage_index': args.stage, 'policy': 'EXPERIMENTAL_NONE_WALK',
        'compatibility_permission': False, 'full_actor_certificate': 'BLOCKED',
        'blocked': ['exact rand32/randf seed and call order', 'IEEE float/numeric equivalence',
                    'clock feed/skipped-frame validation', 'full stats', 'animation timing',
                    'runtime organic spawn/movement/removal and visual proof'],
        'source_speed': str(Fraction(speed, 2560)), 'speed_units': int(speed),
        'source_health': health, 'source_health_wram': syms['ActorBehavior_SourceHealth'],
        'rng_adapter': 'one legacy byte k, random03=30*k; NOT source 3*(unsigned(rand32())%1000)/1000',
        'fraction_policy': 'source /2560; target pixel=3200 units; queue round(*4/5); signed floor projection',
        'queue': [list(r) for r in rows], 'authored_x': [20, 300],
        'expected_facing_left': [1, 0], 'expected_velocity_sign': [1, -1],
        'catalog_record_offset': directory_offset, 'old_catalog_record': replaced_record.hex(),
        'layout': args.layout, 'repurposed_payload_capacity': old_actor_end - old_actor_offset,
        'layout_reason': '28MB completed MSU exceeds both actor and queue 24-bit loaders; catalog-payload layout changes only the replaced fixture identity span',
        'stage_queue_fields': stage_queue_fields, 'old_stage_queue_fields': replaced_queue_fields.hex(),
        'original_msu_size': old_length, 'actor_offset': actor_offset, 'queue_offset': queue_offset,
        'actor_size': len(blob), 'actor_sha256': sha(blob), 'rom_patches': patched,
        'input_rom_sha256': file_sha(args.rom), 'input_msu_sha256': msu_before,
        'fixture_rom_sha256': sha(rom), 'fixture_msu_sha256': file_sha(out / 'bor.msu'),
        'static_zero_flag_contract': contract,
        'runtime_symbols': {k: v for k, v in syms.items() if k.startswith('ActorBehavior_')
                            and (v >= 0x7E0000 or k == 'ActorBehavior_Context')},
        'launch': f'python tools/verify/actor_behavior_organic.py --fixture "{out}"',
    }
    (out / 'fixture.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (out / 'README.md').write_text(
        '# Organic noncombat fixture — experimental, not certified\n\n'
        'No emulator has been launched by the generator. Main must coordinate GUI ownership.\n\n'
        'Launch bor.sfc, skip intro with Start, choose 1P / Easy / default player. '
        'The normal stage loader reads the three-record fixture queue in stage 0. '
        'Two real source-encoded actors spawn at target X 16 and 240; their flips oppose '
        'their drift headings. Leave the player/camera still. A future wait record keeps '
        'the scene loaded after both actors exit. No force-spawn or engine memory writes.\n\n'
        'Use the launch command in fixture.json for the bounded runtime recorder. '
        'That recorder is pending GUI permission; exact RNG, numeric, cadence, stats '
        'and full actor certification remain BLOCKED.\n')
    print(json.dumps({'fixture': str(out), 'status': manifest['status'],
                      'launch': manifest['launch'], 'catalog_slot': slot}, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check-only', action='store_true')
    p.add_argument('--rom', type=Path, default=ROOT / 'distribution/bor.sfc')
    p.add_argument('--msu', type=Path, default=ROOT / 'distribution/bor.msu')
    p.add_argument('--asm', type=Path, default=ROOT / 'src/main.bin')
    p.add_argument('--sym', type=Path, default=ROOT / 'src/main.sym')
    p.add_argument('--report', type=Path, default=ROOT / 'out/bor_compile_s5/bor-summary.json')
    p.add_argument('--pak', type=Path, default=ROOT / 'Beats of Rage Original [v.3.0 Build 4086].pak')
    p.add_argument('--model', default='crab')
    p.add_argument('--stage', type=int, default=0)
    p.add_argument('--slot', type=int)
    p.add_argument('--layout', choices=['append', 'catalog-payload'], default='append')
    p.add_argument('--output', type=Path, default=ROOT / 'out/bor_compile_s5/live-drift-organic')
    args = p.parse_args()
    if args.check_only:
        result = zero_flag_contract(args.asm, args.sym)
        _, rows = fixture_queue(args.model, 44)
        result['real_queue_lowerer_measurement'] = [list(r) for r in rows]
        print(json.dumps(result, indent=2))
    else:
        build(args)


if __name__ == '__main__':
    main()
