"""Special continuation against pinned C cases with ordered query/callback traces."""
import argparse,hashlib,json,re,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_player_special_authority import cases,simulate
from source_player_special_native import emit
from _source_leaf_fixture import run_fixture
from _harness import Reporter
W=0x7fa000
ASM='''
SpecialProbe:
.a16
.i16
 php
 phx
 sed
 ldx #0
 jsl SourceSpecial_Begin
SpecialProbe_Return:
 nop
 bcs SpecialProbe_Bad
 lda.l W+2
 cmp #2
 beq SpecialProbe_Done
 cmp #5
 beq SpecialProbe_Done
 inx
 cpx #32
 bcs SpecialProbe_Bad
SpecialProbe_Request:
 nop
 jsl SourceSpecial_Resume
 bra SpecialProbe_Return
SpecialProbe_Done:
 plx
 plp
 clc
 rtl
SpecialProbe_Bad:
 plx
 plp
 sec
 rtl
'''
LUA=r'''
local mt=emu.memType.snesMemory;local trace,cpu={},{};local fail=0;local decimal=0;local start=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function long(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function mutate(c)
 if c.mutation==1 then put(W+52,0,4);put(W+56,500,4);put(W+128,1,4)
 elseif c.mutation==2 then put(W+48,1,4);put(W+36,1,4)
 elseif c.mutation==3 then put(W+172,2,4);put(W+52,2,4);put(W+56,3,4)
 elseif c.mutation==4 then put(W+112,5,4);put(W+116,9*65536,4);put(W+120,11*65536,4)end
end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];fail=0;decimal=0;trace={};for j=0,191 do emu.write(W+j,0,mt)end
 put(W,c.bad=='ready'and 0 or 0xb682);put(W+2,c.bad=='busy'and 1 or 0)
 for _,p in ipairs(c.fields)do put(W+p[1],p[2],4)end
 put(EXPECTFAULT,c.fault)
 local st=emu.getState();start=st.masterClock;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()if emu.getState()['cpu.ps']&8==0 then decimal=decimal+1 end end,emu.callbackType.exec,RETURN,RETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local role=word(W+12);local kind=word(W+6)
 if word(W+2)==3 then
  if role==2 then trace[#trace+1]=100;put(W+16,c.block)
  else trace[#trace+1]=10+role
   local cost=long(W+172);if cost>=0x80000000 then cost=cost-0x100000000 end
   local mp,hp=long(W+52),long(W+56);if mp>=0x80000000 then mp=mp-0x100000000 end;if hp>=0x80000000 then hp=hp-0x100000000 end
   local allowed=c.present~=0 and(c.only~=(role==0 and 1 or 2))and(role==0 and hp>cost or role==1 and mp>=cost)
   put(W+16,allowed and 1 or 0)
  end
 else trace[#trace+1]=kind;mutate(c)end
 put(W+8,c.bad=='ack'and 0 or 0xb683);put(W+10,c.bad=='service'and 99 or kind);put(W+14,c.bad=='role'and 99 or role)
end,emu.callbackType.exec,REQUESTPOINT,REQUESTPOINT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then fail=fail+1 end end
 if(cpu.ps&254)~=(st['cpu.ps']&254)then fail=fail+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local values={word(W+2)==5 and 1 or 0}
 for _,off in ipairs({52,56,60,64,68,72,76,80,84,88,100,104,96,92,108,112,116,120,124,128,132,136,140})do values[#values+1]=long(W+off)end
 values[#values+1]=#trace;for _,v in ipairs(trace)do values[#values+1]=v end
 emu.log('SPECIALNATIVE|'..word(INDEX)..'|'..word(W+2)..'|'..table.concat(values,',')..'|'..fail..'|'..decimal..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def convert(row):
    ns,cant,aj,block,nocost,cheat,linked,freeze,play,keys,mp,hp,cost,only,mutation,bomb,present=row
    fields=[(24,ns),(28,cant),(32,aj),(36,nocost),(40,cheat),(44,bomb),(48,freeze),(52,mp),(56,hp),(60,99),(64,0),(68,3),
            *[(72+4*i,i+1)for i in range(5)],(92,linked),(96,99),(100,1),(104,1),(108,1),(112,-7),(116,int(3.5*65536)),(120,int(-2.5*65536)),
            (124,0),(128,0),(132,99),(136,play|0x80000000),(140,0x800001c0),(152,keys),(156,64),(168,1),(172,cost),(184,1)]
    values=list(struct.unpack('<57I',simulate(row)))
    for i in (17,18):values[i]=int(struct.unpack('<f',struct.pack('<I',values[i]))[0]*65536)&0xffffffff
    return dict(fields=[list(p)for p in fields],expected=values[:25+values[24]],block=block,mutation=mutation,only=only,present=present,bad='',fault=0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();rows=[convert(c)for c in cases()]
    base=convert([0,0,1,0,0,0,1,0,256,0,30,150,6,0,0,1,1])
    for bad in ('ready','busy','ack','service','role'):
        rows.append(dict(base,bad=bad,fault=1))
    for bad,off,val in (('invalid_port',128,4),('missing_descriptor',168,0),('signed_overflow',56,0x80000000)):
        row=dict(convert([0,0,0,0,0,0,0,0,256,0,30,150,6,0,0,0,1]),bad=bad,fault=1)
        row['fields']=[list(p)for p in row['fields']]
        for field in row['fields']:
            if field[0]==off:field[1]=val
        if bad=='signed_overflow':
            # HP eligibility fails, MP succeeds; a callback-free MP debit must overflow.
            for field in row['fields']:
                if field[0]in (52,172):field[1]=0x7fffffff if field[0]==52 else -1
        rows.append(row)
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);(folder/'report.json').write_text('{"status":"RUNNING"}\n')
    reporter=Reporter('M4-PLAYER-SPECIAL-NATIVE',kind='GATE')
    raw,log=run_fixture(a.rom,folder,rows,'SpecialProbe','SourceAnimationInit4086_Ready',0xb4ec,[],re.sub(r'\bW\b',str(W),LUA),reporter,
        append=ASM.replace('W+',str(W)+'+')+emit(W),probes=dict(RETURN='SpecialProbe_Return',REQUESTPOINT='SpecialProbe_Request'),batch_size=16,frame_limit=3000,link_pcm=False)
    observed=[line.split('SPECIALNATIVE|',1)[1].strip().split('|')for line in log.splitlines()if 'SPECIALNATIVE|'in line]
    errors=[]
    for i,r in enumerate(observed):
        ok=int(r[1])==6 if rows[i]['fault']else list(map(int,r[2].split(',')))==rows[i]['expected']
        if not ok or r[3:5]!=['0','0']:errors.append(dict(case=i,row=rows[i],observed=r))
    reporter.check('source special key/query order, unlink and callbacks, fresh post-callback debit and player row, CPU/decimal retention',len(observed)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_PLAYER_SPECIAL_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),guards=8,observed=len(observed),errors=errors[:5],
        rom_sha256=hashlib.sha256(raw).hexdigest(),peak_master_clocks=max((int(r[5])for r in observed),default=0),snapshot_bytes=192,
        queries_and_services_instrumented=True,canonical_actor_binding=False,smartbomb_and_freeze_owner_bound=False,production_player_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
