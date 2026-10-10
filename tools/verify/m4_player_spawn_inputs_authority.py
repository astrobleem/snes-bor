"""Check actual authored empty-terrain descriptors against pinned C spawnplayer."""
import argparse,hashlib,json,struct,subprocess
from pathlib import Path
from compiler import Source
from source_player_spawn_inputs import derive
from source_player_spawn_authority import BASE,FIELDS,expected


def verify(source,authority):
    report=json.loads((authority/'report.json').read_text())
    if report['status']!='PASS' or report['source_body_sha256']!='052af4b9ecd375c2b38bf5279c8e4d6729fe386a622fd256041988821d9ef7f8':raise ValueError('SPAWN_INPUT_C_AUTHORITY')
    if hashlib.sha256((authority/'spawnplayer.c').read_text().encode()).hexdigest()!=report['fixture_sha256']:raise ValueError('SPAWN_INPUT_C_FIXTURE_IDENTITY')
    inputs=derive(source);cases=[];requirements=[]
    for stage in inputs['stages']:
        if stage['diagnostics']:continue
        for index in range(-1,7):
            slot=index&3;sx,sz=stage['spawn_offsets'][slot]
            c=dict(BASE,index=index,hres=stage['source_width'],minz=stage['minimum_z'],maxz=stage['maximum_z'],sx=sx,sz=sz,direction=8 if stage['scroll']=='left'else 0,setweap=0)
            cases.append(c);requirements.append(stage['placements'][slot])
    if not cases:raise ValueError('SPAWN_INPUT_NO_ADMITTED_CONTEXT')
    data=b''.join(struct.pack('<15i',*[c[k]for k in FIELDS])for c in cases)
    executable=authority/'spawnplayer.exe';raw=subprocess.check_output([str(executable.resolve())],input=data)
    if len(raw)!=80*len(cases):raise ValueError('SPAWN_INPUT_C_OUTPUT_LENGTH')
    results=[]
    for i,(c,r)in enumerate(zip(cases,requirements)):
        actual=list(struct.unpack_from('<20I',raw,80*i));wanted=[v&0xffffffff for v in expected(c)]
        matched=actual==wanted and actual[:3]==[r['x_binary32'],r['z_binary32'],r['flip']]
        results.append(dict(case=c,actual=actual,passed=matched))
    return dict(schema='BYOR_AUTHORED_SPAWN_INPUT_C_PROOF_V1',status='PASS'if all(r['passed']for r in results)else'FAIL',cases=len(cases),results=results,requirements=inputs,input_sha256=hashlib.sha256(data).hexdigest(),output_sha256=hashlib.sha256(raw).hexdigest(),authority_fixture_sha256=report['fixture_sha256'],authority_executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),native_placement_bound=False,full_spawnplayer_bound=False,no_color_reduction=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(Source(a.source),a.authority);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in ('status','cases','input_sha256','output_sha256')}))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
