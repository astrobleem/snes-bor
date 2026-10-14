"""Non-overlapping native master-clock accounting; fail closed on open calls."""
from collections import defaultdict
import json
from pathlib import Path
import re

HZ=21477270


def stat():return dict(calls=0,inclusive_elapsed_clocks=0,inclusive_active_clocks=0,exclusive_active_clocks=0,dma_clocks=0,interrupt_clocks=0,max_inclusive_call_clocks=0,max_exclusive_call_clocks=0,bytes=0,inclusive_dma_bytes=0,inclusive_dma_descriptors=0,own_dma_bytes=0,own_dma_descriptors=0)


def parse(log):
    events=[]
    for line in log.splitlines():
        if 'PROF|' not in line:continue
        p=line.split('PROF|',1)[1].split('|')
        if len(p)!=5:raise ValueError('PROFILE_RECORD_SHAPE')
        events.append(dict(kind=p[0],name=p[1],clock=int(p[2]),ret=int(p[3]),value=int(p[4])))
    return events


def account(events,costs):
    epochs=[];current=None;stack=[];last=None;dma=False;scope='unknown';tile=None
    # DMA completion and a return/phase callback may share an instruction.
    # Consume completion first at that clock; charge preceding interval using
    # the state before processing any event at the new clock.
    ordered=sorted(enumerate(events),key=lambda v:(v[1]['clock'],0 if v[1]['kind']=='d' else 1,v[0]))
    def finish_micro(frame):
        if frame is None or 'micro' not in frame:return
        micro=frame['micro'];row=current['tile_regions'].setdefault(micro['name'],dict(calls=0,clocks=0,max_call_clocks=0))
        row['calls']+=1;row['clocks']+=micro['cost'];row['max_call_clocks']=max(row['max_call_clocks'],micro['cost']);frame.pop('micro')
    def close(frame):
        if frame['name']=='AstraOpaqueTile':finish_micro(frame)
        table=current['routines'] if frame['kind']=='E' else current['inline_blocks']
        s=table.setdefault(frame['name'],stat());s['calls']+=1
        for k in ('inclusive_elapsed_clocks','inclusive_active_clocks','exclusive_active_clocks','dma_clocks','interrupt_clocks'):s[k]+=frame[k]
        s['max_inclusive_call_clocks']=max(s['max_inclusive_call_clocks'],frame['inclusive_elapsed_clocks'])
        s['max_exclusive_call_clocks']=max(s['max_exclusive_call_clocks'],frame['exclusive_active_clocks']);s['bytes']+=frame['bytes']
        for k in ('inclusive_dma_bytes','inclusive_dma_descriptors','own_dma_bytes','own_dma_descriptors'):s[k]+=frame[k]
    for _,event in ordered:
        t=event['clock'];kind=event['kind'];name=event['name']
        if current is not None and last is not None:
            dt=t-last
            if dt<0:raise ValueError('PROFILE_CLOCK_REGRESSION')
            interrupt=any(f['name']=='NMI' for f in stack)
            routine=next((f for f in reversed(stack) if f['kind']=='E'),None)
            block=next((f for f in reversed(stack) if f['kind']=='B'),None)
            for f in stack:
                f['inclusive_elapsed_clocks']+=dt
                if dma:f['dma_clocks']+=dt
                elif interrupt and f['name']!='NMI':f['interrupt_clocks']+=dt
                else:f['inclusive_active_clocks']+=dt
            if not dma and routine is not None:
                routine['exclusive_active_clocks']+=dt
            if not dma and not interrupt and block is not None:
                block['exclusive_active_clocks']+=dt
            tile=next((f for f in stack if f['name']=='AstraOpaqueTile'),None)
            if tile is not None and not dma and not interrupt and 'micro' in tile:tile['micro']['cost']+=dt
            c=costs[len(epochs)];production=t<=c['complete']
            pre=bool(c.get('preflight_start') is not None and last>=c['preflight_start'] and t<=c['start']+c.get('admission_to_blank_clocks',0))
            comp=any(last>=a and t<=b for a,b in current['composition_intervals'])
            if dma:category='DMA'
            elif interrupt:category='NMI'
            elif pre:category='PreflightAllocation'
            elif comp:category='Composition'
            elif routine is not None:category=routine['name']
            elif block is not None:category=block['name']
            else:category=scope
            if production:
                current['attributed'][category]+=dt
                if not pre and not comp and not dma:current['formerly_other'][category]+=dt
            else:current['release_attributed'][category]+=dt
            current['segments']+=1
        if kind=='S' and name=='OnlinePublish':
            if current is not None or stack or dma:raise ValueError('PROFILE_UNFINISHED_EPOCH')
            # The native sequence's following unsupported LEFT request is
            # verified independently; it has no production/publication epoch.
            if len(epochs)==len(costs):break
            i=len(epochs);current=dict(epoch=i,start=t,routines={},inline_blocks={},tile_regions={},attributed=defaultdict(int),formerly_other=defaultdict(int),release_attributed=defaultdict(int),counts=defaultdict(int),composition_intervals=costs[i]['composition_intervals'],segments=0)
            scope='SnapshotValidationProjection'
        elif current is not None:
            if kind in ('E','B'):
                frame=dict(kind=kind,name=name,ret=event['ret'],bytes=event['value'] if kind=='B' and 'MVN' in name else 0,**{k:0 for k in ('inclusive_elapsed_clocks','inclusive_active_clocks','exclusive_active_clocks','dma_clocks','interrupt_clocks','inclusive_dma_bytes','inclusive_dma_descriptors','own_dma_bytes','own_dma_descriptors')})
                if name=='AstraOpaqueTile':frame['micro']=dict(name='tile_setup',cost=0)
                stack.append(frame)
            elif kind=='P':
                while stack and stack[-1]['ret']==int(name):close(stack.pop())
            elif kind=='M':
                tile=next((f for f in stack if f['name']=='AstraOpaqueTile'),None)
                if tile is None:raise ValueError('PROFILE_MICRO_OUTSIDE_TILE')
                finish_micro(tile);tile['micro']=dict(name=name,cost=0)
            elif kind=='D':
                if dma:raise ValueError('PROFILE_DMA_NESTING')
                for frame in stack:
                    frame['inclusive_dma_bytes']+=event['ret'];frame['inclusive_dma_descriptors']+=1
                owner=next((f for f in reversed(stack) if f['kind']=='E'),None)
                if owner is not None:owner['own_dma_bytes']+=event['ret'];owner['own_dma_descriptors']+=1
                dma=True
            elif kind=='d':
                if not dma:raise ValueError('PROFILE_DMA_EXIT_WITHOUT_ENTRY')
                dma=False
            elif kind=='S':
                current['counts'][name]+=1
                mapping=dict(OnlinePreflight='PreflightInitialization',OnlineWorklist='WorklistReferenceLoop',OnlineAllocationStart='AllocationLoop',OnlineAllocate='AllocationLoop',OnlineBlank='BlankSetup',WarmColdBootstrap='ColdBootstrap',WarmBootstrapDone='PostBootstrapSetup',WarmRestore='RestoreLoopGlue',OnlineTile='TileIterationTransferGlue',OnlineMapsTransfer='MapCommitGlue',OnlineComplete='AuthorityEpochCommit',OnlineVblank='VblankBusyPoll')
                scope=mapping.get(name,scope)
                if name=='ForcedBlank' and 'blank_start' not in current:current['blank_start']=t
                if name in ('Release','OnlineNoopComplete'):
                    if stack or dma:raise ValueError('PROFILE_OPEN_CALL_AT_COMPLETION:'+str([f['name'] for f in stack]))
                    c=costs[len(epochs)];total=sum(current['attributed'].values());expected=c['production_clocks']
                    if total!=expected:raise ValueError('PROFILE_PRODUCTION_RECONCILIATION:'+str((total,expected)))
                    if sum(current['formerly_other'].values())!=expected-c.get('preflight_and_allocation_clocks',0)-c['composition_clocks']-c['dma_clocks']:raise ValueError('PROFILE_OTHER_RECONCILIATION')
                    current['production_clocks']=expected;current['publication_clocks']=c['publication_clocks'];current['forced_blank_clocks']=t-current['blank_start'] if 'blank_start' in current else 0;current['vblank_poll_iterations']=event['ret'] if name=='Release' else 0
                    current.pop('composition_intervals');current['reconciliation_residual_clocks']=expected-total
                    epochs.append(current);current=None
                elif name=='OnlineReject':
                    if stack or dma:raise ValueError('PROFILE_REJECTION_OPEN_CALL')
                    current=None
        last=t
    if len(epochs)!=len(costs) or current is not None or stack:raise ValueError('PROFILE_INCOMPLETE_TRACE')
    for row in epochs:
        for table in ('routines','inline_blocks'):
            for name,s in row[table].items():
                for k,v in list(s.items()):
                    if k.endswith('_clocks'):s[k[:-7]+'_ms']=v*1000/HZ
        for s in row['tile_regions'].values():s['ms']=s['clocks']*1000/HZ
        for k in ('attributed','formerly_other','release_attributed'):row[k]=dict(row[k]);row[k+'_category_ms']={n:v*1000/HZ for n,v in row[k].items()}
        row['formerly_other_clocks']=sum(row['formerly_other'].values());row['formerly_other_ms']=row['formerly_other_clocks']*1000/HZ
        row['reconciliation_residual_ms']=row['reconciliation_residual_clocks']*1000/HZ
        tile=row['routines'].get('AstraOpaqueTile',stat())
        if sum(s['clocks'] for s in row['tile_regions'].values())!=tile['inclusive_active_clocks']:raise ValueError('PROFILE_TILE_RECONCILIATION')
    return epochs


