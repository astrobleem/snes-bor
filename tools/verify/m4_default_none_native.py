"""Generic no-walk TYPE_NONE default-init fields under current-model guards."""
import argparse,hashlib,itertools,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_animation_init_4086 import pack as pack_ai
from source_frame_effects_4086 import pack as pack_fe,ANIMATION_FIELDS
from m4_default_init_idle_guards_native import LUA as IDLE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=IDLE_LUA.replace("put(0x43c000,1)","put(0x43c002,c.walk);put(0x43904a+c.slot*80,0xb4fb);put(0x439048+c.slot*80,0);set('SourceLifecycle4086_Ready',0xb4fb);set('SourceLifecycle4086_Status',2)")
LUA=LUA.replace("put(b+8,c.platform,4)","put(b+8,c.platform,4);put(b+72,c.type,4);put(b+20,c.gravity,4);put(b+36,c.adjust,4)")
LUA=LUA.replace("put(v+4,c.alive)","put(v+4,c.alive);put(v+16,1,4);put(v+20,0,4)")
LUA=LUA.replace("set('SourceAnimationInit4086_Ready',0xb4ec)","set('SourceAnimationInit4086_Number',1);set('SourceAnimationInit4086_Ready',0xb4ec)")
LUA=LUA.replace("elseif c.bad=='empty'then", "elseif c.bad=='life'then set('SourceLifecycle4086_Ready',0)\n elseif c.bad=='life_marker'then put(0x43904a+c.slot*80,0)\n elseif c.bad=='life_model'then put(0x439048+c.slot*80,1)\n elseif c.bad=='type'then put(0x40c048+c.slot*96,1,4)\n elseif c.bad=='level'then set('VmSourceWorld_Level',0)\n elseif c.bad=='empty'then")
LUA=LUA.replace("returned=emu.getState()['cpu.a']", """if c.fault==0 then
 local function expect(a,v)for i=0,3 do before[a+i]=(v>>(i*8))&255 end end
 expect(0x439010+c.slot*80,1);expect(0x416820+c.slot*64,131072)
 if c.gravity<0 then expect(0x40c014+c.slot*96,1)end
 if c.adjust<0 then expect(0x40c024+c.slot*96,1)end
 end""")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 c_rows=[r for r in authority['results']if r['case']['type']==0 and not r['case']['mask']&32 and r['case']['level']and not r['case']['mutation']]
 assert c_rows and all(r['actual']['state'][0]==1 and r['actual']['state'][12:14]==[1,1]and r['actual']['state'][18]==0x40000000 for r in c_rows)
 base=dict(level=1,multiple=-1,platform=0,wall=0,bad='',fault=0,type=0,existing=1,walk=0)
 rows=[dict(base,slot=s,alive=alive,gravity=g,adjust=n)for s,alive,g,n in itertools.product((0,1,127),(0,1),(-2147483648,-1,0,1,65536,2147483647),(-2147483648,-1,0,1,65536,2147483647))]
 for bad in ('ready','sticky','world','pool','side','count','slot','core','entities','token','token_high','pending','cache','table','life','life_marker','life_model','type','level'):
  for s in (0,127):rows.append(dict(base,slot=s,alive=1,gravity=-1,adjust=-1,bad=bad,fault=1))
 for s in (0,127):rows.append(dict(base,slot=s,alive=1,gravity=-1,adjust=-1,walk=1,fault=1))
 ai=pack_ai(dict(maximum_animations=4,animations=[dict(handle=1,numframes=1,sync=-1,engine_animation_id=1)]));fe=pack_fe(dict(models=[],media=[],animations=[dict(handle=1,events=dict.fromkeys(ANIMATION_FIELDS,0),frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6)])]))
 r=Reporter('M4-DEFAULT-NONE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceDefaultNone4086_ApplyNoWalk','SourceDefaultPlayer4086_Ready',0xb503,[(59,0,ai),(60,0,fe)],LUA.replace('AIBYTES',str(len(ai))).replace('FEBYTES',str(len(fe))),r)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('TYPE_NONE no-walk nograb, signed current flags and exact multiplier; guards and untouched physical/context state',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 2]for i,(v,c)in enumerate(zip(results,rows))))
 report=dict(schema='BYOR_4086_DEFAULT_NONE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),c_no_walk_cases=len(c_rows),cases=len(rows),inputs=rows,results=results,lease_installation_instrumented=True,current_model_flags_bound=True,walk_service_bound=False,complete_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
