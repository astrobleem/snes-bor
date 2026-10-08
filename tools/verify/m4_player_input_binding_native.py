"""Native history capture/writeback through actual source player role tokens."""
import argparse,hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_player_input_4086 import *
from source_player_input_native import emit as history_emit
from source_player_input_binding import emit as binding_emit
from m4_player_input_history_native import inputs,LUA,ROWS,SCRATCH,OWNER,SEQ,MAGIC
from source_script_input import ADDRESS
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

TIME=0x7fc500;SHADOW=0x7fc700;WORK=0x7fc780

SETUP=r'''
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,128)
 put(sy.SourceRetirement4086_Ready,0xb4f8)
 blob(TIMEADDR,c.times)
 for port,p in ipairs(c.players)do
  local ptr=0x414000+80*p.slot
  blob(ptr,p.view)
  local role=0x43fd80+4*port
  if p.present then put(role,ptr&65535);put(role+2,0x41)else put(role,0);put(role+2,0)end
 end
 if c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='pool'then put(sy.VmSourceWorld_PoolBase,0x4002)
 elseif c.bad=='world_count'then put(sy.VmSourceWorld_Count,129)
 elseif c.bad=='role_ready'then put(sy.SourceRetirement4086_Ready,0)
 elseif c.bad=='pointer_high'then put(0x43fd86,0x42)
 elseif c.bad=='pointer_align'then put(0x43fd84,0x4001)
 elseif c.bad=='pointer_end'then put(0x43fd84,0x6800)
 elseif c.bad=='direction_tag'then put(0x414018,2)
 elseif c.bad=='direction_reserved'then put(0x41401a,1)
 elseif c.bad=='index_tag'then put(0x414028,2)
 elseif c.bad=='index_reserved'then put(0x41402a,1)
 elseif c.bad=='index_value'then put(0x41402c,1)
 elseif c.bad=='index_high'then put(0x41402e,1)
 elseif c.bad=='stale_token'then put(0x414000,0)
 elseif c.bad=='stale_token_high'then put(0x414002,0)
 elseif c.bad=='late_port'then put(0x43fd92,0x42)end
 -- First player valid; later failures must precede any history/movetime writes.
 timesBefore={};for i=0,511 do timesBefore[i]=emu.read(TIMEADDR+i,mt)end
 worldBefore={};for _,p in ipairs(c.players)do local ptr=0x414000+80*p.slot;for i=0,79 do worldBefore[ptr+i]=emu.read(ptr+i,mt)end end
 for i=0,31 do worldBefore[0x43fd80+i]=emu.read(0x43fd80+i,mt)end
'''


