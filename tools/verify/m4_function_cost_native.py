"""Non-mutating function/phase attribution on the accepted exact-coverage ROM."""
from __future__ import annotations
import argparse,collections,json
from pathlib import Path
from unittest.mock import patch
import m4_exact_coverage_native as accepted

BASE=Path('out/byor-motu-exact-coverage-v1/success')
BASE_SHA='0ad890b7390e83e593596e456469fece2ab37ab9378ac733c80b581a56841edd'
MS=21477.270


def require(ok,code):
    if not ok:raise ValueError('FUNCTION_COST:'+code)


def manifest(native,contract):
    from m4_rect_map_audit import statements
    lines=(native/'publisher.pasm').read_text().splitlines()
    sy=contract['native_symbols'];stm=statements([' iny' if x.strip()=='dey' else x for x in lines],sy)
    tags={}
    def tag(pc,key,value=True):
        require(key not in tags.setdefault(pc,{}),'DUPLICATE_TAG:'+key)
        tags[pc][key]=value
    for _,(pc,size,text) in stm.items():
        op,_,arg=text.partition(' ')
        if op not in ('jsr','jsl'):continue
        name=arg
        if arg in sy:target=sy[arg]
        else:
            try:target=int(arg.replace('$','0x'),0)
            except ValueError:raise ValueError('FUNCTION_COST:UNRESOLVED_CALL:'+text)
            if op=='jsr':target=(pc&0xff0000)|(target&65535)
            names=[k for k,v in sy.items() if v==target]
            if names:name=sorted(names,key=lambda x:(len(x),x))[0]
        tag(pc,'call',dict(site=pc,name=name,target=target))
        tags.setdefault(pc+size,{})['return_site']=pc
    phases={'NbBegin':'begin','NbBeginRetry':'mark_setup','NbMark':'mark',
            'NbRestorePlanStart':'prediction','NbRestorePlan':'restoration_plan',
            'NbActorPlanStart':'home_prepare','NbActorPlan':'actor_slot_plan',
            'NbRestoreProduce':'restoration_produce','NbActorProduceStart':'actor_produce',
            'NbAllPairsReady':'ready_validate','NbGuard5':'safe_point',
            'NbMapCommit':'map_commit','NbMapsComplete':'committed_map_copy',
            'NbClearRefs':'clear_refs','NbPublishRefs':'publish_refs'}
    for name,phase in phases.items():tag(sy[name],'phase',phase)
    tag(sy['NbBegin'],'start');tag(sy['NbVisible'],'finish')
    tag(sy['NbBeginRetry'],'exact_begin');tag(sy['NbRestorePlanStart'],'exact_end')
    tag(sy['AstraOpaqueTile'],'tile_begin');tag(sy['AstraTileDone'],'tile_end')
    tag(sy['NbFreshVblank'],'wait_begin');tag(sy['NbWindowStart'],'wait_end')
    for name,pc in sy.items():
        if name.startswith('OnlineDmaDone'):tags.setdefault(pc+2,{})['dma_end']=True
    lo=lines.index('NbActorPlan:');hi=lines.index('NbRestoreProduce:')
    hits=[i for i in range(lo,hi-1) if lines[i:i+2]==[' lda #2',' sta.l $42D600']]
    require(len(hits)==1,'PRELOADING_BOUNDARY')
    # The accepted NbPreloading observer sees state=2 after the LDA/STA pair.
    # Tagging the LDA itself moves its 72 clocks into residual bookkeeping.
    # Keep the exact original boundary rather than adjusting ledger totals.
    boundary=hits[0]+2
    require(boundary in stm,'PRELOADING_INSTRUCTION_BOUNDARY')
    tag(stm[boundary][0],'preloading')
    lo=lines.index('NbPublishRefs:');hi=lines.index('NbVisible:')
    hits=[i for i in range(lo,hi) if lines[i]==' lda $10']
    require(len(hits)==1,'SUCCESS_KEY_BOUNDARY')
    tag(stm[hits[0]][0],'phase','publish_key')
    return tags


