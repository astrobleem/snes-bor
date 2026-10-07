"""Native source findtarget decisions over injected current-tick pool snapshots.

This is a bounded API proof after original bootstrap, not a live MOTU owner.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_target_4086 import Target, find, metadata, descriptor, BASE, ADDRESS, ORDER_BASE, ORDER_READY
from source_entity_abi import record
from source_world_pool import descriptor as world_descriptor
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower, POLICY
from _harness import MESEN_EXE, _free_tcp_port, pasm_constant_in, read_block, run_frames_exact, exact_input_edge, Reporter
from actor_s5_entity_fixture import symbols
from m4_vm_cost_observer import observed_session, pause_for_injection
import game_bor_startup_select as startup


def cases():
    actor=Target(1,type=2,hostile=1)
    left=Target(2,type=1,x=-10*65536)
    right=Target(3,type=1,x=20*65536)
    close=replace(right,x=5*65536)
    cases=[
      ('pool_order_back_first',[actor,left,right],None),
      ('pool_order_front_first',[actor,right,left],None),
      ('near_front_replaces',[actor,left,close],None),
      ('left_facing',[replace(actor,direction=0),right,left],None),
      ('invincible_one',[actor,replace(close,invincible=1),left],None),
      ('invincible_two',[actor,replace(close,invincible=2),left],None),
      ('invulnerable',[actor,replace(close,vulnerable=False),left],None),
      ('dead',[actor,replace(close,dead=True),left],None),
      ('inactive',[actor,replace(close,alive=False),left],None),
      ('wrong_type',[actor,replace(close,type=0),left],None),
      ('stealth_hidden',[actor,replace(close,hide=1),left],None),
      ('signed_stealth',[replace(actor,detect=-1),replace(left,hide=-1),close],None),
      ('range_boundary',[actor,replace(right,x=9999*65536)],None),
      ('range_subpixel_over',[actor,replace(right,x=9999*65536+1)],None),
      ('signed_extreme_distance',[replace(actor,x=-2147483648),replace(right,x=2147483647)],None),
      ('distance_carry',[replace(actor,x=-2147483648,z=-2147483648),replace(right,x=2147483647,z=2147483647)],None),
      ('fractional_tie',[actor,replace(left,x=32768),replace(right,x=32768)],None),
      ('no_opponent',[actor],None),
      ('no_lease',[actor,right],'lease'),
      ('stale_snapshot',[actor,right],'time'),
      ('count_mismatch',[actor,right],'count'),
      ('metadata_reserved',[actor,right],'reserved'),
      ('corrupt_coordinate_type',[actor,right],'coordinate'),
      ('clock_time_mismatch',[actor,right],'clock'),
      ('reordered_pointer_list',[actor,left,right],None),
      ('active_prefix',[actor,left,right],None),
      ('order_duplicate',[actor,left,right],'order_duplicate'),
      ('order_range',[actor,left,right],'order_range'),
      ('order_no_lease',[actor,left,right],'order_no_lease'),
      ('scan_count_invalid',[actor,left,right],'scan_count'),
      ('full_capacity',[actor]+[Target(i+2,type=1,x=(2000+i)*65536) for i in range(126)]
                       +[Target(129,type=1,x=65536)],None),
    ]
    for n in (1,-1,65536,-2147483648):
        cases.extend([('source_exists_self_'+str(n),[actor,right],None),('source_exists_target_'+str(n),[actor,right],None),('source_exists_both_'+str(n),[actor,right],None)])
    cases.append(('source_exists_target_0',[actor,replace(right,alive=False)],None))
    cases.append(('source_exists_self_0',[actor,right],'source_self_dead'))
    return [(n,[replace(t,token=0x414000+i*80) for i,t in enumerate(rows)],bad) for n,rows,bad in cases]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[2];sy=symbols(root/'src/main.sym')
    def c(file,key):return pasm_constant_in(str(root/file),key)
    const='src/core/vm/vm_consts.pasm';call='src/core/vm/vm_call.pasm';variant='src/core/vm/vm_native_variant.pasm'
    entity='src/core/vm/vm_source_entity.pasm';world='src/core/vm/vm_source_world_birth.pasm'
    source='void main(){void self=getlocalvar("self");void target=findtarget(self);}'
    blob,compiled=lower(compile_library(parse_script(source,'source-target-probe.c'),['getlocalvar','findtarget']),numeric_policy=POLICY)
    sections=struct.unpack_from('<6I',blob,24);instructions,slots=struct.unpack_from('<2H',blob,8)
    result_slot=compiled['function_local_slots']['main']['target']
    reporter=Reporter('M4-SOURCE-TARGET',kind='GATE');events=[]
    session=observed_session(folder,sy,0)
    with session(rom=a.rom.resolve(),mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('TARGET_BOOTSTRAP_REQUIRED')
        # Original production bootstrap finishes BW-RAM write admission after
        # entering PLAYING. Match the existing birth fixture's bounded settle.
        run_frames_exact(m,12)
        reporter.check('target metadata lease cold disabled',read_block(m,ADDRESS,32)[:2]==bytes(2))
        for name,rows,bad in cases():
            checkpoint=pause_for_injection(m,sy);m.pause()
            m.write_memory('snesMemory',c(const,'VmCode_Wram'),blob.hex())
            m.write_memory('snesMemory',c(const,'VmSlots_Wram'),blob[sections[1]:sections[1]+slots*8].hex())
            for file,key,value in [('src/core/vm/vm_run.pasm','VmPriv_InstrOff',sections[0]),
                (call,'VmCall_CallsitesOff',sections[2]),(call,'VmCall_ArgSlotsOff',sections[3]),
                ('src/core/vm/vm_string.pasm','VmStr_StringsOff',sections[4])]:m.write_u16(c(file,key),value)
            pool=bytearray(b''.join(record(t.token,dict(a=0,animationid=0,direction=t.direction,health=100,
                playerindex=0,x=t.x,z=t.z,maxhealth=100),alive=t.alive) for t in rows))
            states=bytearray(b''.join(metadata(t) for t in rows))
            source_exists=name.startswith('source_exists_')
            if source_exists:
                _,_,which,value=name.split('_',3);value=int(value)&0xffffffff
                if which in ('self','both'):struct.pack_into('<I',pool,4,value)
                if which in ('target','both'):struct.pack_into('<I',pool,80+4,value)
            if bad=='coordinate':pool[80+48]=1
            if bad=='reserved':struct.pack_into('<H',states,20+10,1)
            order=list(range(len(rows)))
            if name=='reordered_pointer_list':order=[0,2,1]
            if bad=='order_duplicate':order[1]=order[0]
            if bad=='order_range':order[1]=len(rows)
            order_bytes=struct.pack('<'+'H'*len(order),*order)
            scan_count=1 if name=='active_prefix' else len(rows)
            if bad=='scan_count':scan_count+=1
            m.write_memory('snesMemory',0x414000,pool.hex());m.write_memory('snesMemory',BASE,states.hex())
            m.write_memory('snesMemory',ORDER_BASE,order_bytes.hex())
            actual_pool=read_block(m,0x414000,len(pool))
            actual_states=read_block(m,BASE,max(32,len(states)))[:len(states)]
            if actual_pool!=pool or actual_states!=states:
                (folder/'writeback-failure.json').write_text(json.dumps(dict(case=name,pool_expected=pool.hex(),pool_actual=actual_pool.hex(),
                    metadata_expected=states.hex(),metadata_actual=actual_states.hex()),indent=2)+'\n')
                raise ValueError('TARGET_NATIVE_POOL_WRITEBACK')
            m.write_memory('snesMemory',c(world,'VmSourceWorld_Ready'),world_descriptor(len(rows),0x1cb000,1,184,time=48).hex())
            m.write_memory('snesMemory',c(entity,'VmSourceEntity_Base'),struct.pack('<HBxHH',0x4000,0x41,len(rows),0xb5ef if source_exists else 0xb48b).hex())
            m.write_memory('snesMemory',c(variant,'VmNativeVariant_Self'),(struct.pack('<BBHI',5,0,0,rows[0].token)+bytes(24)).hex())
            m.write_u16(c(variant,'VmNativeVariant_ContextValid'),0xb48f)
            lease=bytearray(descriptor(len(rows),48))
            if bad=='lease':struct.pack_into('<H',lease,0,0)
            if bad=='time':struct.pack_into('<I',lease,4,49)
            if bad=='count':struct.pack_into('<H',lease,2,len(rows)+1)
            m.write_memory('snesMemory',ADDRESS,lease.hex())
            m.write_u16(sy['SourceTarget4086_OrderReady'],0 if bad=='order_no_lease' else ORDER_READY)
            m.write_u16(sy['SourceTarget4086_ScanCount'],scan_count)
            m.write_u16(sy['SourceClock4086_Ready'],0xb4c5 if bad=='clock' else 0)
            if bad=='clock':m.write_memory('snesMemory',sy['SourceClock4086_TimeLo'],struct.pack('<I',49).hex())
            for key,value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',instructions),
                ('VmState_SlotCount',slots),('VmState_FrameTop',0)]:m.write_u16(c(const,key),value)
            m.write_u8(c(const,'VmState_Status'),1)
            for fields in range(1,61):
                run_frames_exact(m,1);state=read_block(m,c(const,'VM_STATE_FIRST'),32)
                status=state[c(const,'VmState_Status')-c(const,'VM_STATE_FIRST')]
                error=struct.unpack_from('<H',state,c(const,'VmState_Error')-c(const,'VM_STATE_FIRST'))[0]
                if status in (4,5):break
            returned=read_block(m,c(const,'VmSlots_Wram')+result_slot*8,32)[:8]
            reporter.check(name+' native status',(status,error)==((5,10) if bad else (4,0)))
            expected_token=find(rows,rows[0].token,order=order,scan_count=scan_count) if not bad else None
            if not bad:
                expected=struct.pack('<BBHI',5,0,0,expected_token) if expected_token else bytes(8)
                reporter.check(name+' exact PTR/EMPTY result',returned==expected)
            unchanged=(read_block(m,0x414000,len(pool))==pool and read_block(m,BASE,max(32,len(states)))[:len(states)]==states
                       and read_block(m,ORDER_BASE,max(32,len(order_bytes)))[:len(order_bytes)]==order_bytes)
            reporter.check(name+' immutable pool and metadata',unchanged)
            events.append(dict(case=name,status=status,error=error,returned=returned.hex(),expected_token=expected_token,
                               unchanged=unchanged,checkpoint=checkpoint))
        m.write_u16(ADDRESS,0);m.write_u16(sy['SourceTarget4086_OrderReady'],0)
        m.write_u16(c(world,'VmSourceWorld_Ready'),0);m.write_u16(sy['SourceClock4086_Ready'],0)
    report=dict(schema='BYOR_SOURCE_TARGET_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),cases=events,numeric_policy=POLICY,
        scope='One-argument native findtarget over injected pool/metadata leases after original bootstrap; no live AI or MOTU world.',
        metadata_base=BASE,metadata_bytes_per_entity=20,order_base=ORDER_BASE,order_bytes_per_entity=2,bank0_growth=0,
        source_numeric_equivalence=False,engine_authority='af23dc9c2316bb7853bb266ccf40986aa9765aeb')
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
