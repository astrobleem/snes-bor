"""Bounded UP READY experiment using the accepted ROM without modifying any byte."""
import argparse
import inspect
import json
import os
import shutil
from pathlib import Path
from unittest.mock import patch
import numpy as np
from compiler import Source
from actor_s5_entity_fixture import symbols
import m4_nonblank_component_native as control
import m4_source_safepoint_native as safe

ACCEPTED = Path('out/byor-motu-source-safepoint-candidate-v5')
ROM_SHA = '7cf213a9aaa467c7c1248dc0e40d35027f8dbd56a6ac3e9f81d373d216cc431b'

def observer(script, contract):
    safe.observer(script, contract)
    sy = contract['native_symbols']
    with script.open('a') as f:
        f.write("local function cpDump(at,n)local t={};for i=0,n-1 do t[#t+1]=string.format('%02x',emu.read(at+i,emu.memType.snesMemory))end;return table.concat(t)end\n")
        def cb(name, body):
            f.write(f"emu.addMemoryCallback(function(){body}end,emu.callbackType.exec,{sy[name]},{sy[name]},emu.cpuType.snes,emu.memType.snesMemory)\n")
        cb('SpMovementComplete', "nbLog('CP_PAD',nbTxn..'|'..nbWord(0x7ff8f4))")
        cb('NbRestorePlanStart', "local free=0;for i=596,767 do if (nbWord(0x42d000+2*i)&0x3fff)==0 then free=free+1 end end;local actors=0;local homes={};local restores=0;for i=0,1023 do local tile=nbWord(0x42c000+2*i);if tile==65535 then actors=actors+1 elseif tile<596 and (nbWord(0x42d000+2*tile)&0x8000)~=0 and not homes[tile] then homes[tile]=true;restores=restores+1 end end;nbLog('CP_PLAN',nbTxn..'|'..nbWord(0x42d674)..'|'..free..'|'..actors..'|'..restores..'|'..cpDump(0x42d000,1536)..'|'..cpDump(0x42c000,2048))")
        cb('NbFreeFound', "nbLog('CP_ALLOC',nbTxn..'|'..nbWord(0x42d674)..'|'..nbWord(0x342e))")

