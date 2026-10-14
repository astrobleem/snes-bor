"""Isolated native READY safe-point auditor, observer and genuine controller test."""
import inspect,json
from pathlib import Path
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_nonblank_component_native import sha
import m4_nonblank_batch_native as batch
import m4_conditional_capacity_native as conditional
from source_safepoint import transform,LATCH,LATCH_EPOCH,SOURCE_SYM,SOURCE_ASM
BASE=Path('out/byor-motu-conditional-capacity-regression-v1/native')
BASE_SHA='9ccbb5310ceb73f97ba6bdcfddfeeedb98f0378c448c8c0e98f543581c6ddeea'

def owner_patch(native):
    sy=symbols(native/'publisher.sym');oldsy=symbols(SOURCE_SYM)
    at=offset(oldsy['LiveGroundIdlePoll']);old=(BASE/'bor.sfc').read_bytes()[at:at+12]
    if old[:4]!=bytes.fromhex('af80fb7f') or old[4:7]!=bytes.fromhex('c9e8b4'):raise ValueError('SAFEPOINT_OWNER_POLL_DRIFT')
    target=sy['SpOwnerPoll'];replacement=b'\x5c'+target.to_bytes(3,'little')+b'\xea'*8
    return at,old,replacement

def finalize_rom(rom,native):
    rom=bytearray(rom);at,old,new=owner_patch(native)
    if rom[at:at+12]!=old:raise ValueError('SAFEPOINT_OWNER_MUTATION_BEFORE_PATCH')
    rom[at:at+12]=new;return rom

def audit_rom(rom,native):
    old=(BASE/'bor.sfc').read_bytes()
    if sha(old)!=BASE_SHA:raise ValueError('SAFEPOINT_CONTROL_SHA')
    wanted=transform((BASE/'publisher.pasm').read_text().splitlines())
    if (native/'publisher.pasm').read_text().splitlines()!=wanted:raise ValueError('SAFEPOINT_EXACT_SOURCE')
    sy=symbols(native/'publisher.sym');compiled=(native/'publisher.bin').read_bytes()
    from m4_restore_spill_native import audit_branches
    audit_branches([' iny' if x.strip()=='dey' else x for x in wanted],sy,compiled)
    if sy['NbCodeEnd']>=0x39b000 or sy['SpReadyBoundary']!=0x39b000 or sy['SpCodeEnd']>=0x39c000:raise ValueError('SAFEPOINT_CODE_LEASE')
    if any(old[offset(0x39b000):offset(sy['SpCodeEnd'])]):raise ValueError('SAFEPOINT_NONZERO_LEASE')
    expected=bytearray(old)
    expected[offset(0x39a000):offset(sy['NbCodeEnd'])]=compiled[offset(0x39a000):offset(sy['NbCodeEnd'])]
    expected[offset(0x39b000):offset(sy['SpCodeEnd'])]=compiled[offset(0x39b000):offset(sy['SpCodeEnd'])]
    at,oldpoll,new=owner_patch(native);expected[at:at+12]=new
    if expected!=rom:raise ValueError('SAFEPOINT_UNAUTHORIZED_ROM_CHANGE')
    movement_instructions=audit_movement_clone(rom,native)
    return dict(status='PASS',movement_instructions_identical=movement_instructions,latch=[LATCH,LATCH_EPOCH+2],code=[sy['SpReadyBoundary'],sy['SpCodeEnd']],owner_poll_patch_bytes=12,all_assets_kernels_source_services_and_other_bytes_unchanged=True,immutable_source_body=str(SOURCE_ASM),source_body_sha256=sha(SOURCE_ASM.read_bytes()))

def audit_movement_clone(rom,native):
    from m4_rect_map_audit import statements,BRANCHES
    from source_safepoint import movement_code
    src=SOURCE_ASM.read_text().splitlines();oldsy=symbols(SOURCE_SYM);newsy=symbols(native/'publisher.sym')
    expected=transform((BASE/'publisher.pasm').read_text().splitlines())
    newstm=statements([' iny' if x.strip()=='dey' else x for x in expected],newsy)
    by_pc={pc:(n,text) for pc,n,text in newstm.values()}
    oldrom=(BASE/'bor.sfc').read_bytes();count=0
    ranges=[('LiveGroundStart:','LiveGroundPost:',0),('LiveGroundExecute:','CallbackFixture_GroundDone:',5),('LiveGroundPost:',' jsl $398000',0)]
    for begin,end,extra in ranges:
        lo=src.index(begin);hi=src.index(end,lo)+extra;part=src[lo:hi]
        lines=['.snes','.bank 39',f'.org ${oldsy[begin[:-1]]&65535:04X}',*part]
        oldstm=statements(lines,oldsy)
        oldpc=oldsy[begin[:-1]];newpc=newsy['SpOwner_'+begin[:-1]]
        for pc,n,text in oldstm.values():
            npc=newpc+pc-oldpc;data=bytearray(oldrom[offset(pc):offset(pc)+n]);op,_,arg=text.partition(' ')
            if op in BRANCHES|{'jmp','jsr'} and arg in oldsy:
                target=newsy['SpGroundBad'] if arg=='CallbackFixture_Bad' else newsy['SpOwner_'+arg]
                data[1:]=(target-npc-n).to_bytes(n-1,'little',signed=True) if op in BRANCHES else (target&65535).to_bytes(2,'little')
            if rom[offset(npc):offset(npc)+n]!=data:raise ValueError('SAFEPOINT_MOVEMENT_INSTRUCTION_DIFFERENT:'+text)
            count+=1
    return count

