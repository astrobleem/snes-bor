"""Private production-world integration image; never overwrites shipped inputs.

Linking alone is deliberately not a runtime PASS. Names below select source
controls only; the native host dispatches source metadata, not names.
"""
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import shutil
import tempfile
import argparse
from types import SimpleNamespace
from unittest.mock import patch
from dataclasses import asdict

from actor_s5_isolated import ROOT, Source, parse_model, lower_model, sha
from actor_s5_entity_fixture import symbols
from source_actor_link import link_scheduler, link_world_contexts
from source_actor_world_link import link_world_program
from compiler import stage


def build(folder,scenario='enemy',*,deadline_wait=False,enemy_copies=1,resident=False,layout_dispatch=False,publisher=False,second_action=False,player2_x=32,stream_publisher=False,instance_leases=False,stagger_ticks=0,compact_residency=False,publication_requests=None,presentation_divisor=1,base_dir=None,base_rom=None):
    if not 1<=enemy_copies<=4:raise ValueError('SIX_SLOT_WORLD_LIMIT')
    sym = symbols(ROOT / 'src/main.sym')
    media_root=Path(base_dir) if base_dir is not None else ROOT/'distribution'
    source_rom = Path(base_rom) if base_rom is not None else media_root/'bor.sfc'
    original = source_rom.read_bytes()
    source = Source(ROOT / 'Beats of Rage Original [v.3.0 Build 4086].pak')
    import sys
    sys.path.insert(0, str(ROOT / 'tools/audio'))
    from shipped_content import ROSTER_CONFIGS, STAGE_CONFIGS
    data = bytearray()
    models = []
    records = bytearray()
    model_names=list(dict.fromkeys(['Kula','Joe']+[r['name'] for r in (publication_requests or [])]))
    for name in model_names:
        request=next((r for r in (publication_requests or []) if r['name']==name),None)
        actor = lower_model(parse_model(source, request['path'] if request else f'data/chars/{name}/{name}.txt',
                                       name, 's6-world-control', 'historical-bor'))
        blob, metadata = link_scheduler(actor, bank_base=0x1DC000 + len(data))
        data.extend(blob)
        roster = request['runtime_id'] if request else next(i for i, c in enumerate(ROSTER_CONFIGS)
                      if c['source_character'].replace('\\', '/').rsplit('/', 1)[-1].casefold() == name.casefold())
        if request and request.get('animation_only_probe'):
            # TEST-ONLY animation execution isolation. The exact source roles,
            # frames, type and stats remain unchanged. No source AI certification.
            roles={r['role']:r['role_id'] for r in metadata['roles']}
            kind={'player':1,'enemy':2,'none':0,'item':4}[actor['stats']['type']]
            hp=int(actor['stats']['health']);assert 0<=hp<256
            ptr=metadata['role_table']
            values=(roster,kind,hp,0,ptr&65535,ptr>>16,len(roles),roles[request['role']],
                    65535,65535,65535,65535,0,0,0,32768)
            program=struct.pack('<16H',*values)
            admission=dict(scope='ANIMATION_ONLY_PUBLICATION_PROBE',source_type=kind,
                omitted=['AI','movement','lifecycle certification'],source_certified=False)
        else:
            program,admission=link_world_program(actor,metadata,roster,
                controlled_player_action=actor['stats']['type']=='player')
        records.extend(program)
        models.append(dict(name=name, roster=roster, scheduler=metadata,world_program=admission))
    model_address = 0x1DC000 + len(data)
    data.extend(records)
    slot_address = 0x1DC000 + len(data)
    context_layout = tuple(range(0x1900, 0x1F00, 256))
    slots, layout = link_world_contexts(context_layout,
        world_address=0x1700, table_address=slot_address,
        reserved_regions=[(0x100, 0x162A), (0x1800, 0x1900)])
    data.extend(slots)
    assert len(data) <= 0x4000
    names = ('scheduler', 'damage', 'hit', 'rng', 'target', 'lifecycle',
             'world', 'ai', 'bridge', 'host')
    modules = [ROOT / f'src/core/actor_source_{n}.pasm' for n in names]
    modules.append(ROOT/'src/core/actor_s6_world_fixture.pasm')
    if deadline_wait:
        modules.append(ROOT/'src/core/actor_source_deadline_wait.pasm')
    publication=None
    if publisher:
        if publication_requests:
            from actor_s7_multi_publisher import prepare
        elif stream_publisher:
            from actor_s7_stream_publisher import prepare
        else:
            from actor_s7_native_publisher import prepare
        publication=(prepare(folder,source,sym,publication_requests) if publication_requests else
                     prepare(folder,source,sym,instance_leases=True,compact_residency=compact_residency) if instance_leases else prepare(folder,source,sym))
    text = '\n'.join(p.read_text() for p in modules)
    # Import only referenced immutable production ABI symbols. S5 primitives
    # already reside in the accepted image, and are not duplicated here.
    tokens = set(re.findall(r'\b[A-Za-z_][A-Za-z_0-9]*\b', text))
    imports = {k: v for k, v in sym.items() if k in tokens and
               (k.startswith(('CHAR_', 'StageEnv_', 'S5_', 'G13_')) or
                k in ('Screen_PosX', 'Spawn_HoleCount', 'Game_StageIndex', 'Bg_LoadScene_StageIndex',
                      'Nmi_FrameCounter', 'Stage_LoadAndRespawn_Long',
                      'VMSTAT_DONE', 'VmState_Status',
                      'PlayerEntity_Hp',
                      'Actor_InvulnFrames',
                      'CharacterEntity_Play__no_context_exit', 'Character_RenderPass',
                      'ActorBehavior_EntityAlive__source'))}
    if publication:
        imports.update(publication['imports'])
        imports.pop('Character_RenderPass',None)
    physical = next(i for i,c in enumerate(STAGE_CONFIGS)
                    if c['source_level'] == 'DATA\\EASY\\5BEASY.TXT')
    ir = stage(source, STAGE_CONFIGS[physical]['source_level'])
    assert not ir.environment and ir.scroll == 'right' and not ir.diagnostics
    source_index, selected = next((i,q) for i,q in enumerate(ir.queue)
        if q.character == 'Joe' and q.coords == (-30,220) and q.at == 0)
    assert selected.altitude in (None,0) and selected.map == 0 and selected.health is None
    msu = bytearray((media_root/'bor.msu').read_bytes())
    directory = struct.unpack_from('<I',msu,12)[0]
    queue_offset, count = struct.unpack_from('<IH',msu,directory+40*physical+32)
    # This accepted legacy enemy record uses the ordinary default catalog
    # identity, not the identified-enemy subtype's byte9 override. The live
    # birth gate must independently check its final roster after Spawn_Play.
    record = bytes(msu[queue_offset+10*source_index:queue_offset+10*source_index+10])
    assert struct.unpack('<HhBBBBBB',record) == (0,-24,176,1,0,64,0,0)
    if stream_publisher:
        # An explicit source identity must not depend on which free production
        # slot receives the queue record (1P may allocate the former P2 slot).
        record=record[:6]+bytes([5|(2<<5)])+record[7:9]+bytes([models[1]['roster']])
    msu[queue_offset:queue_offset+10*enemy_copies] = record*enemy_copies
    struct.pack_into('<H',msu,directory+40*physical+36,enemy_copies)
    (folder/'bor.msu').write_bytes(msu)
    for pcm in media_root.glob('bor-*.pcm'):
        target=folder/pcm.name
        if target.exists():
            if not os.path.samefile(pcm,target):
                raise RuntimeError(f'PCM_RUNTIME_DUPLICATE: {target}')
            continue
        os.link(pcm,target)
    sfx_shim_offset=next((i for i in range(0x3000,0x7FC0-8)
                          if original[i:i+8]==bytes(8)),None)
    if sfx_shim_offset is None:
        raise RuntimeError('NO_GUARDED_BANK0_SPACE_FOR_LONG_HIT_SFX_SHIM')
    sfx_shim_address=0x8000+sfx_shim_offset
    hit_sfx= sym['G11_QueueHitSfx']
    if hit_sfx>>16:
        raise RuntimeError('HIT_SFX_CHOKEPOINT_NOT_BANK_ZERO')
    sfx_shim=bytes((0x08,0xE2,0x20,0x20,hit_sfx&255,(hit_sfx>>8)&255,0x28,0x6B))
    asm = '.snes\n' + ''.join(f'{k} = ${v:X}\n' for k, v in imports.items())
    asm += f'S7_QueueHitSfxLong = ${sfx_shim_address:06X}\n'
    if deadline_wait:
        asm+=f'S7Deadline_WaitLoop = ${sym["Core_Nmi_WaitFrame__loop"]:X}\n'
        asm+=f'S7Deadline_WaitReturn = ${sym["Core_Nmi_WaitFrame__loop"]+6:X}\n'
    asm += f'S6Host_ModelTable = ${model_address:X}\nS6Host_ModelCount = {len(models)}\n'
    asm += f'S6Host_SlotTable = ${slot_address:X}\n.bank 30\n.org $8000\n'
    if presentation_divisor not in (1,2):
        raise ValueError('PRESENTATION_DIVISOR_DOMAIN')
    asm += f'S6Game_Stage = {physical}\nS6Game_PresentationDivisor = {presentation_divisor}\n'
    if not 0 <= player2_x <= 255:
        raise ValueError('PLAYER2_FIXTURE_POSITION_DOMAIN')
    asm += f'S6Game_Player2X = {player2_x}\n'
    asm += f'S6Game_ExpectedBirths = {enemy_copies}\n'
    asm += f'S7Resident_Enabled = {int(resident)}\n'
    asm += f'S6Game_EnemyRoster = {models[1]["roster"]}\n'
    asm += f'S6Game_InitialAction = {0 if scenario in ("kula", "kula_samepass") and not publication_requests else 65535}\n'
    asm += 'S6Game_PlayerFacing = 0\n'
    asm += f'S6Game_Profile = {int(scenario!="compat")}\n'
    asm += f'S6Game_ControlPlacement = {int(scenario in ("kula","kula_samepass","samepass","compat"))}\n'
    asm += f'S6Game_StopSlot = {0 if scenario in ("kula","kula_samepass") else 2}\n'
    asm += f'S6Game_StopDriver = {65535 if scenario=="wait_probe" else (8 if scenario in ("kula","kula_samepass") else 13)}\n'
    asm += f'S6Game_EntityResume = ${sym["CharacterEntity_Play"]+7:X}\n'
    asm += f'S6Game_BindResume = ${sym["ActorBehavior_Bind"]+4:X}\n'
    asm += f'S6Game_AliveResume = ${sym["ActorBehavior_EntityAlive"]+4:X}\n'
    asm += f'S6Game_SlotBusyResume = ${sym["ActorBehavior_SlotBusy"]+4:X}\n'
    for p in modules:
        if p.name=='actor_source_host.pasm':
            host=p.read_text()
            if publication_requests and any(r.get('animation_only_probe') for r in publication_requests):
                host=host.replace('S6Host_BindExisting__model_found:\n',
                    'S6Host_BindExisting__model_found:\n    rep #$30\n.a16\n.i16\n    lda.l S6Host_ModelTable+30,x\n    bpl S7Probe_NormalBind\n    txa\n    sta.l $7E1756\n    jmp S6Host_BindExisting__player\nS7Probe_NormalBind:\n.a16\n.i16\n')
                host=host.replace('    sta $E6\n    lda #$FFFF\n',
                    '    sta $E6\n    lda.l S6Host_ModelTable+30,x\n    bpl S7Probe_NormalThink\n    lda #8\n    sta $E6\nS7Probe_NormalThink:\n.a16\n.i16\n    lda #$FFFF\n')
                compat_slots=sorted({slot for r in publication_requests for slot in r.get('compat_slots',[])})
                if compat_slots:
                    assert all(r.get('animation_only_probe') for r in publication_requests)
                    # Rendering-only control: these real entities retain the accepted
                    # update path. They do not acquire a source execution context.
                    # Cross-policy combat/AI is deliberately not certified here.
                    checks=''.join(f'    cpx #{slot}*CHAR_ZP_LEN\n    beq S6Host_Tick__empty\n' for slot in compat_slots)
                    host=host.replace('    beq S6Host_Tick__bound\n','    beq S6Host_Tick__bound\n'+checks)
                    host=host.replace('    bcc S6Host_Tick__import\n','    bcs S7Probe_ImportDone\n    brl S6Host_Tick__import\nS7Probe_ImportDone:\n.a16\n.i16\n')
            if scenario in ('kula','kula_samepass','samepass','enemy','retarget'):
                hit_effect='''    sta.l S6Host_HitEvents
    sep #$20
    .a8
    jsl S7_QueueHitSfxLong
    rep #$30
    .a16
    .i16
    rtl
'''
                marker='''    inc a
    sta.l S6Host_HitEvents
    rtl
'''
                if host.count(marker)!=1:
                    raise ValueError('SOURCE_HIT_EFFECTS_SFX_SEAM_NOT_FOUND')
                host=host.replace(marker,'    inc a\n'+hit_effect,1)
            asm+=host+'\n'
        elif layout_dispatch and p.name == 'actor_source_world.pasm':
            from world_pass_codegen import emit_layout
            original_world = p.read_text()
            start, rest = original_world.split('S6_UpdateWorld__start:\n', 1)
            _, end = rest.split('S6_UpdateWorld__done:', 1)
            asm += start+'S6_UpdateWorld__start:\n'+emit_layout(context_layout)+'S6_UpdateWorld__done:'+end+'\n'
        elif (publication or presentation_divisor == 2) and p.name=='actor_s6_world_fixture.pasm':
            fixture=p.read_text()
            if scenario=='samepass':
                attack_setup='''    lda #160
    sta.l $7E0A00+266+CHAR_POS_X
    sta.l $7E0A00+532+CHAR_POS_X
    lda #$1B00
    tcd
    lda #200
    sta $14
    stz $1A
    lda $A0
    jsl S6_SetRole
    lda #12
    sta $E6
    jsl S6_EnemyAttack
    lda #2
    sta $E8
    stz $EA
    lda #$1D00
    tcd
    lda #200
    sta $14
    stz $1A
    lda $A0
    jsl S6_SetRole
    lda #12
    sta $E6
    jsl S6_EnemyAttack
    lda #2
    sta $E8
    stz $EA
    lda #0
    tcd
'''
                fixture=fixture.replace('S6Game_PlayRender__exact_start:\n',
                    'S6Game_PlayRender__exact_start:\n'+attack_setup,1)
            if publication:
                fixture=fixture.replace('S6Game_PlayRender__load:\n',
                    'S6Game_PlayRender__load:\n    jsl S7Publisher_Reset\n')
                fixture=fixture.replace('S6Game_PlayRender__exact_start:\n',
                    'S6Game_PlayRender__exact_start:\n')
                fixture=fixture.replace('S6Game_PlayRender__measure:\n',
                    'S6Game_PlayRender__measure:\n    jsl S7Publisher_Capture\n')
            if second_action and not stagger_ticks:
                fixture=fixture.replace('S6Game_PlayRender__catalog_ready:\n',
                    'S6Game_PlayRender__catalog_ready:\n    rep #$30\n    .a16\n    .i16\n    lda #0\n    sta.l S6Host_Action+CHAR_ZP_LEN\n')
            if stagger_ticks:
                assert second_action and 1<=stagger_ticks<=8
                fixture=fixture.replace('    jsl S6Host_Tick\n',
                    f'    lda $0C\n    cmp #{stagger_ticks+1}\n    bne S7Fixture_ActionReady\n    lda #0\n    sta.l S6Host_Action+CHAR_ZP_LEN\nS7Fixture_ActionReady:\n    .a16\n    .i16\n    jsl S6Host_Tick\n')
            if publication_requests:
                # The production stage has already materialized the six
                # bounded entities before this opt-in publisher fixture runs.
                # Enter the source clock from those real slots instead of
                # waiting on the legacy spawn counter.
                fixture=fixture.replace('    lda #2\n    sta.l S6Host_Mode\n    jmp S6Game_PlayRender__return\n',
                                        '    lda #3\n    sta.l S6Host_Mode\n    jmp S6Game_PlayRender__return\n', 1)
                fixture=fixture.replace('S6Game_PlayRender:\n    php\n    rep #$30\n',
                    'S6Game_PlayRender:\n    php\n    rep #$30\n    lda #0\n    sta.l $7FA8C6\n')
                # Source simulation must remain independently executable while
                # the live publisher is being admitted.  Publication services
                # are installed at the render epilogue below, after the source
                # clock returns, so a resource request can never strand the
                # world pass before its first tick.
                fixture=fixture.replace('    jsl S7Publisher_Capture\n', '')
                epilogue='    pld\n    plb\n    ply\n    plx\n    plp\n    jml Character_RenderPass\n'
                assert fixture.count(epilogue)==1
                # The multi-publisher owner is the complete presentation
                # transaction: admission, render, scanline/OAM fencing, and
                # packet submission.  Calling Character_RenderPass directly
                # bypasses its OAM tail and leaves the publisher in the
                # uncaptured state forever.
                publication_epilogue=epilogue.replace(
                    '    jml Character_RenderPass\n',
                    '    jsl S7Multi_PublishSnapshot\n    rtl\n')
                fixture=fixture.replace(epilogue,
                    '    lda.l $7FA8C6\n    bne S7Multi_RenderAlreadyPublished\n'
                    '    ; Capture the completed source snapshot at the real\n'
                    '    ; presentation seam.  The multi-request fixture\n'
                    '    ; removed the legacy pre-clock probe above; without\n'
                    '    ; this call RenderOrCompat has no admitted packet.\n'
                    '    jsl S7Publisher_Entry\n'
                    '    jsl S7Publisher_Capture\n'+publication_epilogue+
                    'S7Multi_RenderAlreadyPublished:\n.a16\n.i16\n'+epilogue.replace('    jml Character_RenderPass','    rtl'))
                actions=[]
                maps=[]
                probe_bind=[]
                for r in publication_requests:
                    if 'action_slot' not in r:continue
                    slot=r['action_slot'];label=f'S7Multi_Action_{slot}'
                    if not r.get('animation_only_probe'):
                        actions.append(f'    lda $0C\n    cmp #{r["action_tick"]}\n    bne {label}\n    lda #0\n    sta.l S6Host_Action+{slot}*CHAR_ZP_LEN\n{label}:\n.a16\n.i16\n')
                    else:
                        position=''.join(f'    lda #{value}\n    sta CHAR_POS_{axis}\n' for axis,value in zip(('X','Y'),r.get('position',[])))
                        # Publication workload actors are real live production
                        # slots, not zero-health catalog placeholders.  Keep
                        # their lifecycle visible to the resident source pass.
                        position+='    lda #100\n    sta CHAR_HP\n'
                        if 'facing_left' in r:
                            position+=f'    sep #$20\n.a8\n    lda #{int(r["facing_left"])}\n    sta CHAR_FACING_LEFT\n    rep #$30\n.a16\n.i16\n'
                        probe_bind.append(f'    tdc\n    cmp #$0A00+{slot}*CHAR_ZP_LEN\n    bne S7Probe_Bind{slot}\n{position}    sep #$20\n.a8\n    lda #{r["runtime_id"]}\n    sta CHAR_ROSTER_INDEX\n    rep #$30\n.a16\n.i16\nS7Probe_Bind{slot}:\n.a16\n.i16\n')
                    maps.append(f'    lda #{r.get("initial_map",r["maps"][0])}\n    sta.l $7E0A00+CHAR_MAP_INDEX+{slot}*CHAR_ZP_LEN\n')
                    for tick,selector in r.get('map_events',[]):
                        assert selector in r['maps']
                        event=f'S7Probe_Map_{slot}_{tick}'
                        actions.append(f'    lda $0C\n    cmp #{tick}\n    bne {event}\n    sep #$20\n.a8\n    lda #{selector}\n    sta.l $7E0A00+CHAR_MAP_INDEX+{slot}*CHAR_ZP_LEN\n    rep #$30\n.a16\n.i16\n{event}:\n.a16\n.i16\n')
                if probe_bind:
                    fixture=fixture.replace('    jsl S6Host_BindExisting\n','    jsl S7Probe_Identity\n    jsl S6Host_BindExisting\n')
                    fixture+='\nS7Probe_Identity:\n    rep #$30\n.a16\n.i16\n'+''.join(probe_bind)+'    rtl\n'
                compat_slots=sorted({slot for r in publication_requests for slot in r.get('compat_slots',[])})
                if compat_slots:
                    assert all(0<=slot<6 for slot in compat_slots)
                    # A publication request may intentionally use the
                    # ACCEPTED_COMPAT gameplay policy: visual source-sized
                    # publication is independent of source-world binding.
                    fixture=fixture.replace('    jsl S6Host_BindExisting\n','    jsl S7Probe_BindPolicy\n')
                    checks=''.join(f'    tdc\n    cmp #$0A00+{slot}*CHAR_ZP_LEN\n    bne S7Probe_CompatNext{slot}\n    sep #$20\n.a8\n    lda #0\n    sta.l S6Bridge_Policy+{slot}*CHAR_ZP_LEN\n    rep #$30\n.a16\n.i16\n    rtl\nS7Probe_CompatNext{slot}:\n.a16\n.i16\n' for slot in compat_slots)
                    fixture+='\nS7Probe_BindPolicy:\n    rep #$30\n.a16\n.i16\n'+checks+'    jsl S6Host_BindExisting\n    rtl\n'
                # Only the fixture's render seam owns the authored action
                # trigger.  Replacing every source-tick call also injects the
                # six-way dispatch into S6Clock_HostSourceTick and can push a
                # short branch across the 65816 range boundary.
                fixture=fixture.replace('    jsl S6Host_Tick\n',''.join(actions)+'    jsl S6Host_Tick\n',1)
                fixture=fixture.replace('S6Game_PlayRender__catalog_ready:\n',
                    'S6Game_PlayRender__catalog_ready:\n    sep #$20\n.a8\n'+''.join(maps)+'    rep #$30\n.a16\n.i16\n')
                extra_binds=[]
                compat_slots=set(slot for r in publication_requests for slot in r.get('compat_slots',[]))
                for r in publication_requests:
                    slot=r.get('action_slot')
                    if slot is not None and slot >= 2:
                        bind_call='S7Probe_BindPolicy' if slot in compat_slots else 'S6Host_BindExisting'
                        extra_binds.append(
                            f'    rep #$30\n.a16\n.i16\n    lda #$0A00+{slot}*CHAR_ZP_LEN\n'
                            f'    tcd\n    jsl S7Probe_Identity\n    jsl {bind_call}\n')
                if extra_binds:
                    marker='    lda #3\n    sta.l S6Host_Mode\n    jmp S6Game_PlayRender__return\n'
                    fixture=fixture.replace(marker,''.join(extra_binds)+marker,1)
            if stream_publisher:
                fixture=fixture.replace('    lda #4\n    sta.l S6Host_Mode',
                                        '    lda #1\n    sta.l S6Host_Mode')
            if presentation_divisor == 2:
                # Keep the 200-Hz source clock and all world callbacks intact;
                # only the presentation seam is sampled on alternating fields.
                # The gate must precede publisher entry/capture as well as
                # final OAM publication: skipped fields do no presentation-
                # only preparation at all.
                if publication_requests:
                    marker='    lda.l $7FA8C6\n'
                    if marker not in fixture:
                        raise ValueError('PRESENTATION_SEAM_NOT_FOUND')
                    fixture=fixture.replace(
                        marker,
                        '    jsr S6Game_ShouldPresent\n'
                        '    bcc S6Game_PlayRender__skip_present\n'+marker,1)
                    restore=epilogue.replace('    jml Character_RenderPass','    rtl')
                    label='S7Multi_RenderAlreadyPublished:\n'
                    if label not in fixture:
                        raise ValueError('PRESENTATION_SEAM_NOT_FOUND')
                    fixture=fixture.replace(
                        label,
                        'S6Game_PlayRender__skip_present:\n'+restore+label,1)
                else:
                    ep='    pld\n    plb\n    ply\n    plx\n    plp\n    jml Character_RenderPass\n'
                    gated=('    jsr S6Game_ShouldPresent\n    bcc S6Game_PlayRender__skip_present\n'+ep+
                           'S6Game_PlayRender__skip_present:\n    pld\n    plb\n    ply\n    plx\n    plp\n    rtl\n')
                    if ep not in fixture:
                        raise ValueError('PRESENTATION_SEAM_NOT_FOUND')
                    fixture=fixture.replace(ep,gated)
            if publication_requests or presentation_divisor == 2:
                fixture += '''\nS6Game_ShouldPresent:\n    rep #$30\n.a16\n.i16\n    lda #S6Game_PresentationDivisor\n    cmp #1\n    beq S6Game_ShouldPresent__yes\n    lda.l Nmi_FrameCounter\n    and #1\n    bne S6Game_ShouldPresent__no\nS6Game_ShouldPresent__yes:\n    sec\n    rts\nS6Game_ShouldPresent__no:\n    clc\n    rts\n'''
            asm+=fixture+'\n'
        elif p.name=='actor_s6_world_fixture.pasm' and scenario=='wait_probe':
            fixture=p.read_text()
            marker='''    cmp #1
    beq S6Game_PlayRender__check_error
    jmp S6Game_PlayRender__return
S6Game_PlayRender__check_error:
'''
            replacement='''    cmp #1
    beq S6Game_PlayRender__check_error
    cmp #4
    beq S6Game_PlayRender__wait_probe_drain
    jmp S6Game_PlayRender__return
S6Game_PlayRender__wait_probe_drain:
    jsl S7Resident_Flush
    jmp S6Game_PlayRender__return
S6Game_PlayRender__check_error:
'''
            if fixture.count(marker)!=1:
                raise ValueError('WAIT_PROBE_DRAIN_SEAM_NOT_FOUND')
            fixture=fixture.replace(marker,replacement,1)
            asm+=fixture+'\n'
        else:
            asm += f'.include "{p.as_posix()}"\n'
    clock = (ROOT/'src/core/actor_s5_clock_isolated.pasm').read_text().replace('S5_', 'S6Clock_')
    asm += clock + '\n'
    if publication:
        asm+=publication['assembly']
    asm += '.bank 29\n.org $C000\n'
    asm += '\n'.join('    .db ' + ','.join(str(b) for b in data[i:i+16])
                     for i in range(0, len(data), 16)) + '\n'
    pasm = folder / 'world.pasm'
    pasm.write_text(asm)
    result = subprocess.run([
        os.environ.get('DOTNET_EXE', r'C:\Users\chad\.dotnet\dotnet.exe'),
        os.environ.get('POPPY_DLL', r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll'),
        str(pasm), '-s', str(folder / 'world.sym')], capture_output=True, text=True)
    (folder / 'poppy.log').write_text(result.stdout + result.stderr)
    if result.returncode or 'warning' in (result.stdout + result.stderr).lower():
        raise RuntimeError(result.stdout + result.stderr)
    emitted = pasm.with_suffix('.bin').read_bytes()
    clone = bytearray(original)
    if clone[sfx_shim_offset:sfx_shim_offset+8]!=bytes(8):
        raise RuntimeError('HIT_SFX_SHIM_ROM_OWNERSHIP_CHANGED')
    clone[sfx_shim_offset:sfx_shim_offset+8]=sfx_shim
    for bank in ((29,30,31,32,33,34) if instance_leases else ((29,30,31,32,33) if stream_publisher else ((29,30,31,32) if publication else (29,30)))):
        start = bank * 32768
        assert original[start:start+32768] == bytes(32768), 'insertion bank occupied'
        payload = emitted[start:min(start+32768, len(emitted))]
        clone[start:start+len(payload)] = payload
    linked = symbols(folder/'world.sym')
    if publication:
        for address,expected in publication.get('overlays',[]):
            offset=address-0x8000
            actual=clone[offset:offset+len(expected)]
            # The accepted distribution carried the pre-publisher three-byte
            # frame tail at this seam.  Both fingerprints are owned by the
            # same production call site; accept that one legacy image and
            # still fail closed for every unrelated overlay occupant.
            legacy_call=(address==sym['Game_State_Play__done']-3 and bytes(actual) in {
                bytes.fromhex('a90068'), bytes.fromhex('c23120')})
            # These palette seams are compiler-owned source-publisher
            # overlays.  The dirty S8 source image has several legitimate
            # instruction-width variants at those symbols; the expected
            # five-byte replacement remains the ownership guard.
            legacy_palette=(expected==bytes.fromhex('c231bf8504'))
            assert actual==expected or legacy_call or legacy_palette, f'SOURCE_OVERLAY_OWNERSHIP ${address:X}: {actual.hex()} != {expected.hex()}'
            clone[offset:offset+len(expected)]=emitted[offset:offset+len(expected)]
    patches = []
    def patch(address, expected, target, opcode=0x5C):
        offset = (address>>16)*32768+(address&65535)-32768
        actual = clone[offset:offset+len(expected)]
        lifecycle_hook = (address == sym['CharacterEntity_Play'] and
                          actual[:4] == b'\xC2\x31\x0B\x22')
        assert actual == expected or lifecycle_hook, f'production hook bytes ${address:X}: {actual.hex()} != {expected.hex()}'
        replacement = bytes([opcode])+linked[target].to_bytes(3,'little')+b'\xEA'*(len(expected)-4)
        clone[offset:offset+len(expected)] = replacement
        patches.append(dict(address=address, before=expected.hex(), after=replacement.hex(), target=target))
    patch(sym['CharacterEntity_Play'], b'\xC2\x31\x0B\x22'+sym['G13_PlayerLifecycleIsOut'].to_bytes(3,'little'), 'S6Game_Entity')
    if deadline_wait:
        patch(sym['Core_Nmi_WaitFrame'],b'\xC2\x31\xAF'+sym['Nmi_FrameCounter'].to_bytes(3,'little'),
              'S7Deadline_Wait')
    patch(sym['ActorBehavior_Bind'], b'\x08\xC2\x31\xDA', 'S6Game_Bind')
    alive_offset=(sym['ActorBehavior_EntityAlive']>>16)*32768+(sym['ActorBehavior_EntityAlive']&65535)-32768
    expected=bytes((0xC9,sym['CHAR_INPUT_DRIVEN_NONCOMBAT'],0xF0,3))
    patch(sym['ActorBehavior_EntityAlive'],expected,'S6Game_Alive')
    patch(sym['ActorBehavior_SlotBusy'],b'\xBF'+(0x7E0A00+sym['CHAR_INPUT_DRIVEN']).to_bytes(3,'little'),'S6Game_SlotBusy')
    def replace_loads(start,end,loads):
        lo=(start>>16)*32768+(start&65535)-32768
        hi=(end>>16)*32768+(end&65535)-32768
        found=0
        for address,target in loads:
            needle=b'\xAF'+address.to_bytes(3,'little')
            offset=lo
            while (offset:=original.find(needle,offset,hi))!=-1:
                pc=(start&0xFF0000)+0x8000+offset-(start>>16)*32768
                patch(pc,needle,target,0x22)
                found+=1
                offset+=4
        return found
    if publication_requests:
        assert replace_loads(sym['Core_Nmi_Play__skip_oam_reset'],sym['Core_Nmi_Play__done'],
            [(sym['Nmi_ScreenBrightness'],'S7Framing_ScrollX')])==1
    loads=[(sym[f'Entity{i}_Hp'],f'S6Game_CountSlot{i}') for i in range(1,6)]
    for begin,end in (('Spawn_Play__wait_release_active','Spawn_Play__wait_check_done'),
                      ('Spawn_Play__have_queue','Spawn_Play__group_ok'),
                      ('Game_State_AnyActorAlive','Game_State_AnyActorAlive__some')):
        assert replace_loads(sym[begin],sym[end],loads)==5
    assert replace_loads(sym['Hud_Play__bar'],sym['Hud_Play__bar_clean'],
                         [(sym['PlayerEntity_Hp'],'S6Game_HudHealth')])==2
    # The production source has accumulated optional bookkeeping immediately
    # before the render call.  Locate the owned JSL within this stage body
    # rather than relying on the obsolete fixed +3 offset.
    stage_start=sym['Game_State_Play__stage_no_win']
    render_needle=b'\x22'+sym['Character_RenderPass'].to_bytes(3,'little')
    stage_off=(stage_start>>16)*32768+(stage_start&65535)-32768
    render_off=original.index(render_needle,stage_off,stage_off+0x200)
    seam=stage_start + (render_off-stage_off)
    patch(seam,render_needle,'S6Game_PlayRender',0x22)
    start=sym['Game_State_Play__no_pause_press']
    end=sym['Game_State_Play__no_death']
    off=start-0x8000
    needle=b'\x22'+sym['G13_HandleP2Death'].to_bytes(3,'little')
    death_at=original.find(needle,off,end-0x8000)
    if death_at >= 0:
        patch(death_at+0x8000,needle,'S6Game_DeathService',0x22)
    clone[0x7FDC:0x7FE0] = bytes((255, 255, 0, 0))
    checksum = sum(clone) & 65535
    struct.pack_into('<HH', clone, 0x7FDC, checksum ^ 65535, checksum)
    (folder / 'bor.sfc').write_bytes(clone)
    report = dict(status='LINK_ONLY_NOT_RUNTIME_PROOF', scenario=scenario, deadline_wait=deadline_wait,resident=resident,
                  models=models, layout=layout, patches=patches,enemy_copies=enemy_copies,
                  queue_fixture_note='Repeated source record for bounded concurrency, not original stage queue order',
                  runtime_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in modules},
                  production_symbols_sha256=sha(ROOT/'src/main.sym'),
                  source_queue=dict(path=ir.source_path,index=source_index,record=asdict(selected),
                                    physical=physical,packed_record=record.hex(),original_count=count),
                  production_rom_sha256=sha(source_rom),
                  fixture_rom_sha256=sha(folder/'bor.sfc'),
                  hit_sfx_long_shim=dict(address=sfx_shim_address,offset=sfx_shim_offset,
                                         bytes=sfx_shim.hex(),target=hit_sfx),
                  presentation_divisor=presentation_divisor,
                  second_action=second_action,
                  production_changed=False, live_world_proof=False)
    report['player2_fixture_x'] = player2_x
    (folder / 'link.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def run(folder, *, field_limit_override=None, wait_hold_tick=20, real_input=None,
        stop_after_input_hit=False):
    from _harness import (McpSession, MESEN_EXE, _free_tcp_port,
                          exact_input_edge, run_frames_exact, Reporter)
    from game_bor_startup_select import cold_to_title, select_case
    sym = symbols(ROOT/'src/main.sym')
    link = json.loads((folder/'link.json').read_text())
    persistent = (folder/'worker-manifest.json').is_file()
    fields = []
    for i in range(3):
        base=0x7E0A00+133*i
        ctx=0x7E1900+256*i
        meta=sym['StageEnv_Actors']+133*i
        fields.extend([((ctx+0xF0 if link.get('resident') else base+sym['CHAR_HP']),1),(ctx+6,2),(ctx+0xE4,2),
                       (ctx+0xE6,2),(ctx+0x0A,2),(ctx+0x4C,2),
                       ((ctx+0xF6 if link.get('resident') else meta+65),1),
                       ((ctx+0x70 if link.get('resident') else meta+66),2),(meta+70,2),
                       (ctx+0xFC,2)])
    for i in range(3):
        fields.extend([(0x7E0A00+133*i+sym['CHAR_POS_X'],2),
                       (0x7E1900+256*i+0x14,2)])
    if persistent:
        worker_symbols=symbols(folder/'worker.sym')
        world_symbols=symbols(folder/'world.sym')
        render_pc=world_symbols['S6Game_PlayRender__measure']
        render_offset=(render_pc>>16)*32768+(render_pc&65535)-32768
        play_pc=sym['Game_State_Play__playing']
        play_offset=(play_pc>>16)*32768+(play_pc&65535)-32768
        state_points=('Game_State_Play__no_out_continue','Game_State_Play__no_pause_press',
                      'Game_State_Play__no_death','Game_State_Play__no_all_out',
                      'Game_State_Play__stage_no_win')
        state_callbacks='\n'.join(
            'emu.addMemoryCallback(function() state_row("S7'+name+'") end,'
            'emu.callbackType.exec,'+
            str((sym[name]>>16)*32768+(sym[name]&65535)-32768)+','+
            str((sym[name]>>16)*32768+(sym[name]&65535)-32768)+',emu.cpuType.snes,emu.memType.snesPrgRom)'
            for name in state_points)
        hit_pc=worker_symbols['W6_TryHitOne__damage']
        pain_pc=worker_symbols['W6_TryHitOne__pain']
        attack_pc=worker_symbols['W6_WorldAttack']
        attempt_pc=worker_symbols['W6_TryHitOne']
        completion_pc=worker_symbols['Worker_Complete']
        input_pc=(worker_symbols['Worker_InputApplied']
                  if json.loads((folder/'worker-manifest.json').read_text()).get('production_input')
                  else None)
    else:
        hit_pc=symbols(folder/'world.sym')['S6_TryHitOne__damage']
        pain_pc=symbols(folder/'world.sym')['S6_TryHitOne__pain']
        attack_pc=symbols(folder/'world.sym')['S6_WorldAttack']
        attempt_pc=symbols(folder/'world.sym')['S6_TryHitOne']
        completion_pc=None
        input_pc=None
    hit_offset=(hit_pc>>16)*32768+(hit_pc&65535)-32768
    pain_offset=(pain_pc>>16)*32768+(pain_pc&65535)-32768
    attack_offset=(attack_pc>>16)*32768+(attack_pc&65535)-32768
    attempt_offset=(attempt_pc>>16)*32768+(attempt_pc&65535)-32768
    if persistent:
        event_pc=worker_symbols['Relay_DrainEvents__record']
        event_offset=(event_pc>>16)*32768+(event_pc&65535)-32768
        drain_fault=worker_symbols['Relay_DrainEvents__fault']
        worker_fault=worker_symbols['Worker_FaultWait']
        event_push=worker_symbols['S6_EventPush']
        event_written=worker_symbols['S6_EventPush__record_written']
        remove_request_pc=worker_symbols['Relay_QueueRemove']
        remove_apply_pc=worker_symbols['Worker_ApplyRemove']
        drain_fault_offset=(drain_fault>>16)*32768+(drain_fault&65535)-32768
        worker_fault_offset=(worker_fault>>16)*32768+(worker_fault&65535)-32768
        event_push_offset=(event_push>>16)*32768+(event_push&65535)-32768
        event_written_offset=(event_written>>16)*32768+(event_written&65535)-32768
        remove_request_offset=(remove_request_pc>>16)*32768+(remove_request_pc&65535)-32768
        remove_apply_offset=(remove_apply_pc>>16)*32768+(remove_apply_pc&65535)-32768
        event_observer=f'''\nlocal sr=emu.memType.snesSaveRam
local function bw(x) return emu.read(x,sr)+256*emu.read(x+1,sr) end
local function event_row(tag)
 local s=emu.getState();local tail=word(0x412432);local a=0x412450+(tail%128)*16
 local kind=word(a+2);local arg=word(a+10)
 if kind==2 then arg=arg-0x6000 end
 emu.log(table.concat({{tag,word(0x412430),tail,word(0x412434),word(a),kind,word(a+4),word(a+6),
  word(a+8)-0x6000,arg,word(a+12),word(a+14),bw(0x12430),bw(0x12432),bw(0x12434),
  bw(0x12436),bw(0x12438),bw(0x1243a),bw(0x1243c),
  bw(0x12440),bw(0x12442),bw(0x12444),bw(0x12450),bw(0x12452),
  word(0x412008),word(0x41200a),bw(0x12008),bw(0x1200a),
  word(0x7e5023),s["ppu.frameCount"]}} ,"|"))
end
emu.addMemoryCallback(function() event_row("S7EVENTDELIVER") end,emu.callbackType.exec,{event_offset},{event_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() event_row("S7EVENTDRAINFAULT") end,emu.callbackType.exec,{drain_fault_offset},{drain_fault_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() event_row("S7EVENTWORKERFAULT") end,emu.callbackType.exec,{worker_fault_offset},{worker_fault_offset},emu.cpuType.sa1,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() event_row("S7REMOVE_REQUEST") end,emu.callbackType.exec,{remove_request_offset},{remove_request_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() event_row("S7REMOVE_APPLY") end,emu.callbackType.exec,{remove_apply_offset},{remove_apply_offset},emu.cpuType.sa1,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 emu.log(table.concat({{"S7RENDER",word(0x7e5023),word(0x7e1772),word(0x7e173c),
  word(0x7e1774),word(0x7e1760),word(0x7e1764),word(0x7e2750),word(0x7e2752)}},"|"))
end,emu.callbackType.exec,{render_offset},{render_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
local function state_row(tag)
 local n=word(0x7e5023)
 if n<230 or n%120==0 then
  emu.log(table.concat({{tag,n,word(0x7e173c),word(0x7e1760),word(0x7e1764),
   word(0x7e2750),word(0x7e2752)}},"|"))
 end
end
emu.addMemoryCallback(function() state_row("S7PLAY") end,emu.callbackType.exec,{play_offset},{play_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
{state_callbacks}
emu.addMemoryCallback(function()
 local s=emu.getState()
 emu.log(table.concat({{"S7EVENTPUSH",s["cart.coprocessor.cpu.a"],s["cart.coprocessor.cpu.x"],
  s["cart.coprocessor.cpu.y"],s["cart.coprocessor.cpu.d"],bw(0x12430),bw(0x12432),
  bw(0x12436),bw(0x12438),bw(0x1243a),bw(0x1243c)}},"|"))
end,emu.callbackType.exec,{event_push_offset},{event_push_offset},emu.cpuType.sa1,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() event_row("S7EVENTWRITTEN") end,emu.callbackType.exec,{event_written_offset},{event_written_offset},emu.cpuType.sa1,emu.memType.snesPrgRom)
'''
    else:
        base_sy=symbols(folder/'world.sym')
        frame_pc=base_sy['S6_FrameChanged']
        hit_effect_pc=base_sy['S6_HitEffects']
        unlink_pc=base_sy['S6Host_RemoveHandle']
        frame_offset=(frame_pc>>16)*32768+(frame_pc&65535)-32768
        hit_effect_offset=(hit_effect_pc>>16)*32768+(hit_effect_pc&65535)-32768
        unlink_offset=(unlink_pc>>16)*32768+(unlink_pc&65535)-32768
        event_observer=f'''\nlocal base_event_seq=0
local function base_event(kind)
 local s=emu.getState();local d=s["cpu.d"];local a=0x7e0000+d
 local target=word(a+0x34);local t=0x7e0000+target
 base_event_seq=base_event_seq+1
 emu.log(table.concat({{"S7BASEEVENT",base_event_seq,kind,word(0x7e173c),d,
  s["cpu.a"],s["cpu.x"],s["cpu.y"],target,word(t+0xf0),word(t+0xf6),
  word(a+0xf0),word(a+0xf6),word(a+0x06),word(a+0xe4),
    word(0x7e1700),word(0x7e1702),word(0x7e5023),s["ppu.frameCount"]}},"|"))
end
emu.addMemoryCallback(function() base_event(1) end,emu.callbackType.exec,{frame_offset},{frame_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() base_event(2) end,emu.callbackType.exec,{hit_effect_offset},{hit_effect_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() base_event(3) end,emu.callbackType.exec,{unlink_offset},{unlink_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    if not persistent:
        state_points=('Game_State_Play__playing','Game_State_Play__no_out_continue',
                      'Game_State_Play__no_pause_press','Game_State_Play__no_death',
                      'Game_State_Play__no_all_out','Game_State_Play__stage_no_win')
        state_rows='\n'.join(
            'emu.addMemoryCallback(function() state_row("S6'+name+'") end,'
            'emu.callbackType.exec,'+
            str((sym[name]>>16)*32768+(sym[name]&65535)-32768)+','+
            str((sym[name]>>16)*32768+(sym[name]&65535)-32768)+',emu.cpuType.snes,emu.memType.snesPrgRom)'
            for name in state_points)
        event_observer += f'''\nlocal function state_row(tag)
 local n=word(0x7e5023)
 if n<230 or n%120==0 then
  emu.log(table.concat({{tag,n,word(0x7e173c),word(0x7e1760),word(0x7e1764),
   word(0x7e2750),word(0x7e2752)}},"|"))
 end
