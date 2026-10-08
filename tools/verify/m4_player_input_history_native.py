"""Isolated native input history over an explicit private VM-slot fixture lease.

No production memory allocation or full player controller is claimed. Fixtures
inject immutable control snapshots and entity metadata, compare all four rows,
and preserve every byte beyond the owner's named state/scratch regions.
"""
import argparse,hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_player_input_4086 import *
from source_player_input_authority import cases
from source_player_input_native import emit
from source_script_input import snapshot,ADDRESS
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ROWS=0x7fc000;SCRATCH=0x7fc400;OWNER=0x7fc440;SEQ=0x7fc450;MAGIC=0xb66e

LUA=r'''
local mt=emu.memType.snesMemory;local start=0;local before={};local cpu={};local snapshotBefore={}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function blob(a,hex)for i=1,#hex,2 do emu.write(a+(i-1)//2,tonumber(hex:sub(i,i+1),16),mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 -- The isolated gate replaces instruction dispatch: no source VM library is
 -- executing while the private VM-slot fixture lease is held.
 put(sy.SourceVMRun4086_Ready,0)
 blob(ROWADDR,c.initial);blob(SNAPSHOT,c.snapshot);blob(SEQADDR,c.sequence)
 put(OWNERADDR,0xb66e);put(EXPECTFAULT,c.fault)
 if c.bad=='owner'then put(OWNERADDR,0)end
 if c.bad=='snapshot'then put(SNAPSHOT,0)end
 if c.bad=='count'then put(SNAPSHOT+2,5)end
 if c.bad=='step'then put(ROWADDR+232,27)end
 if c.bad=='step_high'then put(ROWADDR+234,1)end
 before={};for i=0,1023 do before[i]=emu.read(ROWADDR+i,mt)end
 snapshotBefore={};for i=0,55 do snapshotBefore[i]=emu.read(SNAPSHOT+i,mt)end
 local state=emu.getState();cpu={};for _,k in ipairs({"x","y","d","dbr","sp","ps"})do cpu[k]=state["cpu."..k]end
 start=state.masterClock
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local mismatch=0;local diffs={}
 if c.fault==0 then
  for i=1,#c.expected,2 do if emu.read(ROWADDR+(i-1)//2,mt)~=tonumber(c.expected:sub(i,i+1),16)then mismatch=mismatch+1;if #diffs<12 then diffs[#diffs+1]=((i-1)//2)..":"..emu.read(ROWADDR+(i-1)//2,mt)..":"..tonumber(c.expected:sub(i,i+1),16)end end end
 else for i=0,1023 do if emu.read(ROWADDR+i,mt)~=before[i]then mismatch=mismatch+1 end end end
 local state=emu.getState();local context=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=state['cpu.'..k]then context=context+1 end end
 if (cpu.ps&60)~=(state['cpu.ps']&60)then context=context+1 end
 local immutable=0;for i=0,55 do if snapshotBefore[i]~=emu.read(SNAPSHOT+i,mt)then immutable=immutable+1 end end
 if mismatch>0 and word(INDEX)<4 then emu.log('PLAYERDIFF|'..word(INDEX)..'|'..table.concat(diffs,','))end
 emu.log('PLAYERHISTORY|'..word(INDEX)..'|'..mismatch..'|'..word(SCRATCHADDR)..'|'..word(SCRATCHADDR+2)..'|'..word(SCRATCHADDR+4)..'|'..word(SCRATCHADDR+6)..'|'..word(SCRATCHADDR+36)..'|'..(emu.getState().masterClock-start)..'|'..context..'|'..immutable)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def inputs():
    rows=[]
    for i,c in enumerate(cases()):
        ps=[c['player'],*[empty_player()for _ in range(3)]]
        # Exercise independent histories and all four logical ports, including
        # aggregate high bits. Every row receives different direction/time state.
        controls=[(c['new'],c['new'])]
        count=1+i%4
        for j in range(1,4):
            ps[j]=dict(c['player'],direction=(i+j)&1,combostep=(i+j)%27,token=j)
            controls.append(((0x80000008>>j)|j,4 if j&1 else 8)if j<count else(0,0))
        out,both,bothnew=refresh(ps,controls,c['time'])
        seq=c['sequence']
        rows.append(dict(initial=b''.join(map(pack_player,ps)).hex(),
                         snapshot=snapshot([(h,n,0)for h,n in controls[:count]],c['time']).hex(),
                         sequence=(struct.pack('<H',len(seq))+b''.join(struct.pack('<I',v)for v in seq)).hex(),
                         expected=b''.join(map(pack_player,out)).hex(),both=both,bothnew=bothnew,
                         match=match_combo(seq,out[0]),fault=0,bad=''))
    for bad in ('owner','snapshot','count','step','step_high'):
        rows.append(dict(rows[0],fault=1,bad=bad))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--limit',type=int,default=384)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    allrows=inputs();rows=[allrows[i*(len(allrows)-6)//(a.limit-1)]for i in range(a.limit)]+allrows[-5:];reporter=Reporter('M4-PLAYER-HISTORY',kind='GATE')
    native=emit(ROWS,SCRATCH,ADDRESS,SEQ,OWNER,MAGIC)
    wrapper='''
PlayerHistoryFixture_Apply:
.a16
.i16
 jsl PlayerHistory_Refresh
 bcs PlayerHistoryFixture_Return
 lda #0
 jsl PlayerHistory_Match
 sta.l SCRATCH+36
PlayerHistoryFixture_Return:
.a16
.i16
 rtl
'''.replace('SCRATCH',str(SCRATCH))
    lua=LUA
    for k,v in dict(ROWADDR=ROWS,SCRATCHADDR=SCRATCH,SNAPSHOT=ADDRESS,OWNERADDR=OWNER,SEQADDR=SEQ).items():lua=lua.replace(k,str(v))
    raw,log=run_fixture(a.rom,folder,rows,'PlayerHistoryFixture_Apply','VmSourceInput_Ready',MAGIC,[],lua,reporter,
                       append=wrapper+native,batch_size=8,frame_limit=700,link_pcm=False)
    results=[];peak=0;errors=[]
    for line in log.splitlines():
        if 'PLAYERHISTORY|'not in line:continue
        r=list(map(int,line.split('PLAYERHISTORY|',1)[1].split('|')))
        i,mis,blo,bhi,nlo,nhi,match,cost,context,immutable=r;c=rows[i]
        ok=mis==0 and context==0 and immutable==0 and (c['fault']or (blo|(bhi<<16))==c['both']and (nlo|(nhi<<16))==c['bothnew']and match==c['match'])
        if not ok:errors.append(r)
        results.append(r);peak=max(peak,cost)
    reporter.check('all native rows and 32-bit masks equal pinned semantics',len(results)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_PLAYER_HISTORY_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',
                cases=len(rows),results_observed=len(results),errors=errors[:20],peak_master_clocks=peak,
                rom_sha256=hashlib.sha256(raw).hexdigest(),native_asm_sha256=hashlib.sha256(native.encode()).hexdigest(),
                compared_player_bytes=(len(rows)-5)*1024,private_vm_slot_lease=True,
                ring_positions=sorted({int.from_bytes(bytes.fromhex(c['initial'])[232:236],'little')for c in rows if not c['fault']}),
                immutable_control_snapshot=True,register_context_preserved=['X','Y','DP','DBR','SP','M','Xwidth','D','I'],
                production_memory_owner_bound=False,live_entity_metadata_bound=False,
                full_player_think_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');reporter.finish()

if __name__=='__main__':main()