def observer(script,contract):
    conditional.observer(script,contract);sy=contract['native_symbols']
    with script.open('a') as f:
        f.write('local spMoving=false;local spLatched=false;local spLatch=nil;local spProtected=nil;local spRegs=nil\n')
        def cb(name,body):f.write(f'emu.addMemoryCallback(function(){body} end,emu.callbackType.exec,{sy[name]},{sy[name]},emu.cpuType.snes,emu.memType.snesMemory)\n')
        def dump(at,n):return f"(function()local t={{}};for i=0,{n-1} do t[#t+1]=string.format('%02x',emu.read({at}+i,emu.memType.snesMemory))end;return table.concat(t)end)()"
        cb('SpLatched',"spLatched=true;spLatch="+dump(LATCH,20)+";nbLog('SP_LATCH',nbTxn..'|'..spLatch..'|'.."+dump(0x7fba00,146)+")")
        cb('SpHasQueuedMovement',"local s=emu.getState();spRegs={};for _,k in ipairs({'cpu.a','cpu.x','cpu.y','cpu.d','cpu.dbr','cpu.sp','cpu.ps'})do if s[k]==nil then nbLog('FAULT','SAFEPOINT_MISSING_REGISTER:'..k)end;spRegs[k]=s[k]end")
        cb('SpRegistersRestored',"local s=emu.getState();for k,v in pairs(spRegs)do if s[k]~=v then nbLog('FAULT','SAFEPOINT_REGISTER:'..k..'|'..tostring(v)..'|'..tostring(s[k]))end end;nbLog('SP_REGISTERS','RESTORED')")
        cb('SpMovementStart',"spMoving=true;spProtected={};for i=0x42c000,0x42d67f do spProtected[#spProtected+1]=emu.read(i,emu.memType.snesMemory)end;nbLog('SP_START',nbTxn..'|'..nbWord(0x7fba90)..'|'..nbWord(0x42d600)..'|'..nbWord(0x42d660)..'|'.."+dump(0x7fba00,146)+")")
        cb('SpMovementComplete',"spMoving=false;for i=0x42c000,0x42d67f do if emu.read(i,emu.memType.snesMemory)~=spProtected[i-0x42c000+1]then nbLog('FAULT','SAFEPOINT_GRAPHICS_MEMORY')end end;nbLog('SP_DONE',nbTxn..'|'..nbWord(0x7fba90)..'|'.."+dump(0x7fba00,146)+")")
        cb('NbMapCommit',"if spLatched and "+dump(LATCH,20)+"~=spLatch then nbLog('FAULT','SAFEPOINT_LATCH_MUTATED')end;nbLog('SP_COMMIT',nbTxn..'|'..nbWord(0x42d61e)..'|'..nbWord(0x7fba90))")
        cb('NbVisible',"nbLog('SP_VISIBLE',nbTxn..'|'..nbWord(0x7ffb98)..'|'..nbWord(0x7fba90)..'|'.."+dump(0x42d6d0,18)+")")
        for cpu in ('snes','sa1'):
            f.write("emu.addMemoryCallback(function(a,v)if spMoving then nbLog('FAULT','SOURCE_WRITES_GRAPHICS:"+cpu+"|'..a)end end,emu.callbackType.write,0x2c000,0x2d67f,emu.cpuType."+cpu+",emu.memType.snesSaveRam)\n")
            f.write("emu.addMemoryCallback(function(a,v)if spMoving then nbLog('FAULT','SOURCE_WRITES_RENDERER_IRAM:"+cpu+"|'..a)end end,emu.callbackType.write,0x400,0x7ff,emu.cpuType."+cpu+",emu.memType.sa1InternalRam)\n")


