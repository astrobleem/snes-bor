"""Combined normal-enemy horizontal drop: real shared RNG and source C table."""
import argparse,hashlib,itertools,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_actor_numeric import random32_step
from source_binary32_q16 import project
from source_animation_init_4086 import pack as pack_ai
from source_frame_effects_4086 import pack as pack_fe,ANIMATION_FIELDS
from m4_default_drop_context_native import LUA as CONTEXT_LUA
from m4_default_init_idle_guards_native import LUA as IDLE_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols

# Reuse the complete descriptor lease setup, relocated into the second private
# bank. This fixture deliberately exercises the absent-JUMP source no-call.
setup=IDLE_LUA.split("set('SourceAnimationInit4086_Ready',0xb4ec)",1)[1].split(" if c.bad==",1)[0]
setup="set('SourceAnimationInit4086_Ready',0xb4ec)"+setup
setup=setup.replace("'SourceAnimationInit4086_Bank',59","'SourceAnimationInit4086_Bank',60").replace("'SourceUpdateFrame4086_Base',0x8000","'SourceUpdateFrame4086_Base',0x9000").replace("'SourceModelEntityCopy4086_Models',1","'SourceModelEntityCopy4086_Models',16").replace("'SourceModelAnimationCopy4086_Models',1","'SourceModelAnimationCopy4086_Models',16").replace("'SourceModelAnimationCopy4086_Bytes',8","'SourceModelAnimationCopy4086_Bytes',128")
LUA=CONTEXT_LUA.replace("set('SourceAnimationInit4086_Ready',0);set('SourceAnimationInit4086_State',0)",setup)
LUA=LUA.replace("put(v+4,c.alive)","put(v+4,c.alive);put(v+16,1,4);put(v+20,0,4)")
LUA=LUA.replace("put(0x416804+c.slot*64,1)","put(0x416804+c.slot*64,1);put(0x416830+c.slot*64,c.base,4);put(0x43900c+c.slot*80,77,4);for i=0,127 do emu.write(0x43c000+i,0,mt)end")
LUA=LUA.replace("set('SourceDefaultPlayer4086_Slot',c.slot)","set('SourceDefaultPlayer4086_Slot',c.slot);set('SourceDefaultPlayer4086_Jump',1);set('SourceRandom4086_Ready',0xb4d4);set('SourceRandom4086_Busy',0);put(sy.SourceRandom4086_SeedLo,c.seed,4);put(sy.SourceRandom4086_CallsLo,c.calls,4)")
LUA=LUA.replace("elseif c.bad=='empty'then","elseif c.bad=='rng'then set('SourceRandom4086_Ready',0)\n elseif c.bad=='rng_busy'then set('SourceRandom4086_Busy',1)\n elseif c.bad=='cache'then set('SourceModelAnimationCopy4086_Ready',0)\n elseif c.bad=='ai_table'then set('SourceAnimationInit4086_Base',0x8002)\n elseif c.bad=='empty'then")
LUA=LUA.replace("returned=emu.getState()['cpu.a']","""returned=emu.getState()['cpu.a']
 if c.fault==0 then
 local function expect(a,v)for i=0,3 do before[a+i]=(v>>(i*8))&255 end end
 expect(0x41400c+c.slot*80,c.expected_a)
 if c.air~=0 then expect(0x43900c+c.slot*80,5)end
 end
""")
LUA=LUA.replace("..returned)","..returned..'|'..(word(sy.SourceRandom4086_SeedLo)|(word(sy.SourceRandom4086_SeedHi)<<16))..'|'..(word(sy.SourceRandom4086_CallsLo)|(word(sy.SourceRandom4086_CallsHi)<<16)))")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--context',type=Path,required=True);p.add_argument('--source-values',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 cr=json.loads((a.context/'report.json').read_text());assert cr['status']=='PASS';bundle=bytearray((a.context/'bundle.bin').read_bytes());extra=bytearray(bundle[:32]);struct.pack_into('<H',extra,12,1);nobase=0x8000+len(bundle);bundle.extend(extra)
 bits=json.loads(a.source_values.read_text());assert len(bits)==10000
 base=dict(level=1,multiple=-1,platform=0,wall=0,bad='',fault=0,bank=59,type=2,subtype=0,camera=0,meta=0x8000,x=0,altitude=0,base=0,calls=0)
 rows=[]
 for slot,alive,stage,seed in itertools.product((0,127),(0,1),(1,2),(0,1,0xffffffff,0x80000000,1234567890,0x1234ffff)):
  rows.append(dict(base,slot=slot,alive=alive,stage=stage,meta=0x8000+(stage-1)*32,seed=seed))
 for slot,altitude,ground,x in itertools.product((0,127),(0,1,6553,6554,65536,-6554),(0,65536),(-30*65536,0,350*65536)):
  rows.append(dict(base,slot=slot,alive=1,stage=1,seed=1234567890,altitude=altitude,base=ground,x=x,calls=0xffffffff))
 for slot in(0,127):
  rows.append(dict(base,slot=slot,alive=1,stage=1,seed=0xffffffff,meta=nobase))
  for bad in('ready','sticky','world','pool','side','count','slot','core','entities','token','token_high','pending','life','life_sticky','life_marker','life_model','stage','environment','scroll','a_tag','x_tag','cache','ai_table','rng','rng_busy'):
   rows.append(dict(base,slot=slot,alive=1,stage=1,seed=1234567890,bad=bad,fault=1))
  for bad in('rng','rng_busy'):
   rows.append(dict(base,slot=slot,alive=1,stage=1,seed=1234567890,bad=bad,altitude=1))
 for c in rows:
  draw=not c['fault'] and c['meta']!=nobase and c['altitude']==0 and -30*65536<c['x']<350*65536
  ns,result=random32_step(c['seed']);c['draw']=int(draw);c['expected_seed']=ns if draw else c['seed'];c['expected_calls']=(c['calls']+int(draw))&0xffffffff;c['expected_a']=project(bits[result%10000])if draw else c['altitude'];c['air']=int(abs(c['expected_a']-c['base'])>=6554)
 ai=pack_ai(dict(maximum_animations=4,animations=[dict(handle=1,numframes=1,sync=-1,engine_animation_id=1)]));fe=pack_fe(dict(models=[],media=[],animations=[dict(handle=1,events=dict.fromkeys(ANIMATION_FIELDS,0),frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6)])]))
 sy=symbols(Path('src/main.sym'));bp=0x7ffd8a;kp=0x7ffd8c;lua=LUA.replace('AIBYTES',str(len(ai))).replace('FEBYTES',str(len(fe)))
 for k,v in dict(BASEPARAM=bp,BANKPARAM=kp,CAMERAX=sy['VmSourceWorld_AdvanceX'],SCROLLAXIS=sy['VmSourceWorld_ScrollAxis']).items():lua=lua.replace(k,str(v))
 lua=lua.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
 lua+="emu.addMemoryCallback(function()local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+6 end,emu.callbackType.exec,DROP,DROP,emu.cpuType.snes,mt)"
 wrapper=f"DropBodyFixture_Apply:\n.a16\n.i16\n lda.l {bp}\n tax\n lda.l {kp}\n tay\n jsl DROP\n rtl\n"
 r=Reporter('M4-DEFAULT-DROP-BODY',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'DropBodyFixture_Apply','SourceDefaultPlayer4086_Ready',0xb503,[(59,0,bytes(bundle)),(60,0,ai),(60,0x1000,fe)],lua,r,append=wrapper,bindings=dict(DROP='SourceDefaultEnemy4086_BeginHorizontalDrop'))
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('combined source RNG/table/altitude/action, absent-JUMP no-call, guards and context',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 2]and(c['fault']or v[4]==0)and v[5:]==[c['expected_seed'],c['expected_calls']]for i,(c,v)in enumerate(zip(rows,results))))
 report=dict(schema='BYOR_4086_DEFAULT_ENEMY_DROP_BODY_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),context_sha256=hashlib.sha256((a.context/'bundle.bin').read_bytes()).hexdigest(),source_values_sha256=hashlib.sha256(a.source_values.read_bytes()).hexdigest(),cases=len(rows),inputs=rows,results=results,actual_source_rng=True,altitude_expression_c_derived=True,numeric_policy='ACCEPTED_COMPAT_Q16_16',jump_frame_zero_proven=False,full_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
