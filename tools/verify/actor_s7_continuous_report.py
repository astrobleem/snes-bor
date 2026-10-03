"""Continuous workload progress, fail-closed domains and unchanged finite prefix."""
from collections import Counter
import json
from pathlib import Path

from actor_s7_continuous import EPOCH,HORIZON

ROOT=Path(__file__).resolve().parents[2]
RUNS=(('actor_s7_dma_hprpos_s','actor_s7_dma_7jzr1hoq'),
      ('actor_s7_dma_icb30d79','actor_s7_dma_r00epu1p'))
RATE=21477270
PERIOD_MIN=357364*200
PERIOD_MAX=357368*200
OFFSETS=(6,8,16,18,20,22,24,26,52,112,180,182,194,196,208,210,212,214,216,218,220,222,224,228,230,232,234,236,238,240,242,244,246,250,252,254)


def due_bounds(emitted,remainder,committed,initial_committed=164):
    total=emitted*RATE+remainder
    added=(total+(PERIOD_MIN+PERIOD_MAX)//4)//((PERIOD_MIN+PERIOD_MAX)//2)
    assert added*PERIOD_MIN<=total<=added*PERIOD_MAX
    # The historical trace began at counter164. Replay fixtures may begin at
    # a different observed NMI counter, so keep that origin explicit.
    unadded=committed-initial_committed-added
    estimates=(emitted+(remainder+unadded*period)//RATE
               for period in (PERIOD_MIN,PERIOD_MAX))
    bounds=tuple(estimates)
    return min(bounds),max(bounds)


def state(row, returns):
    at=int(row[2])
    good=[(clock,tick) for clock,tick in returns if clock<=at]
    completed=good[-1][1] if good else 0
    emitted,remainder,committed=map(int,row[7:10])
    due_lo,due_hi=due_bounds(emitted,remainder,committed)
    # Bounds avoid guessing unobserved field parity. An interval is retained
    # if either legal parity could cross a source-tick threshold.
    actors=[dict(zip(('exists','hp','display_hp','role','frame','driver','error','x','y','target'),
                     map(int,row[21+10*s:31+10*s]))) for s in range(6)]
    return dict(clock=at,physical_field=int(row[3]),completed=completed,
        emitted=emitted,due=[due_lo,due_hi],debt=[due_lo-completed,due_hi-completed],
        prepared=int(row[13]),published=int(row[14]),prepared_id=int(row[15]),published_id=int(row[16]),
        committed_field=committed,last_processed_field=int(row[10]),
        pending_committed_fields=committed-int(row[10]),captured_fields_remaining=int(row[11]),
        owner=int(row[12]),dma_bytes=int(row[17]),oam_pending=int(row[18]),pending_dma_slots=int(row[81]),
        actors=actors,live_count=sum(bool(a['exists']) for a in actors))


def main():
    output=dict(classification='FIXTURE_EXECUTION_DOMAIN_BLOCKED',epoch=EPOCH,
        selected_horizon=HORIZON,physical_fields=128,input='neutral; no post-initialization writes',runs=[])
    data=[]
    for path,baseline in RUNS:
        d=json.loads((ROOT/'out'/path/'dma.json').read_text());data.append(d)
        old=json.loads((ROOT/'out'/baseline/'dma.json').read_text())
        assert d['semantic_rows'][:43]==old['semantic_rows']
        assert d['event_rows'][:25]==old['event_rows']
        assert d['cpu_rows'][:86]==old['cpu_rows'][:86]
        finite_endpoint=next(r for r in d['continuous_rows'] if r[1]=='S6Game_PlayRender__return' and r[6]=='43')
        finite_expected=108599290 if baseline==RUNS[0][1] else 108730224
        assert int(finite_endpoint[2])==finite_expected
        first_fault=next(r for r in d['continuous_rows'] if r[1]=='FAULT')
        fault_clock=int(first_fault[2])
        returns=[(int(r[3]),int(r[4])) for r in d['cpu_rows'] if r[1]=='S6Host_Tick__return' and int(r[3])<fault_clock]
        assert returns[-1][1]==308
        nmis=[state(r,returns) for r in d['continuous_rows'] if r[1]=='Core_Nmi_Play__done' and int(r[2])<fault_clock]
        services=Counter(r[1] for r in d['continuous_rows'] if r[1] not in ('FAULT_VALUE','FAULT') and EPOCH<=int(r[2])<fault_clock)
        changes=[];prev=None
        for r in d['semantic_rows']:
            drivers=[int(r[20+s*36+OFFSETS.index(0xe6)]) for s in range(6)]
            if drivers!=prev:changes.append(dict(tick=int(r[1]),drivers=drivers));prev=drivers
        bins=[]
        for start in range(292,384,16):
            group=[r for r in nmis if start<=r['physical_field']<start+16]
            if not group:continue
            bins.append(dict(fields=[start,min(start+15,383)],samples=len(group),
                debt_min=min(r['debt'][0] for r in group),debt_max=max(r['debt'][1] for r in group),
                first=group[0]['debt'],last=group[-1]['debt'],
                min_live=min(r['live_count'] for r in group),max_live=max(r['live_count'] for r in group)))
        commits=dict((tick,clock) for clock,tick in returns)
        entries={int(r[4]):int(r[3]) for r in d['cpu_rows'] if r[1]=='S6Host_Tick'}
        frames=[]
        for f,tick in enumerate((1,9,17,25,33,37)):
            cutoff=104073048+(tick-1)*RATE//200+357368
            frames.append(dict(frame=f,tick=tick,ready=commits[tick],cutoff=cutoff,slack=cutoff-commits[tick]))
        # Continue the same clock comparison as a diagnostic upper bound on
        # world completion for frame events, NOT source visual certification.
        events=[]
        for r in d['event_rows']:
            tick=int(r[2])
            if r[1]!='FrameChanged' or tick not in commits:continue
            cutoff=104073048+(tick-1)*RATE//200+357368
            events.append(dict(tick=tick,context=r[3],role=r[5],frame=r[4],
                world_ready=commits[tick],cutoff=cutoff,slack=cutoff-commits[tick],
                tick_entry=entries[tick],entry_slack=cutoff-entries[tick],
                frame_event_exact_timestamp_observed=False))
        output['runs'].append(dict(path=path,prefix_snapshots=43,prefix_callbacks=25,
            prefix_tick_timestamps_unchanged=True,last_successful_tick=308,
            finite_epoch_elapsed=finite_expected-EPOCH,
            first_error=state(first_fault,returns),error_value=13,error_context='1E00',
            first_unsupported_driver_tick=next(c['tick'] for c in changes if 13 in c['drivers']),
            workload_driver_changes=changes,service_counts=dict(services),subwindows=bins,
            nmi_progress=nmis,original_frame_cutoffs=frames,
            continuation_frame_world_checks=events,
            common_last_prefault_nmi=nmis[-1]))
    assert data[0]['semantic_rows']==data[1]['semantic_rows']
    assert data[0]['event_rows']==data[1]['event_rows']
    output.update(complete_tick_snapshots_equal=308,partial_fault_tick_equal=309,
                  callback_events_equal=len(data[0]['event_rows']),completed_tick_callbacks_equal=116,production_modified=False,
                  finite_envelope_result='UNCHANGED_FAIL_NOT_RELABELED',source_visual_certification=False)
    # Compare every common physical NMI boundary, not equal completed-tick endpoints.
    maps=[{s['physical_field']:s for s in r['nmi_progress']} for r in output['runs']]
    output['paired_boundaries']=[dict(field=f,baseline=maps[0][f],candidate=maps[1][f])
        for f in sorted(set(maps[0])&set(maps[1]))]
    (ROOT/'out/actor_s7_continuous_report.json').write_text(json.dumps(output,indent=2)+'\n')
    for r in output['runs']:
        print(r['path'],'fault',r['first_error']['clock'],'subwindows',r['subwindows'])
        print('last',r['common_last_prefault_nmi'])
        print('frame-world minimum slack',min(e['slack'] for e in r['continuation_frame_world_checks']))


if __name__=='__main__':main()