def run(folder,source,sy,contract,left_safe=False):
    original_observer=batch.observer
    def wrapped(script,c):
        with patch.object(batch,'observer',original_observer):observer(script,c)
    # Reuse the established per-field driver; append a queued real step only
    # after source epoch 2 is sealed and graphics owns PREPARING/PRELOADING.
    import m4_nonblank_component_native as control
    body=inspect.getsource(control.run).replace('def run(folder,source,sy,contract):','def execute_safe(folder,source,sy,contract):')
    needle="        m.hold_input(m.BTN_LEFT,port=0);field('left-input')"
    replacement="        m.write_u16(REQUEST,0xb4e9)\n        for i in range(10):\n            field('newer-view')\n            if startup.u16(m,DISPLAY_EPOCH)==3:break\n        else:raise ValueError('SAFEPOINT_NEWER_VIEW_TIMEOUT')\n        save_checkpoint('noop');capture('noop')\n"+needle
    body=body.replace(needle,replacement).replace('startup.u16(m,DISPLAY_EPOCH)!=2','startup.u16(m,DISPLAY_EPOCH)!=3')
    # Capture the epoch-2 oracle first, then queue a second real source command
    # while native graphics is still preparing it.
    body=body.replace("        for i in range(350):\n            field('movement',True)","        m.write_u16(REQUEST,0xb4e8)\n        for i in range(350):\n            field('movement',True)")
    if body.count('m.write_u16(REQUEST,0xb4e8)')<4:raise ValueError('SAFEPOINT_DRIVER_ANCHOR')
    body=body.replace("        save_checkpoint('cold')","            (native/f'{name}-queue.bin').write_bytes(m.read_memory('SnesMemory',0x42d660,32))\n        save_checkpoint('cold')")
    if left_safe:
        body=body.replace("        m.write_u16(REQUEST,0xb4e8)\n        for i in range(350):\n            field('movement',True)","        m.hold_input(m.BTN_LEFT,port=0);m.write_u16(REQUEST,0xb4e8)\n        for i in range(350):\n            field('movement',True)")
        begin=body.index('        m.write_u16(REQUEST,0xb4e9)');end=body.index("        m.hold_input(m.BTN_LEFT,port=0);field('left-input')",begin)
        body=body[:begin]+"        m.write_u16(REQUEST,0xb4e9)\n        for i in range(5):field('newer-invalid')\n        if startup.u16(m,DISPLAY_EPOCH)!=2 or startup.u16(m,0x7ffb84)!=1:raise ValueError('SAFEPOINT_INVALID_NEW_WORLD_NOT_REJECTED')\n        save_checkpoint('noop');capture('noop')\n        m.hold_input(m.BTN_RIGHT,port=0);field('recover-input');field('recover-input');m.write_u16(REQUEST,0xb4e8)\n        for i in range(10):\n            field('recover')\n            if startup.u16(m,DISPLAY_EPOCH)==4:break\n        else:raise ValueError('SAFEPOINT_LATCHED_KEY_RECOVERY_FAILED')\n"+body[end:]
        body=body.replace('DISPLAY_EPOCH)!=3','DISPLAY_EPOCH)!=4')
        contract=dict(contract,safe_step_left=True)
    # The movement oracle must retain snapshot 2, even after world advances.
    # Existing driver captures the image on first observation of epoch 2.
    with patch.object(control,'observer',wrapped),patch.object(control,'certify',certify):
        ns=dict(control.__dict__);exec(body,ns);ns['execute_safe'](folder,source,sy,contract)


def run_inherited(folder,source,sy,contract,fault_mode=1):
    original=batch.observer
    def wrapped(script,c):
        with patch.object(batch,'observer',original):observer(script,c)
    with patch.object(batch,'audit_rom',audit_rom),patch.object(batch,'observer',wrapped):batch.run(folder,source,sy,contract,fault_mode)
    r=json.loads((folder/'result.json').read_text());r['classification']='SOURCE_SAFEPOINT_INHERITED_CONTROL_PASS';r['source_update_during_transaction']=False;(folder/'result.json').write_text(json.dumps(r,indent=2)+'\n')

