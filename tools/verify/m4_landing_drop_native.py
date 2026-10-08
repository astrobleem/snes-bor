"""Native zero-drop landing callback component against actual pinned C."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from source_damage_inputs_4086 import pack
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def bits(n):return struct.unpack('<I',struct.pack('<f',n))[0]

LUA=r'''
local mt=emu.memType.snesMemory;local before={}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 local slot=c.slot%128;local life=0x439000+slot*80;local side=0x416800+slot*64;local combat=0x437e00+slot*20;local damage=0x7fb900+slot*12
 put(DROPREADY,0xb62e);put(DROPSLOT,c.slot);put(DROPSTATUS,0)
 put(sy.SourceLifecycle4086_Ready,0xb4fb);put(0x7fbf00,0xb62b);put(sy.SourceFactors4086_Ready,0xb5f1)
 put(sy.VmSourceWorld_Time,c.time,4);put(DROPBASE,0x8000);put(DROPBANK,0x3a);put(DROPBYTES,TABLEBYTES);put(DROPMODELS,2)
 put(life+64,c.model_bits,4);put(life+72,c.animal);put(life+74,0xb4fb);put(side,c.animal)
 put(0x43b900+slot*4,c.animal);put(0x43b902+slot*4,0xb5f1);put(0x432808+slot*32,0x3f800000,4)
 put(combat,c.drop,4);put(combat+16,0xb5fb);put(combat+18,0)
 put(damage,c.bits,4);put(damage+4,c.deadline,4);put(damage+8,0x13579bdf,4)
 local changes={ready={DROPREADY,0},state_ready={0x7fbf00,0},life_ready={sy.SourceLifecycle4086_Ready,0},factor_ready={sy.SourceFactors4086_Ready,0},life_marker={life+74,0},life_model={life+72,2},side_model={side,2},factor_marker={0x43b902+slot*4,0},factor_model={0x43b900+slot*4,2},factor_low={0x432808+slot*32,1},factor_high={0x43280a+slot*32,0},combat_marker={combat+16,0},combat_reserved={combat+18,1},table_bank={DROPBANK,0x40},table_base={DROPBASE,0x7fff},table_bytes={DROPBYTES,TABLEBYTES-1},table_models={DROPMODELS,0},model_range={life+72,2},current_nan={damage+2,0x7fc0},model_nan={life+66,0x7fc0}}
 if c.bad and changes[c.bad]then local r=changes[c.bad];put(r[1],r[2])end
 if c.bad=='model_range'then put(side,2);put(0x43b900+slot*4,2)end
 before={};local ranges={{0x7fb8f0,1552},{0x7fbf06,14},{0x7fbf2e,226},{0x437e00,2560},{life,80},{side,64},{0x432800+slot*32,32},{0x43b900+slot*4,4}}
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local damage=0x7fb900+(c.slot%128)*12;local combat=0x437e00+(c.slot%128)*20
 if c.fault==0 then
  for _,r in ipairs({{damage,c.expected_bits},{damage+4,c.expected_deadline},{combat,c.expected_drop}})do for i=0,3 do before[r[1]+i]=(r[2]>>(8*i))&255 end end
 end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('LANDDROP|'..word(INDEX)..'|'..n..'|'..word(DROPSTATUS))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
    rows=[]
    for c in authority['results']:
        r=c['case']
        if r['mode']!=1:continue
        for slot in(0,63,127):
            rows.append(dict(slot=slot,animal=r['animal'],drop=r['drop'],bits=bits(r['count']),model_bits=bits(r['model_count']),deadline=r['deadline'],time=48,fault=0,
                             expected_drop=c['expected'][0],expected_bits=bits(c['expected'][9]),expected_deadline=c['expected'][10]))
    seed=next(r for r in rows if r['animal']==0 and r['drop']==0 and r['deadline']==47)
    for slot in(0,63,127):
        for b in(0x80000000,0,1,0x80000001,0x7f7fffff,0xff7fffff):
            rows.append(dict(seed,slot=slot,bits=b,deadline=48,expected_bits=b,expected_deadline=248,expected_drop=int(b&0x80000000!=0 and b&0x7fffffff!=0)))
        for time in(65530,0xffffffff):
            rows.append(dict(seed,slot=slot,bits=bits(3.),deadline=0,expected_bits=bits(3.),time=time,expected_deadline=(time+200)&0xffffffff,expected_drop=0))
    for bad in('ready','state_ready','life_ready','factor_ready','life_marker','life_model','side_model','factor_marker','factor_model','factor_low','factor_high','combat_marker','combat_reserved','table_bank','table_base','table_bytes','table_models','model_range','current_nan','model_nan'):
        rows.append(dict(seed,bad=bad,fault=1))
    rows.extend(dict(seed,slot=slot,fault=1)for slot in(128,65535))
    table=pack(dict(models=[dict(id=i,fields=dict(animal=i,nodrop=0,guardpoints=0))for i in range(2)]))
    reporter=Reporter('M4-LANDING-DROP-COMPONENT',kind='GATE')
    bindings={name:'SourceLandingDrop4086_'+suffix for name,suffix in dict(DROPREADY='Ready',DROPSLOT='Slot',DROPSTATUS='Status',DROPBASE='Base',DROPBANK='Bank',DROPBYTES='Bytes',DROPMODELS='Models').items()}
    raw,log=run_fixture(a.rom,a.output,rows,'SourceLandingDrop4086_Execute','SourceLandingDrop4086_Ready',0xb62e,[(58,0,table)],LUA.replace('TABLEBYTES',str(len(table))),reporter,bindings=bindings)
    actual=[list(map(int,l.split('LANDDROP|',1)[1].split('|')))for l in log.splitlines()if'LANDDROP|'in l]
    expected=[[i,0,3 if r['fault']else 2]for i,r in enumerate(rows)];ok=actual==expected
    reporter.check('actual source drop/count/timer behavior, negative zero and finite extremes, unsigned timer wrap, fault atomicity and surrounding actor/WRAM preservation',ok)
    report=dict(schema='BYOR_4086_LANDING_DROP_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,
                authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),
                attack_policy='zero-drop, no_pain0, unit defense.knockdown; guardbreak does not alter zero attack_drop',
                full_damage_callback_bound=False,world_post_acknowledgement_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
