"""Retain bounded reload-scheduler trial statistics, without native admission."""
import argparse
import hashlib
import json
import time
from pathlib import Path
from raster_slot_greedy import schedule_slots


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--seeds',type=int,default=8)
    parser.add_argument('--lookahead',type=int,nargs='+',default=[8,17,64])
    parser.add_argument('--repack',action='store_true')
    parser.add_argument('--permute-banks',action='store_true')
    args=parser.parse_args()
    raw=args.schedule.read_bytes();source=json.loads(raw)
    report=dict(source_schedule=str(args.schedule),source_schedule_sha256=hashlib.sha256(raw).hexdigest(),
                repack=args.repack,permute_banks=args.permute_banks,window_master_clocks=356,beam=32,trials=[],
                universal_raster_rejected=False,native_timing_admitted=False,no_color_reduction=True)
    for lookahead in args.lookahead:
        for seed in range(args.seeds):
            started=time.perf_counter()
            result=schedule_slots(source,window=356,lookahead=lookahead,seed=seed,beam=32,repack=args.repack,permute_banks=args.permute_banks)
            summary=result.get('physical_slot_layout',result).copy()
            summary['elapsed_seconds']=time.perf_counter()-started
            report['trials'].append(summary)
            if 'physical_slot_layout' in result:
                args.candidate.write_text(json.dumps(result,indent=2)+'\n')
                report['candidate_sha256']=hashlib.sha256(args.candidate.read_bytes()).hexdigest()
            args.output.write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(summary),flush=True)
            if 'physical_slot_layout' in result:return


if __name__=='__main__':main()