def certify(folder,contract,fields):
    # Source/memory/epoch evidence supplements a candidate-specific adaptation
    # of the existing complete batch pixel/VRAM/DMA certification.
    with patch.object(batch,'audit_rom',audit_rom):r=batch.certify(folder,contract,fields)
    n=folder/'native';events=json.loads((folder/'native-events.json').read_text())
    def event(kind):return next(e for e in events if e['kind']==kind and e['data'][0]=='2')
    latch=event('SP_LATCH');start=event('SP_START');done=event('SP_DONE');commit=event('SP_COMMIT');visible=event('SP_VISIBLE')
    ready=next(e for e in events if e['kind']=='PHASE' and e['data'][:2]==['NbReady','2'])
    if not ready['clock']<=latch['clock']<start['clock']<done['clock']<commit['clock']<visible['clock']:raise ValueError('SAFEPOINT_NATIVE_ORDER')
    before=bytes.fromhex(start['data'][-1]);after=bytes.fromhex(done['data'][-1]);image_world=(n/'moved-world.bin').read_bytes()
    if before!=image_world or bytes.fromhex(latch['data'][-1])!=before or int(start['data'][1])!=2 or int(done['data'][1])!=3:raise ValueError('SAFEPOINT_SOURCE_EPOCH_OR_LATCH')
    if before[:4]!=after[:4] or int.from_bytes(after[52:56],'little',signed=True)-int.from_bytes(before[52:56],'little',signed=True)!=(-32768 if contract.get('safe_step_left') else 32768):raise ValueError('SAFEPOINT_GENUINE_PERSISTENT_MOVEMENT')
    control_world=Path('out/byor-motu-conditional-capacity-regression-v1/native/noop-world.bin').read_bytes()
    if (not contract.get('safe_step_left') and after!=control_world) or after!=(n/'noop-world.bin').read_bytes():raise ValueError('SAFEPOINT_SOURCE_CONTROL_DRIFT')
    if start['data'][2:4]!=['3','0'] or commit['data'][1:3]!=['2','3'] or visible['data'][1:3]!=['2','3']:raise ValueError('SAFEPOINT_PENDING_DISPLAY_CANONICAL_SEPARATION')
    key=bytes.fromhex(latch['data'][1])[:18]
    if bytes.fromhex(visible['data'][3])!=key:raise ValueError('SAFEPOINT_SUCCESSFUL_KEY_NOT_LATCHED')
    if int.from_bytes(bytes.fromhex(latch['data'][1])[18:20],'little')!=2:raise ValueError('SAFEPOINT_LATCH_EPOCH')
    if any(e['kind']=='PACKET' and start['clock']<=e['clock']<=done['clock'] for e in events):raise ValueError('SAFEPOINT_DMA_CRITICAL_OVERLAP')
    if len([e for e in events if e['kind']=='SP_START'])!=1:raise ValueError('SAFEPOINT_MORE_THAN_ONE_OPERATION')
    if len([e for e in events if e['kind']=='SP_REGISTERS' and e['data']==['RESTORED']])!=1:raise ValueError('SAFEPOINT_REGISTER_RESTORE_NOT_OBSERVED')
    r.pop('capacity_admission',None)  # Historical batch-fixture text predates the accepted spill backend.
    if contract.get('safe_step_left') and key[6:8]==after[28:30]:raise ValueError('SAFEPOINT_KEY_DIVERGENCE_NOT_EXERCISED')
    r.update(classification='BYOR_MOTU_SOURCE_SAFEPOINT_PASS',source_movement='Actual JOY1 '+('LEFT, X 81 -> 80.5' if contract.get('safe_step_left') else 'RIGHT, X 81 -> 81.5')+' through retained input-history, ground/frame, velocity and check_move pipeline',source_movement_clocks=done['clock']-start['clock'],source_movement_ms=(done['clock']-start['clock'])/21477.270,pending_epoch=2,canonical_epoch_after_safepoint=3,displayed_epoch_at_commit=2,next_presented_epoch=4 if contract.get('safe_step_left') else 3,newer_unsupported_world_rejected=bool(contract.get('safe_step_left')),key_divergence_exercised=bool(contract.get('safe_step_left')),next_presentation_is_projected_noop=True,source_world_control_byte_identical=not contract.get('safe_step_left'),latched_successful_key=True,native_order={name:e['clock'] for name,e in [('ready',ready),('latch',latch),('movement_start',start),('movement_done',done),('commit',commit),('visible',visible)]})
    return r


def main():
    import argparse
    from compiler import Source
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,required=True,help='Existing --source-safepoint native build')
    parser.add_argument('--case',choices=('right','left','partial','stale'),default='right')
    parser.add_argument('--source',type=Path,default=Path('Masters of the Universe [v.3.0 Build 4086].pak'))
    args=parser.parse_args();folder=args.folder.resolve()
    contract=json.loads((folder/'contract.json').read_text())
    source=Source(args.source);sy=symbols(Path('src/main.sym'))
    if args.case in ('right','left'):run(folder,source,sy,contract,left_safe=args.case=='left')
    else:run_inherited(folder,source,sy,contract,2 if args.case=='partial' else 3)

if __name__=='__main__':main()
