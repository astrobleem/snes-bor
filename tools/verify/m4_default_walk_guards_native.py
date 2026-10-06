"""Native default-walk no-op/guard cases; actual authored execution separate."""
import argparse,hashlib,itertools,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_animation_init_4086 import pack as pack_ai
from source_frame_effects_4086 import pack as pack_fe,ANIMATION_FIELDS
from m4_default_none_native import LUA as NONE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=NONE_LUA.replace("put(0x439048+c.slot*80,0)","put(0x439048+c.slot*80,0);put(0x43902c+c.slot*80,c.mode,4)")
LUA=LUA.replace("put(v+20,0,4)","put(v+20,1,4)")
start=LUA.index(' if c.fault==0 then\n local function expect')
end=LUA.index(' local s=emu.getState();for',start)
LUA=LUA[:start]+" returned=emu.getState()['cpu.a']\n"+LUA[end:]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 base=dict(level=1,multiple=-1,platform=0,wall=0,gravity=-1,adjust=-1,bad='',fault=0,type=0,existing=1,walk=0)
 rows=[dict(base,slot=s,alive=alive,mode=mode,walk=w)for s,alive,mode,w in itertools.product((0,1,127),(0,1),(0,1),(0,1))]
 for bad in ('ready','sticky','world','pool','side','count','slot','token','token_high','pending','cache','table','life','life_marker','life_model'):
  for s in (0,127):rows.append(dict(base,slot=s,alive=1,mode=0,bad=bad,fault=1))
 for s,m in itertools.product((0,127),(-1,2,65536,2147483647,-2147483648)):rows.append(dict(base,slot=s,alive=1,mode=m,fault=1))
 ai=pack_ai(dict(maximum_animations=4,animations=[dict(handle=1,numframes=1,sync=-1,engine_animation_id=1)]));fe=pack_fe(dict(models=[],media=[],animations=[dict(handle=1,events=dict.fromkeys(ANIMATION_FIELDS,0),frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6)])]))
 r=Reporter('M4-DEFAULT-WALK-GUARDS',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceWalk4086_BeginDefaultOnly','SourceDefaultPlayer4086_Ready',0xb503,[(59,0,ai),(60,0,fe)],LUA.replace('AIBYTES',str(len(ai))).replace('FEBYTES',str(len(fe))),r)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('missing or already-current walk has no frame service; checked mode/current model and untouched physical/context state',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 2]and(c['fault']or v[4]==0)for i,(v,c)in enumerate(zip(results,rows))))
 report=dict(schema='BYOR_4086_DEFAULT_WALK_GUARDS_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cases=len(rows),inputs=rows,results=results,lease_installation_instrumented=True,actual_authored_walk_separately_proven=True,type_none_velocity_think_setup_bound=False,complete_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
