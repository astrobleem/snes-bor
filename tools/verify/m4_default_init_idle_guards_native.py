"""No-op existing animation and bounded missing-animation initializer guards."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_animation_init_4086 import pack as pack_ai
from source_frame_effects_4086 import pack as pack_fe,ANIMATION_FIELDS
from m4_default_init_tail_native import LUA as TAIL_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=TAIL_LUA.replace("{0x439000,10240}","{0x439000,10240},{0x43eb00,4096},{0x43c000,8192},{0x43e000,512},{0x41f500,2560}")
LUA=LUA.replace("put(0x416804+c.slot*64,1)","put(0x416804+c.slot*64,c.existing);put(0x416800+c.slot*64,0);put(0x43eb14+c.slot*32,0,4);put(0x43c000,1)")
LUA=LUA.replace("local before,cpu,ctx", "local returned=0\nlocal before,cpu,ctx")
LUA=LUA.replace("set('SourceAnimationInit4086_Ready',0);set('SourceAnimationInit4086_State',0)","""set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',0);set('SourceAnimationInit4086_Base',0x8000);set('SourceAnimationInit4086_Bank',59);set('SourceAnimationInit4086_Bytes',AIBYTES);set('SourceAnimationInit4086_Handles',1)
 set('SourceModelEntityCopy4086_Models',1);set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',1);set('SourceModelAnimationCopy4086_Maximum',4);set('SourceModelAnimationCopy4086_Bytes',8)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',FEBYTES);set('SourceUpdateFrame4086_Animations',1)
 set('SourceIdle4086_Ready',0xb4f3);set('SourceIdle4086_Status',0)""")
LUA=LUA.replace("elseif c.bad=='empty'then", "elseif c.bad=='idle_ready'then set('SourceIdle4086_Ready',0)\n elseif c.bad=='idle_absent'then put(0x43c000,0)\n elseif c.bad=='idle_mode'then put(0x43eb14+c.slot*32,2)\n elseif c.bad=='cache'then set('SourceModelAnimationCopy4086_Ready',0)\n elseif c.bad=='table'then set('SourceAnimationInit4086_Base',0x8002)\n elseif c.bad=='empty'then")
LUA=LUA.replace("if c.fault==0 and c.level~=0 and c.multiple<0 then for i=0,3 do before[0x40c000+c.slot*96+i]=0 end end", "returned=emu.getState()['cpu.a']")
LUA=LUA.replace("..word(sy.SourceEmptyInitEnvironment4086_Status))", "..returned)")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 base=dict(level=1,alive=0,multiple=-1,platform=1,wall=1,bad='',fault=0)
 rows=[dict(base,slot=s,existing=1,level=l)for s in (0,1,127)for l in (0,1)]
 for bad in ('ready','sticky','world','pool','side','count','slot','core','entities','token','token_high','pending','idle_ready','idle_absent','idle_mode','cache','table'):
  for s in (0,127):rows.append(dict(base,slot=s,existing=0,bad=bad,fault=1))
 ai=pack_ai(dict(maximum_animations=4,animations=[dict(handle=1,numframes=1,sync=-1,engine_animation_id=0)]))
 fe=pack_fe(dict(models=[],media=[],animations=[dict(handle=1,events=dict.fromkeys(ANIMATION_FIELDS,0),frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6)])]))
 r=Reporter('M4-DEFAULT-IDLE-GUARDS',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceDefaultInit4086_BeginIdle','SourceDefaultPlayer4086_Ready',0xb503,[(59,0,ai),(60,0,fe)],LUA.replace('AIBYTES',str(len(ai))).replace('FEBYTES',str(len(fe))),r)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('existing animation skips service; invalid idle capability fails before physical writes; dead pointers/context',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 2]and(c['fault']or v[4]==0)for i,(v,c)in enumerate(zip(results,rows))))
 report=dict(schema='BYOR_4086_DEFAULT_IDLE_GUARDS_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,lease_installation_instrumented=True,actual_authored_idle_execution_separately_proven=True,full_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
