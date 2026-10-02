"""Private persistent SA-1 owner for the bounded six-actor S7 fixture."""
import json
import os
import subprocess
from pathlib import Path

import actor_s7_worker as legacy
from actor_s5_entity_fixture import symbols
from actor_s5_isolated import ROOT


def install(folder, *, production_runtime=False):
    """Install the async resident worker over the reviewed private pilot ABI."""
    main_sy = symbols(ROOT / 'src/main.sym')
    world_sy = symbols(folder / 'world.sym')
    hit_sfx_shim = None
    if 'S7_QueueHitSfxLong' not in world_sy:
        # Retained six-actor replay ROMs predate the fixture-side long-call
        # shim. Keep those immutable inputs usable by placing the identical
        # guarded bank-0 trampoline in an unused zero run at install time.
        # New fixture builds already export this symbol and take no patch.
        hit_sfx = main_sy['G11_QueueHitSfx']
        if hit_sfx >> 16:
            raise RuntimeError('HIT_SFX_CHOKEPOINT_NOT_BANK_ZERO')
        original_rom = (folder / 'bor.sfc').read_bytes()
        shim_offset = next((i for i in range(0x3000, 0x7FC0 - 8)
                            if original_rom[i:i + 8] == bytes(8)), None)
        if shim_offset is None:
            raise RuntimeError('NO_GUARDED_BANK0_SPACE_FOR_LONG_HIT_SFX_SHIM')
        shim_address = 0x8000 + shim_offset
        hit_sfx_shim = (shim_offset, bytes((0x08, 0xE2, 0x20, 0x20,
                                            hit_sfx & 255, (hit_sfx >> 8) & 255,
                                            0x28, 0x6B)))
        world_sy = {**world_sy, 'S7_QueueHitSfxLong': shim_address}
    link_manifest=json.loads((folder/'link.json').read_text())
    clock_patch = _patch_elapsed_source_clock(folder, main_sy, world_sy)
    legacy.install(folder)
    source = folder / 'worker.pasm'
    asm = source.read_text()
    old_sy = symbols(folder / 'worker.sym')
    relay_bank=old_sy['Relay_Run']>>16
    worker_bank=old_sy['Worker_Gate']>>16

    def offset(address):
        return (address >> 16) * 32768 + (address & 65535) - 32768

    relay_marker=f'\n.bank {relay_bank}\n.org $8000\n'
    asm = _inject_event_producers(asm)
    gate_start = asm.index('Worker_Gate:\n')
    bank27 = asm.index(relay_marker, gate_start)
    gate = _worker_gate(production_runtime=production_runtime)
    asm = asm[:gate_start] + gate + asm[bank27:]
    gate_start = asm.index('Worker_Gate:\n')
    asm = asm[:gate_start] + _event_push() + asm[gate_start:]

    marker = f'.bank {worker_bank}\n.org $8000\n'
    aliases = (f'Relay_HostScreen_PosX = ${main_sy["Screen_PosX"]:06X}\n'
               f'Relay_HostSpawn_HoleCount = ${main_sy["Spawn_HoleCount"]:06X}\n')
    asm = asm.replace(marker, aliases + marker, 1)
    relay_start = asm.index('Relay_Run:\n')
    relay=_scpu_relay(main_sy, world_sy, production_input=production_runtime).replace('lda #$001C',f'lda #${worker_bank:04X}')
    asm = asm[:relay_start] + relay
    source.write_text(asm)

    command = [os.environ.get('DOTNET_EXE', r'C:\Users\chad\.dotnet\dotnet.exe'),
               os.environ.get('POPPY_DLL', r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll'),
               str(source), '-s', str(folder / 'worker.sym')]
    result = subprocess.run(command, capture_output=True, text=True)
    (folder / 'worker-build.log').write_text(result.stdout + result.stderr)
    if result.returncode or 'warning' in (result.stdout + result.stderr).lower():
        raise RuntimeError(result.stdout + result.stderr)

    new_sy = symbols(folder / 'worker.sym')
    binary = source.with_suffix('.bin').read_bytes()
    rom = bytearray((folder / 'bor.sfc').read_bytes())
    if hit_sfx_shim is not None:
        shim_offset, shim_bytes = hit_sfx_shim
        if rom[shim_offset:shim_offset + len(shim_bytes)] != bytes(len(shim_bytes)):
            raise RuntimeError('HIT_SFX_SHIM_GUARD_CHANGED_DURING_INSTALL')
        rom[shim_offset:shim_offset + len(shim_bytes)] = shim_bytes
    for bank in (relay_bank, worker_bank):
        part = binary[bank * 32768:(bank + 1) * 32768]
        rom[bank * 32768:bank * 32768 + len(part)] = part

    gate_at = offset(main_sy['sa1_wait'])
    assert rom[gate_at] == 0x5C, 'PERSISTENT_WORKER_GATE_NOT_OWNED'
    rom[gate_at:gate_at + 4] = b'\x5C' + new_sy['Worker_Gate'].to_bytes(3, 'little')
    call_sites=(('Relay_Run','S6_UpdateWorld',ROOT/'src/core/actor_source_host.pasm'),
                ('Relay_Flush','S7Resident_Flush',ROOT/'src/core/actor_s6_world_fixture.pasm'))
    for label,source_call,source_path in call_sites:
        old = b'\x22' + old_sy[label].to_bytes(3, 'little')
        start,end=30*32768,31*32768
        source_expected=sum(line.strip()==f'jsl {source_call}' for line in source_path.read_text().splitlines())
        allowed_extra=1 if label=='Relay_Flush' and link_manifest.get('scenario')=='wait_probe' else 0
        expected=source_expected+allowed_extra
        count=0
        at=rom.find(old,start,end)
        while at>=0:
            rom[at+1:at+4]=new_sy[label].to_bytes(3,'little')
            count+=1
            at=rom.find(old,at+4,end)
        assert count==expected and count>0,(label,count,expected)
    if production_runtime:
        # Controller edges are captured at the completed hardware-poll
        # boundary, not when a later source tick happens to be queued. This
        # preserves one-field edges across skipped presentation fields and
        # lets the relay attach them to the first subsequent command.
        poll_start=offset(main_sy['Core_Input_Poll'])
        poll_end=offset(main_sy['Core_Input_Poll_P2'])
        old_poll_call=b'\x22'+main_sy['Core_Input_Poll_P2'].to_bytes(3,'little')
        new_poll_call=b'\x22'+new_sy['Relay_Poll_P2'].to_bytes(3,'little')
        poll_body=bytes(rom[poll_start:poll_end])
        count=poll_body.count(old_poll_call)
        assert count==2,('INPUT_POLL_CAPTURE_CALLSITES',count)
        rom[poll_start:poll_end]=poll_body.replace(old_poll_call,new_poll_call)
    # Once S6Host_Tick has admitted its resident epoch, later source ticks
    # bypass S6Host_Tick__execute and call S6_UpdateWorldBound directly. Route
    # that path to the same asynchronous queue or the SA-1 would receive only
    # the acquisition tick while S-CPU silently kept simulating the rest.
    resident_at=offset(world_sy['S6Host_Tick__resident_execute'])
    assert rom[resident_at]==0x22,'PERSISTENT_RESIDENT_PATH_NOT_JSL'
    resident_target=int.from_bytes(rom[resident_at+1:resident_at+4],'little')
    resident_legacy=(resident_target>>16)!=0 and \
        rom[offset(resident_target):offset(resident_target)+4]==bytes.fromhex('08C230DA')
    assert resident_target==world_sy['S6_UpdateWorldBound'] or resident_legacy,(
        'PERSISTENT_RESIDENT_PATH_TARGET',hex(resident_target),
        hex(world_sy['S6_UpdateWorldBound']))
    rom[resident_at+1:resident_at+4]=new_sy['Relay_Run'].to_bytes(3,'little')
    remove_call=b'\xAF\x76\x17\x7E\x22'+world_sy['S6Host_RemoveHandle'].to_bytes(3,'little')
    remove_start=offset(world_sy['S6Game_PlayRender__tick'])
    remove_end=offset(world_sy['S6Game_PlayRender__no_remove'])
    assert rom[remove_start:remove_end].count(remove_call)==1,'FIXTURE_REMOVE_CALLSITE_CHANGED'
    patched_remove=remove_call[:4]+b'\x22'+new_sy['Relay_QueueRemove'].to_bytes(3,'little')
    rom[remove_start:remove_end]=rom[remove_start:remove_end].replace(remove_call,patched_remove,1)
    (folder / 'bor.sfc').write_bytes(rom)
    (folder / 'worker-manifest.json').write_text(json.dumps({
        'status': ('OPT_IN_PERSISTENT_SOURCE_WORLD_RUNTIME' if production_runtime
                   else 'PRIVATE_PERSISTENT_OWNER_NOT_PRODUCTION'),
        'bwram_regions': {**legacy.REGIONS, 'tick_ring': [0x13000, 0x14000],
                          'snapshot_a': [0x14000, 0x14110],
                          'snapshot_b': [0x14110, 0x14220],
            **({'input_ring': [0x15000, 0x16000],
              'input_state': [0x12014, 0x1201C],
              'input_telemetry': [0x12020, 0x12028]}
                             if production_runtime else {})},
        'tick_record_bytes': 8, 'tick_record_capacity': 512,
        'code_banks': {'s_cpu': relay_bank, 'sa1': worker_bank},
        'snapshot_bytes': 272, 'snapshot_buffers': 2,
        'event_protocol': {'header': [0x12430, 0x12448],
                           'ring': [0x12450, 0x12C50],
                           'record_bytes': 16, 'capacity': 128,
                           'overflow': 'fail-closed; never overwrite unread events'},
        'control_protocol': {'remove_request': 0x12440,
                             'remove_ack': 0x12442,
                             'remove_actor_handle': 0x12444,
                             'remove_apply_tick': 0x12446,
                             'apply_boundary': 'before the next queued source-world tick',
                             'one_outstanding': True},
        'protocol': 'commit request record then advance target; SA-1 drains asynchronously; presentation requests a sequence-acknowledged snapshot',
        'per_tick_wait': False, 'source_tick_limit': 306,
        'production_input': ({'status': 'SEQUENCED_PER_SOURCE_TICK',
                              'bytes_per_tick': 8,
                              'sampled_fields': ['Input_press', 'Input_trigger',
                                                 'Input2_press', 'Input2_trigger'],
                              'capture_boundary': 'completed controller poll; trigger latched until first queued tick',
                              'edge_policy': 'trigger delivered once to first queued tick after input poll',
                              'action_mapping': 'Y edge ($4000) selects source attack1 for bound player slots'}
                             if production_runtime else None),
        'source_clock_patch': clock_patch,
        'production_changed': False}, indent=2) + '\n')
    return new_sy


def _patch_elapsed_source_clock(folder, main_sy, world_sy):
    """Replace the legacy one-quantum-per-render-pass probe with elapsed NMI time."""
    path = folder / 'bor.sfc'
    rom = bytearray(path.read_bytes())

    def offset(address):
        return (address >> 16) * 32768 + (address & 65535) - 32768

    entry = offset(world_sy['S6Game_PlayRender__measure'])
    body = (b'\xAF' + main_sy['Nmi_FrameCounter'].to_bytes(3, 'little') +
            b'\x38\xEF' + world_sy['S6Game_LastField'].to_bytes(3, 'little') +
            b'\x29\xFF\x00')
    if rom[entry:entry + len(body)] == body:
        return 'already_elapsed_gated'

    body_at = rom.find(body, entry, entry + 128)
    assert body_at > entry, 'SOURCE_CLOCK_ELAPSED_BODY_NOT_FOUND'
    assert rom[entry:entry + 5] == bytes.fromhex('C230A98017'), \
        ('UNEXPECTED_SOURCE_CLOCK_ENTRY', rom[entry:entry + 8].hex())
    flush = b'\x22' + world_sy['S7Resident_Flush'].to_bytes(3, 'little')
    flush_sites = []
    cursor = entry
    while True:
        cursor = rom.find(flush, cursor, body_at)
        if cursor < 0:
            break
        flush_sites.append(cursor)
        cursor += len(flush)
    assert len(flush_sites) == 1, ('LEGACY_CLOCK_FLUSH_SITE_COUNT', len(flush_sites))
    # This fixed-field branch becomes unreachable after the jump. NOP its
    # stale flush call so the resident relay installer sees only the live loop.
    rom[flush_sites[0]:flush_sites[0] + 4] = b'\xEA' * 4
    target = world_sy['S6Game_PlayRender__measure'] + (body_at - entry)
    assert target >> 16 == world_sy['S6Game_PlayRender__measure'] >> 16
    rom[entry:entry + 6] = b'\xC2\x30\x5C' + target.to_bytes(3, 'little')
    path.write_bytes(rom)
    return 'reused_elapsed_nmi_delta_body'


def _copy(label, src, dst, size):
    assert size % 2 == 0
    return f'''    ldx #0
{label}:
    .a16
    .i16
    lda.l ${src:06X},x
    sta.l ${dst:06X},x
    inx
    inx
    cpx #{size}
    bcc {label}
'''


def _relocate(label, delta):
    out = ''
    for slot in range(6):
        for off in legacy.POINTER_OFFSETS:
            address = 0x411900 + slot * 256 + off
            name = f'{label}_{slot}_{off}'
            out += f'''    lda.l ${address:06X}
    beq {name}
    clc
    adc #${delta & 65535:04X}
    sta.l ${address:06X}
{name}:
    .a16
    .i16
'''
    for off in (0x44, 0x46, 0x4E, 0x50):
        address = 0x411700 + off
        name = f'{label}_world_{off}'
        out += f'''    lda.l ${address:06X}
    beq {name}
    clc
    adc #${delta & 65535:04X}
    sta.l ${address:06X}
{name}:
    .a16
    .i16
'''
    return out


def _worker_gate(*, production_runtime=False):
    out = '''Worker_Gate:
    .a8
    .i16
    lda $3025
    cmp #$55
    beq Worker_Enter
    cmp #$AA
    beq Worker_LegacyAck
    jml Worker_Gate
Worker_LegacyAck:
    .a8
    .i16
    jml LEGACY_ACK
Worker_Enter:
    php
    phb
    phd
    sep #$20
    .a8
    .i16
    lda #0
    pha
    plb
    lda #8
    sta $2225
    lda #3
    sta $3027
    rep #$30
    .a16
    .i16
    lda #$7700
    tcd
Worker_Poll:
    .a16
    .i16
    sep #$20
    .a8
    lda.l $41200A
    beq Worker_NoFault
    jml Worker_FaultWait
Worker_NoFault:
    rep #$30
    .a16
    .i16
    lda.l $412434
    beq Worker_NoEventOverflow
    jml Worker_EventFault
Worker_NoEventOverflow:
    lda.l $412002
    cmp.l $412004
    beq Worker_NoTick
    jml Worker_Tick
Worker_NoTick:
    lda.l $412440
    cmp.l $412442
    beq Worker_NoRemoveCommand
    lda.l $41173C
    jsl Worker_ApplyRemove
Worker_NoRemoveCommand:
    sep #$20
    .a8
    lda.l $412006
    cmp.l $412007
    bne Worker_HasSnapshot
    jml Worker_Poll
Worker_HasSnapshot:
    and #1
    rep #$30
    .a16
    .i16
    beq Worker_Snapshot_A
    jml Worker_Snapshot_B
Worker_Snapshot_A:
    .a16
    .i16
'''
    out += _worker_snapshot(0x414000)
    out += '''    jml Worker_Snapshot_Ack
Worker_Snapshot_B:
    .a16
    .i16
'''
    out += _worker_snapshot(0x414110)
    out += '''    jml Worker_Snapshot_Ack
Worker_Snapshot_Ack:
    .a16
    .i16
    sep #$20
    .a8
    lda.l $412006
    sta.l $412007
    rep #$30
    .a16
    .i16
    jml Worker_Poll
Worker_Tick:
    .a16
    .i16
    lda.l $412004
    cmp #512
    bcc Worker_Tick__ring_room
    jml Worker_RingFault
Worker_Tick__ring_room:
    asl a
    asl a
    asl a
    tax
    lda.l $413000,x
    sta $3C
    lda.l $413002,x
    sta $3E
    lda.l $413004,x
    sta.l $412420
    lda.l $413006,x
    sta.l $412422
    lda $3C
    jsl Worker_ApplyRemove
Worker_Execute:
    .a16
    .i16
    jsl W6_UpdateWorld
    lda.l $412434
    beq Worker_EventsOkay
    jml Worker_EventFault
Worker_EventsOkay:
    lda $3A
    bne Worker_WorldFault
Worker_Complete:
    .a16
    .i16
    lda.l $412004
    inc a
    sta.l $412004
Worker_Complete__Poll:
    jml Worker_Poll
Worker_EventFault:
    .a16
    .i16
    lda #23
    bra Worker_Fault
Worker_RingFault:
    .a16
    .i16
    lda #22
    bra Worker_Fault
Worker_WorldFault:
    .a16
    .i16
    lda $3A
Worker_Fault:
    .a16
    .i16
    sta.l $412008
    sep #$20
    .a8
    lda #1
    sta.l $41200A
    rep #$30
    .a16
    .i16
Worker_FaultWait:
    .a16
    .i16
    jml Worker_FaultWait
Worker_ApplyRemove:
    .a16
    .i16
    sta.l $41243E
    lda.l $412440
    cmp.l $412442
    beq Worker_ApplyRemove__done
    lda.l $41243E
    cmp.l $412446
    bcc Worker_ApplyRemove__done
    bne Worker_ApplyRemove__bad
    lda.l $412444
    sec
    sbc #$0A00
    ldx #0
Worker_ApplyRemove__slot:
    cmp #0
    beq Worker_ApplyRemove__found
    sec
    sbc #CHAR_ZP_LEN
    bcc Worker_ApplyRemove__bad
    inx
    cpx #6
    bcc Worker_ApplyRemove__slot
    bra Worker_ApplyRemove__bad
Worker_ApplyRemove__found:
    txa
    asl a
    tax
    lda.l WHost_SlotTable,x
    tcd
    stz $FC
    jsl W6_KillUnlinked
    lda $FC
    bne Worker_ApplyRemove__bad
    lda.l $412440
    sta.l $412442
    lda #$7700
    tcd
Worker_ApplyRemove__done:
    rtl
Worker_ApplyRemove__bad:
    lda #24
    jml Worker_Fault
'''
    if production_runtime:
        # Production stages are not bounded to the six-actor fixture's 306
        # ticks. The shared command ring is a 512-row modulo ring; keep one
        # row empty so head==tail remains an unambiguous empty condition.
        old_consumer = '''    lda.l $412004
    cmp #512
    bcc Worker_Tick__ring_room
    jml Worker_RingFault
Worker_Tick__ring_room:
    asl a
    asl a
    asl a
'''
        new_consumer = '''    lda.l $412004
    and #$01FF
    asl a
    asl a
    asl a
'''
        old_advance = '''    lda.l $412004
    inc a
    sta.l $412004
'''
        new_advance = '''    lda.l $412004
    inc a
    and #$01FF
    sta.l $412004
'''
        if out.count(old_consumer) != 1 or out.count(old_advance) != 1:
            raise RuntimeError('PRODUCTION_TICK_RING_TEMPLATE_DRIFT')
        out = out.replace(old_consumer, new_consumer, 1)
        out = out.replace(old_advance, new_advance, 1)
        inputs = '''    lda.l $412004
    asl a
    asl a
    asl a
    tax
    lda.l $415000,x
    sta.l $412020
    lda.l $415002,x
    sta.l $412022
    lda.l $415004,x
    sta.l $412024
    lda.l $415006,x
    sta.l $412026
    lda.l $415002,x
    and #$4000
    beq Worker_Input_P1_Done
    lda #0
    sta.l $41214A
Worker_Input_P1_Done:
    lda.l $415006,x
    and #$4000
    beq Worker_InputApplied
    lda #0
    sta.l $4121CF
Worker_InputApplied:
'''
        out=out.replace('Worker_Execute:\n',inputs+'Worker_Execute:\n',1)
    return out.replace('LEGACY_ACK', f'${symbols(ROOT / "src/main.sym")["sa1_wait"] + 7:06X}')


def _inject_event_producers(asm):
    """Attach sequenced records to source events without changing their order."""
    def before_rtl(label, body):
        nonlocal asm
        start = asm.index(label + ':\n')
        end = asm.index('    rtl\n', start)
        asm = asm[:end] + body + asm[end:]

    before_rtl('W6_FrameChanged', '''    lda $E4
    sta.l $41243E
    lda #1
    ldx $7A
    ldy $06
    jsl S6_EventPush
''')
    before_rtl('W6_HitEffects', '''    ldx $34
    lda.l $40A0F0,x
    tay
    lda.l $40A0BA,x
    sta.l $41243E
    ldx $34
    lda #2
    jsl S6_EventPush
''')
    # Successful unlinked removal is published after the source clears its
    # canonical references. Policy rejection returns without emitting.
    asm = asm.replace('    bcs W6_KillUnlinked__done\n',
                      '    bcs W6_KillUnlinked__policy_done\n', 1)
    marker = 'W6_KillUnlinked__done:\n'
    insertion = '''W6_KillUnlinked__policy_done:
    .a16
    .i16
    rtl
W6_KillUnlinked__done:
    lda #0
    sta.l $41243E
    lda #3
    ldx $7A
    ldy #0
    jsl S6_EventPush
'''
    assert asm.count(marker) == 1
    asm = asm.replace(marker, insertion, 1)
    return asm


def _event_push():
    return '''S6_EventPush:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    sta.l $412436
    txa
    sta.l $412438
    tya
    sta.l $41243A
    tdc
    sta.l $41243C
    lda.l $412430
    sec
    sbc.l $412432
    cmp #128
    bcs S6_EventPush__overflow
    lda.l $412430
    and #$007F
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $412430
    sta.l $412450,x
    lda.l $412436
    sta.l $412452,x
    lda.l $41173C
    sta.l $412454,x
    lda.l $41173E
    sta.l $412456,x
    lda.l $41243C
    sta.l $412458,x
    lda.l $412438
    sta.l $41245A,x
    lda.l $41243A
    sta.l $41245C,x
    lda.l $41243E
    sta.l $41245E,x
S6_EventPush__record_written:
    lda.l $412430
    inc a
    sta.l $412430
    bra S6_EventPush__return
S6_EventPush__overflow:
    lda #1
    sta.l $412434
S6_EventPush__return:
    ply
    plx
    pla
    plp
    rtl
'''


def _event_drain(world_sy, main_sy):
    host_remove = world_sy['S6Host_RemoveHandle']
    hit_sfx = world_sy['S7_QueueHitSfxLong']
    context = main_sy['StageEnv_Actors'] + 68
    row_bytes = main_sy['CHAR_ZP_LEN']
    return f'''Relay_DrainEvents:
    .a16
    .i16
    php
    rep #$30
    phx
    phy
    phd
    phb
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l $7E175C
    bne Relay_DrainEvents__owned
    jml Relay_DrainEvents__done
Relay_DrainEvents__owned:
Relay_DrainEvents__loop:
    lda.l $412434
    beq Relay_DrainEvents__no_overflow
    jml Relay_DrainEvents__fault
Relay_DrainEvents__no_overflow:
    lda.l $412432
    cmp.l $412430
    bne Relay_DrainEvents__has_event
    jml Relay_DrainEvents__done
Relay_DrainEvents__has_event:
    and #$007F
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $412450,x
    cmp.l $412432
    beq Relay_DrainEvents__sequence_ok
    jml Relay_DrainEvents__fault
Relay_DrainEvents__sequence_ok:
Relay_DrainEvents__record:
    lda.l $412452,x
    cmp #1
    beq Relay_DrainEvents__visual
    cmp #2
    beq Relay_DrainEvents__hit
    cmp #3
    beq Relay_DrainEvents__unlink
    bra Relay_DrainEvents__fault
Relay_DrainEvents__visual:
    lda.l $7E176C
    inc a
    sta.l $7E176C
    bra Relay_DrainEvents__ack
Relay_DrainEvents__hit:
    ; HP/role are already coherent in the acknowledged snapshot. This record
    ; carries the ordered external hit notification; do not replay damage or
    ; increment the canonical source hit counter mirrored by that snapshot.
    ; Dispatch the existing S-CPU landed-hit sound service exactly once; the
    ; separate delivery sequence below remains independent of world counters.
    jsl ${hit_sfx:06X}
    bra Relay_DrainEvents__ack
Relay_DrainEvents__unlink:
    lda.l $412458,x
    sec
    sbc #$6000
    sta.l $41243C
    ldx #0
Relay_DrainEvents__find:
    lda.l ${context:06X},x
    cmp.l $41243C
    bne Relay_DrainEvents__next_context
    jml Relay_DrainEvents__found
Relay_DrainEvents__next_context:
    txa
    clc
    adc #{row_bytes}
    tax
    cpx #{row_bytes * 6}
    bcc Relay_DrainEvents__find
    jml Relay_DrainEvents__fault
Relay_DrainEvents__found:
    txa
    clc
    adc #$0A00
    jsl ${host_remove:06X}
    lda.l $7E1764
    beq Relay_DrainEvents__unlink_ok
    jml Relay_DrainEvents__fault
Relay_DrainEvents__unlink_ok:
Relay_DrainEvents__ack:
    lda.l $412432
    inc a
    sta.l $412432
    lda.l $7E1778
    inc a
    sta.l $7E1778
    jml Relay_DrainEvents__loop
Relay_DrainEvents__fault:
    lda #23
    sta.l $7E1764
    stp
Relay_DrainEvents__done:
    rep #$30
    pld
    plb
    ply
    plx
    plp
    rtl
'''


def _worker_snapshot(base):
    out = ''
    # Bytes 0..51 are the source world and protocol header. Each 36-byte actor
    # row then carries the render projection plus the mutable role/driver
    # mirrors consumed by the S-CPU fixture. Keep the row map explicit: the
    # previous 32-byte layout accidentally wrote frame metadata over facing
    # and read actor fields using source-context offsets against a packed row.
    for off in range(0, 0x24, 2):
        out += f'    lda.l ${0x411700 + off:06X}\n    sta.l ${base + off:06X}\n'
    for dest, src in ((36, 0x41173C), (38, 0x41173E), (40, 0x41176C),
                      (42, 0x41176E), (44, 0x411764), (46, 0x412004),
                      (48, 0x412002), (50, 0x41200A)):
        out += f'    lda.l ${src:06X}\n    sta.l ${base + dest:06X}\n'
    fields = ((0, 0x14), (2, 0x16), (4, 0x18), (6, 0x1A), (8, 0xE4),
              (10, 0x06), (12, 0xF6), (14, 0xFC), (16, 0xF0),
              (18, 0x70), (30, 0x34), (32, 0xE6))
    for slot in range(6):
        ctx = 0x411900 + slot * 256
        env = 0x412100 + slot * 133
        dest = base + 52 + slot * 36
        for dst, src in fields:
            out += f'    lda.l ${ctx + src:06X}\n    sta.l ${dest + dst:06X}\n'
        for dst, src in ((20, env + 70), (22, env + 64), (24, env + 74),
                         (26, env + 84), (28, env + 86), (34, env + 65)):
            out += f'    lda.l ${src:06X}\n    sta.l ${dest + dst:06X}\n'
    return out


def _scpu_relay(main_sy, world_sy, *, production_input=False):
    host_remove = world_sy['S6Host_RemoveHandle']
    input_code=''
    if production_input:
        input_code=f'''    lda.l $412014
    sta.l $415000,x
    lda.l $412016
    sta.l $415002,x
    lda.l $412018
    sta.l $415004,x
    lda.l $41201A
    sta.l $415006,x
    lda #0
    sta.l $412016
    sta.l $41201A
'''
    poll_wrapper=''
    if production_input:
        poll_wrapper=f'''Relay_Poll_P2:
    php
    rep #$30
    .a16
    .i16
    jsl ${main_sy['Core_Input_Poll_P2']:06X}
    pha
    lda.l $7E175C
    bne Relay_Poll_P2__owned
    pla
    plp
    rtl
Relay_Poll_P2__owned:
    lda.l ${main_sy['Input_press']:06X}
    sta.l $412014
    lda.l ${main_sy['Input_trigger']:06X}
    ora.l $412016
    sta.l $412016
    lda.l ${main_sy['Input2_press']:06X}
    sta.l $412018
    lda.l ${main_sy['Input2_trigger']:06X}
    ora.l $41201A
    sta.l $41201A
    pla
    plp
    rtl

'''
    out = f'''{poll_wrapper}Relay_QueueRemove:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    pha
    lda.l $7E175E
    cmp #2
    beq Relay_QueueRemove__owned
    pla
    jsl ${host_remove:06X}
    bra Relay_QueueRemove__return
Relay_QueueRemove__owned:
    lda.l $412440
    cmp.l $412442
    bne Relay_QueueRemove__busy
    pla
    sta.l $412444
    lda.l $7E1760
    cmp #4
    beq Relay_QueueRemove__current_tick
    lda.l $7E173C
    inc a
    bra Relay_QueueRemove__store_tick
Relay_QueueRemove__current_tick:
    lda.l $7E173C
Relay_QueueRemove__store_tick:
    sta.l $412446
    lda.l $412440
    inc a
    sta.l $412440
    bra Relay_QueueRemove__return
Relay_QueueRemove__busy:
    pla
    lda #24
    sta.l $7E1764
Relay_QueueRemove__return:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    rtl

Relay_Run:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l $7E175C
    bne Relay_Queue
    jsl Relay_Acquire
Relay_Queue:
    .a16
    .i16
    sep #$20
    .a8
    lda.l $41200A
    beq Relay_Queue__healthy
    jml Relay_Flagged
Relay_Queue__healthy:
    rep #$20
    .a16
    lda.l $7E173C
    cmp #307
    bcc Relay_Queue__tick_allowed
    jml Relay_Queued
Relay_Queue__tick_allowed:
    lda.l $412002
    cmp #512
    bcc Relay_Queue__ring_room
    jml Relay_Failed
Relay_Queue__ring_room:
    asl a
    asl a
    asl a
    tax
    lda.l $7E173C
    sta.l $413000,x
    lda.l $7E173E
    sta.l $413002,x
{input_code}    .a16
    .i16
    lda.l Relay_HostScreen_PosX
    sta.l $413004,x
    lda.l Relay_HostSpawn_HoleCount
    sta.l $413006,x
    lda.l $412002
    inc a
    sta.l $412002
    sta.l $7E175A
Relay_Queued:
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl
Relay_Failed:
    .a16
    .i16
    lda #21
    sta.l $7E1764
    bra Relay_Queued
Relay_Flagged:
    .a8
    rep #$20
    .a16
    lda #21
    sta.l $7E1764
    bra Relay_Queued

Relay_Acquire:
    .a16
    .i16
    lda #0
    sta.l $412002
    sta.l $412004
    sta.l $412008
    sta.l $412430
    sta.l $412432
    sta.l $412434
    sta.l $412436
    sta.l $412438
    sta.l $41243A
    sta.l $41243C
    sta.l $41243E
    sta.l $412440
    sta.l $412442
    sta.l $412444
    sta.l $412446
    sta.l $7E1778
'''
    if production_input:
        out += '''    lda #0
    sta.l $412014
    sta.l $412016
    sta.l $412018
    sta.l $41201A
    sta.l $412020
    sta.l $412022
    sta.l $412024
    sta.l $412026
'''
    out += '''
    sep #$20
    .a8
    lda #0
    sta.l $412006
    sta.l $412007
    sta.l $41200A
    lda #$89
    sta $2231
    stz $3026
    stz $3027
    rep #$30
    .a16
    .i16
'''
    out += _copy('Relay_InWorld', 0x7e1700, 0x411700, 256)
    out += _copy('Relay_InActors', 0x7e1900, 0x411900, 1536)
    out += _copy('Relay_InFields', main_sy['StageEnv_Actors'], 0x412100, 798)
    out += (f'    lda.l ${main_sy["Screen_PosX"]:06X}\n    sta.l $412420\n'
            f'    lda.l ${main_sy["Spawn_HoleCount"]:06X}\n    sta.l $412422\n')
    out += _relocate('Relay_ToWorker', 0x6000)
    out += '''    lda #WHost_SlotTable & $FFFF
    sta.l $411730
    lda #$001C
    sta.l $411732
    sep #$20
    .a8
    lda #$55
    sta $3025
    ldy #$FFFF
Relay_Acquired:
    .a8
    .i16
    lda $3027
    cmp #3
    beq Relay_AcquireDone
    dey
    bne Relay_Acquired
    jml Relay_Timeout
Relay_AcquireDone:
    .a8
    .i16
    rep #$30
    .a16
    .i16
    lda #1
    sta.l $7E175C
    lda #2
    sta.l $7E175E
    rtl

Relay_Flush:
    .a16
    .i16
    php
    rep #$30
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    lda.l $7E175C
    bne Relay_Flush_Owned
    jml Relay_Flush_Return
Relay_Flush_Owned:
    ldy #$FFFF
Relay_Wait_Ticks:
    .a8
    lda.l $41200A
    beq Relay_Flush_Ticks_NoFault
    jml Relay_Timeout
Relay_Flush_Ticks_NoFault:
    rep #$20
    .a16
    lda.l $412002
    cmp.l $412004
    beq Relay_Request_Snapshot
    sep #$20
    .a8
    dey
    bne Relay_Wait_Ticks
    jml Relay_Timeout
Relay_Request_Snapshot:
    .a16
    .i16
    sep #$20
    .a8
    lda.l $412006
    inc a
    sta.l $412006
    ldy #$FFFF
Relay_Wait_Snapshot:
    .a8
    lda.l $41200A
    beq Relay_Flush_Snapshot_NoFault
    jml Relay_Timeout
Relay_Flush_Snapshot_NoFault:
    lda.l $412007
    cmp.l $412006
    beq Relay_Snapshot_Ready
    dey
    bne Relay_Wait_Snapshot
    jml Relay_Timeout
Relay_Snapshot_Ready:
    .a8
    lda.l $412006
    and #1
    beq Relay_Commit_A
    jml Relay_Commit_B
Relay_Commit_A:
    rep #$30
    .a16
    .i16
'''
    out += _snapshot_commit(0x414000, world_sy, main_sy, 'A')
    out += '''    jml Relay_Flush_Return
Relay_Commit_B:
    .a8
    rep #$30
    .a16
    .i16
'''
    out += _snapshot_commit(0x414110, world_sy, main_sy, 'B')
    out += '''Relay_Flush_Return:
    .a16
    .i16
    jsl Relay_DrainEvents
    .a16
    .i16
    rep #$30
    pld
    plb
    ply
    plx
    plp
    rtl
Relay_Timeout:
    .a8
    .i16
    rep #$30
    .a16
    lda #21
    sta.l $7E1764
    stp
'''
    out += _event_drain(world_sy, main_sy)
    if production_input:
        old_queue = '''    lda.l $7E173C
    cmp #307
    bcc Relay_Queue__tick_allowed
    jml Relay_Queued
Relay_Queue__tick_allowed:
    lda.l $412002
    cmp #512
    bcc Relay_Queue__ring_room
    jml Relay_Failed
Relay_Queue__ring_room:
    asl a
    asl a
    asl a
'''
        new_queue = '''    lda.l $412002
    inc a
    and #$01FF
    cmp.l $412004
    beq Relay_Failed
    lda.l $412002
    and #$01FF
    asl a
    asl a
    asl a
'''
        old_publish = '''    lda.l $412002
    inc a
    sta.l $412002
'''
        new_publish = '''    lda.l $412002
    inc a
    and #$01FF
    sta.l $412002
'''
        if out.count(old_queue) != 1 or out.count(old_publish) != 1:
            raise RuntimeError('PRODUCTION_TICK_RING_PRODUCER_TEMPLATE_DRIFT')
        out = out.replace(old_queue, new_queue, 1)
        out = out.replace(old_publish, new_publish, 1)
    return out


def _snapshot_commit(base, world_sy, main_sy, suffix):
    out = ''
    for off in range(0, 0x24, 2):
        out += f'    lda.l ${base + off:06X}\n    sta.l ${0x7e1700 + off:06X}\n'
    for src, dst in ((40, 0x7e176C), (42, 0x7e176E), (44, 0x7e1764)):
        out += f'    lda.l ${base + src:06X}\n    sta.l ${dst:06X}\n'
    for slot in range(6):
        row = slot * main_sy['CHAR_ZP_LEN']
        ctx = 0x7e1900 + slot * 256
        env = main_sy['StageEnv_Actors'] + row
        actor = 0x7e0a00 + row
        src = base + 52 + slot * 36
        # Packed snapshot-row offsets are deliberately not source context
        # offsets. Project source state into the S-CPU mirrors without
        # aliasing facing with the sampled display frame.
        fields = ((0, 0x14), (2, 0x16), (4, 0x18), (6, 0x1A), (8, 0xE4),
                  (10, 0x06), (12, 0xF6), (14, 0xFC), (16, 0xF0), (18, 0x70),
                  (30, 0x34), (32, 0xE6))
        for source_off, dest_off in fields:
            out += f'    lda.l ${src + source_off:06X}\n    sta.l ${ctx + dest_off:06X}\n'
        for source_off, dest_off in ((20, 70), (22, 64), (18, 66), (24, 74),
                                     (26, 84), (28, 86), (34, 65)):
            out += f'    lda.l ${src + source_off:06X}\n    sta.l ${env + dest_off:06X}\n'
        out += f'''    lda #${0x1900 + slot * 256:04X}
    tcd
    lda.l ${src:06X}
    jsl ${world_sy['S6Bridge_Project']:06X}
    bcs Relay_ProjectFault_{suffix}_{slot}
    sta.l ${actor + main_sy['CHAR_POS_X']:06X}
    lda.l ${src + 2:06X}
    jsl ${world_sy['S6Bridge_Project']:06X}
    bcs Relay_ProjectFault_{suffix}_{slot}
    sta.l ${actor + main_sy['CHAR_POS_Y']:06X}
    sep #$20
    .a8
    lda.l ${src + 16:06X}
    sta.l ${actor + main_sy['CHAR_HP']:06X}
    lda.l ${src + 6:06X}
    sta.l ${actor + main_sy['CHAR_FACING_LEFT']:06X}
    rep #$30
    .a16
    .i16
    bra Relay_ProjectNext_{suffix}_{slot}
Relay_ProjectFault_{suffix}_{slot}:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_ProjectNext_{suffix}_{slot}:
    .a16
    .i16
'''
    return out