def analyze(folder,result):
    events=parse((folder/'native/mesen.log').read_text(errors='replace'))
    (folder/'profile-events.json').write_text(json.dumps(events,indent=2)+'\n')
    costs=[dict(r,composition_intervals=[]) for r in result['measured_costs']['epochs']]
    i=-1;start=None
    for e in json.loads((folder/'native/timing-events.json').read_text()):
        if e['phase']=='OnlinePublish':i+=1;start=None
        elif e['phase']=='OnlineTile':start=e['clock']
        elif e['phase']=='OnlineEncode':costs[i]['composition_intervals'].append((start,e['clock']));start=None
    for c in costs:
        if sum(b-a for a,b in c['composition_intervals'])!=c['composition_clocks']:raise ValueError('PROFILE_COMPOSITION_BOUNDARIES')
    epochs=account(events,costs)
    baseline=json.loads(Path('out/byor-motu-tile-fusion-v2/result.json').read_text())
    packets=json.loads((folder/'native/dma-packets.json').read_text())
    if packets!=json.loads(Path('out/byor-motu-tile-fusion-v2/native/dma-packets.json').read_text()):raise ValueError('PROFILE_DMA_CONTROL_DRIFT')
    for i,row in enumerate(epochs):
        for name in ('world','directory','cgram','expected'):
            ext='rgb555' if name=='expected' else 'bin'
            if (folder/f'native/{name}-{i:02d}.{ext}').read_bytes()!=Path(f'out/byor-motu-tile-fusion-v2/native/{name}-{i:02d}.{ext}').read_bytes():raise ValueError('PROFILE_CONTROL_DRIFT:'+name)
        observed=result['observations'][i]['dirty_tiles']
        if row['routines'].get('AstraOpaqueTile',stat())['calls']!=observed or row['tile_regions'].get('blend_body',dict(calls=0))['calls']!=8*observed:raise ValueError('PROFILE_TILE_COUNTS')
        row['baseline_costs']=baseline['measured_costs']['epochs'][i];row['measured_costs']=result['measured_costs']['epochs'][i]
        c=row['measured_costs'];noop=bool(c.get('render_noop'))
        row['work_counts']=dict(worklist_cells=row['counts'].get('OnlineWorklist',0),allocation_cells=row['counts'].get('OnlineAllocate',0),restore_cells=row['counts'].get('WarmRestore',0),candidate_tiles=row['counts'].get('OnlineTile',0),composed_tiles=observed,rendered_rows=8*observed)
        row['dma_bytes']=c['dma_bytes'];row['dma_descriptors']=c['dma_transfers']
        row['preflight_clocks']=0 if noop else c['allocation_start']-c['preflight_start']
        row['allocation_clocks']=c.get('allocation_clocks',0)
        row['blanked_production_clocks']=0 if noop else c['production_clocks']-c['admission_to_blank_clocks']
        row['complete_to_release_clocks']=c['publication_clocks']-c['production_clocks']
        if result['measured_costs']['epochs'][i].get('render_noop') and (row['routines'] or row['inline_blocks'] or row['forced_blank_clocks']):raise ValueError('PROFILE_NOOP_WORK')
    warm=[e for e in epochs[1:] if not e['measured_costs'].get('render_noop')]
    peak=max(warm,key=lambda e:e['formerly_other_clocks'])
    ranking=sorted(((n,max(e['formerly_other'].get(n,0) for e in warm)) for n in {n for e in warm for n in e['formerly_other']}),key=lambda x:-x[1])
    summary=dict(status='PASS',master_clock_hz=HZ,epochs=18,peak_other_epoch=peak['epoch'],peak_other_clocks=peak['formerly_other_clocks'],peak_other_ms=peak['formerly_other_ms'],peak_reconciliation_residual_clocks=peak['reconciliation_residual_clocks'],ranked_formerly_other_warm_max=[dict(name=n,clocks=v,ms=v*1000/HZ) for n,v in ranking],peak_other_attribution=peak['formerly_other_category_ms'])
    return dict(schema='BYOR_MOTU_NATIVE_COST_ATTRIBUTION_V1',summary=summary,epochs=epochs,
                baseline_macro_costs_identical=result['measured_costs']==baseline['measured_costs'],
                baseline_helper_costs_identical=result['helper_measurements']==baseline['helper_measurements'],
                boundaries='Routine entry to actual caller return fetch; inclusive elapsed includes children/DMA/interrupts. Exclusive active subtracts child routines, DMA and OnlineNmi service, while retaining inline MVN CPU/bus cost. Non-DMA non-interrupt activity includes SNES bus waits and DRAM refresh, not nominal instruction-only cycles. NMI hardware/vector dispatch before OnlineNmi is not independently isolated and stays within its scoped caller interval. DMA completion at first post-DMA instruction as in certified control. Inline/MVN and fused regions are diagnostic subsets, not extra terms in the production sum.')
