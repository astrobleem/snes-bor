"""Native method-1 variable cleanup and shared animation program binding."""
import argparse,hashlib,itertools,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from script_callback_owner import derive,pack
from source_script_clone import derive as clone,pack as pack_clone
from m4_default_init_tail_native import LUA as TAIL_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols

LUA=TAIL_LUA.replace("local ranges={{0x40c000,12288},{0x414000,18432},{0x439000,10240}}","local ranges={{0x40c000,12288},{0x414000,18432},{0x439000,10240},{0x409000,8192},{0x418800,24576}}")
LUA=LUA.replace("set('SourceDefaultPlayer4086_Ready',0xb503)","""put(MODE,c.mode);local rel=0x409000+c.slot*64;for i=0,63 do emu.write(rel+i,0,mt)end;put(rel+44,c.oldmask,4)
 for i=0,24575 do emu.write(0x418800+i,0,mt)end
 for i=0,5 do local r=0x418800+i*64;put(r,i<4 and v or 0x414000+((c.slot+1)%128)*80,4);put(r+4,i%2+1);put(r+6,3);put(r+8,i%3==0 and 1 or i%3==1 and 2 or 5,4);put(r+12,0x12345678+i,4);for j=0,2 do emu.write(r+16+j,97+i,mt)end end
 put(0x416800+c.slot*64,c.model)
 set('SourceScriptClone4086_Ready',0xb5c1);set('SourceScriptClone4086_Status',0);set('SourceScriptClone4086_Slot',c.slot);set('SourceScriptClone4086_Model',c.model);set('SourceScriptClone4086_Base',0x8000);set('SourceScriptClone4086_Bank',59);set('SourceScriptClone4086_Bytes',CLONEBYTES);set('SourceScriptClone4086_Models',16)
 set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_Base',0x8000);set('SourceAnimationCallback4086_Bank',60);set('SourceAnimationCallback4086_Bytes',CALLBACKBYTES);set('SourceAnimationCallback4086_Models',16);set('SourceAnimationCallback4086_Programs',PROGRAMS)
 set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Count',384);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41)
 set('SourceDefaultPlayer4086_Ready',0xb503)""")
LUA=LUA.replace(" if c.bad=='ready'then set('SourceDefaultPlayer4086_Ready',0)",""" if c.bad=='ready'then set('SourceScriptClone4086_Ready',0)
 elseif c.bad=='clone_sticky'then set('SourceScriptClone4086_Status',3)
 elseif c.bad=='clone_slot'then set('SourceScriptClone4086_Slot',128)
 elseif c.bad=='models'then set('SourceScriptClone4086_Models',15)
 elseif c.bad=='model'then set('SourceScriptClone4086_Model',16)
 elseif c.bad=='table'then set('SourceScriptClone4086_Base',0x8002)
 elseif c.bad=='bank'then set('SourceScriptClone4086_Bank',0)
 elseif c.bad=='bytes'then set('SourceScriptClone4086_Bytes',CLONEBYTES-2)
 elseif c.bad=='vars'then set('VmSourceVars_Ready',0)
 elseif c.bad=='vars_count'then set('VmSourceVars_Count',385)
 elseif c.bad=='vars_base'then set('VmSourceVars_Base',0x8802)
 elseif c.bad=='vars_bank'then set('VmSourceVars_Bank',0x40)
 elseif c.bad=='callback'then set('SourceAnimationCallback4086_Ready',0)
 elseif c.bad=='callback_models'then set('SourceAnimationCallback4086_Models',15)
 elseif c.bad=='callback_program'then set('SourceAnimationCallback4086_Base',0x8010)
 elseif c.bad=='old_wide'then put(rel+46,1)
 elseif c.bad=='clear_entry'then put(rel+48,1,4)
 elseif c.bad=='onkill'then put(rel+52,1,4)
 elseif c.bad=='side_model'then put(0x416800+c.slot*64,(c.model+1)%16)
""")
LUA=LUA.replace("if c.fault==0 and c.level~=0 and c.multiple<0 then for i=0,3 do before[0x40c000+c.slot*96+i]=0 end end","""if c.fault==0 then
 local mask=c.mode==0 and 0 or c.mask;for j=0,3 do before[0x40902c+c.slot*64+j]=(mask>>(j*8))&255 end
 if c.mode==0 then for i=0,3 do for j=0,7 do before[0x418808+i*64+j]=0 end end end
 end""")