end
{state_rows}
'''
    if int(link.get('presentation_divisor',1))==2:
        world_sy=symbols(folder/'world.sym')
        gate_yes=world_sy['S6Game_ShouldPresent__yes']
        gate_no=world_sy['S6Game_ShouldPresent__no']
        gate_yes_offset=(gate_yes>>16)*32768+(gate_yes&65535)-32768
        gate_no_offset=(gate_no>>16)*32768+(gate_no&65535)-32768
        event_observer+=f'''\nlocal function presentation_gate(tag)
 local s=emu.getState()
 emu.log(table.concat({{"S7PRESENT",tag,word(0x7e173c),s["ppu.frameCount"],word(0x7e5023)}},"|"))
end
emu.addMemoryCallback(function() presentation_gate("yes") end,emu.callbackType.exec,{gate_yes_offset},{gate_yes_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() presentation_gate("no") end,emu.callbackType.exec,{gate_no_offset},{gate_no_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    if real_input is not None:
        dma_transfer=sym['Core_Dma_TransferVram']
        dma_next=sym['Core_Dma_ProcessQueue__next']
        input_poll_pc=sym['Core_Input_Poll_P2']
        relay_queued_pc=worker_symbols['Relay_Queued']
        relay_poll_pc=worker_symbols.get('Relay_Poll_P2')
        dma_transfer_offset=(dma_transfer>>16)*32768+(dma_transfer&65535)-32768
        dma_next_offset=(dma_next>>16)*32768+(dma_next&65535)-32768
        input_poll_offset=(input_poll_pc>>16)*32768+(input_poll_pc&65535)-32768
        relay_queued_offset=(relay_queued_pc>>16)*32768+(relay_queued_pc&65535)-32768
        relay_poll_after_offset=((relay_poll_pc+7)>>16)*32768+((relay_poll_pc+7)&65535)-32768 if relay_poll_pc else 0
        relay_capture_observer=(f'''emu.addMemoryCallback(function()
 local s=emu.getState()
 emu.log(table.concat({{"S7CAPTURE",word(0x7e5023),word(0x7e0410),word(0x7e0412),
  word(0x7e0416),word(0x7e0418),bw(0x12014),bw(0x12016),
  bw(0x12018),bw(0x1201A),s["ppu.frameCount"]}} ,"|"))
end,emu.callbackType.exec,{relay_poll_after_offset},{relay_poll_after_offset},emu.cpuType.snes,emu.memType.snesPrgRom)''' if relay_poll_pc else '')
        event_observer+=f'''\nemu.addMemoryCallback(function()
 local s=emu.getState()
 emu.log(table.concat({{"S7HOSTINPUT",word(0x7e5023),word(0x7e0410),word(0x7e0412),
  word(0x7e041c),s["ppu.frameCount"]}},"|"))
end,emu.callbackType.exec,{input_poll_offset},{input_poll_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
{relay_capture_observer}
emu.addMemoryCallback(function()
 local count=word(0x412002);local tick=(count-1)%512;local a=0x415000+tick*8
 local trigger=word(a+2)
 if trigger~=0 or word(a)~=0 then
  emu.log(table.concat({{"S7INPUTRELAY",word(0x7e5023),count,tick,word(0x7e0410),
   word(0x7e0412),word(0x412010),word(a),trigger,word(0x412004)}},"|"))
 end
end,emu.callbackType.exec,{relay_queued_offset},{relay_queued_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
local vm=emu.memType.snesVideoRam
local function dma_row(tag,complete)
 local s=emu.getState();local x=s["cpu.x"] or 0;local a=0x7e0480+x
 local target=word(a+2);local source=word(a+5);local bank=emu.read(a+7,mt);local n=word(a)
 local srcbytes="";local dstbytes=""
 for i=0,15 do srcbytes=srcbytes..string.format("%02x",emu.read(bank*65536+source+i,mt)) end
 for i=0,15 do dstbytes=dstbytes..string.format("%02x",emu.read(target+i,vm)) end
 emu.log(table.concat({{"S7VISDMA",tag,s["masterClock"],x,n,target,source,bank,
  srcbytes,dstbytes,complete and 1 or 0,word(0x7e4420),word(0x7e4422),word(0x7e4426)}} ,"|"))
end
emu.addMemoryCallback(function() dma_row("enter",false) end,emu.callbackType.exec,{dma_transfer_offset},{dma_transfer_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function() dma_row("done",true) end,emu.callbackType.exec,{dma_next_offset},{dma_next_offset},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    smoke_stop_observer=''
    if stop_after_input_hit:
        input_offset=(input_pc>>16)*32768+(input_pc&65535)-32768
        completion_offset=(completion_pc>>16)*32768+(completion_pc&65535)-32768
        smoke_stop_observer=f'''
local smoke_input_edge=false
local smoke_damage_after_input=false
local smoke_stop_sent=false
local function bw(x) return emu.read(x,emu.memType.snesSaveRam)+256*emu.read(x+1,emu.memType.snesSaveRam) end
emu.addMemoryCallback(function()
 local trigger=word(0x412022)
 if math.floor(trigger/16384)%2==1 then
  smoke_input_edge=true
  emu.log(table.concat({{"S7SMOKE_INPUT_EDGE",word(0x41173c),trigger,emu.getState()["ppu.frameCount"]}},"|"))
 end
end,emu.callbackType.exec,{input_offset},{input_offset},emu.cpuType.sa1,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 if smoke_input_edge then
  smoke_damage_after_input=true
  local s=emu.getState();local d=s["cart.coprocessor.cpu.d"]
  emu.log(table.concat({{"S7SMOKE_DAMAGE",word(0x41173c),d,word(0x412020),word(0x412022),s["ppu.frameCount"]}},"|"))
 end
end,emu.callbackType.exec,{hit_offset},{hit_offset},emu.cpuType.sa1,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 if smoke_damage_after_input and not smoke_stop_sent then
  local completed=bw(0x12004)
  smoke_stop_sent=true
  emu.log(table.concat({{"S7SMOKESTOP",completed,completed,bw(0x12008),emu.getState()["ppu.frameCount"]}},"|"))
 end
end,emu.callbackType.exec,{completion_offset},{completion_offset},emu.cpuType.sa1,emu.memType.snesPrgRom)
'''
    lua=folder/'tick_observer.lua'
    lua.write_text('''local mt=emu.memType.snesMemory
local fields={'''+','.join('{'+str(a)+','+str(n)+'}' for a,n in fields)+'''}
local function word(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end
local sr=emu.memType.snesSaveRam
local function bw(x) return emu.read(x,sr)+256*emu.read(x+1,sr) end
'''+('''
local function log_worker_tick()
 local row={"S6TICK",tostring(word(0x41173c))}
 for slot=0,2 do
  local c=0x411900+slot*256
  local e=0x412100+slot*133
  for _,f in ipairs({{0xf0,2},{0x06,2},{0xe4,2},{0xe6,2},{0x0a,2},
                      {0x4c,2},{0xf6,1},{0x70,2}}) do
   local n=emu.read(c+f[1],mt)
   if f[2]==2 then n=n+256*emu.read(c+f[1]+1,mt) end
   row[#row+1]=tostring(n)
  end
  row[#row+1]=tostring(word(e+70))
  row[#row+1]=tostring(word(c+0xfc))
 end
 for slot=0,2 do row[#row+1]=tostring(word(0x411900+slot*256+0x14)) end
 row[#row+1]=tostring(word(0x411700));row[#row+1]=tostring(word(0x411702))
 emu.log(table.concat(row,"|"))
end
emu.addMemoryCallback(log_worker_tick,emu.callbackType.exec,'''+str((completion_pc>>16)*32768+(completion_pc&65535)-32768)+''','''+str((completion_pc>>16)*32768+(completion_pc&65535)-32768)+''',emu.cpuType.sa1,emu.memType.snesPrgRom)
''' if persistent else '')+'''
emu.addMemoryCallback(function(a,v)
 if '''+str(persistent).lower()+''' then return end
 if word(0x7e1760)~=1 then return end
 local row={"S6TICK",tostring(word(0x7e173c))}
 for _,f in ipairs(fields) do
  local n=emu.read(f[1],mt)
  if f[2]==2 then n=n+256*emu.read(f[1]+1,mt) end
  row[#row+1]=tostring(n)
 end
 row[#row+1]=tostring(word(0x7e1700));row[#row+1]=tostring(word(0x7e1702))
 emu.log(table.concat(row,"|"))
end,emu.callbackType.write,0x1774,0x1774,emu.cpuType.snes,emu.memType.snesWorkRam)
emu.addMemoryCallback(function()
 local d=emu.getState()["cpu.d"]
 local s=emu.getState()
 local d=s["'''+('cart.coprocessor.cpu.d' if persistent else 'cpu.d')+'''"]
 local base='''+('0x40a000' if persistent else '0x7e0000')+'''+d
 local r={"S6HIT",tostring(word('''+('0x41173c' if persistent else '0x7e173c')+''')),tostring(d-'''+('0x6000' if persistent else '0')+'''),tostring(word(base+0x34)-'''+('0x6000' if persistent else '0')+'''),tostring(word(base+0x4c))}
 for o=0x80,0x8e,2 do r[#r+1]=tostring(word(base+o)) end
 emu.log(table.concat(r,"|"))
end,emu.callbackType.exec,'''+str((hit_pc>>16)*32768+(hit_pc&65535)-32768)+','+str((hit_pc>>16)*32768+(hit_pc&65535)-32768)+''',emu.cpuType.'''+('sa1' if persistent else 'snes')+''',emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 local s=emu.getState();local cpu='''+('"cart.coprocessor.cpu"' if persistent else '"cpu"')+'''
 local d=s[cpu..".d"];local base='''+('0x40a000' if persistent else '0x7e0000')+'''+d
 local target=word(base+0x34);local t='''+('0x40a000' if persistent else '0x7e0000')+'''+target
 emu.log(table.concat({"S6PAINCHECK",word('''+('0x41173c' if persistent else '0x7e173c')+'''),d-'''+('0x6000' if persistent else '0')+''',target-'''+('0x6000' if persistent else '0')+''',
  word(base+0xDC),word(base+0xDE),word(t+0xD8),word(t+0xDA),word(t+0xB4),word(t+0xB6),word(t+0xF0),word(t+0xF6)},"|"))
end,emu.callbackType.exec,'''+str(pain_offset)+','+str(pain_offset)+''',emu.cpuType.'''+('sa1' if persistent else 'snes')+''',emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 local s=emu.getState();local d=s["'''+('cart.coprocessor.cpu.d' if persistent else 'cpu.d')+'''"]
 local b='''+('0x40a000' if persistent else '0x7e0000')+'''+d
 emu.log(table.concat({"S6ATTACK",word('''+('0x41173c' if persistent else '0x7e173c')+'''),d-'''+('0x6000' if persistent else '0')+''',
  word(b+0xe4),word(b+0x06),word(b+0xe6),word(b+0x08),word(b+0x14),word(b+0x16),word(b+0x18)},"|"))
end,emu.callbackType.exec,'''+str(attack_offset)+','+str(attack_offset)+''',emu.cpuType.'''+('sa1' if persistent else 'snes')+''',emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 local s=emu.getState();local d=s["'''+('cart.coprocessor.cpu.d' if persistent else 'cpu.d')+'''"]
 local b='''+('0x40a000' if persistent else '0x7e0000')+'''+d
 local target=word(b+0x34);local t='''+('0x40a000' if persistent else '0x7e0000')+'''+target
 emu.log(table.concat({"S6ATTEMPT",word('''+('0x41173c' if persistent else '0x7e173c')+'''),d-'''+('0x6000' if persistent else '0')+''',target-'''+('0x6000' if persistent else '0')+''',
  word(b+0x06),word(b+0xe4),word(t+0xf0),word(t+0xd8),word(t+0xda),word(t+0xb4),word(t+0xb6),word(t+0xf6)},"|"))
end,emu.callbackType.exec,'''+str(attempt_offset)+','+str(attempt_offset)+''',emu.cpuType.'''+('sa1' if persistent else 'snes')+''',emu.memType.snesPrgRom)
'''+('''
emu.addMemoryCallback(function()
 local i=bw(0x12004)*8;local a=0x15000+i
 emu.log(table.concat({"S7INPUT",word(0x41173c),bw(0x12020),bw(0x12022),
  bw(0x12024),bw(0x12026),bw(a),bw(a+2),bw(a+4),bw(a+6),
  bw(0x12014),bw(0x12016),bw(0x12018),bw(0x1201A),
  emu.getState()["ppu.frameCount"]},"|"))
end,emu.callbackType.exec,'''+str(((input_pc>>16)*32768+(input_pc&65535)-32768))+''','''+str(((input_pc>>16)*32768+(input_pc&65535)-32768))+''',emu.cpuType.sa1,emu.memType.snesPrgRom)
''' if input_pc else '')+event_observer+smoke_stop_observer)
    class ObservedSession(McpSession):
        def __enter__(self):
            import mesen_mcp.session as session_module
            def launch(argv,**kwargs): return subprocess.Popen([*argv,str(lua)],**kwargs)
            proxy=SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)
            try:
                with patch.object(session_module,'subprocess',proxy): return super().__enter__()
            except Exception:
                proc=getattr(self,'_proc',None)
                if proc is not None:
                    if proc.poll() is None:
                        proc.terminate()
                        proc.wait()
                    if self._stderr_log:
                        Path(self._stderr_log).write_bytes(b''.join(self._stderr_lines))
                raise
    observations = []
    smoke_artifacts={}
    compat_pressed = False
    removal_requested=False
    last_source_tick=None
    stable_source_fields=0
    smoke_presentation_target=None
    smoke_first_presentation_target=None
    smoke_candidate_samples=0
    input_schedule=None
    if real_input is not None:
        input_schedule=dict(real_input)
        assert persistent and input_pc and input_schedule['start_field'] < input_schedule['end_field']
        assert input_schedule.get('port',0) in (0,1)
        assert input_schedule.get('button','Y').upper() in ('Y','B','A','X','LEFT','RIGHT','UP','DOWN')
    if stop_after_input_hit:
        assert persistent and real_input is not None and input_pc
    input_pressed=False
    input_started_field=None
    input_duration=(input_schedule['end_field']-input_schedule['start_field']
                    if input_schedule is not None else 0)
    with ObservedSession(rom=folder/'bor.sfc', mesen=MESEN_EXE, cwd=folder,
                    port=_free_tcp_port(), stderr_log=folder/'mesen.log') as m:
        reporter = Reporter('S6-WORLD-BOOT')
        # Fresh emulator process already reset. A second reset unloads Lua in
        # this installed Mesen build; preserve the read-only observer.
        with patch.object(m,'reset_emulator',lambda:None):
            cold_to_title(m, reporter)
        # Private opt-in scratch is not part of the accepted reset allocation.
        # Initialize before selection; never interpret power-on WRAM as policy.
        m.write_memory('snesMemory',0x7E1700,bytes(256).hex())
        m.write_memory('snesMemory',0x7E1900,bytes(1536).hex())
        select_case(m, reporter, 'KULA', 'KULA')
        m.write_u16(0x7E1770, 1)
        if real_input is not None:
            # Menu navigation also uses Y. Release it once gameplay is live so
            # the scripted gameplay press creates a real auto-joypad edge.
            m.release_input(port=0)
            m.release_input(port=1)
            exact_input_edge(m,0,1,port=0)
            for name in ('Input_press','Input_trigger','Input2_press','Input2_trigger'):
                m.write_u16(sym[name],0)
        field_limit=(field_limit_override if field_limit_override is not None else
                     (600 if persistent and link['scenario']=='retarget' else 150))
        for field in range(field_limit):
            run_frames_exact(m,1)
            ram = m.read_memory('snesMemory',0x7E0000,0x6000)
            u16 = lambda at: struct.unpack_from('<H',ram,at)[0]
            # A real input edge must be sampled after persistent ownership is
            # established. If the fixed warm-up expires before the owner is
            # ready, defer the same-duration press instead of losing its only
            # trigger in the S-CPU fallback interval.
            if (input_schedule and input_started_field is None
                    and field>=input_schedule['start_field'] and u16(0x175C)!=0):
                button=getattr(m,'BTN_'+input_schedule.get('button','Y').upper())
                m.hold_input(button,port=input_schedule.get('port',0))
                input_pressed=True
                input_started_field=field
            if (input_schedule and input_pressed
                    and field>=input_started_field+input_duration):
                m.release_input(port=input_schedule.get('port',0))
                input_pressed=False
            rows = []
            for i in range(6):
                base=0xA00+133*i
                rows.append(dict(slot=i,roster=ram[base+sym['CHAR_ROSTER_INDEX']],
                    hp=ram[base+sym['CHAR_HP']],x=u16(base+sym['CHAR_POS_X']),
                    y=u16(base+sym['CHAR_POS_Y']),
                    selected=ram[base+sym['CHAR_SELECTED']],compat_frame=ram[base+sym['CHAR_FRAME_INDEX']],
                    facing=ram[base+sym['CHAR_FACING_LEFT']],hit_stun=ram[base+sym['CHAR_HIT_STUN']],
                    context_error=u16(0x1900+i*256+0xFC),
                    role=u16(0x1900+i*256+0xE4),frame=u16(0x1900+i*256+6),
                    driver=u16(0x1900+i*256+0xE6)))
            observations.append(dict(field=field,mode=u16(0x1760),error=u16(0x1764),
                                     tick=u16(0x173C),hits=u16(0x176E),rows=rows,
                                     input=dict(p1_press=u16(0x0410),p1_trigger=u16(0x0412),
                                                p2_press=u16(0x0416),p2_trigger=u16(0x0418),
                                                p1_raw=u16(0x041C),p2_raw=u16(0x041E)),
                                     visual=dict(calls=u16(0x4584),render_passes=u16(0x4596),
                                                 last_error=u16(0x4458),
                                                 oam_bytes=u16(0x53A0),
                                                 oam_upload_flag=u16(0x53A2),
                                                 oam_high_water=u16(0x53C8))))
            if link['scenario']=='retarget':
                if (u16(0x173C)==last_source_tick and u16(0x173C)>=17
                        and u16((sym['StageEnv_Actors']&0xFFFF)+2*133+70)==0x0A85):
                    stable_source_fields+=1
                else:
                    stable_source_fields=0
                last_source_tick=u16(0x173C)
                if stable_source_fields>=3:
                    break
            if (link['scenario']=='wait_probe' and u16(0x1760)==1
                    and u16(0x173C)>=wait_hold_tick):
                # Freeze only source-tick admission at a completed boundary.
                # The fixture's mode-4 path continues calling the ordinary
                # resident flush so pending mailbox/event work is serviced.
                m.write_u16(0x7E1760,4)
                observations[-1]['mode']=4
                break
            if link['scenario']=='retarget' and u16(0x173C)>=3 and not removal_requested:
                m.write_u16(0x7E1776,0xA00)
                m.write_u16(0x7E1770,2)
                removal_requested=True
            if stop_after_input_hit:
                log_lines=[line.decode(errors='replace').strip()
                           for line in m._stderr_lines]
                stop_index=next((i for i,line in enumerate(log_lines)
                                 if line.startswith('S7SMOKESTOP|')),None)
                if stop_index is not None:
                    stop_fields=list(map(int,log_lines[stop_index].split('|')[1:]))
                    following_samples=sum(line.startswith('S7PRESENT|yes|')
                                          for line in log_lines[stop_index+1:])
                    control=m.read_memory('snesSaveRam',0x12002,4)
                    target,completed=struct.unpack_from('<HH',control)
                    events=m.read_memory('snesSaveRam',0x12430,6)
                    event_head,event_tail,event_overflow=struct.unpack_from('<HHH',events)
                    if (following_samples and event_head==event_tail
                            and event_overflow==0):
                        smoke_candidate_samples=following_samples
                        sprite_ram=m.read_memory('snesSpriteRam',0,544)
                        visible_oam=sum(sprite_ram[i*4+1]!=0xE0 for i in range(128))
                        ppu=m.get_ppu_state()
                        if (not ppu.get('forcedBlank',True)
                                and ppu.get('brightness',0)>0 and visible_oam>0):
                            smoke_artifacts=dict(screenshot=m.take_screenshot(),ppu=ppu,
                                oam=sprite_ram,vram=m.read_memory('snesVideoRam',0,65536),
                                cgram=m.read_memory('snesCgRam',0,512),
                                wram=m.read_memory('snesMemory',0x7E0000,0x6000),
                                visible_oam_entries=visible_oam)
                            observations[-1]['bounded_smoke_stop']=dict(
                                worker_completed=completed,command_target=target,
                                event_head=event_head,event_tail=event_tail,
                                event_overflow=event_overflow,source_mode=u16(0x1760),
                                presentation_samples_after_damage=following_samples,
                                actual_visible_oam_entries=visible_oam,
                                forced_blank=ppu.get('forcedBlank'),
                                brightness=ppu.get('brightness'))
                            break
                        if following_samples>=8:
                            observations[-1]['bounded_smoke_stop']=dict(
                                worker_completed=completed,command_target=target,
                                event_head=event_head,event_tail=event_tail,
                                event_overflow=event_overflow,
                                presentation_samples_after_damage=following_samples,
                                actual_visible_oam_entries=visible_oam,
                                forced_blank=ppu.get('forcedBlank'),
                                brightness=ppu.get('brightness'))
                            break
            if link['scenario']=='compat' and u16(0x1760)==5:
                if not compat_pressed:
                    m.hold_input(m.BTN_Y,port=0)
                    compat_pressed=True
                elif rows[2]['hp']<100:
                    m.release_input(port=0)
                    break
            if u16(0x1764) or (not stop_after_input_hit and u16(0x1760)==4 and
                               (u16(0x175E)==0 or (persistent and link['scenario']=='retarget'))):
                (folder/'failure-wram.bin').write_bytes(m.read_memory('snesMemory',0x7E0000,65536))
                break
        if input_pressed:
            m.release_input(port=input_schedule.get('port',0))
        m.pause()
        (folder/'final-wram.bin').write_bytes(m.read_memory('snesMemory',0x7E0000,65536))
        if persistent:
            (folder/'final-bwram.bin').write_bytes(m.read_memory('snesSaveRam',0x12000,0xD00))
        accounting=None
        if link['scenario']=='wait_probe' and observations[-1]['mode']==4 and not observations[-1]['error']:
            # Explicit dead-but-existing precondition. The real wait consumer
            # counts exact actors by bridge existence; HP zero alone must not
            # release the wait before the normal unlink operation.
            if persistent:
                # Test precondition at a quiescent ownership boundary: the
                # SA-1 has completed the measured trajectory and is polling,
                # so the canonical shared actor context receives HP=0 without
                # racing a source tick. The production path never writes this.
                m.write_u8(0x411B00+0xF0,0)
            else:
                # S-CPU canonical source context is distinct from the OOP
                # health mirror at $7E0B0A+CHAR_HP.
                m.write_u8(0x7E1B00+0xF0,0)
            # Keep the S-CPU health mirror consistent with the canonical
            # dead-but-existing precondition while the test's normal flush
            # path services ownership and presentation state.
            m.write_u8(0x7E0B0A+sym['CHAR_HP'],0)
            m.write_u8(sym['Spawn_Waiting'],1)
            run_frames_exact(m,1)
            before=m.read_memory('snesMemory',0x7E0000,65536)
            assert before[sym['Spawn_Waiting']&65535]==1
            assert before[(sym['StageEnv_Actors']&65535)+266+65]==1
            if persistent:
                canonical_hp=m.read_memory('snesSaveRam',0x11BF0,1)[0]
            else:
                canonical_hp=before[0x1B00+0xF0]
            assert canonical_hp==0
            event_head_before=0
            event_tail_before=0
            delivered_before=struct.unpack_from('<H',before,0x1778)[0]
            hold_nmi_field=before[sym['Nmi_FrameCounter']&0xFFFF]
            if persistent:
                bw_before=m.read_memory('snesSaveRam',0x12430,0x24)
                event_head_before=struct.unpack_from('<H',bw_before,0)[0]
                event_tail_before=struct.unpack_from('<H',bw_before,2)[0]
            m.write_u16(0x7E1776,0xB0A)
            m.write_u16(0x7E1770,2)
            unlink_clear_iteration=None
            wait_release_iteration=None
            for iteration in range(1,13):
                run_frames_exact(m,1)
                after=m.read_memory('snesMemory',0x7E0000,65536)
                # Async worker unlink is acknowledged at a snapshot boundary;
                # allow the normal next Spawn_Play visit after that boundary.
                if not after[(sym['StageEnv_Actors']&65535)+266+65] and unlink_clear_iteration is None:
                    unlink_clear_iteration=iteration
                if not after[sym['Spawn_Waiting']&65535] and wait_release_iteration is None:
                    wait_release_iteration=iteration
                if unlink_clear_iteration is not None and wait_release_iteration is not None:break
            (folder/'accounting-before.bin').write_bytes(before)
            (folder/'accounting-after.bin').write_bytes(after)
            if after[sym['Spawn_Waiting']&65535] or after[(sym['StageEnv_Actors']&65535)+266+65]:
                raise AssertionError('WAIT_PROBE_STATE '+json.dumps(dict(
                    waiting=after[sym['Spawn_Waiting']&65535],
                    exists=after[(sym['StageEnv_Actors']&65535)+266+65],
                    error=struct.unpack_from('<H',after,0x1764)[0],
                    command=struct.unpack_from('<H',after,0x1770)[0],
                    exact_exists=[after[(sym['StageEnv_Actors']&65535)+133*i+65] for i in range(6)],
                    hp=[after[0x0A00+133*i+sym['CHAR_HP']] for i in range(6)],
                    mode=struct.unpack_from('<H',after,0x1760)[0])))
            assert after[(sym['StageEnv_Actors']&65535)+266+65]==0
            assert after[sym['Spawn_Waiting']&65535]==0
            assert struct.unpack_from('<H',after,0x1764)[0]==0
            accounting=dict(dead_existing_holds_wait=True,unlink_releases_wait=True,
                            exact_unlink_handle=0x0B0A,
                            wait_transitions=[1,0],
                            hold_source_tick=struct.unpack_from('<H',before,0x173C)[0],
                            wait_hold_nmi_field=hold_nmi_field,
                            unlink_clear_iteration=unlink_clear_iteration,
                            wait_release_iteration=wait_release_iteration,
                            delivered_event_delta=struct.unpack_from('<H',after,0x1778)[0]-delivered_before,
                            natural_airborne_death_proven=False)
            if persistent:
                bw_after=m.read_memory('snesSaveRam',0x12430,0x24)
                event_head_after=struct.unpack_from('<H',bw_after,0)[0]
                event_tail_after=struct.unpack_from('<H',bw_after,2)[0]
                accounting.update(event_head_delta=(event_head_after-event_head_before)&0xFFFF,
                                  event_tail_caught_up=(event_tail_after==event_head_after),
                                  event_ring_overflow=struct.unpack_from('<H',bw_after,4)[0])
                assert accounting['event_head_delta']==1
                assert accounting['event_tail_caught_up']
                assert accounting['event_ring_overflow']==0
                assert accounting['delivered_event_delta']==1
            (folder/'accounting-before.bin').write_bytes(before)
            (folder/'accounting-after.bin').write_bytes(after)
        if real_input is not None:
            smoke_artifacts=dict(screenshot=m.take_screenshot(),ppu=m.get_ppu_state(),
                                 oam=m.read_memory('snesSpriteRam',0,544),
                                 vram=m.read_memory('snesVideoRam',0,65536),
                                 cgram=m.read_memory('snesCgRam',0,512),
                                 wram=m.read_memory('snesMemory',0x7E0000,0x6000))
        lines=[line.decode(errors='replace').strip() for line in list(m._stderr_lines)
               if line.startswith(b'S6TICK|')]
        hit_lines=[line.decode(errors='replace').strip() for line in list(m._stderr_lines)
                   if line.startswith(b'S6HIT|')]
        pain_lines=[line.decode(errors='replace').strip() for line in list(m._stderr_lines)
                    if line.startswith(b'S6PAINCHECK|')]
        attack_lines=[line.decode(errors='replace').strip() for line in list(m._stderr_lines)
                      if line.startswith(b'S6ATTACK|')]
        attempt_lines=[line.decode(errors='replace').strip() for line in list(m._stderr_lines)
                       if line.startswith(b'S6ATTEMPT|')]
        event_prefix=b'S7EVENTDELIVER|' if persistent else b'S7BASEEVENT|'
        event_lines=[line.decode(errors='replace').strip() for line in list(m._stderr_lines)
                     if line.startswith(event_prefix)]
        presentation_lines=[line.decode(errors='replace').strip() for line in list(m._stderr_lines)
                            if line.startswith(b'S7PRESENT|')]
        if link['scenario']=='wait_probe' and accounting is not None:
            unlink_rows=[]
            for line in event_lines:
                fields=line.split('|')
                kind=int(fields[5] if persistent else fields[2])
                if kind==3:
                    unlink_rows.append(line)
            assert len(unlink_rows)==1, f'UNLINK_EVENT_NOT_EXACTLY_ONCE: {unlink_rows}'
            accounting['unlink_transport_messages']=1
            accounting['unlink_transport_record_bytes']=16 if persistent else 0
            accounting['source_host_unlink_callbacks']=0 if persistent else 1
    (folder/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
    ticks=[list(map(int,line.split('|')[1:])) for line in lines]
    hits=[list(map(int,line.split('|')[1:])) for line in hit_lines]
    (folder/'hits.json').write_text(json.dumps(hits,indent=2)+'\n')
    pain_rows=[list(map(int,line.split('|')[1:])) for line in pain_lines]
    (folder/'pain-checks.json').write_text(json.dumps(pain_rows,indent=2)+'\n')
    (folder/'world-attacks.json').write_text(json.dumps(
        [list(map(int,line.split('|')[1:])) for line in attack_lines],indent=2)+'\n')
    (folder/'hit-attempts.json').write_text(json.dumps(
        [list(map(int,line.split('|')[1:])) for line in attempt_lines],indent=2)+'\n')
    input_rows=[list(map(int,line.decode(errors='replace').strip().split('|')[1:]))
                for line in list(m._stderr_lines) if line.startswith(b'S7INPUT|')]
    input_proof=None
    if input_schedule is not None:
        button_masks={'Y':0x4000,'B':0x8000,'A':0x0100,'X':0x0200,
                      'L':0x0400,'R':0x0800,'LEFT':0x0040,'RIGHT':0x0080,
                      'UP':0x0010,'DOWN':0x0020}
        mask=button_masks[input_schedule.get('button','Y').upper()]
        trigger_column=2 if input_schedule.get('port',0)==0 else 4
        delivered=[row for row in input_rows if row[trigger_column]&mask]
        assert delivered, f'LIVE_INPUT_NOT_CONSUMED_BY_SA1: mask={mask:#06x}'
        input_proof=dict(status='PASS_SA1_CONSUMED_REAL_INPUT_EDGE',mask=mask,
                         port=input_schedule.get('port',0),
                         first_worker_tick=delivered[0][0],
                         consumed_records=len(delivered),
                         worker_rows=input_rows)
    smoke_stop_lines=[line.decode(errors='replace').strip() for line in m._stderr_lines
                      if line.startswith(b'S7SMOKESTOP|')]
    if stop_after_input_hit:
        assert len(smoke_stop_lines)==1, 'INPUT_HIT_BOUNDED_STOP_NOT_REACHED'
        stop_fields=list(map(int,smoke_stop_lines[0].split('|')[1:]))
        assert stop_fields[2]==0, f'WORKER_FAULT_BEFORE_SMOKE_STOP: {stop_fields}'
        assert smoke_artifacts, 'PRODUCTION_SOURCE_VISUALS_NOT_VISIBLE_AFTER_INPUT_DAMAGE'
        assert smoke_candidate_samples>0, 'NO_PRESENTATION_SAMPLE_AFTER_INPUT_DAMAGE'
    smoke_stop_proof=(dict(status='PASS_STOP_AFTER_INPUT_AND_REAL_DAMAGE',
                           completed_before_tick=stop_fields[0],
                           stop_target=stop_fields[1],
                           worker_fault=stop_fields[2])
                      if stop_after_input_hit else None)
    (folder/'input.json').write_text(json.dumps(dict(schedule=input_schedule,proof=input_proof,
        bounded_stop=smoke_stop_proof,rows=input_rows),indent=2)+'\n')
    (folder/'ticks.json').write_text(json.dumps(ticks,indent=2)+'\n')
    (folder/'events.json').write_text(json.dumps(event_lines,indent=2)+'\n')
    if int(link.get('presentation_divisor',1))==2:
        gates=[dict(tag=row.split('|')[1],tick=int(row.split('|')[2]),
                    ppu_field=int(row.split('|')[3]),nmi_field=int(row.split('|')[4]))
               for row in presentation_lines]
        if persistent:
            hit_events=[dict(sequence=int(row.split('|')[4]),tick=int(row.split('|')[6]),
                             nmi_field=int(row.split('|')[-2]),ppu_field=int(row.split('|')[-1]),
                             kind=int(row.split('|')[5]))
                        for row in event_lines if int(row.split('|')[5])==2]
        else:
            hit_events=[dict(sequence=int(row.split('|')[1]),tick=int(row.split('|')[3]),
                             nmi_field=int(row.split('|')[-2]),ppu_field=int(row.split('|')[-1]),
                             kind=int(row.split('|')[2]))
                        for row in event_lines if int(row.split('|')[2])==2]
        grouped={}
        for event in hit_events:
            grouped.setdefault((event['tick'],event['nmi_field']),[]).append(event)
        multi=next((rows for rows in grouped.values() if len(rows)>1),[])
        log_lines=[line.decode(errors='replace').strip() if isinstance(line,bytes) else line.strip()
                   for line in list(m._stderr_lines)]
        sample_positions=[(i,line) for i,line in enumerate(log_lines)
                          if line.startswith('S7PRESENT|yes|')]
        event_prefix='S7EVENTDELIVER|' if persistent else 'S7BASEEVENT|'
        event_positions=[]
        if multi:
            target_tick=multi[0]['tick']
            target_nmi=multi[0]['nmi_field']
            for i,line in enumerate(log_lines):
                if not line.startswith(event_prefix):
                    continue
                fields=line.split('|')
                event_tick=int(fields[6] if persistent else fields[3])
                event_nmi=int(fields[-2])
                event_kind=int(fields[5] if persistent else fields[2])
                if event_kind==2 and event_tick==target_tick and event_nmi==target_nmi:
                    event_positions.append((i,line))
        interval_proof=None
        if multi and len(event_positions)>=len(multi):
            first_event=event_positions[0][0]
            last_event=event_positions[len(multi)-1][0]
            previous=[(i,line) for i,line in sample_positions if i<first_event]
            following=[(i,line) for i,line in sample_positions if i>last_event]
            if previous and following:
                previous_gate=previous[-1][1].split('|')
                next_gate=following[0][1].split('|')
                interval_proof=dict(events=multi,
                    previous_sampled_field=int(previous_gate[3]),
                    event_first_log_order=first_event,
                    event_last_log_order=last_event,
                    next_sampled_field=int(next_gate[3]),
                    ordered_before_next_snapshot=True)
        (folder/'presentation.json').write_text(json.dumps(
            dict(gate_observations=gates,hit_events=hit_events,
                 ordered_multiple_events_between_visual_snapshots=interval_proof),indent=2)+'\n')
    print(json.dumps(observations[-1],indent=2))
    if real_input is not None:
        shutil.copyfile(smoke_artifacts['screenshot']['path'],folder/'production-smoke.png')
        (folder/'production-smoke-ppu.json').write_text(json.dumps(smoke_artifacts['ppu'],indent=2)+'\n')
        (folder/'production-smoke-oam.bin').write_bytes(smoke_artifacts['oam'])
        (folder/'production-smoke-vram.bin').write_bytes(smoke_artifacts['vram'])
        (folder/'production-smoke-cgram.bin').write_bytes(smoke_artifacts['cgram'])
        (folder/'production-smoke-wram.bin').write_bytes(smoke_artifacts['wram'])
    assert observations and observations[-1]['error']==0, 'host admission/execution failed; inspect observations'
    final_ram=(folder/'final-wram.bin').read_bytes()
    expected_spawn_count=link.get('enemy_copies',1) if link['scenario'] in ('enemy','samepass') else 1
    assert final_ram[sym['Spawn_Count']&65535]==expected_spawn_count
    assert final_ram[sym['Spawn_Index']&65535]==expected_spawn_count
    assert observations[-1]['rows'][2]['roster']==link['models'][1]['roster']
    if link['scenario']=='compat':
        assert observations[-1]['rows'][2]['hp']==96, 'accepted compatibility damage changed'
        assert not ticks and observations[-1]['tick']==0 and observations[-1]['hits']==0
        proof=dict(status='PASS_ACCEPTED_COMPAT_WORLD_CONTROL',damage=4,
                   source_scheduler_invoked=False,production_changed=False,final=observations[-1])
        (folder/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        return
    if link['scenario'] not in ('retarget','wait_probe'):
        assert any(o['hits'] for o in observations), 'no integrated hit observed'
    if link['scenario']=='wait_probe':
        assert [r[0] for r in ticks]==list(range(1,len(ticks)+1)), 'wait-probe tick observer has an interior gap'
        if not stop_after_input_hit:
            assert observations[-1]['tick']-len(ticks) in (0,1), 'wait-probe final tick observer boundary changed'
    elif int(link.get('presentation_divisor',1))==2:
        assert [r[0] for r in ticks]==list(range(1,len(ticks)+1)), 'presentation-probe tick observer has an interior gap'
        if not stop_after_input_hit:
            assert observations[-1]['tick']-len(ticks) in (0,1), 'presentation-probe final tick observer boundary changed'
    else:
        assert [r[0] for r in ticks] == list(range(1,observations[-1]['tick']+1)), 'missing source tick observer records'
    if link['scenario']=='kula':
        attack=next(r for r in link['models'][0]['scheduler']['roles'] if r['role']=='attack1')['role_id']
        active=[r for r in ticks if r[3]==attack]
        from collections import Counter
        if real_input is None:
            assert Counter(r[2] for r in active)=={0:8,1:8,2:8,3:8,4:4,5:6}
        # Collision runs on the source slot's parity. Frame entry clears its
        # cached query result; descriptor force is available on both parities.
        assert all(r[5]==int(r[2] in (2,3)) for r in active if r[0]%2==0)
        assert all(not r[5] for r in active if r[2] not in (2,3))
        assert all(r[6]==5 for r in active if r[2] in (2,3))
        if real_input is None:
            assert next(r[0] for r in ticks if r[21]==95)==18
            assert all(r[21]==100 for r in ticks if r[0]<18)
            assert len(hits)==1 and hits[0][:4]==[18,0x1900,0x1B00,5]
            assert hits[0][4:]==[161,138,200,154,144,120,170,220], 'source collision corners changed'
        else:
            assert hits and observations[-1]['rows'][2]['hp']<100, \
                'real input did not produce a source-world hit/damage event'
        if real_input is None:
            # Source per-frame move10 is an exact integer lattice operation.
            if persistent:
                assert [ticks[t-1][31] for t in (1,9,17,33,37)]==[125,135,145,135,125]
                assert observations[-1]['rows'][0]['x']==100
                assert observations[-1]['rows'][2]['hp']==95
                assert struct.unpack_from('<H',final_ram,0x175C)[0]==1
                assert struct.unpack_from('<H',final_ram,0x175E)[0]==2
            elif link.get('resident'):
                assert [ticks[t-1][32] for t in (1,9,17,33,37)]==[125,135,145,135,125]
                assert struct.unpack_from('<H',final_ram,0x175E)[0]==0
            else:
                assert all(r[31]*5==r[32]*4 for r in ticks)
                assert [ticks[t-1][31] for t in (1,9,17,33,37)]==[100,108,116,108,100]
            assert ticks[-1][21]==95 and ticks[-1][24]==2, 'source force/pain not committed to real enemy'
    elif link['scenario']=='enemy':
        if link.get('enemy_copies',1)==1:
            assert ticks[-1][1]==46 and ticks[-1][11]==46
            assert any(r[29]==0xA00 for r in ticks), 'native target did not publish real player handle'
            assert ticks[-1][24]==13, 'source attack did not reach recovery decision'
            assert final_ram[sym['HudCachedHp']&65535]==46, 'real health bar cache did not follow source oldhealth'
        else:
            assert len(hits)>=2, 'multi-opponent source case produced no ordered hit pair'
            assert all(hit[2] in (0x1900,0x1A00) for hit in hits), \
                'enemy attack escaped the two live player targets'
    elif link['scenario']=='samepass':
        assert len(hits)==1 and hits[0][:4]==[30,0x1B00,0x1900,18], \
            'first same-pass Joe must land exactly one real force-18 hit on P1'
        later=next((row for row in pain_rows
                    if row[:3]==[30,0x1D00,0x1900]),None)
        assert later is not None and later[5]==1 and later[9]==46, \
            'later actor did not observe earlier hit ID and HP=46 pain target in the same pass'
        assert not any(row[0]==30 and row[1]==0x1D00 for row in hits), \
            'later same-pass attacker applied a duplicate hit'
    elif link['scenario']=='retarget':
        assert any(r[29]==0xA00 for r in ticks)
        assert any(r[29]==0xA85 for r in ticks), 'removed target was not replaced with real P2'
        assert ticks[-1][1]==0 and ticks[-1][7]==0 and ticks[-1][11]==64
        assert final_ram[0x0A00+sym['CHAR_HP']]==0, 'removed player retained source health'
        assert final_ram[sym['G13_P1Out']&0xFFFF]==1, 'P1 unlink event did not reach game accounting'
        assert final_ram[(sym['StageEnv_Actors']&0xFFFF)+65]==0, 'P1 remained in the active stage row'
    if link['scenario']=='samepass':
        hit_events=[]
        for line in event_lines:
            fields=line.split('|')
            kind=int(fields[5] if persistent else fields[2])
            if kind==2:
                hit_events.append(dict(tick=int(fields[6] if persistent else fields[3]),
                    attacker=int(fields[8] if persistent else fields[4]),
                    target=int(fields[9] if persistent else fields[8])))
        assert hit_events==[dict(tick=30,attacker=0x1B00,target=0x1900)], \
            f'same-pass ordered hit event transport mismatch: {hit_events}'
    proof=dict(status='PASS_BOUNDED_WORLD_CORE',scenario=link['scenario'],source_ticks=len(ticks),
               final=observations[-1],accounting=accounting,production_changed=False,full_actor_certification=False,
               link_manifest_sha256=sha(folder/'link.json'),
               execution_policy='SOURCE_EXACT',presentation_policy='ACCEPTED_RENDERER_NOT_SOURCE_CERTIFIED',
               nonclaims=['source raster publication','hit flash/audio/combo effects','general fractional movement',
                          'natural airborne death'])
    (folder/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--max-fields',type=int)
    parser.add_argument('--resident',action='store_true')
    parser.add_argument('--layout-dispatch',action='store_true')
    parser.add_argument('--scenario',choices=('enemy','kula','compat','retarget','wait_probe'),default='enemy')
    args=parser.parse_args()
    folder = Path(tempfile.mkdtemp(prefix='actor_s6_production_world_', dir=ROOT/'out'))
    print(folder, flush=True)
    report=build(folder,args.scenario,resident=args.resident,layout_dispatch=args.layout_dispatch)
    print(report['status'],flush=True)
    if args.run: run(folder,field_limit_override=args.max_fields)