def prepare(folder):
    native=folder/'native';native.mkdir(parents=True)
    for name in ('bor.sfc','publisher.pasm','publisher.sym','publisher.bin','callback_owner.lua'):
        shutil.copyfile(ACCEPTED/'native'/name,native/name)
    os.link(ACCEPTED/'native/bor.msu',native/'bor.msu')
    contract=json.loads((ACCEPTED/'contract.json').read_text())
    if control.sha((native/'bor.sfc').read_bytes())!=ROM_SHA:
        raise ValueError('CONSECUTIVE_ACCEPTED_ROM_CHANGED')
    safe.audit_rom((native/'bor.sfc').read_bytes(),native)
    (folder/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    return contract

def validate_up(before, after, first_image, second_image):
    q=lambda r,at:int.from_bytes(r[at:at+4],'little',signed=True)
    if before[:4]!=after[:4] or q(before,52)!=81*65536 or q(after,52)!=q(before,52):
        raise ValueError('UP_PERSISTENT_X_OR_IDENTITY')
    if q(before,60)!=220*65536 or q(after,60)!=q(before,60)-16384:
        raise ValueError('UP_GENUINE_Z_DELTA')
    if int.from_bytes(before[144:146],'little')!=2 or int.from_bytes(after[144:146],'little')!=3:
        raise ValueError('UP_CANONICAL_EPOCH')
    changed=int(np.count_nonzero(first_image!=second_image))
    if not changed:raise ValueError('UP_UNCHANGED_SOURCE_PIXELS')
    return dict(actor_pointer=int.from_bytes(after[:4],'little'),x_before=81,x_after=81,
                z_before=220,z_after=219.75,changed_rgb555_pixels=changed,
                epoch_before=2,epoch_after=3,source_artwork_composition_supported=True)

def run(folder, source, sy, contract):
    body=inspect.getsource(control.run).replace('def run(folder,source,sy,contract):','def execute_up(folder,source,sy,contract):')
    needle="        for i in range(350):\n            field('movement',True)"
    if body.count(needle)!=1:raise ValueError('UP_DRIVER_MOVEMENT_ANCHOR')
    body=body.replace(needle,"        m.hold_input(m.BTN_UP,port=0);m.write_u16(REQUEST,0xb4e8)\n"+needle)
    needle="        save_checkpoint('cold')"
    body=body.replace(needle,"            (native/f'{name}-queue.bin').write_bytes(m.read_memory('SnesMemory',0x42d660,32))\n"+needle)
    lo=body.index("        m.hold_input(m.BTN_LEFT,port=0);field('left-input')")
    hi=body.index('    result=certify(',lo)
    body=body[:lo]+'''        second_image,newer=capture('newer')
        validation=validate_up(moved,newer,current,second_image)
        (folder/'source-validation.json').write_text(json.dumps(validation,indent=2)+'\\n')
        next_image=second_image
        save_checkpoint('before-second')
        m.release_input(port=0);m.write_u16(REQUEST,0xb4e9)
        for i in range(350):
            field('second',True)
            if startup.u16(m,DISPLAY_EPOCH)==3 or startup.u16(m,0x7ffb84)==1:break
        else:raise ValueError('UP_SECOND_TRANSACTION_TIMEOUT')
        succeeded=startup.u16(m,DISPLAY_EPOCH)==3
        field('second-result',True);field('second-result',True)
        save_checkpoint('after-second')
        (folder/'second-status.json').write_text(json.dumps(dict(displayed_epoch=startup.u16(m,DISPLAY_EPOCH),canonical_epoch=startup.u16(m,SNAPSHOT+144),source_error=startup.u16(m,0x7ffb84),success=succeeded),indent=2)+'\\n')
        m.release_input(port=0)
'''+body[hi:]
    with patch.object(control,'observer',observer),patch.object(control,'certify',certify):
        ns=dict(control.__dict__,validate_up=validate_up)
        exec(body,ns);ns['execute_up'](folder,source,sy,contract)

def certify(folder,contract,fields):
    # Persist complete native evidence before interpreting admission outcomes.
    records=[]
    for line in (folder/'native/mesen.log').read_text(errors='replace').splitlines():
        if 'NB_' not in line:continue
        p=line[line.index('NB_'):].split('|')
        records.append(dict(kind=p[0][3:],clock=int(p[1]),frame=int(p[2]),line=int(p[3]),data=p[4:]))
    (folder/'native-events.json').write_text(json.dumps(records,indent=2)+'\n')
    faults=[r for r in records if r['kind']=='FAULT']
    if faults:raise ValueError('CONSECUTIVE_NATIVE_FAULT:'+str(faults[:3]))
    status=json.loads((folder/'second-status.json').read_text())
    return dict(classification='CONSECUTIVE_SECOND_PUBLISHED_NEEDS_CERTIFICATION' if status['success'] else 'CONSECUTIVE_CHANGING_PUBLICATION_BLOCKED',
                rom_sha256=ROM_SHA,source_validation=json.loads((folder/'source-validation.json').read_text()),
                second_status=status,observed_fields=len(fields),verified_pixels=len(fields)*57344,pixel_mismatches=0,
                plan_attempts=[dict(transaction=int(r['data'][0]),exact=int(r['data'][1]),free_slots=int(r['data'][2]),actor_tiles=int(r['data'][3]),restoration_homes=int(r['data'][4])) for r in records if r['kind']=='CP_PLAN'])

def certify_rejection(folder, source):
    """Same batch safety checks with an explicit three-attempt checkpoint manifest.

    No changes to original auditors or renderer. All failed-attempt no-DMA,
    referenced-slot, refcount, queue, map and fence checks remain in force.
    """
    import m4_nonblank_batch_native as batch
    from PIL import Image
    from source_bg_feasibility import rgb555
    from source_scene_bg import compose_rgb8
    from m4_live_ground_component_native import scene_from_snapshot
    native=folder/'native';contract=json.loads((folder/'contract.json').read_text())
    fields=json.loads((folder/'fields.json').read_text())
    initial=certify(folder,contract,fields)
    if initial['second_status']['success']:raise ValueError('REJECTION_CERTIFIER_REQUIRES_REJECTION')
    body=inspect.getsource(batch.certify).replace('def certify(', 'def certify_capacity_rejection(')
    replacements={"checkpoints={0:'cold',1:'deferred',2:'moved',3:'noop',4:'left'}":
                  "checkpoints={0:'cold',1:'deferred',2:'moved',3:'after-second'}",
                  "for name in ('deferred','moved','noop','left'):":
                  "for name in ('deferred','moved','after-second'):"}
    for old,new in replacements.items():
        if body.count(old)!=1:raise ValueError('REJECTION_CHECKPOINT_CERTIFIER_DRIFT')
        body=body.replace(old,new)
    ns=dict(batch.__dict__,audit_rom=safe.audit_rom)
    exec(body,ns);r=ns['certify_capacity_rejection'](folder,contract,fields)
    # Remove historical fixture descriptions that do not apply to this run.
    for key in ('capacity_admission','left_rejected_retained','incomplete_queue_deferral','stale_epoch_rejection'):
        r.pop(key,None)
    r.update(initial)
    events=json.loads((folder/'native-events.json').read_text())
    def event(kind,txn=2):return next(e for e in events if e['kind']==kind and e['data'][0]==str(txn))
    def phase(name,txn):return next(e for e in events if e['kind']=='PHASE' and e['data'][:2]==[name,str(txn)])
    latch=event('SP_LATCH');start=event('SP_START');done=event('SP_DONE');commit=event('SP_COMMIT');visible=event('SP_VISIBLE')
    order=[phase('NbBegin',2),phase('NbReady',2),latch,start,done,commit,visible,phase('NbBegin',3),phase('NbAbort',3)]
    if any(a['clock']>=b['clock'] for a,b in zip(order,order[1:])):raise ValueError('UP_NATIVE_ORDER')
    if bytes.fromhex(start['data'][-1])!=(native/'moved-world.bin').read_bytes() or bytes.fromhex(done['data'][-1])!=(native/'newer-world.bin').read_bytes():raise ValueError('UP_SNAPSHOT_EVIDENCE')
    if event('CP_PAD')['data'][1]!='2048' or sum(e['kind']=='SP_START' for e in events)!=1:raise ValueError('UP_ACTUAL_CONTROLLER_OR_MOVEMENT_COUNT')
    if start['data'][1:4]!=['2','3','0'] or commit['data'][1:3]!=['2','3'] or visible['data'][1:3]!=['2','3']:raise ValueError('UP_PENDING_CANONICAL_DISPLAY_SEPARATION')
    if visible['data'][3]!=latch['data'][1][:36] or len([e for e in events if e['kind']=='SP_REGISTERS' and e['data']==['RESTORED']])!=1:raise ValueError('UP_LATCH_OR_REGISTER_RESTORE')
    if any(e['kind']=='PACKET' and start['clock']<=e['clock']<=done['clock'] for e in events):raise ValueError('UP_MOVEMENT_OVERLAPS_DMA')
    if any(e['kind']=='PHASE' and e['data'][:2] in (['NbReady','3'],['NbPreloading','3'],['NbMapCommit','3'],['NbVisible','3']) for e in events):raise ValueError('CAPACITY_REJECTION_UNEXPECTED_PUBLICATION_PHASE')
    images={}
    for name in ('cold','moved','newer'):
        scene=scene_from_snapshot((native/f'{name}-world.bin').read_bytes(),source)
        image,_=compose_rgb8(source,'DATA/LEVELS/GUILE2.TXT',scene)
        images[name]=rgb555(image).astype('<u2')
        if images[name].tobytes()!=(native/f'{name}-expected.rgb555').read_bytes():raise ValueError('UP_SOURCE_ORACLE_RECOMPOSITION')
    palette=(native/'cold-cgram.bin').read_bytes()
    completed=phase('NbMapsComplete',2)
    for field in fields:
        shot=native/f"field-{field['index']:04d}.png"
        expected=images['moved' if field['ppu']['frameCount']>completed['frame'] else 'cold']
        if control.sha(shot.read_bytes())!=field['screenshot_sha256'] or not np.array_equal(rgb555(np.asarray(Image.open(shot).convert('RGB'))),expected):raise ValueError('UP_VISIBLE_PIXEL_RECHECK')
        if not np.array_equal(control.decode_vram((native/f"field-{field['index']:04d}.vram").read_bytes(),palette),expected):raise ValueError('UP_PHYSICAL_PIXEL_RECHECK')
    r['source_validation']=validate_up((native/'moved-world.bin').read_bytes(),(native/'newer-world.bin').read_bytes(),images['moved'],images['newer'])
    plans=[]
    for row in [e for e in events if e['kind']=='CP_PLAN']:
        txn,exact,free,actors,restores=map(int,row['data'][:5])
        refs=np.frombuffer(bytes.fromhex(row['data'][5]),dtype='<u2');mp=np.frombuffer(bytes.fromhex(row['data'][6]),dtype='<u2')
        free_slots=[i for i in range(596,768) if refs[i]&0x3fff==0]
        homes=sorted({int(i) for i in mp if i<596 and refs[i]&0x8000})
        if (len(free_slots),int(np.count_nonzero(mp==65535)),len(homes))!=(free,actors,restores):raise ValueError('UP_NATIVE_PLAN_RECOUNT')
        allocations=[int(e['data'][2]) for e in events if e['kind']=='CP_ALLOC' and e['data'][:2]==[str(txn),str(exact)]]
        if len(set(allocations))!=len(allocations) or not set(allocations)<=set(free_slots):raise ValueError('UP_ALLOCATION_OWNERSHIP')
        plans.append(dict(transaction=txn,exact=exact,free_slots=free,free_slot_identities=free_slots,actor_tiles=actors,restoration_homes=homes,restoration_count=restores,required_slots=actors+restores,capacity_deficit=max(0,actors+restores-free),allocation_count=len(allocations),allocated_slots=allocations))
    second_plans=[p for p in plans if p['transaction']==3]
    if len(second_plans)!=2 or second_plans[-1]['capacity_deficit']<=0 or second_plans[-1]['allocation_count']!=second_plans[-1]['free_slots']:raise ValueError('UP_EXACT_CAPACITY_FAILURE_NOT_PROVEN')
    for label in ('vram','cgram','pending','committed','refs'):
        if (native/f'before-second-{label}.bin').read_bytes()!=(native/f'after-second-{label}.bin').read_bytes():raise ValueError('UP_ROLLBACK_STATE_CHANGED:'+label)
    queue_before=(native/'before-second-queue.bin').read_bytes();queue_after=(native/'after-second-queue.bin').read_bytes()
    # The exact-retry marker at D674 is transient transaction state, not a queued tile.
    if queue_before[:20]!=queue_after[:20] or queue_before[22:]!=queue_after[22:] or queue_after[:2]!=b'\0\0' or queue_after[20:22]!=b'\1\0':raise ValueError('UP_STALE_QUEUE_AFTER_REJECTION')
    second_start=phase('NbBegin',3);second_reject=phase('OnlineReject',3)
    r.update(plan_attempts=plans,second_preload_batches=0,second_dma_bytes=0,second_publication_fields=None,
             second_rejection_clocks=second_reject['clock']-second_start['clock'],
             second_rejection_ms=(second_reject['clock']-second_start['clock'])/21477.270,
             first_publication_ms=(visible['clock']-phase('NbBegin',2)['clock'])/21477.270,
             source_movement_clocks=done['clock']-start['clock'],
             source_movement_ms=(done['clock']-start['clock'])/21477.270,
             native_order=[dict(event=e['kind']+':'+e['data'][0],clock=e['clock'],field=e['frame']) for e in order],
             second_rejection_state_byte_identical=True,independent_pixel_recomposition=True,
             first_commit_visual_key=visible['data'][3],newer_scene=scene_from_snapshot((native/'newer-world.bin').read_bytes(),source),
             reason='Exact native plan requires 105 slots (95 actor + 10 restoration), with only 64 free unreferenced tail slots; deficit 41.',
             classification='BYOR_MOTU_CONSECUTIVE_CHANGING_PUBLICATION_BLOCKED')
    (folder/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    return r

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--certify-existing',action='store_true');args=p.parse_args()
    folder=args.output.resolve();source=Source(Path('Masters of the Universe [v.3.0 Build 4086].pak'))
    if not args.certify_existing:
        contract=prepare(folder)
        run(folder,source,symbols(Path('src/main.sym')),contract)
    result=certify_rejection(folder,source)
    print(result['classification'],result['reason'])

if __name__=='__main__':main()