LUA=r'''
local fcActive=false;local fcStack={};local fcRoots={};local fcResidual={};local fcExactOwners={}
local fcBuckets={preparing=0,tile=0,wait=0,dma=0,residual=0}
local fcLast=0;local fcStart=0;local fcPhase='begin';local fcPrep=false;local fcExact=false
local fcTile=false;local fcWait=false;local fcDma=false;local fcCalls=0;local fcFn=0
local function fcAdd(t,k,v)t[k]=(t[k]or 0)+v end
local function fcAccount(clock)
 local delta=clock-fcLast;if delta<0 then nbLog('FAULT','FC_CLOCK_REVERSED')end
 local top=fcStack[#fcStack];local owner=fcPhase..':'..(top and top.name or '@root')
 if top then top.exclusive=top.exclusive+delta else fcAdd(fcRoots,fcPhase,delta)end
 local category=fcPrep and 'preparing' or fcTile and 'tile' or fcWait and 'wait' or fcDma and 'dma' or 'residual'
 fcAdd(fcBuckets,category,delta)
 if category=='residual' then fcAdd(fcResidual,owner,delta)end
 if fcExact then fcAdd(fcExactOwners,owner,delta)end
 fcLast=clock
end
local function fcHook(pc,tag)
 local clock=emu.getState()['masterClock']
 if tag.start and nbTxn==3 then
  if fcActive then nbLog('FAULT','FC_DUPLICATE_BEGIN')end
  fcActive=true;fcStart=clock;fcLast=clock;fcPrep=true
 end
 if not fcActive then return end
 fcAccount(clock)
 if tag.finish then
  if #fcStack~=0 or fcPrep or fcExact or fcTile or fcWait or fcDma then nbLog('FAULT','FC_UNFINISHED')end
  local roots=0;for k,v in pairs(fcRoots)do nbLog('FC_ROOT',k..'|'..v);roots=roots+v end
  for k,v in pairs(fcResidual)do nbLog('FC_RESIDUAL',k..'|'..v)end
  for k,v in pairs(fcExactOwners)do nbLog('FC_EXACT',k..'|'..v)end
  for k,v in pairs(fcBuckets)do nbLog('FC_ACCOUNT',k..'|'..v)end
  nbLog('FC_TOTAL',fcStart..'|'..(clock-fcStart)..'|'..fcFn..'|'..roots..'|'..fcCalls)
  fcActive=false;return
 end
 local top=fcStack[#fcStack]
 if tag.return_site and top and top.site==tag.return_site then
  top=table.remove(fcStack);local elapsed=clock-top.start;fcCalls=fcCalls+1;fcFn=fcFn+top.exclusive
  nbLog('FC_CALL',top.site..'|'..top.name..'|'..top.phase..'|'..(top.exact and 1 or 0)..'|'..top.start..'|'..elapsed..'|'..top.exclusive..'|'..(#fcStack+1))
 end
 if tag.phase then
  fcPhase=tag.phase
  if fcPhase=='mark' or fcPhase=='mark_setup' then fcPhase=fcPhase..(nbWord(0x42d674)==1 and '_exact' or '_source')end
 end
 if tag.exact_begin then fcExact=nbWord(0x42d674)==1 end
 if tag.exact_end then fcExact=false end
 if tag.preloading then fcPrep=false end
 if tag.tile_begin then fcTile=true end
 if tag.tile_end then fcTile=false end
 if tag.wait_begin then fcWait=true end
 if tag.wait_end then fcWait=false end
 if tag.dma_end then fcDma=false end
 if tag.call then
  fcStack[#fcStack+1]={site=tag.call.site,name=tag.call.name,phase=fcPhase,exact=fcExact,start=clock,exclusive=0}
 end
end
'''


def lua(value):
    if isinstance(value,bool):return 'true' if value else 'false'
    if isinstance(value,(str,int)):return json.dumps(value)
    return '{'+','.join('['+json.dumps(k)+']='+lua(v) for k,v in value.items())+'}'


def observer(script,contract):
    accepted.observer(script,contract)
    tags=manifest(script.parent,contract)
    (script.parent/'function-cost-hooks.json').write_text(json.dumps(tags,indent=2)+'\n')
    with script.open('a') as stream:
        stream.write(LUA)
        for pc,tag in sorted(tags.items()):
            stream.write('emu.addMemoryCallback(function() fcHook('+str(pc)+','+lua(tag)+') end,emu.callbackType.exec,'+str(pc)+','+str(pc)+',emu.cpuType.snes,emu.memType.snesMemory)\n')
        stream.write("emu.addMemoryCallback(function() if fcActive then fcAccount(emu.getState()['masterClock']);if fcDma then nbLog('FAULT','FC_NESTED_DMA')end;fcDma=true end end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)\n")


