"""Native addscore scalar arithmetic; extra-life/script services stay required."""
import argparse
import hashlib
import json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory;local before={}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 put(SCOREREADY,0xb631);put(SCOREINDEX,c.index,4);put(SCOREADD,c.add,4);put(SCORELIFE,c.lifescore,4);put(SCOREMASK,c.script==1 and 15 or 0);put(SCORESTATUS,0)
 put(SCORENOSCRIPT,0xb632);put(SCORESTATS,0xb633)
 for i=0,3 do put(0x7fbfa0+i*4,c.score,4);put(0x7fbfb0+i*4,5,4)end
 local changes={ready={SCOREREADY,0},stats_ready={SCORESTATS,0},script_mask={SCOREMASK,16},script_proof={SCORENOSCRIPT,0},lifescore_zero={SCORELIFE,0}}
 if c.bad and changes[c.bad]then local r=changes[c.bad];put(r[1],r[2],c.bad=='lifescore_zero'and 4 or 2)end
 before={};for _,r in ipairs({{0x7fbfa0,32},{0x7fbf92,14},{0x7fbfc0,80},{0x7fbf3a,36}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.status==0 and c.index>=0 then for i=0,3 do before[0x7fbfa0+(c.index&3)*4+i]=(c.final_score>>(8*i))&255 end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 local q,r,nextup,newscore=0,0,0,0
 if c.calc==1 then q=dw(SCOREQUOT);r=dw(SCOREREM);nextup=dw(SCORENEXT);newscore=dw(SCORENEW)end
 emu.log('SCORENATIVE|'..word(INDEX)..'|'..n..'|'..word(SCORESTATUS)..'|'..q..'|'..r..'|'..nextup..'|'..newscore)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
    rows=[]
    for case in authority['results']:
        r=case['case'];score=case['expected'][0]
        status=0 if r['index']<0 else 1 if case['expected'][1]>5 else 2 if r['script']else 0
        rows.append(dict(r,fault=0,status=status,final_score=score,calc=int(r['index']>=0)))
    seed=next(r for r in rows if r['index']==0 and r['score']==0 and r['add']==70 and r['script']==0 and r['sample']==-1)
    rows.extend(dict(seed,bad=bad,fault=1,status=3,calc=0)for bad in('ready','stats_ready','script_mask','script_proof','lifescore_zero'))
    rows.extend(dict(seed,score=score,status=4,calc=0)for score in(1000000000,4294967295))
    reporter=Reporter('M4-SCORE-SCALAR',kind='GATE')
    bindings={name:'SourceScore4086_'+field for name,field in dict(SCOREREADY='Ready',SCOREINDEX='Index',SCOREADD='Add',SCORELIFE='LifeScore',SCOREMASK='ScriptMask',SCORESTATUS='Status',SCORENOSCRIPT='NoScriptsReady',SCORESTATS='StatsReady',SCOREQUOT='Quotient',SCOREREM='Remainder',SCORENEXT='Next',SCORENEW='New').items()}
    raw,log=run_fixture(a.rom,a.output,rows,'SourceScore4086_Execute','SourceScore4086_Ready',0xb631,[],LUA,reporter,bindings=bindings)
    actual=[list(map(int,l.split('SCORENATIVE|',1)[1].split('|')))for l in log.splitlines()if'SCORENATIVE|'in l]
    expected=[]
    for i,r in enumerate(rows):
        if r['calc']:
            q,rem=divmod(r['score'],r['lifescore']);nextup=(q+1)*r['lifescore'];newscore=min((r['score']+r['add'])&0xffffffff,999999999)
        else:q=rem=nextup=newscore=0
        expected.append([i,0,r['status'],q,rem,nextup,newscore])
    ok=actual==expected
    reporter.check('actual source unsigned wrap/cap/index masking/strict threshold; native unsigned division including full-width divisors; negative index literal no-op; required life/script services; atomic guard rejection and neighboring state preservation',ok)
    report=dict(schema='BYOR_4086_SCORE_SCALAR_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,
                authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),
                native_complete_domain='nonnegative index: valid source score0..999999999, nonzero unsigned lifescore, no crossed source threshold and absent score script; negative index no-op',
                extra_life_and_script_services_proven=False,required_service_player_state_preserved=True,
                full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
