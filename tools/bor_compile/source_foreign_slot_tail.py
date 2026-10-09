"""Derive a lease plan from the compiled module's actual VM slot extent.

No slot relocation, hidden reduction or aliasing of live module slots. Runtime
ownership must validate the loaded slot count and retain its generation before
publishing entity state in this tail. A plan alone does not grant that lease.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from compiler import Source
from script_callback_owner import derive, validate_pair, pack
from source_model_registry import derive as models, pack as pack_models

BASE=0x7fc000
CAPACITY=1024
ENTITY_FIELDS=('charging','turning','getting','rush.count.current','rush.count.max','rush.time')


def layout(slot_count, entities=128):
    if not 1<=slot_count<=CAPACITY or not 1<=entities<=128:
        raise ValueError('FOREIGN_VM_TAIL_GEOMETRY')
    start=BASE+slot_count*8
    limit=BASE+CAPACITY*8
    count=entities*4*len(ENTITY_FIELDS)
    if start+count>limit:
        raise ValueError('FOREIGN_VM_TAIL_ENTITY_STATE_CAPACITY')
    return dict(schema='BYOR_FOREIGN_VM_SLOT_TAIL_LAYOUT_V1',
                live_slot_count=slot_count,live_slot_bytes=slot_count*8,
                base=start,bytes=limit-start,end=limit,
                entity_fields=list(ENTITY_FIELDS),entity_stride=24,entities=entities,
                entity_state_bytes=count,remaining_bytes=limit-start-count,
                integer_fields_lossless=True,live_slots_overlapped=False,
                required_lease='compiled slot count equals loaded VmState_SlotCount; immutable module extent and nonzero matching lifetime generation',
                runtime_owner_bound=False,canonical_entity_state_bound=False,
                motu_gameplay_proven=False,no_color_reduction=True)


def derive_plan(source):
    owners,code,metadata,dispatch=derive(source)
    validate_pair(pack(owners),pack_models(models(source)),code,metadata,dispatch)
    # B48R's checked ABI publishes the complete linked slot count at +10.
    if metadata[:4]!=b'B48R':raise ValueError('FOREIGN_VM_TAIL_METADATA_ABI')
    report=layout(struct.unpack_from('<H',metadata,10)[0])
    report.update(source_sha256=hashlib.sha256(source.path.read_bytes()).hexdigest(),
                  module_code_sha256=hashlib.sha256(code).hexdigest(),
                  module_metadata_sha256=hashlib.sha256(metadata).hexdigest(),
                  live_slot_identity_preserved=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=derive_plan(Source(a.source))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Compiled VM slot tail:',report['live_slot_count'],'live slots;',
          report['entity_state_bytes'],'state bytes;',report['remaining_bytes'],'remain')


if __name__=='__main__':main()
