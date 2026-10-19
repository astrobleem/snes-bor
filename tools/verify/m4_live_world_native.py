"""Opt-in source-clock world integration beside the accepted renderer.

The accepted image is the immutable input. Private provider code is regenerated
from the source compiler, relocated into verified empty banks, and never
selected by the production build. Bootstrap instrumentation is retained only
until the real constructor; the foreground owns every subsequent tick.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path[:0] = [str(Path(__file__).resolve().parent),
                str(Path(__file__).resolve().parents[1] / 'bor_compile')]
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset

BASE = Path('out/byor-motu-abort-copy-v1/success/native')
BASE_SHA = '2ae50b27ac69986a07925e37fd99f5f5506044dec6195662ea54524a8ac4166f'
OLD_OWNER = Path('out/byor-motu-online-v3/native')
ROOT = Path('out/byor-motu-live-world-v1')


def assembler_command():
    """Use an explicitly configured compiler or the host's dotnet on PATH."""
    dotnet = os.environ.get('DOTNET') or shutil.which('dotnet')
    poppy = os.environ.get('POPPY_DLL')
    require(dotnet and (Path(dotnet).is_file() or shutil.which(dotnet)),
            'DOTNET_REQUIRED: configure DOTNET or install dotnet on PATH')
    require(poppy and Path(poppy).is_file(),
            'POPPY_DLL_REQUIRED: configure the built Poppy CLI DLL')
    return [str(dotnet), str(poppy)]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError('LIVE_WORLD:' + code)


def assemble(source, folder, name):
    path = folder / (name + '.pasm')
    path.write_text(source, encoding='utf-8')
    cmd = [*assembler_command(), str(path), '--output', str(path.with_suffix('.bin')),
           '--symbols', str(path.with_suffix('.sym')), '--no-pansy']
    r = subprocess.run(cmd, capture_output=True, text=True)
    path.with_suffix('.log').write_text(r.stdout + r.stderr)
    require(r.returncode == 0, name + '_ASSEMBLY')
    return path.with_suffix('.bin').read_bytes(), symbols(path.with_suffix('.sym'))


def player_library(source, folder, baseline, sy):
    """Reproduce the generic player owner, then relocate its two private banks.

    The sandbox image below is an offline compiler input only. It is never
    launched: its cleared banks and empty MSU file are not runtime assets.
    """
    clean = bytearray(baseline)
    for bank in (39, 54, 55, 57, 58, 59, 60):
        clean[bank * 32768:(bank + 1) * 32768] = bytes(32768)
    at = offset(sy['SourceVM_InstructionReservation'])
    clean[at:at + 32768] = b'\xff' * 32768
    for name, shape in (('Vm_SourceFrameGate', '08c231da5a'),
                        ('SourceAIState4086_InitializeBirth', '08c238da5a'),
                        ('SourceCtorModel4086_Apply', '08c238da5a')):
        at = offset(sy[name]); clean[at:at + 5] = bytes.fromhex(shape)
    inputs = folder / 'compiler-input'; inputs.mkdir()
    (inputs / 'bor.sfc').write_bytes(clean)
    (inputs / 'bor.msu').write_bytes(b'')
    emitted = folder / 'player-emitted'
    flags = ('effects-runner frame-owner initial-select default-owner ctor-owner '
             'freeze-state ai-state-birth player-state-birth run-tuple-birth '
             'pending-jump-birth early-player early-attack early-jump-entry '
             'player-controller foreign-ai-player foreign-ai-world-ack '
             'foreign-ai-native-target ctor-state ctor-factors ctor-model '
             'script-clone physics-state-birth '
             'damage-effects-state-birth').split()
    cmd = [sys.executable, '-B', 'tools/verify/m4_animation_callback_owner_native.py',
           '--source', str(source.resolve()), '--rom', str(inputs / 'bor.sfc'),
           '--output', str(emitted), '--emit-only', *['--' + f for f in flags]]
    p = subprocess.run(cmd, capture_output=True, text=True)
    (folder / 'player-compiler.log').write_text(p.stdout + p.stderr)
    require(p.returncode == 0, 'PLAYER_COMPILER')
    code = (emitted / 'callback_fixture.pasm').read_text()
    require(code.count('.bank 39\n') == 1 and code.count('.bank 57\n') == 1,
            'PLAYER_SOURCE_BANKS')
    code = code.replace('.bank 39\n', '.bank 40\n').replace('.bank 57\n', '.bank 56\n')
    from source_pending_jump_native import emit as pending_native
    from source_pending_jump_layout import layout as old_jump, rehost as new_jump
    from source_foreign_state_layout import layout as arena_layout
    pending_work = next(r['address'] for r in arena_layout(0x7fa000,6400)['regions']
                        if r['name']=='pending_jump_controls')
    previous = pending_native(old_jump(),pending_work,sy)
    require(code.count(previous) == 1, 'PENDING_JUMP_SOURCE_AUTHORITY')
    code = code.replace(previous,pending_native(new_jump(),pending_work,sy))
    needle='SourcePlayerState_BirthDelegate:\n.a16\n.i16'
    require(code.count(needle) == 1, 'BIRTH_IDENTITY_JOIN')
    code=code.replace(needle,' lda 5,s\n jsl $308000\n bcs SourcePlayerState_BirthBad\n'+needle)
    # These explicit arithmetic operands work around bankless assembler label
    # expressions in the established emitters. Only their owning bank changes.
    code, n1 = re.subn(r'(PlayerJumpEntry_Fields\+\d+\+)2555904', r'\g<1>2621440', code)
    code, n2 = re.subn(r'(CommonJump_MetadataTable\+)3735552', r'\g<1>3670016', code)
    code, n3 = re.subn(r'(CommonJump_MetadataTable\+\d+\+)3735552', r'\g<1>3670016', code)
    require(n1 == 4 and n2 == 1 and n3 == 2, 'PLAYER_LITERAL_BANK_FIXUPS')
    compiled, ps = assemble(code, folder, 'player-library')
    require(ps['CallbackFixture_MainEnd'] >> 16 == 40, 'PLAYER_MAIN_BANK_EXTENT')
    require(max(v for v in ps.values() if 0x388000 <= v < 0x390000) < 0x390000,
            'PLAYER_ACTION_BANK_EXTENT')
    return compiled, ps, emitted, flags


