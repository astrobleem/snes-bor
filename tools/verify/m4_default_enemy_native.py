"""Normal enemy/NPC preparation; drop service is explicitly returned pending."""
import argparse,hashlib,itertools,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_animation_init_4086 import pack as pack_ai
from source_frame_effects_4086 import pack as pack_fe,ANIMATION_FIELDS
from source_binary32_q16 import project
from m4_default_none_native import LUA as NONE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=NONE_LUA.replace("put(0x43c002,c.walk)","put(0x43c002,c.spawn);put(0x43c004,c.respawn)")
LUA=LUA.replace("put(b+36,c.adjust,4)","put(b+36,c.adjust,4);put(0x41683c+c.slot*64,c.speed,4);local l=0x439000+c.slot*80;put(l+48,c.subtype,4);put(l+52,c.nomove,4);put(l+68,c.truth,4);put(l+76,0xb508);put(l+16,3,4);put(l+12,77,4)")
LUA=LUA.replace("set('SourceIdle4086_Status',0)","set('SourceIdle4086_Status',0);set('SourceDefaultChoice4086_Ready',0xb4fa);set('SourceDefaultChoice4086_Status',2);set('SourceDefaultChoice4086_Spawn',1);set('SourceDefaultChoice4086_Respawn',2);set('SourceAnimationInit4086_Handles',2)")
LUA=LUA.replace("set('SourceUpdateFrame4086_Animations',1)","set('SourceUpdateFrame4086_Animations',2)")
LUA=LUA.replace("elseif c.bad=='empty'then", "elseif c.bad=='life_sticky'then set('SourceLifecycle4086_Status',3)\n elseif c.bad=='choice'then set('SourceDefaultChoice4086_Ready',0)\n elseif c.bad=='choice_sticky'then set('SourceDefaultChoice4086_Status',3)\n elseif c.bad=='truth_marker'then put(0x43904c+c.slot*80,0)\n elseif c.bad=='truth_high'then put(0x439046+c.slot*80,1)\n elseif c.bad=='truth_range'then put(0x439044+c.slot*80,2)\n elseif c.bad=='truth_conflict'then put(0x439044+c.slot*80,0);put(0x41683c+c.slot*64,65536,4)\n elseif c.bad=='empty'then")
start=LUA.index('if c.fault==0 then');end=LUA.index(' local s=emu.getState();',start)
LUA=LUA[:start]+'''returned=emu.getState()['cpu.a']
 if c.fault==0 then
 local function expect(a,v)for i=0,3 do before[a+i]=(v>>(i*8))&255 end end
 local l=0x439000+c.slot*80;local b=0x40c000+c.slot*96
 expect(l,6);expect(l+4,10);expect(l+8,9)
 if c.spawn~=0 or c.respawn~=0 then expect(l+12,4)end
 if c.subtype==2 then expect(l+16,1)end
 expect(b,c.multiple~=0 and c.multiple or(c.type==512 and -1 or 5))
 expect(0x41683c+c.slot*64,c.expected_speed)
 expect(l+68,c.nomove~=0 and 0 or 1);before[l+76]=8;before[l+77]=0xb5
 end
'''+LUA[end:]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 base=dict(level=1,alive=0,platform=0,wall=0,gravity=-1,adjust=-1,existing=1,bad='',fault=0)
 rows=[];seen=set()
 for ar in authority['results']:
  c=ar['case'];state=ar['actual']['state']
  if c['type']not in(2,512)or c['subtype']in(1,3)or not c['level']or c.get('mutation',0):continue
  key=(c['type'],c['subtype'],c['mask']&6,c['speed'],c['nomove'],c['multiple'])
  if key in seen:continue
  seen.add(key);assert state[20:23]==[10,6,9]
  for slot in(0,127):rows.append(dict(base,slot=slot,type=c['type'],subtype=c['subtype'],spawn=1 if c['mask']&2 else 0,respawn=2 if c['mask']&4 else 0,speed=c['speed']*65536,truth=int(c['speed']!=0),nomove=c['nomove'],multiple=c['multiple'],expected_speed=project(state[19])))
 for slot,typ,nomove in itertools.product((0,127),(2,512),(0,1)):
  rows.append(dict(rows[0],slot=slot,type=typ,nomove=nomove,speed=0,truth=1,expected_speed=0,tiny_nonzero=True))
 for bad in('ready','sticky','world','pool','side','count','slot','core','entities','token','token_high','pending','cache','table','life','life_marker','life_model','type','level','life_sticky','choice','choice_sticky','truth_marker','truth_high','truth_range','truth_conflict'):
  for slot in(0,127):rows.append(dict(rows[0],slot=slot,bad=bad,fault=1))
 for slot,subtype in itertools.product((0,127),(1,3)):rows.append(dict(rows[0],slot=slot,subtype=subtype,fault=1))
 ai=pack_ai(dict(maximum_animations=4,animations=[dict(handle=i,numframes=1,sync=-1,engine_animation_id=i)for i in(1,2)]));fe=pack_fe(dict(models=[],media=[],animations=[dict(handle=i,events=dict.fromkeys(ANIMATION_FIELDS,0),frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6)])for i in(1,2)]))
 r=Reporter('M4-DEFAULT-ENEMY-NORMAL',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceDefaultEnemy4086_PrepareNormal','SourceDefaultPlayer4086_Ready',0xb503,[(59,0,ai),(60,0,fe)],LUA.replace('AIBYTES',str(len(ai))).replace('FEBYTES',str(len(fe))),r)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('C-derived normal enemy/NPC fields, current speed truth, pending drop signal, guards/context',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 2]and(c['fault']or v[4]==int(not(c['spawn']or c['respawn'])))for i,(v,c)in enumerate(zip(results,rows))))
 report=dict(schema='BYOR_4086_DEFAULT_ENEMY_NORMAL_PREPARATION_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cases=len(rows),inputs=rows,results=results,normal_callback_ids=dict(think=6,damage=10,trymove=9,spawn=4),drop_service_bound=False,callback_execution_bound=False,tiny_nonzero_speed_not_defaulted=True,numeric_policy='ACCEPTED_COMPAT_Q16_16',full_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