LUA=LUA.replace("..word(sy.SourceDefaultPlayer4086_Status)..'|'..word(sy.SourceEmptyInitEnvironment4086_Status))","..word(sy.SourceScriptClone4086_Status))")

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--model-copy',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);source=Source(a.source);cr=clone(source);ct=pack_clone(cr);cb,*_=derive(source);bt=pack(cb)
 base=dict(level=1,alive=1,multiple=0,platform=0,wall=0,bad='',fault=0)
 rows=[]
 for slot,m,old in itertools.product((0,1,127),cr['models'],(0,1)):
  rows.append(dict(base,slot=slot,model=m['id'],mask=m['initialized_mask'],mode=0,oldmask=old))
 if old==0:rows.append(dict(base,slot=slot,model=m['id'],mask=m['initialized_mask'],mode=1,oldmask=0))
 if a.model_copy:
  rows=[dict(base,slot=slot,model=m['id'],mask=m['initialized_mask'],mode=mode,oldmask=old)for slot,m,old,mode in itertools.product((0,1,127),cr['models'],(0,1),(0,1))]
 for mode,slot in itertools.product((0,1),(0,127)):
  for bad in('ready','clone_sticky','world','pool','side','count','clone_slot','token','token_high','models','model','table','bank','bytes','vars','vars_count','vars_base','vars_bank','callback','callback_models','old_wide','clear_entry','onkill'):
   rows.append(dict(rows[0],mode=mode,slot=slot,bad=bad,fault=1))
  rows.append(dict(rows[0],mode=mode,slot=slot,oldmask=2,fault=1))
  if mode==1:
   if not a.model_copy:rows.append(dict(rows[0],mode=1,slot=slot,oldmask=1,fault=1))
   for bad in('side_model','callback_program'):rows.append(dict(rows[0],mode=1,slot=slot,model=3,mask=1,bad=bad,fault=1))
 sy=symbols(Path('src/main.sym'));lua=LUA.replace('MODE',str(0x7ffd88)).replace('CLONEBYTES',str(len(ct))).replace('CALLBACKBYTES',str(len(bt))).replace('PROGRAMS',str(cb['program_count']))
 lua=lua.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
 for label in('SourceScriptClone4086_Clear','SourceScriptClone4086_Bind'):
  lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};ctx=0;for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{sy[label]},{sy[label]},emu.cpuType.snes,mt)\n"
 options={};apply='SourceScriptClone4086_Clear'
 if a.model_copy:
  from source_script_model_copy_native import emit
  lua=lua.replace('local mask=c.mode==0 and 0 or c.mask','local mask=c.mode==0 and 0 or(c.mask~=0 and c.mask or c.oldmask)')
  lua=lua.replace(' if c.mode==0 then for i=0,3 do for j=0,7 do before[0x418808+i*64+j]=0 end end end','')
  # Observe the compiled method-0 wrapper's complete CPU context.
  lua+="emu.addMemoryCallback(function()local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)\n"
  assembly='''
ModelScriptProbe:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l $7FFD88
 beq ModelScriptProbe_Clear
 jsl ModelScriptCopy_Copy0
 bra ModelScriptProbe_Return
ModelScriptProbe_Clear:
.a16
.i16
 jsl ModelScriptCopy_Clear0
ModelScriptProbe_Return:
.a16
.i16
 bcs ModelScriptProbe_Bad
 ply
 plx
 plp
 clc
 rtl
ModelScriptProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''+emit(sy)
  apply='ModelScriptProbe';options=dict(append=assembly,link_pcm=False)
 else:options=dict(finish='SourceScriptClone4086_Bind',link_pcm=False)
 r=Reporter('M4-SCRIPT-CLONE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,apply,'SourceScriptClone4086_Ready',0xb5c1,[(59,0,ct),(60,0,bt)],lua,r,batch_size=4,**options)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('all authored model instances, retained names/scopes, foreign owner values, paired program identity, guards and CPU context',results==[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)])
 d=dict(schema='BYOR_4086_SCRIPT_CLONE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,script_table_sha256=hashlib.sha256(ct).hexdigest(),callback_table_sha256=hashlib.sha256(bt).hexdigest(),no_init_or_clear_entries=cr,model_script_copy_bound=a.model_copy,named_values_retained=a.model_copy,full_constructor_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