def analyze(folder):
    calls=[];maps={name:{} for name in ('ROOT','RESIDUAL','EXACT','ACCOUNT')};totals=[]
    for line in (folder/'native/mesen.log').read_text(errors='replace').splitlines():
        require('callback_owner.lua:' not in line,'LUA_ERROR:'+line)
        if not line.startswith('NB_'):continue
        p=line.split('|');kind=p[0][3:];d=p[4:]
        require(kind!='FAULT','NATIVE_FAULT:'+'|'.join(d))
        if kind=='FC_CALL':
            site,name,phase,exact,start,elapsed,exclusive,depth=d
            row=dict(site=int(site),name=name,phase=phase,exact=bool(int(exact)),start=int(start),end=int(p[1]),inclusive=int(elapsed),exclusive=int(exclusive),depth=int(depth))
            require(0<=row['exclusive']<=row['inclusive']==row['end']-row['start'],'CALL_ACCOUNTING')
            calls.append(row)
        elif kind=='FC_TOTAL':totals.append(list(map(int,d)))
        elif kind.startswith('FC_') and kind[3:] in maps:
            target=maps[kind[3:]];require(d[0] not in target,'DUPLICATE_BUCKET');target[d[0]]=int(d[1])
    require(len(totals)==1,'PUBLICATION_TOTAL_COUNT')
    start,duration,function_sum,root_sum,count=totals[0]
    require(count==len(calls) and function_sum==sum(c['exclusive'] for c in calls),'FUNCTION_TOTAL')
    require(root_sum==sum(maps['ROOT'].values()) and root_sum+function_sum==duration,'EXCLUSIVE_TOTAL')
    require(sum(maps['ACCOUNT'].values())==duration,'DISJOINT_TOTAL')
    require(sum(maps['RESIDUAL'].values())==maps['ACCOUNT']['residual'],'RESIDUAL_TOTAL')
    require(sum(maps['EXACT'].values())==2092856,'EXACT_MARK_TOTAL')
    wanted=dict(preparing=5683806,tile=1874122,wait=1712658,dma=112168,residual=2651338)
    require(maps['ACCOUNT']==wanted,'ACCEPTED_LEDGER_DRIFT')
    functions=collections.defaultdict(lambda:dict(calls=0,inclusive=0,exclusive=0))
    for call in calls:
        row=functions[call['phase']+':'+call['name']];row['calls']+=1
        for key in ('inclusive','exclusive'):row[key]+=call[key]
    ordered=lambda values:sorted([dict(name=k,clocks=v,ms=v/MS) for k,v in values.items()],key=lambda x:-x['clocks'])
    result=dict(classification='FUNCTION_COST_PROFILE_PASS',rom_sha256=accepted.q8.sha(folder/'native/bor.sfc'),
        start=start,total_clocks=duration,disjoint=maps['ACCOUNT'],residual=ordered(maps['RESIDUAL']),
        exact_mark=ordered(maps['EXACT']),root_exclusive=ordered(maps['ROOT']),
        functions=sorted([dict(name=k,**v) for k,v in functions.items()],key=lambda x:-x['exclusive']),calls=calls,
        boundaries='Callsite before JSR/JSL to after return; inclusive includes child time. Exclusive is measured between instrumented call boundaries. Ledger separately removes exact original TILE/WAIT/DMA spans.')
    (folder/'function-cost-profile.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();root=a.output.resolve();require(not root.exists(),'FRESH_OUTPUT_REQUIRED')
    accepted.q8.configure_capture_runtime(root)
    child=root/'success';accepted.build(child)
    require(accepted.q8.sha(child/'native/bor.sfc')==BASE_SHA,'BASELINE_ROM_DRIFT')
    with patch.object(accepted.q8,'audit_rom',accepted.audit_rom),patch.object(accepted.q8,'observer',observer):
        result=accepted.q8.run_case(child,'success')
    baseline=json.loads((BASE/'eight-result.json').read_text())
    require(result['transactions']==baseline['transactions'],'PROFILE_PERTURBED_NATIVE_TIMING')
    profile=analyze(child)
    print(profile['classification'],json.dumps(dict(residual=profile['residual'][:14],exact=profile['exact_mark'][:12])),flush=True)


if __name__=='__main__':main()