def build(source, folder):
    folder = folder.resolve(); require(not folder.exists(), 'FRESH_OUTPUT_REQUIRED')
    folder.mkdir(parents=True)
    baseline = (BASE / 'bor.sfc').read_bytes()
    require(sha(baseline) == BASE_SHA, 'ACCEPTED_ROM_DIGEST')
    sy = symbols(Path('src/main.sym'))
    old = symbols(OLD_OWNER / 'callback_fixture.sym')
    code, player, emitted, flags = player_library(source, folder, baseline, sy)
    publisher = symbols(BASE / 'publisher.sym')
    player['_accepted_nmi'] = publisher['OnlineNmi']
    raw = bytearray(baseline)
    ranges = []

    def write(at, data, reason, empty=False):
        require(at + len(data) <= len(raw), 'ROM_RANGE')
        if empty: require(not any(raw[at:at + len(data)]), 'ROM_NONEMPTY:' + reason)
        raw[at:at + len(data)] = data
        ranges.append(dict(offset=at, bytes=len(data), reason=reason))

    for bank, end in ((40, offset(player['CallbackFixture_MainEnd'])),
                      (56, len(code))):
        start = bank * 32768
        require(start < end <= start + 32768, 'PLAYER_CODE_SIZE')
        write(start, code[start:end], 'relocated source player owner', empty=True)
    generated = (emitted / 'bor.sfc').read_bytes()
    for bank in (54, 55, 58):
        start = bank * 32768
        write(start, generated[start:start + 32768], 'source player immutable tables', empty=True)
    # Existing bootstrap roots keep their stable offsets into the common table
    # prefix. Added constructor metadata is appended, never inserted before it.
    start = offset(sy['SourceVM_InstructionReservation'])
    before = baseline[start:start + 32768]
    after = generated[start:start + 32768]
    prefix = before.rstrip(b'\xff')
    require(after[:len(prefix)] == prefix, 'EXISTING_SCRIPT_TABLE_PREFIX')
    write(start, after, 'source-derived table extension, identical existing prefix')
    for name, bridge in (('SourceAIState4086_InitializeBirth', 'SourcePlayerState_BirthBridge'),
                         ('SourceCtorModel4086_Apply', 'SourceRunTuple_CtorModelBridge')):
        at = offset(sy[name]); require(raw[at] == 0x5c, 'EXISTING_BIRTH_BRIDGE')
        write(at, b'\x5c' + player[bridge].to_bytes(3, 'little') + b'\xea',
              'real constructor birth bridge to relocated generic player owner')
    from source_live_world_native import emit
    assembly, config = emit(sy, old, player, source)
    runtime, rs = assemble(assembly, folder, 'live-world')
    require(rs['LiveWorld_HitBirth']==0x308000,'FIXED_BIRTH_ENTRY')
    start = 48 * 32768; end = offset(rs['LiveWorld_CodeEnd'])
    require(start < end <= start + 32768, 'WORLD_CODE_BANK_EXTENT')
    write(start, runtime[start:end], 'clock/input/world owner', empty=True)
    for table in config['table_rows']:
        start=table['bank']*32768;size=table['bytes']
        write(start,runtime[start:start+size],'source '+table['name']+' descriptor',empty=True)
    at = offset(old['CallbackFixture_Init'])
    require(raw[at] == 0xea and raw[at + 1] == 0x22, 'PRE_CONSTRUCTOR_ENTRY')
    write(at, b'\x5c' + rs['LiveWorld_PreConstructor'].to_bytes(3, 'little') + b'\xea',
          'pre-birth source capability installation')
    at=offset(old['LiveGroundAcquire'])
    require(raw[at:at+4]==bytes.fromhex('e220a900'),'PRE_BOOTSTRAP_ACQUIRE_ENTRY')
    write(at,b'\x5c'+rs['LiveWorld_WaitLegacy'].to_bytes(3,'little'),
          'drain original DMA before immutable bootstrap or any overlay writes')
    at=offset(old['CallbackFixture_Gate'])
    require(raw[at:at+5]==bytes.fromhex('08c238da5a'),'OUTER_GATE_PROLOGUE')
    write(at,b'\x5c'+rs['LiveWorld_VmGate'].to_bytes(3,'little')+b'\xea',
          'nested source callback executes real VM gate without outer fixture return')
    at=offset(old['CallbackFixture_AudioService'])
    require(raw[at:at+4]==bytes.fromhex('eaa90900'),'CONSTRUCTOR_AUDIO_STUB_ENTRY')
    write(at,b'\x5c'+rs['LiveWorld_ConstructorAudio'].to_bytes(3,'little'),
          'required authored constructor audio remains pending until a real backend is bound')
    at = offset(old['CallbackFixture_GroundPrepare'])
    require(raw[at:at+2] == b'\xea\x4c' and
            int.from_bytes(raw[at+2:at+4], 'little') == (old['LiveGroundBoot'] & 65535),
            'POST_CONSTRUCTOR_BOOT_ENTRY')
    write(at, b'\x5c' + rs['LiveWorld_Boot'].to_bytes(3, 'little'),
          'native constructor snapshot and clock owner; bypass operation fixture boot')
    at = offset(old['CallbackFixture_Return'])
    require(raw[at:at+4] == bytes.fromhex('e220a981'), 'LEGACY_RETURN_ENTRY')
    write(at, b'\x5c' + rs['LiveWorld_ReturnGate'].to_bytes(3, 'little'),
          'exclude legacy foreground resumption for retired staging lease lifetime')
    at=offset(sy['SourceForeignWork_Check'])
    require(raw[at:at+5]==bytes.fromhex('08c23148da'),'FOREIGN_CHECK_ENTRY')
    write(at,b'\x5c'+rs['LiveWork_Check'].to_bytes(3,'little')+b'\xea',
          'private BG-owner foreign-work lease; preserve generation and full DMA guards')
    nmi_entry=int.from_bytes(raw[0x7fea:0x7fec],'little');at=offset(nmi_entry)
    require(raw[at:at+4]==b'\x5c'+publisher['OnlineNmi'].to_bytes(3,'little'),
            'ACCEPTED_NMI_VECTOR_OWNER')
    write(at,b'\x5c'+rs['LiveWorld_Nmi'].to_bytes(3,'little'),
          'count actual hardware fields while owned; original NMI delegation before acquisition')
    (folder / 'bor.sfc').write_bytes(raw)
    media = (BASE / 'bor.msu').resolve()
    try: os.link(media, folder / 'bor.msu')
    except OSError as exc:
        if getattr(exc, 'winerror', None) != 1142: raise
        import shutil
        shutil.copyfile(media, folder / 'bor.msu')
    report = dict(schema='BYOR_LIVE_WORLD_BUILD_V1', status='STATIC_CANDIDATE',
                  accepted_rom_sha256=BASE_SHA, rom_sha256=sha(raw), ranges=ranges,
                  source_sha256=sha(source.read_bytes()), config=config,
                  symbols={**sy, **old, **player, **rs}, reproduce_flags=flags,
                  renderer_bank_unchanged=raw[57*32768:58*32768] == baseline[57*32768:58*32768])
    require(report['renderer_bank_unchanged'], 'ACCEPTED_RENDERER_CHANGED')
    (folder / 'contract.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = build(args.source, args.output)
    print(json.dumps({k: result[k] for k in ('status', 'rom_sha256', 'renderer_bank_unchanged')}))
