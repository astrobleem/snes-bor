"""Native current-stage horizontal drop eligibility, before RNG/entity writes."""
import argparse,hashlib,itertools,json,struct,sys
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_default_init_tail_native import LUA as TAIL_LUA
from actor_s5_entity_fixture import symbols

LUA=TAIL_LUA.replace('local before,cpu,ctx','local returned=0\nlocal before,cpu,ctx')
LUA=LUA.replace("put(v+4,c.alive)","put(v+4,c.alive);put(v+8,2,4);put(v+12,c.altitude,4);put(v+48,2,4);put(v+52,c.x,4)")
LUA=LUA.replace("put(0x416804+c.slot*64,1)","put(0x416804+c.slot*64,1);put(0x416800+c.slot*64,0);put(0x439048+c.slot*80,0);put(0x43904a+c.slot*80,0xb4fb);put(0x439030+c.slot*80,c.subtype,4);set('SourceLifecycle4086_Ready',0xb4fb);set('SourceLifecycle4086_Status',2)")
LUA=LUA.replace("put(b+8,c.platform,4)","put(b+8,c.platform,4);put(b+72,c.type,4)")
LUA=LUA.replace("set('SourceEnvironment4086_Stage',1)","set('SourceEnvironment4086_Stage',c.stage);put(CAMERAX,c.camera*65536,4);put(SCROLLAXIS,0);put(BASEPARAM,c.meta);put(BANKPARAM,c.bank)")
LUA=LUA.replace("elseif c.bad=='empty'then", "elseif c.bad=='life'then set('SourceLifecycle4086_Ready',0)\n elseif c.bad=='life_sticky'then set('SourceLifecycle4086_Status',3)\n elseif c.bad=='life_marker'then put(0x43904a+c.slot*80,0)\n elseif c.bad=='life_model'then put(0x439048+c.slot*80,1)\n elseif c.bad=='model_domain'then put(0x439048+c.slot*80,16);put(0x416800+c.slot*64,16)\n elseif c.bad=='stage'then set('SourceEnvironment4086_Stage',3)\n elseif c.bad=='environment'then set('SourceEnvironment4086_Ready',0)\n elseif c.bad=='scroll'then put(SCROLLAXIS,1)\n elseif c.bad=='models'then set('SourceModelEntityCopy4086_Models',15)\n elseif c.bad=='paired_models'then set('VmSourceWorld_TemplateCount',15)\n elseif c.bad=='a_tag'then put(v+8,1)\n elseif c.bad=='a_reserved'then put(v+10,1)\n elseif c.bad=='x_tag'then put(v+48,1)\n elseif c.bad=='x_reserved'then put(v+50,1)\n elseif c.bad=='fractional_camera'then put(CAMERAX,1)\n elseif c.bad=='wide_type'then put(b+72,65538,4)\n elseif c.bad=='empty'then")
LUA=LUA.replace("if c.fault==0 and c.level~=0 and c.multiple<0 then for i=0,3 do before[0x40c000+c.slot*96+i]=0 end end", "returned=emu.getState()['cpu.a']")
LUA=LUA.replace("..word(sy.SourceEmptyInitEnvironment4086_Status))","..returned)")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--context',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 report=json.loads((a.context/'report.json').read_text());assert report['status']=='PASS';bundle=bytearray((a.context/'bundle.bin').read_bytes());assert len(report['stages'])==2 and len(bundle)<32768
 # An alternate readonly context exercises the source global nodropspawn flag.
 tablebase=report['table_address']&65535;extra=bytearray(bundle[:32]);struct.pack_into('<H',extra,12,1);nobase=0x8000+len(bundle);bundle.extend(extra)
 base=dict(level=1,multiple=-1,platform=0,wall=0,bad='',fault=0,bank=59,type=2,subtype=0)
 rows=[]
 for slot,alive,stage,offset,camera,altitude in itertools.product((0,127),(0,1),(1,2),(-31*65536,-30*65536,-30*65536+1,0,349*65536+65535,350*65536,351*65536),(0,256),(0,65536)):
  rows.append(dict(base,slot=slot,alive=alive,stage=stage,meta=0x8000+(stage-1)*32,camera=camera,x=camera*65536+offset,altitude=altitude,expected=int(altitude==0 and -30*65536<offset<350*65536)))
 rows.extend(dict(rows[0],slot=s,meta=nobase,stage=1,x=0,altitude=0,expected=0,bad='fractional_camera')for s in(0,127))
 rows.extend(dict(rows[0],slot=s,altitude=1,x=0,expected=0,bad='fractional_camera')for s in(0,127))
 for bad in('ready','sticky','world','pool','side','count','slot','core','entities','token','token_high','pending','life','life_sticky','life_marker','life_model','model_domain','stage','environment','scroll','models','paired_models','a_tag','a_reserved','x_tag','x_reserved','fractional_camera','wide_type'):
  for slot in(0,127):rows.append(dict(rows[0],slot=slot,x=0,altitude=0,bad=bad,fault=1))
 for slot,subtype in itertools.product((0,127),(1,3)):rows.append(dict(rows[0],slot=slot,subtype=subtype,fault=1))
 for slot,meta,bank in((0,0x7fff,59),(127,0xffe1,59),(0,0x8000,0),(127,0x8000,64),(0,tablebase,59)):
  rows.append(dict(rows[0],slot=slot,meta=meta,bank=bank,fault=1))
 for typ in(0,1,3,512):rows.append(dict(rows[0],type=typ,x=0,altitude=0,expected=1,fault=int(typ!=512)))
 for camera in(-32739,32418):rows.append(dict(rows[0],camera=camera,x=0,altitude=0,fault=1))
 sy=symbols(Path('src/main.sym'));baseparam=0x7ffd8a;bankparam=0x7ffd8c;lua=LUA
 for k,v in dict(BASEPARAM=baseparam,BANKPARAM=bankparam,CAMERAX=sy['VmSourceWorld_AdvanceX'],SCROLLAXIS=sy['VmSourceWorld_ScrollAxis']).items():lua=lua.replace(k,str(v))
 wrapper='''
DropContextFixture_Apply:
.a16
.i16
 lda.l BASEPARAM
 tax
 lda.l BANKPARAM
 tay
 jsl CHOOSE
 rtl
'''.replace('BASEPARAM',str(baseparam)).replace('BANKPARAM',str(bankparam))
 # The wrapper loads input registers, so guard context at the real leaf entry
 # and compare after the wrapper returns (two JSL return addresses).
 lua=lua.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end", "")
 lua+='''
emu.addMemoryCallback(function()local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+6 end,emu.callbackType.exec,CHOOSE,CHOOSE,emu.cpuType.snes,mt)
'''
 r=Reporter('M4-DEFAULT-DROP-CONTEXT',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'DropContextFixture_Apply','SourceDefaultPlayer4086_Ready',0xb5dc,[(59,0,bytes(bundle))],lua,r,append=wrapper,bindings=dict(CHOOSE='SourceDefaultEnemy4086_ChooseHorizontalDrop'))
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('source-sized strict bounds, paired stage/model context, inactive branch skips camera; guards and no entity writes',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 2]and(c['fault']or v[4]==c['expected'])for i,(c,v)in enumerate(zip(rows,results))))
 out=dict(schema='BYOR_4086_HORIZONTAL_DEFAULT_DROP_CONTEXT_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),context_sha256=hashlib.sha256((a.context/'bundle.bin').read_bytes()).hexdigest(),cases=len(rows),inputs=rows,results=results,source_width=320,source_height=240,random_draw_performed=False,drop_owner_bound=False,world_stage_owner_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(out,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
