"""Actual model-copy hook: optional-off baseline, scalar install and preflight."""
import argparse,hashlib,json,struct
from pathlib import Path
from m4_attack_timing_native import LUA as TIMING_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from compiler import Source
from source_attack_timing_4086 import derive,pack
from source_model_core_4086 import derive as derive_core,CACHED_FIELDS,FLOAT_FIELDS
from m4_animation_init_native import luav

ASM='''
TimingModelProbe:
.a16
.i16
 jsl LOADTIMING
TimingModelProbe_LoadAfter:
.a16
.i16
 nop
 bcc TimingModelProbe_Apply
 sec
 rtl
TimingModelProbe_Apply:
.a16
.i16
 lda.l MODE
 beq TimingModelProbe_Off
 cmp #1
 beq TimingModelProbe_Copy
 cmp #2
 bne TimingModelProbe_Busy
 lda #$B604
 sta.l TIMINGREADY
 bra TimingModelProbe_Copy
TimingModelProbe_Busy:
.a16
.i16
 lda #0
 sta.l TIMINGSTATUS
 bra TimingModelProbe_Copy
TimingModelProbe_Off:
.a16
.i16
 lda #0
 sta.l TIMINGREADY
TimingModelProbe_Copy:
.a16
.i16
 jsl COPYTIMING
TimingModelProbe_CopyAfter:
.a16
.i16
 nop
 rtl
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--attack-body',action='store_true')
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';source=Source(a.source)
 real=pack(derive(source));synthetic=real[:28]+b''.join(struct.pack('<iII',*v)for v in authority['actual'][16:32]);core=bytearray()
 for m in derive_core(source)['models']:
  f=m['fields'];core.extend(b''.join(struct.pack('<f'if k in FLOAT_FIELDS else'<i',f[k])for k in CACHED_FIELDS)+struct.pack('<i',f['type']))
 assert len(core)==2560
 rows=[]
 for which in (0,1):
  for model in range(16):
   slot=((0,1,95,96,127)if a.attack_body else(0,1,63,127))[model%(5 if a.attack_body else 4)];key=which*16+model
   for mode in (0,1):rows.append(dict(slot=slot,model=model,synthetic=which,mode=mode,key=key,bad='',fault=0,loaded=True,patch=-1,value=0))
 for mode in (2,3):rows.append(dict(rows[0],mode=mode,fault=1))
 setup=r'''
 put(MODE,c.mode)
 for j,value in ipairs(corebytes)do emu.write(0x40b000+j-1,value,mt)end
 for _,r in ipairs({{0x414000,18432},{0x40c000,12288}})do for j=0,r[2]-1 do emu.write(r[1]+j,0,mt)end end
 local view=0x414000+c.slot*80;put(view,view,4);put(view+4,1,4);put(view+32,1,4);put(view+36,250,4);put(view+64,1,4);put(view+68,250,4);put(0x40c04c+c.slot*96,250,4)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Count',128)
 set('SourceLifecycle4086_Ready',0);set('SourceModelAttackPolicy4086_Ready',0);set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Status',0);set('SourceModelEntityCopy4086_Entities',128);set('SourceModelEntityCopy4086_Models',16);set('SourceModelEntityCopy4086_Slot',c.slot);set('SourceModelEntityCopy4086_Model',c.model)
'''
 lua='local corebytes='+luav(list(core))+'\nlocal baselines={}\n'+TIMING_LUA.replace(' before={};',setup+' before={};').replace('{{0x40bd00,204}','{{0x40b000,2560},{0x40bd00,204}')
 start=lua.index(' if c.fault==0 then local base=0x438800')
 end=lua.index(' local changed=0;',start)
 lua=lua[:start]+r'''
 if c.fault==0 then
  local ranges={{0x414000+c.slot*80,80},{0x416800+c.slot*64,64},{0x40c000+c.slot*96,96}}
  if c.mode==0 then baselines[c.key]={};for _,r in ipairs(ranges)do for j=0,r[2]-1 do local addr=r[1]+j;baselines[c.key][addr]=emu.read(addr,mt);before[addr]=emu.read(addr,mt)end end
  else for addr,v in pairs(baselines[c.key])do before[addr]=v end
   local base=0x438800+c.slot*14;for j=0,11 do before[base+j]=data[29+c.model*12+j]end;before[base+12]=3;before[base+13]=0xb6
  end
 end
