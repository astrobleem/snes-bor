"""Consolidate bounded native evidence; never promote timing/engine certificates."""
import hashlib
import json
import shutil
import struct
import subprocess
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def actual_live_ledger(folder,manifest):
    """Displayed and queued references reconstructed from actual DMA events."""
    frames={(f['model'],f['role'],f['frame'],f['map']):f for f in manifest['frames']}
    preparing={};pending={};displayed=[];events=[];peak=[];peak_bytes=-1;last_use={}
    def references(packet):
        if packet['closing']:return []
        refs=[]
        for slot in range(6):
            row=packet['rows'][slot*32:(slot+1)*32]
            u=lambda o:struct.unpack_from('<H',row,o)[0]
            if not u(6):continue
            f=frames[(u(16),u(8),u(10),u(14))]
            for block in sorted({p['resource'] for p in f['pieces']}):
                refs.append(dict(sha256=block,slot=slot,model=u(16),role=u(8),frame=u(10),map=u(14),snapshot=u(12)))
        return refs
    with (folder/'mesen.log').open() as trace:
        for line in trace:
            if not line.startswith(('PACK|','QUEUED|','CONSUMED|','REJECTED_PACKET|','DISPLAY_RETIRED|')):continue
            a=line.strip().split('|')
            if a[0]=='PACK':
                preparing[int(a[4])]=dict(rows=bytes.fromhex(a[3]),closing=int(a[5]) if len(a)>5 else 0)
                continue
            clock=int(a[1])
            if a[0]=='QUEUED':
                intended,actual,tick,sequence=map(int,a[3:7])
                assert intended==actual
                pending[(actual,sequence)]=references(preparing[actual])
            elif a[0]=='REJECTED_PACKET':
                pending.pop((int(a[2]),int(a[3])))
            elif a[0]=='DISPLAY_RETIRED':displayed=[]
            else:
                key=(int(a[7]),int(a[4]));displayed=pending.pop(key)
                for ref in displayed:last_use[ref['sha256']]=clock
            blocks={}
            for ownership,refs in [('displayed',displayed)]+[(f'queued:{k[0]:04x}:{k[1]}',v) for k,v in pending.items()]:
                for ref in refs:blocks.setdefault(ref['sha256'],[]).append(dict(ref,ownership=ownership))
            live=len(blocks)*256
            events.append(dict(clock=clock,event=a[0],live_bytes=live,pending_packets=len(pending)))
            if live>peak_bytes:
                peak_bytes=live;peak=[]
                for key,refs in sorted(blocks.items()):
                    slot=manifest['blocks'][key]['slot'];tile=(slot//8)*64+(slot%8)*2
                    peak.append(dict(sha256=key,size=256,placement_slot=slot,
                        vram_byte_ranges=[[0x8000+(tile+16*r)*32,0x8000+(tile+16*r)*32+64] for r in range(4)],references=refs))
    assert not any(pending.values()) and not displayed,'Epoch closed before actual source hardware references retired'
    for b in peak:b['last_actual_consumption']=last_use[b['sha256']]
    return dict(peak_minimum_emitted_block_bytes=peak_bytes,available_bytes=8192-256*len(manifest.get('reserved_slots',[])),
        pinned_admitted_bytes=manifest['required_bytes'],fragmentation_bytes=0,
        peak_blocks=peak,events=events,terminal_displayed_bytes=0,terminal_pending_packets=0,
        terminal_shared_source_excluded_packets=len(pending),
        source_pixel_global_minimum_proven=False)


def main():
    output=ROOT/'out/s7_delivery';output.mkdir(exist_ok=True)
    result=dict(status='S7_PUBLISHER_COMPLETE_WITH_BOUNDED_ADMISSION',
        whole_engine_certified=False,whole_pak_certified=False,strict_latency_certified=False,
        production_policy='ACCEPTED_COMPAT_UNCHANGED',
        vram_bytes=[0x8000,0xA000],cgram_bytes=[0x1C0,0x200],
        immutable_oam_buffers=[0x7F8D00,0x7FA600],cases={},controls={})
    history=subprocess.check_output(['git','log','--reverse','--format=%H%x09%s',
        'cf79e2a9b0fbe76c4cd84f16a0b0b803b13c4daa..HEAD'],cwd=ROOT,text=True)
    result['implementation_commits']=[dict(zip(('hash','subject'),line.split('\t',1))) for line in history.splitlines()]
    for case,foldername in [('maps','s7_lease_enforced_maps'),('bonus','s7_lease_enforced_bonus'),
                            ('palette-phase','s7_lease_enforced_phase_02'),('epoch-reuse','s7_lease_enforced_epoch'),
                            ('mixed','s7_dma_lease_negative')]:
        folder=ROOT/'out'/foldername
        manifest=json.loads((folder/'publisher-multi.json').read_text())
        proof=json.loads((folder/'multi-proof.json').read_text())
        teardown=json.loads((folder/'teardown.json').read_text())
        assert proof['resource_status']=='PASS' and not proof['publication_faults'] and not proof['live_packet_overwrites']
        assert all(p['bad_pixels']==0 for p in proof['proofs'])
        assert proof['proofs'] and not proof['publication_order_regressions']
        assert not proof['admission_blocked'],'A positive bounded workload exhausted its admitted descriptor set'
        assert not proof['vram_live_reference_violations']
        assert teardown[-1]==dict(phase=3,pending=['0000','0000'],hardware_hidden=True)
        ledger=actual_live_ledger(folder,manifest)
        (output/f'{case}-live-ledger.json').write_text(json.dumps(ledger,indent=2))
        sample=max(proof['proofs'],key=lambda p:sum(a[2]+a[3] for a in p['instances']))
        shutil.copyfile(folder/sample['screenshot'],output/f'{case}.png')
        result['cases'][case]=dict(path=str(folder.relative_to(ROOT)),rom_sha256=sha(folder/'bor.sfc'),msu_sha256=sha(folder/'bor.msu'),
            manifest_sha256=sha(folder/'publisher-multi.json'),trace_sha256=sha(folder/'mesen.log'),
            frame_coverage=proof['frame_coverage'],pinned_bytes=manifest['required_bytes'],
            available_source_bytes=ledger['available_bytes'],
            peak_actual_live_bytes=ledger['peak_minimum_emitted_block_bytes'],
            palette_slots=2 if manifest.get('packet_palettes') else len(manifest['palettes']),
            palette_identities=len(manifest['palettes']),atomic_palette_packets=manifest.get('packet_palettes',False),
            transfers=len(proof['transfer_completions']),transfer_bytes=sum(t[1] for t in proof['transfer_completions']),
            queued_packets=len(proof['queued_packets']),visible_proofs=len(proof['proofs']),
            maximum_oam=max(p['oam_pieces'] for p in proof['proofs']),
            maximum_scanline_slivers=max(p['max_scanline_slivers'] for p in proof['proofs']),
            last_entry_transfer_completed=max(t[0] for t in proof['transfer_completions']),example=sample,
            next_field_preparation_misses=proof['missed_next_field_opportunities'],
            snapshot_next_field_misses=[p['snapshot'] for p in proof['proofs'] if not p['captured_next_field_consumption']],
            capture_to_preparation_clocks=dict(min=min(p['prepared']-p['snapshot_capture'] for p in proof['proofs']),
                median=statistics.median(p['prepared']-p['snapshot_capture'] for p in proof['proofs']),
                max=max(p['prepared']-p['snapshot_capture'] for p in proof['proofs'])),
            strict_snapshot_latency=proof['strict_snapshot_next_field_timing'],teardown=teardown,
            shared_admission=proof.get('shared_resources',[]),
            ownership_negative_after_positive_workload=(case=='mixed'),
            scope='Animation-only publication probe in real slots; no AI/numeric/whole-model certification')
        if manifest.get('packet_palettes'):
            assert proof['palette_completions'] and all(p[3]==0 for p in proof['palette_completions'])
            result['cases'][case].update(palette_transactions=len(proof['palette_completions']),
                palette_prepare_min=min(p[0] for p in proof['palette_prepare_calls']),
                palette_prepare_max=max(p[0] for p in proof['palette_prepare_calls']),
                cgram_completed_before_oam_in_same_field=True)
        if case=='epoch-reuse':
            assert not proof['vram_live_reference_violations']
            assert proof['terminal_source_references']==dict(displayed=False,queued=0)
            assert proof['compat_oam_transfers'] and all(p[2]==0 for p in proof['compat_oam_transfers'])
            result['cases'][case].update(epoch_reuse=json.loads((folder/'epoch-reuse.json').read_text()),
                ordinary_oam_transfers_verified=len(proof['compat_oam_transfers']))
        for miss in result['cases'][case]['next_field_preparation_misses']:
            q=next(q for q in proof['queued_packets'] if q[4]==miss['snapshot'])
            miss.update(queued=q[0],queued_field=q[1],
                first_unavailable_dependency='IMMUTABLE_OAM_PACKET_NOT_SUBMITTED_BEFORE_NEXT_NMI',
                tiles_already_completed=True,
                palette_completion_policy='SAME_VBLANK_TRANSACTION_BEFORE_OAM' if manifest.get('packet_palettes') else 'ENTRY_COMPLETED',
                preparation_to_queue_elapsed_including_interrupts=q[0]-miss['prepared'])
    expected={'single':'2736cfead18747c3b8e7ff8760166ca9bf87d25c21d09624fd033cbd4502aef1',
              'sync':'67953df872febe68731b8e0d363ee2bdff4b21c8ee2598213ed13427c1285430',
              'stagger':'2ee5cdfa6924a3f002d7e91a1257abdd8db99001af27548a47ffdac9193c7752'}
    for name,digest in expected.items():
        folder=ROOT/('out/s7_closure_single' if name=='single' else f'out/s7_final_{name}');proof=json.loads((folder/'stream-publication.json').read_text())
        assert sha(folder/'bor.sfc')==digest and proof['all_six_pixels'] and not proof['readiness_miss_count']
        result['controls'][name]=dict(path=str(folder.relative_to(ROOT)),rom_sha256=digest,msu_sha256=sha(folder/'bor.msu'),
            all_six_pixels=True,readiness_misses=0,identical_accepted_rom=True)
    for name,folder,hp in [('compat','actor_s6_production_world_hzd_2r_t',96),('exact','actor_s6_production_world_tyzzz57n',95)]:
        p=ROOT/'out'/folder;proof=json.loads((p/'proof.json').read_text())
        assert proof['final']['rows'][2]['hp']==hp
        result['controls'][name]=dict(path=str(p.relative_to(ROOT)),victim_hp=hp,proof_sha256=sha(p/'proof.json'))
    result['foreign_probes']=json.loads((ROOT/'out/s7_foreign_publication.json').read_text())
    rejected=json.loads((ROOT/'out/s7_map_switch_delivery_02/multi-proof.json').read_text())
    result['rejected_same_height_maps']=dict(path='out/s7_map_switch_delivery_02',
        status='RESOURCE_BLOCKED_EMITTED_SCANLINE_LAYOUT',available_slivers=34,
        required_slivers=max(p['max_scanline_slivers'] for p in rejected['proofs']),
        observed_missing_pixels=max(p['bad_pixels'] for p in rejected['proofs']),
        source_pixel_global_minimum_proven=False)
    guarded=ROOT/'out/s7_final_scanline_guard_02'
    rejection=json.loads((guarded/'multi-proof.json').read_text())
    assert rejection['resource_status']=='RESOURCE_BLOCKED' and not rejection['proofs']
    assert rejection['terminal_source_references']==dict(displayed=False,queued=0)
    result['native_resource_rejection']=dict(path=str(guarded.relative_to(ROOT)),
        trace_sha256=sha(guarded/'mesen.log'),status='REJECTED_BEFORE_SOURCE_HARDWARE_PUBLICATION',
        closed_through_public_api=True)
    retirement=ROOT/'out/s7_display_retirement_02'
    events=json.loads((retirement/'display-retirement.json').read_text())
    assert len(events)==1 and events[0][1:3]==[0,0] and 225<=events[0][3]<=261
    result['displayed_framing_rejection']=dict(path=str(retirement.relative_to(ROOT)),
        trace_sha256=sha(retirement/'mesen.log'),actual_retirement=events,
        source_pixels_removed=True,accepted_oam_and_cgram_preserved=True)
    denied=json.loads((ROOT/'out/s7_dma_lease_negative/dma-lease-rejection.json').read_text())
    assert len(denied)==2 and {d[1] for d in denied}=={0,2} and all(d[-2:]==[0,0] for d in denied)
    result['consumer_lease_rejection']=dict(path='out/s7_dma_lease_negative',
        actual_requests=denied,status='VRAM_AND_CGRAM_UNCHANGED')
    from actor_s5_isolated import Source,parse_model
    from source_publication_set import live_set_report
    source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
    model=parse_model(source,'data/chars/kula/kula.txt','Kula','resource-fixture','historical-bor')
    requests=[dict(model=model,runtime_id=22,role='attack1',role_id=0,frames=[i],maps=[0]) for i in range(6)]
    blocked=live_set_report(source,[dict(identity='six-independent-source-frames',ownership='new_packet',requests=requests)])
    assert blocked['status']=='RESOURCE_BLOCKED' and blocked['required_bytes']>8192
    blocked['scope']='Dry simultaneous-packet layout diagnostic, not a six-actor runtime benchmark'
    (output/'blocked-packet-ledger.json').write_text(json.dumps(blocked,indent=2))
    result['blocked_packet']=dict(required_bytes=blocked['required_bytes'],available_bytes=8192,
        fragmentation_bytes=0,scope=blocked['scope'],lower_bound='EMITTED_INDIVISIBLE_BLOCK_ABI_ONLY')
    result['remaining_blockers']=dict(
        CPU=['Strict source-snapshot/display latency remains uncertified; six-actor early/burst failures retained.',
             'Current long-cycle and palette workload preparation misses are listed individually above; no transfer margin inferred.'],
        NUMERIC=['Unrestricted movement/gravity/decimal drift outside bounded Watcom-family proof.'],
        AI=['Runoff driver13 and other previously unsupported behavior/effect paths.'],
        MEDIA=['SEWER; independent model role-media gaps are not changed by a frame publisher.'],
        DIALECT=['Foreign palette/transparency/remap interpretation blocks TMNT/He-Man publication certification.'],
        RESOURCE=['Pinned tile set <=8192 bytes and <=16 linked frame/map keys; arbitrary larger future pools need another residency strategy.',
                  'Two physical palette slots; packet palettes stream more identities, at most two admitted simultaneous instance slots.',
                  'Same-height two-Lobster layout exceeds34 slivers; current native admission rejects it before publication.',
                  'Full-frame packer bounds are not proofs of global SNES artwork impossibility.'],
        ENVIRONMENT=['Water, rocking, depth-dependent blocked/endhole, alias/opponent HUD unchanged.'],
        SPECIAL_EFFECT=['Time timer/lifecycle, auxiliary flash/audio/combo capability gaps unchanged.'])
    phase=result['cases']['palette-phase'];epoch=result['cases']['epoch-reuse']
    result['publisher_capabilities']=dict(
        compiler_source_frames=all(c['visible_proofs']>0 for c in result['cases'].values()),
        coherent_snapshots=all(c['visible_proofs']>0 for c in result['cases'].values()) and bool(events),
        native_tile_palette_completion=phase['palette_transactions']>0,
        legal_vram=all(c['pinned_bytes']<=c['available_source_bytes'] for c in result['cases'].values()),
        shared_oam_admission=all(c['shared_admission'] for c in result['cases'].values()),
        consumer_graphics_lease=bool(denied),
        simultaneous_instances=result['controls']['sync']['all_six_pixels'],
        independent_phases=result['controls']['stagger']['all_six_pixels'],
        distinct_models=len({a[1] for a in phase['example']['instances']})==2,
        alternate_map_ge4=any(a[3]>=4 for a in phase['example']['instances']),
        deterministic_release_reuse=epoch['epoch_reuse'][-1]==dict(event='reopen',phase=0,generation=1),
        explicit_resource_diagnostics=result['blocked_packet']['required_bytes']>8192,
        accepted_compat=epoch['ordinary_oam_transfers_verified']>0 and result['controls']['compat']['victim_hp']==96)
    assert all(result['publisher_capabilities'].values())
    result['scope']='PUBLISHER_CAPABILITIES_WITH_EXPLICIT_ADMISSION; TIMING_BLOCKED_WORKLOADS_REMAIN_FAILED'
    (output/'report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:{x:y for x,y in v.items() if x in ('rom_sha256','pinned_bytes','peak_actual_live_bytes','visible_proofs','next_field_preparation_misses')} for k,v in result['cases'].items()},indent=2))


if __name__=='__main__':main()
