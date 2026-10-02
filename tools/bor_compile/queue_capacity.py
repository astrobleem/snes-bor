"""S3 queue-only compatibility report; does not compile models or publish content."""
import argparse
import json
import re
from pathlib import Path
from compiler import Source, stage, key, baseline, ROOT
from analyze import inventory_project
from queue_abi import RECORD_SIZE, TARGET_CAPACITY, check_count, QueueCapacityError, plan_build


def inventory(source):
    rows=[]
    for s in inventory_project(source)['sets']:
        for ordinal,e in enumerate(s['entries']):
            if e['kind']!='STAGE': continue
            ir=stage(source,e['source_path'])
            # Only registered queue controls may be counted as packed. Other
            # dialect diagnostics must not be flattened into a fake queue.
            packed=None if ir.diagnostics else len(ir.queue)+len(ir.environment.get('hole',[]))
            terminators=sum(d.name=='at' for d in ir.directives)
            row=dict(project=source.path.name,set=s['name'],stage=ordinal,source_path=ir.source_path,
                authored_records=len(ir.queue) if not ir.diagnostics else None,
                authored_at_directives=terminators,recognized_records=len(ir.queue),
                runtime_added_records=len(ir.environment.get('hole',[])),packed_records=packed,
                required_bytes=None if packed is None else packed*RECORD_SIZE,
                capacity_status='BLOCKED_UNKNOWN_QUEUE_SHAPE' if packed is None else 'PASS',
                diagnostics=ir.diagnostics,payload_emitted=False)
            if packed is not None:
                try: check_count(packed,project=row['project'],set_name=row['set'],stage=ordinal,source_path=ir.source_path)
                except QueueCapacityError as error:
                    row['capacity_status']='QUEUE_CAPACITY_EXCEEDED';row['diagnostics'].append(error.diagnostic)
            rows.append(row)
    known=[r for r in rows if r['packed_records'] is not None]
    return dict(project=source.path.name,rows=rows,target_capacity=TARGET_CAPACITY,
        maximum_packed=max(known,key=lambda r:r['packed_records']) if known else None,
        maximum_authored_at=max(rows,key=lambda r:r['authored_at_directives']) if rows else None,
        complete_packed_inventory=len(known)==len(rows))


def report():
    cfg,git=baseline('28c71f99c51428bb3d18457b434fd5973048a01e')
    shipped=[dict(project=c['pak'],set='production',stage=i,source_path=c['source_level'],
                  packed_records=len(git(c['spawn']))//RECORD_SIZE) for i,c in enumerate(cfg['STAGE_CONFIGS'])]
    projects=[]
    for filename in ('Beats of Rage Original [v.3.0 Build 4086].pak',
                     'Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak',
                     'Masters of the Universe [v.3.0 Build 4086].pak'):
        if (ROOT/filename).exists(): projects.append(inventory(Source(ROOT/filename)))
    normal=[r for r in projects[0]['rows'] if r['set']=='Normal' and r['packed_records'] is not None]
    old_spawn=git('src/core/spawn.pasm').decode();old_main=git('src/main.pasm').decode()
    def number(text,name): return int(re.search(rf'(?m)^{name}\s*=\s*\$([0-9A-Fa-f]+)',text)[1],16)
    old_base=number(old_spawn,'SpawnTable_Wram')
    old_capacity=int(re.search(r'(?m)^SPAWN_MAX_RECORDS\s*=\s*(\d+)',old_spawn)[1])
    following={}
    for text in (old_spawn,old_main):
        for name,value in re.findall(r'(?m)^(\w+)\s*=\s*\$([0-9A-Fa-f]+)',text):
            address=int(value,16)
            if old_base+old_capacity*RECORD_SIZE<=address<0x7E5900:
                following.setdefault(hex(address),[]).append(name)
    overflow=[dict(records=count,bytes_copied=count*RECORD_SIZE,
                   overflow_bytes=(count-old_capacity)*RECORD_SIZE,
                   first_oob=hex(old_base+old_capacity*RECORD_SIZE),last_oob=hex(old_base+count*RECORD_SIZE-1),
                   overwritten_object_starts={k:v for k,v in following.items() if int(k,16)<old_base+count*RECORD_SIZE}) for count in (92,94)]
    return dict(baseline_layout=dict(commit='28c71f99c51428bb3d18457b434fd5973048a01e',base=hex(old_base),
                capacity=old_capacity,allocated_bytes=old_capacity*RECORD_SIZE,following_region=following,overflow=overflow),
                production=plan_build(shipped),production_max=max(shipped,key=lambda r:r['packed_records']),
                complete_normal=plan_build(normal),projects=projects)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    r=report();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(production=r['production_max'],normal_capacity=r['complete_normal']['capacity'],
        projects=[dict(name=x['project'],max_packed=x['maximum_packed'],max_at=x['maximum_authored_at']) for x in r['projects']]),indent=2))


if __name__=='__main__': main()
