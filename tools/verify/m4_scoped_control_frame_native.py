"""Join scoped control snapshots to the actual native frame continuation owner."""
import argparse,json,re,sys
from pathlib import Path
from unittest.mock import patch
import m4_frame_stack_native as parent
from actor_s5_entity_fixture import symbols
from source_scoped_control_stack import layout,emit_frame_owner
from source_foreign_water_retirement import emit as water,transform as retire_water
from m4_animation_init_native import luav


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--self-context',action='store_true');a=p.parse_args();a.output=a.output.resolve();plan=layout();sy=symbols(Path('src/main.sym'));original=Path.write_text;original_bytes=Path.write_bytes;w=plan['controls'];base=plan['base'];stride=plan['stride']
 def write(path,text,*args,**kwargs):
  if path.parent==a.output and path.name=='fixture.pasm':
   for op in ('Push','Pop'):
    anchor=' jsl '+str(sy['SourceFrameStack4086_'+op]);assert text.count(anchor)==1
    text=text.replace(anchor,' jsl ScopedFrameStack4086_'+op)
   text+='\n'+emit_frame_owner(plan,sy,Path('src/core/vm/vm_source_frame_stack.pasm'))+water(sy)
  if path.parent==a.output and path.name=='observer.lua':
   fs=symbols(a.output/'fixture.sym')
   for op in ('Push','Pop'):text=re.sub(r'\b'+str(sy['SourceFrameStack4086_'+op])+r'\b',str(fs['ScopedFrameStack4086_'+op]),text)
   text='local scopedExtra='+luav({k:v for k,v in sy.items()if k.startswith(('StageFp_','StreamScrollFp_'))or k=='DmaQueue'})+'\n'+'local scopedPlan='+luav(plan)+f'\nlocal W={w};local BASE={base};local STRIDE={stride};local foreignReady={sy["SourceForeignWork_Ready"]};local foreignGeneration={sy["SourceForeignWork_Generation"]}\n'+text
   text=text.replace('local ranges=', 'for k,v in pairs(scopedExtra)do sy[k]=v end\nlocal ranges=',1)
   anchor='if self_context then ranges[#ranges+1]={0x7ffe38,4}end';assert text.count(anchor)==1
   text=text.replace(anchor,anchor+'\nranges[#ranges+1]={0x420000,0xb500};ranges[#ranges+1]={0x42b500,1600};ranges[#ranges+1]={0x7fa000,6400};ranges[#ranges+1]={0x42bb40,0x10c0};ranges[#ranges+1]={0x7ffaec,52}\n')
   anchor='r[1]==0x40f000 or r[1]==0x43fd00';assert text.count(anchor)==1
   text=text.replace(anchor,anchor+' or r[1]==0x420000')
   anchor=' before={};for _,r in ipairs(ranges)';assert text.count(anchor)==1
   setup='''
 for _,r in ipairs(scopedPlan.regions)do for i=0,r.bytes-1 do emu.write(r.address+i,(i*53+c.seed)&255,mt)end end
 if c.chain~=1 or c.step==0 then for d=0,7 do put(BASE+d*STRIDE,c.mode==0 and 0 or 0xb6af);put(BASE+d*STRIDE+2,d);put(BASE+d*STRIDE+4,1);put(BASE+d*STRIDE+6,0);put(BASE+d*STRIDE+8,STRIDE)end end
 put(W,0xb6ae);put(W+8,1);put(W+10,0);put(W+16,BASE&65535);put(W+18,0x42);put(W+20,scopedPlan.chr_capacity);put(W+22,8);put(W+24,STRIDE)
 put(foreignReady,0xb671);put(foreignGeneration,1);put(foreignGeneration+2,0)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do put(sy[n],0)end
 for i=0,7 do emu.write(sy.DmaQueue+8*i+7,0,mt)end

'''
   text=text.replace(anchor,setup+anchor)
   anchor=' local mismatch=0;';assert text.count(anchor)==1
   adjust='''
 if c.fault==0 then
  local row=BASE+STRIDE*(c.mode==0 and c.depth or c.depth-1)
  for _,r in ipairs(scopedPlan.regions)do for i=0,r.bytes-1 do if c.mode==0 then before[row+r.offset+i]=before[r.address+i]else before[r.address+i]=before[row+r.offset+i]end end end
  if c.mode==0 then
   before[row]=0xaf;before[row+1]=0xb6;before[row+2]=c.depth;before[row+3]=0;before[row+4]=1;before[row+5]=0;before[row+6]=0;before[row+7]=0;before[row+8]=STRIDE&255;before[row+9]=STRIDE>>8
  else before[row]=0;before[row+1]=0 end
 end
'''
   text=text.replace(anchor,adjust+anchor)
  return original(path,text,*args,**kwargs)
 def write_bytes(path,data):
  if path.parent==a.output and path.name=='bor.sfc':
   data=bytearray(data);retire_water(data,{**sy,**symbols(a.output/'fixture.sym')})
  return original_bytes(path,data)
 args=['m4_frame_stack_native.py','--rom',str(a.rom),'--output',str(a.output)]+(['--self-context']if a.self_context else [])
 with patch.object(Path,'write_text',write),patch.object(Path,'write_bytes',write_bytes),patch.object(sys,'argv',args):
  try:parent.main()
  except SystemExit as e:
   if e.code not in (None,0):raise
 assert (a.output/'bor.sfc').read_bytes()[:32768]==a.rom.read_bytes()[:32768]
 path=a.output/'report.json';r=json.loads(path.read_text());r.update(schema='BYOR_SCOPED_CONTROL_FRAME_OWNER_JOIN_V1',layout=plan,frame_owner_hook_bound=True,bank_zero_unchanged=True,production_memory_owner_bound=False,root_constructor_scope_bound=False,peak_master_clocks=max(v[1]for v in r['cpu_costs']));path.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
