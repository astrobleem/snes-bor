"""Private ordered-world SA-1 pilot. No production output or actor-name policy.

Worker state: BW-RAM offsets 10000..11fff, SA-1 bank8 window6000..7fff.
Job:12000..1200f; host callback fields12100..12423. Legacy canvas <=6eff,
save bytes0..7. IRAM26/27 are an explicitly handed-off request/complete pair.
The stock canvas loop is preserved behind the private opt-in gate.
"""
import os
import json
from pathlib import Path
import re
import subprocess
from actor_s5_entity_fixture import symbols
from actor_s5_isolated import ROOT

POINTER_OFFSETS = (0x34,0x36,0xB0)
REGIONS = {'save':(0,8),'legacy_canvas':(0x3000,0x6f00),
           'resident_window':(0x10000,0x12000),'job':(0x12000,0x12010),
           'callback_fields':(0x12100,0x12424),
           'bridge_scratch':(0x12D20,0x12D30)}


def install(folder):
    admission=json.loads((folder/'link.json').read_text())
    assert admission.get('resident') and admission.get('layout',{}).get('source_slot_count')==6, 'WORKER_PILOT_REQUIRES_SIX_SOURCE_SLOTS'
    sym=symbols(ROOT/'src/main.sym')
    ws=symbols(folder/'world.sym')
    old_worker_sym_path = folder/'worker.sym'
    old_worker_sy = symbols(old_worker_sym_path) if old_worker_sym_path.is_file() else {}
    rom=bytearray((folder/'bor.sfc').read_bytes())
    assert rom[0x7fd8]==8, 'WORKER_REQUIRES_AUDITED_256K_BWRAM'
    def blank(bank):
        start=bank*32768
        return rom[start:start+32768]==bytes(32768)
    if blank(27) and blank(28):
        relay_bank,worker_bank=27,28
    else:
        pair=next(((bank,bank+1) for bank in range(33,127)
                   if blank(bank) and blank(bank+1)),None)
        assert pair is not None,'WORKER_REQUIRES_TWO_ADJACENT_UNUSED_ROM_BANKS'
        relay_bank,worker_bank=pair
    ordered=sorted(REGIONS.values())
    assert all(a[1]<=b[0] for a,b in zip(ordered,ordered[1:]))
    assert ordered[-1][1]<=0x40000
    # Code and metadata are source-derived; only the target address ABI changes.
    names=('scheduler','damage','hit','rng','target','lifecycle','world','ai')
    host=(ROOT/'src/core/actor_source_host.pasm').read_text()
    prefix='\n'.join((ROOT/f'src/core/actor_source_{n}.pasm').read_text() for n in names)
    code=(ROOT/'src/core/actor_s5_isolated.pasm').read_text()+'\n'+prefix+'\nS6_Think:'+host.split('\nS6_Think:',1)[1]
    bridge=(ROOT/'src/core/actor_source_bridge.pasm').read_text()
    code+='\nS6Bridge_UnprojectPolicy:'+bridge.split(
        '\nS6Bridge_UnprojectPolicy:',1)[1].split('\nS6Bridge_ProjectPolicy:',1)[0]
    code+='\nS6Bridge_UnprojectRounded:'+bridge.split(
        '\nS6Bridge_UnprojectRounded:',1)[1]
    # Cross-context addresses use the BW-RAM window's equivalent linear base.
    code=re.sub(r'\$7E00([0-9A-Fa-f]{2})',r'$40A0\1',code)
    code=code.replace('#$1F00','#$7F00').replace('#$1FF9','#$7FF9')
    # Preserve the aligned window admission test in the relocated address ABI.
    code=code.replace('and #$E0FF', 'and #$E0FF\n    cmp #$6000')
    code=re.sub(r'\bS6Host_', 'WHost_', code)
    code=re.sub(r'\bS6Bridge_', 'WBridge_', code)
    code=re.sub(r'\bS6_', 'W6_', code)
    code=re.sub(r'\bS5_', 'W5_', code)
    # No executable worker operand may reach S-CPU WRAM or PPU/APU registers.
    for line in code.splitlines():
        instruction=line.split(';',1)[0]
        assert not re.search(r'\$7[EF][0-9A-Fa-f]{4}',instruction),instruction
    defs=dict(CHAR_ZP_LEN=sym['CHAR_ZP_LEN'],Screen_PosX=0x412420,
        Spawn_HoleCount=0x412422,WBridge_TargetHandle=0x412100+70,
        WBridge_Policy=0x412100+64,
        WBridge_Temp78=0x412D20,WBridge_Temp7C=0x412D22,
        WBridge_Temp80=0x412D24,WBridge_Temp82=0x412D26,
        WBridge_Temp84=0x412D28,WBridge_Temp86=0x412D2A,
        WBridge_Temp88=0x412D2C,WBridge_Temp8A=0x412D2E,
        WHost_Action=0x412100+74,WHost_Frame=0x412100+84,WHost_Role=0x412100+86,
        WHost_InputP1Press=0x412020,WHost_InputP1Trigger=0x412022,
        WHost_InputP2Press=0x412024,WHost_InputP2Trigger=0x412026,
        WHost_Mode=0x411760,WHost_Error=0x411764,
        WHost_PlayerWorldMaxX=0x412D06,
        S7Resident_Owner=0x41175e,
        WHost_FrameEvents=0x41176c,WHost_HitEvents=0x41176e)
    defs['CHAR_SELECTED'] = sym['CHAR_SELECTED']
    defs['CHAR_SELECTED_JUMP'] = sym['CHAR_SELECTED_JUMP']
    asm='.snes\n'+''.join(f'{k} = ${v:X}\n' for k,v in defs.items())
    asm+=f'.bank {worker_bank}\n.org $8000\n'+code+'\nWHost_SlotTable:\n    .dw $7900,$7A00,$7B00,$7C00,$7D00,$7E00\n'
    asm+='\nW5_HostRandom03:\n    .a16\n    .i16\n    lda #$FFFF\n    sta $BE\n    lda #10\n    sta $FC\n    rtl\n'
    asm+='''
Worker_Gate:
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
    .a8
    .i16
    php
    phb
    phd
    lda #0
    pha
    plb
    lda #8
    sta $2225
    lda #3
    sta $3027
Worker_Wait:
    .a8
    .i16
    lda $3026
    cmp #2
    beq Worker_Exit
    cmp #1
    bne Worker_Wait
    stz $3026
    rep #$30
    .a16
    .i16
    lda #$7700
    tcd
Worker_Execute:
    .a16
    .i16
    jsl W6_UpdateWorld
    ; Fail closed if this pilot needs an unbound S-CPU unlink service.
    ; The six-actor control has no removals; no death is silently discarded.
    ldx #$7900
Worker_Check:
    .a16
    .i16
    lda.l $40A0F6,x
    beq Worker_UnlinkBlocked
    lda.l $40A0FC,x
    bne Worker_Fault
    txa
    clc
    adc #$100
    tax
    cpx #$7F00
    bcc Worker_Check
    bra Worker_Complete
Worker_UnlinkBlocked:
    .a16
    .i16
    lda #19
Worker_Fault:
    .a16
    .i16
    sta $3A
Worker_Complete:
    .a16
    .i16
    lda.l $412002
    sta.l $412004
    sep #$20
    .a8
    lda #1
    sta $3027
    bra Worker_Wait
Worker_Exit:
    .a8
    .i16
    stz $2225
    stz $3025
    stz $3026
    lda #2
    sta $3027
    pld
    plb
    plp
    jml Worker_Gate
'''.replace('LEGACY_ACK',f'${sym["sa1_wait"]+7:06X}')
    # S-CPU relay. Entire ordered pass per request; no per-actor RPC.
    asm+=f'.bank {relay_bank}\n.org $8000\n'
    asm+='''
Relay_Run:
    .a16
    .i16
    lda.l $7E175C
    bne Relay_Ready
    jsl Relay_Acquire
Relay_Ready:
    .a16
    .i16
    lda.l $7E173C
    sta.l $41173C
    lda.l $7E173E
    sta.l $41173E
    lda.l $7E175A
    inc a
    sta.l $7E175A
    sta.l $412002
    sep #$20
    .a8
    stz $3027
    lda #1
    sta $3026
    ldy #$FFFF
Relay_Wait:
    .a8
    .i16
    lda $3027
    cmp #1
    beq Relay_Completed
    dey
    bne Relay_Wait
    jml Relay_Timeout
Relay_Completed:
    .a8
    .i16
    rep #$30
    .a16
    .i16
    lda.l $412004
    cmp.l $7E175A
    beq Relay_Result
    lda #20
    sta.l $7E173A
    rtl
Relay_Result:
    .a16
    .i16
    lda.l $41173A
    sta.l $7E173A
    lda.l $41176C
    sta.l $7E176C
    lda.l $41176E
    sta.l $7E176E
    rtl
Relay_Acquire:
    .a16
    .i16
    sep #$20
    .a8
    lda #$89
    sta $2231
    stz $3026
    stz $3027
    rep #$30
    .a16
    .i16
'''
    def copy(label,src,dst,size):
        assert size%2==0
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
    asm+=copy('Relay_InWorld',0x7e1700,0x411700,256)
    asm+=copy('Relay_InActors',0x7e1900,0x411900,1536)
    asm+=copy('Relay_InFields',sym['StageEnv_Actors'],0x412100,798)
    asm+=f'    lda.l ${sym["Screen_PosX"]:06X}\n    sta.l $412420\n    lda.l ${sym["Spawn_HoleCount"]:06X}\n    sta.l $412422\n'
    # Relocate typed handles, never arbitrary integer values or source stats.
    def relocate(label,delta):
        out=''
        for slot in range(6):
            # B8 is attacker X, NOT a handle; never relocate numeric payloads.
            for off in POINTER_OFFSETS:
                address=0x411900+slot*256+off
                unique=f'{label}_{slot}_{off}'
                out+=f'    lda.l ${address:06X}\n    beq {unique}\n    clc\n    adc #${delta&65535:04X}\n    sta.l ${address:06X}\n{unique}:\n    .a16\n    .i16\n'
        for off in (0x44,0x46,0x4E,0x50):
            a=0x411700+off;unique=f'{label}_world_{off}'
            out+=f'    lda.l ${a:06X}\n    beq {unique}\n    clc\n    adc #${delta&65535:04X}\n    sta.l ${a:06X}\n{unique}:\n    .a16\n    .i16\n'
        return out
    asm+=relocate('Relay_ToWorker',0x6000)
    asm+='''    lda #WHost_SlotTable & $FFFF
    sta.l $411730
    lda #WORKER_BANK
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
    rtl
Relay_Flush:
    .a16
    .i16
    php
    rep #$30
    phx
    phy
    lda.l $7E175C
    bne Relay_Release
    jmp Relay_Flushed
Relay_Release:
    .a16
    .i16
'''
    asm+=relocate('Relay_ToHost',-0x6000)
    # Preserve host clock/owner/scratch; copy only worker-owned world outputs.
    asm+=copy('Relay_OutWorld',0x411700,0x7e1700,0x30)
    asm+=copy('Relay_OutActors',0x411900,0x7e1900,1536)
    asm+=copy('Relay_OutFields',0x412100,sym['StageEnv_Actors'],798)
    for off in (0x3A,0x44,0x46,0x4E,0x50,0x6C,0x6E):
        asm+=f'    lda.l ${0x411700+off:06X}\n    sta.l ${0x7e1700+off:06X}\n'
    asm+='''    lda #0
    sta.l $7E175C
    sep #$20
    .a8
    stz $3027
    lda #2
    sta $3026
    ldy #$FFFF
Relay_Released:
    .a8
    .i16
    lda $3027
    cmp #2
    beq Relay_ReleaseDone
    dey
    bne Relay_Released
    jml Relay_Timeout
Relay_ReleaseDone:
    .a8
    .i16
    lda #$09
    sta $2231
    stz $2236
Relay_Flushed:
    .a16
    .i16
    rep #$30
    ply
    plx
    plp
    jml HOST_FLUSH
Relay_Timeout:
    .a8
    .i16
    rep #$30
    .a16
    lda #21
    sta.l $7E1764
    ; Diagnostic-only quarantine: never publish a partially owned result.
    stp
'''.replace('HOST_FLUSH',f'${ws["S7Resident_Flush"]:06X}')
    asm=asm.replace('WORKER_BANK',f'${worker_bank:04X}')
    path=folder/'worker.pasm';path.write_text(asm)
    result=subprocess.run([os.environ.get('DOTNET_EXE',r'C:\Users\chad\.dotnet\dotnet.exe'),
        os.environ.get('POPPY_DLL',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll'),
        str(path),'-s',str(folder/'worker.sym')],capture_output=True,text=True)
    (folder/'worker-build.log').write_text(result.stdout+result.stderr)
    if result.returncode or 'warning' in (result.stdout+result.stderr).lower():
        raise RuntimeError(result.stdout+result.stderr)
    binary=path.with_suffix('.bin').read_bytes();sy=symbols(folder/'worker.sym')
    for bank in (relay_bank,worker_bank):
        part=binary[bank*32768:(bank+1)*32768]
        rom[bank*32768:bank*32768+len(part)]=part
    def offset(address):return (address>>16)*32768+(address&65535)-32768
    gate=offset(sym['sa1_wait'])
    if rom[gate:gate+3]!=b'\xAD\x25\x30':
        assert rom[gate]==0x5C,'WORKER_SA1_GATE_NOT_SOURCE_WAIT_OR_KNOWN_GATE'
        previous=int.from_bytes(rom[gate+1:gate+4],'little')
        previous_at=offset(previous)
        signature=bytes.fromhex('AD2530C955F00CC9AAF0045C')
        assert rom[previous_at:previous_at+len(signature)]==signature,'WORKER_PREEXISTING_GATE_SIGNATURE_MISMATCH'
    rom[gate:gate+4]=b'\x5C'+sy['Worker_Gate'].to_bytes(3,'little')
    execute_at=offset(ws['S6Host_Tick__execute'])
    assert rom[execute_at]==0x22,'WORKER_SOURCE_UPDATE_CALLSITE_NOT_JSL'
    update_target=int.from_bytes(rom[execute_at+1:execute_at+4],'little')
    if update_target in (ws['S6_UpdateWorld'], ws.get('S6_UpdateWorldBound')):
        old_relay_bank=None
    else:
        old_relay_bank=update_target>>16
        old_at=offset(update_target)
        assert rom[old_at:old_at+4]==bytes.fromhex('08C230DA'),'WORKER_EXISTING_RELAY_SIGNATURE_MISMATCH'
    rom[execute_at+1:execute_at+4]=sy['Relay_Run'].to_bytes(3,'little')
    render_start=offset(ws['S6Game_PlayRender'])
    render_end=offset(ws['S6Game_PlayRender__return'])
    flush_source=ROOT/'src/core/actor_s6_world_fixture.pasm'
    source_expected=sum(line.strip()=='jsl S7Resident_Flush' for line in flush_source.read_text().splitlines())
    expected=source_expected+(1 if admission.get('scenario')=='wait_probe' else 0)
    flush_sites=[]
    for at in range(render_start,render_end-3):
        if rom[at]!=0x22:continue
        target=int.from_bytes(rom[at+1:at+4],'little')
        if (target==ws['S7Resident_Flush'] or
                (old_relay_bank is not None and target==old_worker_sy.get('Relay_Flush'))):
            flush_sites.append(at)
    assert len(flush_sites)==expected and expected>0,('S7Resident_Flush',len(flush_sites),expected)
    for at in flush_sites:rom[at+1:at+4]=sy['Relay_Flush'].to_bytes(3,'little')
    # Bounded-stop observer consumes the current authoritative worker driver.
    # The fixture now lives in the source-owned world module (bank $1E), not
    # the historical bank-$1E/$1F hook image this pilot originally searched.
    # Relocate only the observer read, using the current source symbols.
    observe_start=offset(ws['S6Clock_HostSourceTick__running'])
    observe_end=offset(ws['S6Clock_HostSourceTick__done'])
    stop_slot=0 if admission.get('scenario')=='kula' else 2
    observer_source=b'\xAF'+(0x7e19e6+stop_slot*256).to_bytes(3,'little')
    observer_target=b'\xAF'+(0x4119e6+stop_slot*256).to_bytes(3,'little')
    observer_legacy_target=b'\xAF'+(0x4119e6).to_bytes(3,'little')
    observer_reads=tuple(dict.fromkeys(
        (observer_source,observer_target,observer_legacy_target)))
    sites=[]
    for needle in observer_reads:
        at=rom.find(needle,observe_start,observe_end)
        while at>=0:
            sites.append((needle,at))
            at=rom.find(needle,at+1,observe_end)
    assert len(sites)==1,('S6Clock_HostSourceTick observer',len(sites))
    needle,at=sites[0]
    if needle!=observer_target:
        rom[at+1:at+4]=(0x4119e6+stop_slot*256).to_bytes(3,'little')
    (folder/'bor.sfc').write_bytes(rom)
    (folder/'worker-manifest.json').write_text(json.dumps(dict(
        status='PRIVATE_PILOT_NOT_PRODUCTION',bwram_regions=REGIONS,
        direct_page_window=[0x6000,0x8000],sa1_bwbank=8,
        world_dp=0x7700,actor_dps=list(range(0x7900,0x7f00,256)),
        code_banks={'s_cpu':relay_bank,'sa1':worker_bank},
        source_pointer_offsets=POINTER_OFFSETS,
        acquire_bulk_bytes=2594,release_bulk_bytes=2396,
        protocol='sequence body before byte request; result before byte completion',
        unsupported=['synchronous S-CPU unlink service','unproven drift numeric hook'],
        production_changed=False),indent=2)+'\n')
    return sy
