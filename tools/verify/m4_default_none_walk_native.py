"""TYPE_NONE walk setup from current movement state, before actual walk service."""
import argparse,hashlib,itertools,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_animation_init_4086 import pack as pack_ai
from source_frame_effects_4086 import pack as pack_fe,ANIMATION_FIELDS
from source_binary32_q16 import project
from m4_default_none_native import LUA as NONE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=NONE_LUA.replace("put(0x439048+c.slot*80,0)","put(0x439048+c.slot*80,0);put(0x43902c+c.slot*80,c.mode,4);put(0x41683c+c.slot*64,c.speed_q16,4)")
LUA=LUA.replace("put(v+20,0,4)","put(v+20,0,4);put(v+24,1,4);put(v+28,c.direction,4)")
LUA=LUA.replace("elseif c.bad=='empty'then", "elseif c.bad=='direction_tag'then put(v+24,2)\n elseif c.bad=='direction_reserved'then put(v+26,1)\n elseif c.bad=='empty'then")
LUA=LUA.replace("expect(0x416820+c.slot*64,131072)","expect(0x439000+c.slot*80,15);expect(0x416824+c.slot*64,c.velocity_q16)")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 base=dict(level=1,multiple=-1,platform=0,wall=0,gravity=-1,adjust=-1,bad='',fault=0,type=0,existing=1,walk=1)
 rows=[];seen=set()
 for r in authority['results']:
  c=r['case'];state=r['actual']['state']
  if c['type']!=0 or not c['mask']&32 or not c['level']or c['mutation']:continue
  key=c['speed'],c['direction']
  if key in seen:continue
  seen.add(key);assert state[0]==1 and state[21]==15
  for slot,mode,alive in itertools.product((0,1,127),(0,1),(0,1)):
   rows.append(dict(base,slot=slot,alive=alive,mode=mode,direction=c['direction'],speed_q16=c['speed']*65536,velocity_q16=project(state[17])))
 for bad in ('ready','sticky','world','pool','side','count','slot','core','entities','token','token_high','pending','cache','table','life','life_marker','life_model','type','level','direction_tag','direction_reserved'):
  for s in (0,127):rows.append(dict(rows[0],slot=s,bad=bad,fault=1))
 for s,mode in itertools.product((0,127),(-1,2,65536)):rows.append(dict(rows[0],slot=s,mode=mode,fault=1))
 for s in (0,127):
  rows.append(dict(rows[0],slot=s,walk=0,fault=1));rows.append(dict(rows[0],slot=s,direction=0,speed_q16=-2147483648,fault=1))
 ai=pack_ai(dict(maximum_animations=4,animations=[dict(handle=1,numframes=1,sync=-1,engine_animation_id=1)]));fe=pack_fe(dict(models=[],media=[],animations=[dict(handle=1,events=dict.fromkeys(ANIMATION_FIELDS,0),frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6)])]))
 r=Reporter('M4-DEFAULT-NONE-WALK',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceDefaultNone4086_PrepareWalk','SourceDefaultPlayer4086_Ready',0xb503,[(59,0,ai),(60,0,fe)],LUA.replace('AIBYTES',str(len(ai))).replace('FEBYTES',str(len(fe))),r)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('C-derived TYPE_NONE walk flags, anything_walk and current-speed velocity; guards and unrelated physical/context state',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 2]for i,(v,c)in enumerate(zip(results,rows))))
 report=dict(schema='BYOR_4086_DEFAULT_NONE_WALK_PREPARATION_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cases=len(rows),inputs=rows,results=results,numeric_policy='ACCEPTED_COMPAT_Q16_16',current_speed_used=True,cached_original_speed_substitution=False,anything_walk_id=15,anything_walk_execution_bound=False,walk_frame_zero_required_next=True,full_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
