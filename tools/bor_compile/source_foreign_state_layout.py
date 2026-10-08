"""Compile caller-owned controller state inside the explicit canvas arena.

The layout is an address plan, not a runtime lease or gameplay admission.
"""
import argparse,json
from pathlib import Path


def layout(base,size,entities=128,players=4):
    if base&255 or not 1<=entities<=128 or players!=4:
        raise ValueError('FOREIGN_STATE_LAYOUT_GEOMETRY')
    if not 0<=base<=0xffffff or size<=0 or base+size>0x1000000:
        raise ValueError('FOREIGN_STATE_LAYOUT_EXTENT')
    # Store only the missing entity fields. Shared animation animhits already
    # belongs to the existing animation initializer at 43E000, not these rows.
    specs=[('input_history',players*256,'source player ring and input words'),
           ('entity_movetime',entities*4,'source entity movetime uint32'),
           ('entity_combo_tail',entities*16,'source entity combostep[1..4]'),
           ('input_scratch',40,'serialized input service controls'),
           ('input_snapshot',56,'immutable outer controller snapshot'),
           ('combo_sequence',110,'one copied immutable source command'),
           ('input_owner',2,'input service readiness'),
           ('binding_shadow',128,'four preflighted entity bindings'),
           ('binding_controls',32,'serialized input entity binding'),
           ('costmove_controls',64,'serialized costmove continuation'),
           ('combo_controls',96,'serialized combo selection continuation'),
           ('entity_combostyle',entities*4,'source mutable entity modeldata.combostyle int32'),
           ('attack_chain_controls',96,'serialized attack-chain continuation'),
           ('entity_run_tuple',entities*2,'lossless immutable RUN snapshot handle'),
           ('run_tuple_controls',64,'serialized RUN capture/read controls')]
    cursor=base;regions=[]
    for name,count,authority in specs:
        cursor=(cursor+1)&~1
        if cursor+count>base+size:raise ValueError('FOREIGN_STATE_LAYOUT_CAPACITY')
        regions.append(dict(name=name,address=cursor,bytes=count,end=cursor+count,
                            authority=authority));cursor+=count
    return dict(schema='BYOR_FOREIGN_CONTROLLER_ARENA_LAYOUT_V1',base=base,
        bytes=size,used_bytes=cursor-base,remaining_bytes=base+size-cursor,
        entities=entities,players=players,regions=regions,
        required_lease='SourceForeignWork B671 nonzero matching generation; retired canvas/frontpanel/water owners',
        overlaps_vm_slots=False,runtime_owner_bound=False,motu_gameplay_proven=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--symbols',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    # Use assembler authority rather than guessing space from an old report.
    import re
    text=a.symbols.read_text();values={}
    for name in ('SOURCE_FOREIGN_WORK_BASE','SOURCE_FOREIGN_WORK_BYTES','SOURCE_FOREIGN_WORK_END'):
        hit=re.search(r'^([0-9A-Fa-f]+):([0-9A-Fa-f]+) '+name+r'$',text,re.M)
        if not hit:raise ValueError('FOREIGN_ARENA_SYMBOL:'+name)
        values[name]=(int(hit[1],16)<<16)|int(hit[2],16)
    base=values['SOURCE_FOREIGN_WORK_BASE'];size=values['SOURCE_FOREIGN_WORK_BYTES']
    if base+size!=values['SOURCE_FOREIGN_WORK_END']:raise ValueError('FOREIGN_ARENA_SYMBOL_EXTENT')
    report=layout(base,size)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Compiled controller arena:',report['used_bytes'],'bytes;',report['remaining_bytes'],'remain')


if __name__=='__main__':main()