def cases():
    candidates=inputs()[:-5];chosen=[candidates[i*(len(candidates)-1)//127]for i in range(128)]
    rows=[]
    for c in chosen:
        ps=[unpack_player(bytes.fromhex(c['initial'])[i*256:(i+1)*256])for i in range(4)]
        times=bytearray([0xa5])*512;players=[]
        for i,p in enumerate(ps):
            slot=(0,1,63,127)[i];ptr=0x414000+80*slot;view=bytearray([0x5a])*80
            struct.pack_into('<I',view,0,ptr);struct.pack_into('<BBHI',view,24,1,0,0,p['direction']);struct.pack_into('<BBHI',view,40,1,0,0,i)
            players.append(dict(present=bool(p['present']),slot=slot,view=view.hex()))
            if p['present']:struct.pack_into('<I',times,slot*4,p['movetime']);p['token']=ptr;p['present']=1
            else:p.update(movetime=0,direction=0,token=0,present=0)
        snap=bytes.fromhex(c['snapshot']);_,count,time=struct.unpack_from('<HHI',snap)
        controls=[struct.unpack_from('<II',snap,8+12*i)if i<count else(0,0)for i in range(4)]
        out,both,bothnew=refresh(ps,controls,time)
        wanted=bytearray(times)
        for p,m in zip(out,players):
            if m['present']:struct.pack_into('<I',wanted,4*m['slot'],p['movetime'])
        # Every cached metadata field contradicts the live source owner.
        poison=[]
        for p in ps:poison.append(pack_player(dict(p,movetime=0x76543210,direction=0x12345678,token=0x11111111,present=0)))
        sequence=bytes.fromhex(c['sequence']);length=struct.unpack_from('<H',sequence)[0];seq=list(struct.unpack_from('<'+str(length)+'I',sequence,2))
        rows.append(dict(c,initial=b''.join(poison).hex(),players=players,times=times.hex(),expected_times=wanted.hex(),
                         expected=b''.join(map(pack_player,out)).hex(),both=both,bothnew=bothnew,match=match_combo(seq,out[0])))
    base=next(c for c in rows if all(p['present']for p in c['players']))
    for bad in ('owner','snapshot','count','step','step_high','world','pool','world_count','role_ready','pointer_high','pointer_align','pointer_end','direction_tag','direction_reserved','index_tag','index_reserved','index_value','index_high','stale_token','stale_token_high','late_port'):
        rows.append(dict(base,bad=bad,fault=1))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);sy=symbols(Path('src/main.sym'));rows=cases()
    code=history_emit(ROWS,SCRATCH,ADDRESS,SEQ,OWNER,MAGIC)+binding_emit(ROWS,WORK,SHADOW,TIME,OWNER,MAGIC,sy)
    wrapper='''
PlayerHistoryFixture_Apply:
.a16
.i16
 jsl PlayerHistoryBinding_Refresh
 bcs PlayerHistoryFixture_Return
 lda #0
 jsl PlayerHistory_Match
 sta.l SCRATCH+36
PlayerHistoryFixture_Return:
.a16
.i16
 rtl
'''.replace('SCRATCH',str(SCRATCH))
    lua=LUA.replace('local cpu={};','local cpu={};local timesBefore={};local worldBefore={};')
    lua=lua.replace(' before={};for i=0,1023',SETUP+' before={};for i=0,1023')
    lua=lua.replace(" emu.log('PLAYERHISTORY|'",''' local extra=0
 if c.fault==0 then for i=1,#c.expected_times,2 do if emu.read(TIMEADDR+(i-1)//2,mt)~=tonumber(c.expected_times:sub(i,i+1),16)then extra=extra+1 end end
 else for i=0,511 do if emu.read(TIMEADDR+i,mt)~=timesBefore[i]then extra=extra+1 end end end
 for a,v in pairs(worldBefore)do if emu.read(a,mt)~=v then extra=extra+1 end end
 mismatch=mismatch+extra
 emu.log('PLAYERHISTORY|' ''')
    for k,v in dict(ROWADDR=ROWS,SCRATCHADDR=SCRATCH,SNAPSHOT=ADDRESS,OWNERADDR=OWNER,SEQADDR=SEQ,TIMEADDR=TIME).items():lua=lua.replace(k,str(v))
    reporter=Reporter('M4-PLAYER-INPUT-BINDING',kind='GATE')
    raw,log=run_fixture(a.rom,folder,rows,'PlayerHistoryFixture_Apply','VmSourceInput_Ready',MAGIC,[],lua,reporter,
                       append=wrapper+code,batch_size=4,frame_limit=700,link_pcm=False)
    results=[];errors=[]
    for line in log.splitlines():
        if 'PLAYERHISTORY|'not in line:continue
        r=list(map(int,line.split('PLAYERHISTORY|',1)[1].split('|')));i,mis,lo,hi,nlo,nhi,match,cost,ctx,immutable=r;c=rows[i]
        if mis or ctx or immutable or not c['fault']and ((lo|(hi<<16))!=c['both']or(nlo|(nhi<<16))!=c['bothnew']or match!=c['match']):errors.append(r)
        results.append(r)
    reporter.check('actual source roles/direction/movetime writeback; world and controls retained',len(results)==len(rows)and not errors)
    report=dict(schema='BYOR_4086_PLAYER_INPUT_ENTITY_BINDING_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',
                cases=len(rows),guard_cases=21,results_observed=len(results),errors=errors[:10],peak_master_clocks=max(r[7]for r in results),
                rom_sha256=hashlib.sha256(raw).hexdigest(),source_role_pointer_binding=True,source_typed_direction_binding=True,
                native_entity_movetime_storage_binding=True,private_fixture_lease=True,production_memory_lease_bound=False,
                entity_movetime_birth_hook_bound=False,world_installer_instrumented=True,full_player_think_bound=False,
                motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');reporter.finish()

if __name__=='__main__':main()