'''+lua[end:]
 lua=lua.replace("..word(sy.SourceAttackTiming4086_Models))","..word(sy.SourceAttackTiming4086_Models)..'|'..word(sy.SourceModelEntityCopy4086_Status))")
 from _source_leaf_fixture import REQUEST
 from actor_s5_entity_fixture import symbols
 sy=symbols(Path('src/main.sym'));mode=REQUEST+14;asm=ASM.replace('MODE',str(mode)).replace('TIMINGREADY',str(sy['SourceAttackTiming4086_Ready'])).replace('TIMINGSTATUS',str(sy['SourceAttackTiming4086_Status']))
 tables=[(59,0,real)]
 if a.attack_body:
  from source_attack_body_profile import derive as body_profile,pack_runtime
  body=pack_runtime(body_profile(source));tables.append((60,0,body))
  lua='local bodybytes='+luav(list(body))+'\n'+lua
  lua=lua.replace(' before={};'," set('SourceAttackBody4086_Ready',c.mode==0 and 0 or 0xb605);set('SourceAttackBody4086_Status',0);set('SourceAttackBody4086_Bank',60);set('SourceAttackBody4086_Base',0x8000);set('SourceAttackBody4086_Bytes',160);for _,r in ipairs({{0x435980,1056},{0x40bdcc,352}})do for j=0,r[2]-1 do emu.write(r[1]+j,0xa5,mt)end end\n before={};")
  lua=lua.replace('{{0x40b000,2560}', '{{0x435800,1536},{0x40bdcc,352},{0x40b000,2560}')
  lua=lua.replace('  else for addr,v in pairs(baselines[c.key])do before[addr]=v end', '  else for addr,v in pairs(baselines[c.key])do before[addr]=v end\n   local b=c.slot<96 and 0x435980+c.slot*11 or 0x40bdcc+(c.slot-96)*11;for j=0,8 do before[b+j]=bodybytes[17+c.model*9+j]end;before[b+9]=5;before[b+10]=0xb6')
  asm=asm.replace(' sta.l '+str(sy['SourceAttackTiming4086_Ready'])+'\n bra TimingModelProbe_Copy\nTimingModelProbe_Busy:', ' sta.l '+str(sy['SourceAttackBody4086_Ready'])+'\n bra TimingModelProbe_Copy\nTimingModelProbe_Busy:')
  asm=asm.replace(' lda #0\n sta.l '+str(sy['SourceAttackTiming4086_Status']), ' lda #1\n sta.l '+str(sy['SourceAttackBody4086_Status']))
 else:lua=lua.replace(' before={};'," set('SourceAttackBody4086_Ready',0)\n before={};")
 lua='local tables='+luav([list(real),list(synthetic)])+'\n'+lua.replace('TABLEBYTES',str(len(real))).replace('SLOT',str(REQUEST+10)).replace('MODEL',str(REQUEST+12)).replace('MODE',str(mode))
 reporter=Reporter('M4-ATTACK-TIMING-MODEL-COPY',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'TimingModelProbe','SourceAttackTiming4086_Ready',0xb603,tables,lua,reporter,append=asm,bindings=dict(LOADTIMING='SourceAttackTiming4086_Load',COPYTIMING='SourceModelEntityCopy4086_Apply'),probes=dict(LOADAFTER='TimingModelProbe_LoadAfter',COPYAFTER='TimingModelProbe_CopyAfter'),batch_size=1,frame_limit=6000)
 actual=[list(map(int,l.split('TIMINGSCALARS|',1)[1].split('|')))for l in log.splitlines()if 'TIMINGSCALARS|'in l];expected=[[i,0,0,0,0 if c['mode']==3 and not a.attack_body else 2,16,2 if c['fault']else 1]for i,c in enumerate(rows)];failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('actual model-copy hook preserves optional-off core/view/side results, copies C-derived timing, retains siblings/sentinel/VM/engine+CRT RNG/CPU, and rejects before core writes',len(actual)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_ATTACK_TIMING_MODEL_COPY_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),actual_model_copy_hook_bound=True,attack_body_model_copy_hook_bound=a.attack_body,actual_birth_constructors_proven=False,optional_off_results_unchanged=True,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
