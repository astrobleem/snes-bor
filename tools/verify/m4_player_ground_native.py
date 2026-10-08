"""Native ground continuation with ordered instrumented queries and callbacks."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_player_ground_authority import cases, simulate
from source_player_ground_native import emit
from source_player_run_4086 import KEYS
from _source_leaf_fixture import run_fixture
from _harness import Reporter

WORK=0x7fa000
ASM='''
GroundProbe:
.a16
.i16
 php
 phx
 sed
 ldx #0
 jsl SourceGround_Begin
GroundProbe_Return:
 nop
 bcs GroundProbe_Bad
 lda.l W+2
 cmp #2
 beq GroundProbe_Done
 inx
 cpx #32
 bcs GroundProbe_Bad
GroundProbe_Request:
 nop
 jsl SourceGround_Resume
 bra GroundProbe_Return
GroundProbe_Done:
 plx
 plp
 clc
 rtl
GroundProbe_Bad:
 plx
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local trace,cpu,start={},{},0;local decimal=0;local ctx=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function long(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function mutate(c)
 if c.mutation==1 then put(WORK+28,1-long(WORK+28),4);put(WORK+72,2,4);put(WORK+78,1,4)
 elseif c.mutation==2 then put(WORK+52,9*65536,4);put(WORK+56,11*65536,4);put(WORK+64,0,4)
 elseif c.mutation==3 then put(WORK+32,17,4);put(WORK+36,3,4);put(WORK+72,3,4);put(WORK+78,0,4);put(WORK+82,10,4)
 elseif c.mutation==4 then put(WORK+60,77,4);put(WORK+64,1,4)end
end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];trace={};decimal=0;ctx=0
 put(EXPECTFAULT,c.fault);for j=0,127 do emu.write(WORK+j,0,mt)end
 put(WORK,c.bad=='ready'and 0 or 0xb679);put(WORK+2,c.bad=='busy'and 1 or 0)
 for _,pair in ipairs(c.fields)do put(WORK+pair[1],pair[2],pair[3])end
 local s=emu.getState();start=s.masterClock;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 if emu.getState()['cpu.ps']&8==0 then decimal=decimal+1 end
end,emu.callbackType.exec,RETURN,RETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local state=word(WORK+2);local service=word(WORK+90);local role=word(WORK+6)
 if state==5 then trace[#trace+1]=100+role;put(WORK+10,(c.valid&(1<<role))~=0 and 1 or 0)
 else trace[#trace+1]=service;if service==1 then trace[#trace+1]=role end
 if service==1 or service==2 then mutate(c)end end
 put(WORK+8,c.bad=='ack'and 0 or 0xb67a);put(WORK+12,c.bad=='service'and 99 or service);put(WORK+14,c.bad=='role'and 99 or role)
end,emu.callbackType.exec,REQUESTPOINT,REQUESTPOINT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local values={word(WORK+2)}
 for _,off in ipairs({28,24,32,68,64,60,52,56,72,78,82,36})do values[#values+1]=long(WORK+off)end
 values[#values+1]=#trace;for _,v in ipairs(trace)do values[#values+1]=v end
 emu.log('GROUNDNATIVE|'..word(INDEX)..'|'..table.concat(values,',')..'|'..ctx..'|'..decimal..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def convert(row):
    mask,plane,running,direction,timer,valid,facing,levelfacing,scroll,mutation,notinair=row
    keys=0x80000000
    for i,name in enumerate(('moveleft','moveright','moveup','movedown')):
        if mask&(1<<i):keys|=KEYS[name]
    turntime,delay,time=((0,0,48),(0,7,48),(48,7,48),(49,7,48),(0,7,0xfffffffe))[timer]
    fields=[(16,keys,4),(20,plane,2),(22,notinair,2),(24,running,4),(28,direction,4),
            (32,turntime,4),(36,delay,4),(40,time,4),(44,int(2.5*65536),4),(48,int(4.5*65536),4),
            (52,7*65536,4),(56,-3*65536,4),(60,99,4),(64,-4,4),(68,-3,4),
            (72,facing,4),(76,1,2),(78,levelfacing,4),(82,scroll,4)]
    values=list(struct.unpack('<45I',simulate(row)))
    for i in (6,7):values[i]=int(struct.unpack('<f',struct.pack('<I',values[i]))[0]*65536)&0xffffffff
    expected=[2]+values[:13]+values[13:13+values[12]]
    return dict(fields=[list(v) for v in fields],expected=expected,valid=valid,mutation=mutation,bad='',fault=0,source=row)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();rows=[convert(r)for i,r in enumerate(cases())if i%3==0]
    for bad in ('ready','busy','ack','service','role'):
        rows.append(dict(convert([4,1,0,0,0,31,0,0,0,0,1]),bad=bad,fault=1))
    for bad,mask,speed in (('fractional_half',4,163841),('negation_overflow',1,0x80000000)):
        row=convert([mask,1,0,0,0,31,0,0,0,0,1])
        row.update(bad=bad,fault=1)
        for field in row['fields']:
            if field[0]==44:field[1]=speed
        rows.append(row)
    reporter=Reporter('M4-PLAYER-GROUND-NATIVE',kind='GATE');out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    raw,log=run_fixture(a.rom,out,rows,'GroundProbe','SourceAnimationInit4086_Ready',0xb4ec,[],LUA.replace('WORK',str(WORK)),reporter,
                        append=ASM.replace('W+',str(WORK)+'+')+emit(WORK),probes=dict(RETURN='GroundProbe_Return',REQUESTPOINT='GroundProbe_Request'),
                        batch_size=16,frame_limit=2000,link_pcm=False)
    actual=[line.split('GROUNDNATIVE|',1)[1].strip().split('|')for line in log.splitlines()if 'GROUNDNATIVE|'in line]
    errors=[]
    for i,row in enumerate(actual):
        values=list(map(int,row[1].split(',')))
        ok=values[0]==6 if rows[i]['fault']else values==rows[i]['expected']
        if not ok or row[2:4]!=['0','0']:errors.append(dict(case=i,input=rows[i],actual=row))
    reporter.check('source movement/turn/item continuation, ordered query/service trace, fresh callback fields, CPU and decimal retention',len(actual)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_PLAYER_GROUND_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),guards=7,errors=errors[:8],observed_cases=len(actual),
                rom_sha256=hashlib.sha256(raw).hexdigest(),peak_master_clocks=max((int(v[4])for v in actual),default=0),
                snapshot_abi_bytes=128,velocity_abi='finite exactly representable Q16; fractional half-slot operands reject',
                services_instrumented=True,canonical_actor_storage_bound=False,production_player_owner_bound=False,
                motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
