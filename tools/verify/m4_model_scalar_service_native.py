"""Source model alpha/style installation, retained dynamics and canvas lease."""
import argparse,hashlib,itertools,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_model_scalar_service_native import derive,emit
from source_foreign_state_layout import layout
from m4_model_palette_service_native import LUA as PALETTE_LUA
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols

LUA=PALETTE_LUA.replace('local ranges={{0x433800','local ranges={{STYLES,512},{0x433800')
LUA=LUA.replace("set('SourceModelTransition4086_Service',6)","set('SourceModelTransition4086_Service',2)").replace("set('SourceModelTransition4086_Service',3)","set('SourceModelTransition4086_Service',6)").replace("set('SourceModelTransition4086_Acknowledged',6)","set('SourceModelTransition4086_Acknowledged',2)")
LUA=LUA.replace(" if c.bad=='transition_ready'then", """
 set('SourceModelEntityCopy4086_Status',1);set('SourceModelEntityCopy4086_Slot',c.slot);set('SourceModelEntityCopy4086_Model',c.model);set('SourceModelEntityCopy4086_Entity',0xc000+c.slot*96);set('SourceModelEntityCopy4086_View',0x4000+c.slot*80)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4);put(0x7ffd8a,c.generation,4)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,name in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do put(sy[name],0)end
 for i=0,7 do put(sy.DmaQueue+i*8+4,0)end
 if c.bad=='copy_status'then set('SourceModelEntityCopy4086_Status',0)
 elseif c.bad=='copy_slot'then set('SourceModelEntityCopy4086_Slot',(c.slot+1)%128)
 elseif c.bad=='copy_model'then set('SourceModelEntityCopy4086_Model',(c.model+1)%16)
 elseif c.bad=='copy_core'then set('SourceModelEntityCopy4086_Entity',0xc002+c.slot*96)
 elseif c.bad=='copy_view'then set('SourceModelEntityCopy4086_View',0x4002+c.slot*80)
 elseif c.bad=='foreign_ready'then set('SourceForeignWork_Ready',0)
 elseif c.bad=='foreign_generation'then put(sy.SourceForeignWork_Generation,2,4)
 elseif c.bad=='foreign_high'then put(sy.SourceForeignWork_Generation+2,1)
 elseif c.bad=='foreign_zero'then put(sy.SourceForeignWork_Generation,0,4);put(0x7ffd8a,0,4)
 elseif c.bad=='canvas_ready'then put(0x7ff840,0)
 elseif c.bad=='canvas_owner'then put(0x7ff862,0)
 elseif c.bad=='canvas_busy'then put(0x7ff856,1)
 elseif c.bad=='water_owner'then put(0x7ff866,0)
 elseif c.bad=='canvas_target'then put(0x7ff846,0x7f)
 elseif c.bad=='frontpanel'then put(sy.StageFp_BG2Active,1)
 elseif c.bad=='queue_overlay'then put(sy.DmaQueue,2);put(sy.DmaQueue+4,DMAACTIVE);put(sy.DmaQueue+5,0xa000);put(sy.DmaQueue+7,0x7f,1)
 elseif c.bad=='transition_ready'then""")
start=LUA.index(' if c.fault==0 then');end=LUA.index(' local s=emu.getState()',start)
LUA=LUA[:start]+""" if c.fault==0 then
 before[0x41681e+c.slot*64]=c.alpha;before[0x41681f+c.slot*64]=0
 for j=0,3 do before[STYLES+c.slot*4+j]=(c.style>>(j*8))&255 end
 end
"""+LUA[end:]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);report=derive(Source(a.source));sy=symbols(Path('src/main.sym'));styles=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='entity_combostyle')
 base=dict(level=1,alive=1,multiple=0,platform=0,wall=0,bad='',fault=0,map=0,generation=1)
 rows=[dict(base,slot=slot,model=m['id'],alpha=m['alpha'],style=m['combostyle'])for slot,m in itertools.product((0,1,127),report['models'])]
 guards=('transition_ready','transition_state','transition_service','transition_ack','transition_slot','transition_side','transition_core','transition_model','side_model','template','copy_models','ctor_ready','ctor_models','row_lease','token','token_high','world','pool','side','count','core','entities','copy_status','copy_slot','copy_model','copy_core','copy_view','foreign_ready','foreign_generation','foreign_high','foreign_zero','canvas_ready','canvas_owner','canvas_busy','water_owner','canvas_target','frontpanel','queue_overlay')
 rows.extend(dict(rows[0],slot=slot,bad=bad,fault=1)for slot,bad in itertools.product((0,127),guards))
 lua=LUA.replace('STYLES',str(styles)).replace('DMAACTIVE',str(sy['DMA_OPT_ACTIVE']));extra={k:sy[k]for k in('SourceForeignWork_Ready','SourceForeignWork_Generation','StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled','DmaQueue')};lua='local extra='+luav(extra)+'\nfor k,v in pairs(extra)do sy[k]=v end\n'+lua
 lua=lua.replace("local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end",'')
 lua+="emu.addMemoryCallback(function()local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)\n"
 wrapper='''
ModelScalarProbe:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l $7FFD8A
 tax
 lda.l $7FFD8C
 tay
 jsl ModelScalarService_Apply2
 bcs ModelScalarProbe_Bad
 ply
 plx
 plp
 clc
 rtl
ModelScalarProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
 r=Reporter('M4-MODEL-SCALAR-SERVICE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'ModelScalarProbe','SourceModelTransition4086_Ready',0xb4f0,[],lua,r,batch_size=4,append=wrapper+emit(report,styles,sy),link_pcm=False)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('authored alpha/style and intact dynamics/identity/controller rows/CPU context',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 1]and(c['fault']or v[4:]==[3,0])for i,(v,c)in enumerate(zip(results,rows))))
 r.check('stale requests never acknowledge',len(results)==len(rows)and all(not c['fault']or v[5]==(2 if c['bad']=='transition_ack'else 0)for v,c in zip(results,rows)))
 d=dict(schema='BYOR_4086_MODEL_SCALAR_SERVICE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,model_scalars=report,completed_copy_request_installed_by_fixture=True,canvas_lease_installed_by_fixture=True,real_canvas_generation_check=True,real_transition_ack=True,full_transition_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
