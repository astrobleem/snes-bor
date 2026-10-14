"""Apply audited opt-in splice to retained nonblank generated Poppy assembly.

This does not write any repository source or change the default ROM. Run from
repo root against the previously certified native/publisher.pasm. The artifact
is inspection-only until assembled and verified by Sol's Mesen test driver.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from nonblank_batch_rescue import transform,IRAM_LEASE,QUEUE_CAPACITY,RESTORE_CAPACITY


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--control-pasm',type=Path,required=True)
    p.add_argument('--candidate-pasm',type=Path,required=True)
    args=p.parse_args()
    if args.candidate_pasm.exists():p.error('Output must be a new file')
    raw=args.control_pasm.read_bytes()
    source=raw.decode('utf-8').splitlines()
    after=transform(source)
    args.candidate_pasm.parent.mkdir(parents=True,exist_ok=True)
    output='\n'.join(after)+'\n'
    args.candidate_pasm.write_text(output,encoding='utf-8')
    result={'status':'OFFLINE_SOURCE_TRANSFORM_PASS','source_sha256':hashlib.sha256(raw).hexdigest(),
            'output_sha256':hashlib.sha256(output.encode()).hexdigest(),
            'source_statements':len(source),'candidate_statements':len(after),
            'iram_exclusive_lease':[hex(x) for x in IRAM_LEASE],
            'queue_capacity':QUEUE_CAPACITY,'restore_record_capacity':RESTORE_CAPACITY,
            'native_assembled':False,'native_timed':False}
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
