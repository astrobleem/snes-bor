"""Bounded generic source entity read-view proof; not a gameplay world proof."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bor_compile'))
from script_ir_4086 import parse_script
from script_bytecode import compile_library
from script_native_module import lower, POLICY
from source_entity_abi import record, view, get_property, MAGIC, STRIDE
from _harness import (McpSession, MESEN_EXE, _free_tcp_port, pasm_constant_in,
                      read_block, run_frames_exact, exact_input_edge, Reporter)
import game_bor_startup_select as startup
from actor_s5_entity_fixture import symbols
from m4_vm_cost_observer import observed_session,pause_for_injection,spans

SOURCE = '''void main(){
 void self=getlocalvar("self");
 void a=getentityproperty(self,"a"); void x=getentityproperty(self,"X");
 void z=getentityproperty(self,"z"); void d=getentityproperty(self,"direction");
 void hp=getentityproperty(self,"health"); void pi=getentityproperty(self,"playerindex");
 void maxhp=getentityproperty(self,"maxhealth");
 void prefix="anim"; void suffix="ationID";
 void an=getentityproperty(self,prefix+suffix);
 void absent=getentityproperty(NULL(),"not_bound");
}'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
    blob, compiled = lower(compile_library(parse_script(SOURCE, 'entity-view-probe.c'),
        ['NULL', 'getlocalvar', 'getentityproperty']), numeric_policy=POLICY)
    (a.output / 'probe.b48s').write_bytes(blob)
    root = Path(__file__).resolve().parents[2]
    def c(file, name): return pasm_constant_in(str(root / file), name)
    const = 'src/core/vm/vm_consts.pasm'; call = 'src/core/vm/vm_call.pasm'
    entity = 'src/core/vm/vm_source_entity.pasm'; variant = 'src/core/vm/vm_native_variant.pasm'
    code = c(const, 'VmCode_Wram'); slots = c(const, 'VmSlots_Wram')
    offsets = struct.unpack_from('<6I', blob, 24); count, slotcount = struct.unpack_from('<2H', blob, 8)
    token = 0x6abcde
    values = dict(a=93*65536, animationid=36, direction=0, health=271,
                  playerindex=1, x=-(18*65536+16384), z=220*65536+32768,maxhealth=4096)
    records = [record(0x9abcde, {key: 0 for key in values}), record(token, values)]
    from m4_source_entity_fixture import fixture_base
    entity_base=fixture_base(root,len(records)*STRIDE)
    descriptor, payload = view(entity_base, records)
    malformed = bytearray(payload); malformed[STRIDE+8] = 1
    cases = [('valid', token, descriptor, payload, True),
             ('stale', token+1, descriptor, payload, False),
             ('no_lease', token, descriptor[:6]+b'\0\0', payload, False),
             ('bank_spill', token, struct.pack('<HBxHH', 0xffc0, 0x7f, 2, MAGIC), payload, False),
             ('old_abi',token,descriptor[:6]+struct.pack('<H',0xb48d),payload,False),
             ('bad_variant', token, descriptor, bytes(malformed), False)]
    reporter = Reporter('M4-SOURCE-ENTITY-VIEW', kind='GATE'); results = []
    runtime_symbols=symbols(root/'src/main.sym')
    session_type=observed_session(a.output,runtime_symbols,count)
    with session_type(rom=a.rom.resolve(), mesen=MESEN_EXE, port=_free_tcp_port(),
                    stderr_log=a.output/'mesen.log') as m:
        with patch.object(m, 'reset_emulator', return_value=None): startup.cold_to_title(m, reporter)
        startup.title_to_charselect(m); exact_input_edge(m, m.BTN_START, 1, port=0)
        if not startup.wait_state(m, startup.PLAYING, 300): raise ValueError('ENTITY_VIEW_PLAYING_REQUIRED')
        for name, handle, lease, data, valid in cases:
            checkpoint=pause_for_injection(m,runtime_symbols)
            m.pause(); m.write_memory('snesMemory', code, blob.hex())
            m.write_memory('snesMemory', slots, blob[offsets[1]:offsets[1]+slotcount*8].hex())
            for file, key, value in [('src/core/vm/vm_run.pasm','VmPriv_InstrOff',offsets[0]),
                    (call,'VmCall_CallsitesOff',offsets[2]),(call,'VmCall_ArgSlotsOff',offsets[3]),
                    ('src/core/vm/vm_string.pasm','VmStr_StringsOff',offsets[4])]: m.write_u16(c(file,key),value)
            context = struct.pack('<BBHI',5,0,0,handle)+bytes(24)
            m.write_memory('snesMemory', c(variant,'VmNativeVariant_Self'), context.hex())
            m.write_u16(c(variant,'VmNativeVariant_ContextValid'),0xb48f)
            m.write_memory('snesMemory',c(entity,'VmSourceEntity_Base'),lease.hex())
            m.write_memory('snesMemory',entity_base,data.hex())
            for key, value in [('VmState_Ip',0),('VmState_Error',0),('VmState_InstrCount',count),
                              ('VmState_SlotCount',slotcount),('VmState_FrameTop',0)]: m.write_u16(c(const,key),value)
            m.write_u8(c(const,'VmState_Status'),c(const,'VMSTAT_READY'))
            for field in range(1,61):
                run_frames_exact(m,1); state=read_block(m,c(const,'VM_STATE_FIRST'),32)
                status=state[c(const,'VmState_Status')-c(const,'VM_STATE_FIRST')]
                error=struct.unpack_from('<H',state,c(const,'VmState_Error')-c(const,'VM_STATE_FIRST'))[0]
                if status in (4,5): break
            expected_status, expected_error = (4,0) if valid else (5,10)
            reporter.check(name+' native terminal state', (status,error)==(expected_status,expected_error))
            checks=[]
            if valid:
                for key, prop in [('a','a'),('x','x'),('z','z'),('d','direction'),('hp','health'),
                                  ('pi','playerindex'),('an','animationID'),('maxhp','maxhealth'),('absent',None)]:
                    index=compiled['function_local_slots']['main'][key]
                    actual=read_block(m,slots+index*8,32)[:8]
                    expected=get_property(records,token,prop) if prop else bytes(8)
                    reporter.check(key+' full typed property',actual==expected)
                    checks.append(dict(local=key,actual=actual.hex(),expected=expected.hex()))
            results.append(dict(case=name,fields=field,status=status,error=error,checks=checks,injection_checkpoint=checkpoint))
    result=dict(schema='BYOR_SOURCE_ENTITY_NATIVE_READ_VIEW_V2',view_magic=MAGIC,record_stride=STRIDE,
        entity_fixture_base=entity_base,
        status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),module=compiled,
        source=SOURCE,cases=results,native_cpu_spans=spans(a.output/'mesen.log'),numeric_policy=POLICY,source_numeric_equivalence=False,
        entity_world_allocator_bound=False,motu_gameplay_proven=False,
        scope='Generic typed read view with injected world records; no gameplay entity allocation')
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n'); reporter.finish()


if __name__ == '__main__': main()
