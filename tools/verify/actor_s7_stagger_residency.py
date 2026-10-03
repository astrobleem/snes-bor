"""Reconstruct the blocked resource set from native packet/DMA evidence."""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def resources(folder):
    manifest=json.loads((folder/'publisher-frame.json').read_text())
    rom=(folder/'bor.sfc').read_bytes();image=bytearray((folder/'publisher-assets.bin').read_bytes()[:8192])
    catalog={};frames=[]
    for index,f in enumerate(manifest['frames']):
        for j in manifest['jobs']:
            if j['frame']!=index:continue
            at=j['target']-0x8000;source=33*32768+j['source']-0x8000
            image[at:at+j['size']]=rom[source:source+j['size']]
        refs={}
        for c in f['chunks']:
            spans=[(0x8000+(c['tile']+row*16)*32,64) for row in range(4)]
            data=b''.join(image[a-0x8000:a-0x8000+n] for a,n in spans)
            key=hashlib.sha256(data).hexdigest()
            catalog.setdefault(key,dict(data=data,frames=[]))['frames'].append(index)
            refs[key]=spans
        frames.append(refs)
    return manifest,rom,catalog,frames


def audit(folder):
    manifest,rom,catalog,frames=resources(folder)
    report=json.loads((folder/'stream-publication.json').read_text())
    packets=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        if not line.startswith('S7PACK|'):continue
        _,clock,field,raw=line.split('|');raw=bytes.fromhex(raw)
        actors=[]
        for i in range(6):
            row=raw[i*32:(i+1)*32];u=lambda n:struct.unpack_from('<H',row,n)[0]
            if u(6):actors.append(dict(slot=i,frame=u(10),tick=u(12)))
        packets.append(dict(clock=int(clock),field=int(field),actors=actors))
    def associated(c):
        candidates=[p for p in packets if p['clock']<c['clock'] and p['actors'] and p['actors'][0]['tick']==c['snapshot_tick']]
        return max(candidates,key=lambda p:p['clock']) if candidates else dict(actors=[])
    completions=[dict(c,actors=associated(c)['actors']) for c in report['consumed_packets']]
    rows=[]
    for miss in report['readiness_misses']:
        consumed=max((c for c in completions if c['clock']<miss['clock']),key=lambda c:c['clock'])
        assert consumed['bad_oam_bytes']==0 and consumed['palette_match']
        displayed=consumed['actors'];new=miss['instances']
        queued=[p for p in packets if consumed['clock']<p['clock']<miss['clock']]
        assert not queued,'Unaccounted queued publication'
        assert all(j['state']==0 for j in miss['unfinished_jobs']),'Unaccounted in-flight DMA'
        required=set().union(*(frames[a['frame']].keys() for a in displayed+new))
        image=bytearray((folder/'publisher-assets.bin').read_bytes()[:8192])
        for e in report['events']:
            if e['name']!='Core_Dma_ProcessQueue__next' or e['bank']!=33 or e['clock']>=miss['clock']:continue
            check=next(t for t in report['transfer_checks'] if t['clock']==e['clock'])
            assert not check['bad_bytes'] and not check['live_overwrite']
            at=e['target']-0x8000;source=33*32768+e['source']-0x8000
            image[at:at+e['length']]=rom[source:source+e['length']]
        blocks=[];protected=set()
        for key in sorted(required):
            drefs=[a for a in displayed if key in frames[a['frame']]]
            nrefs=[a for a in new if key in frames[a['frame']]]
            ranges={str(a['frame']):frames[a['frame']][key] for a in drefs+nrefs}
            for a in drefs:
                for at,n in frames[a['frame']][key]:protected.update(range(at,at+n))
            history=[c for c in completions if any(key in frames[a['frame']] for a in c['actors'])]
            past=[c for c in history if c['clock']<miss['clock']]
            demands=[dict(kind='consumed',clock=c['clock'],tick=c['snapshot_tick']) for c in history]
            demands += [dict(kind='required_miss',clock=m['clock'],tick=m['snapshot_tick']) for m in report['readiness_misses'] if any(key in frames[a['frame']] for a in m['instances'])]
            demands.sort(key=lambda d:d['clock'])
            placement=next(iter(ranges.values()))
            native=b''.join(image[at-0x8000:at-0x8000+n] for at,n in placement)
            next_release=next((c['clock'] for c in completions if c['clock']>miss['clock'] and not any(key in frames[a['frame']] for a in c['actors'])),None) if drefs else None
            blocks.append(dict(sha256=key,size=256,vram_byte_ranges=ranges,
                actor_references=dict(displayed=drefs,new_packet=nrefs),source_frames=sorted(set(catalog[key]['frames'])),
                ownership=(['currently_displayed'] if drefs else [])+(['required_new_packet'] if nrefs else []),
                first_required_publication=demands[0],final_required_publication_in_trace=demands[-1],
                last_actual_hardware_consumption=past[-1]['clock'] if past else None,
                earliest_observed_safe_release=next_release,
                matching_bytes_at_compiled_placement=sum(a==b for a,b in zip(native,catalog[key]['data']))))
        free=set(range(0x8000,0xA000))-protected
        resident=[]
        for slot in range(32):
            tile=(slot//8)*64+(slot%8)*2
            spans=[(0x8000+(tile+r*16)*32,64) for r in range(4)]
            addresses={a+i for a,n in spans for i in range(n)}
            data=b''.join(image[a-0x8000:a-0x8000+n] for a,n in spans)
            referenced_new=[a for a in new if any(addresses.intersection(range(start,start+n)) for rs in frames[a['frame']].values() for start,n in rs)]
            resident.append(dict(slot=slot,actual_sha256=hashlib.sha256(data).hexdigest(),size=256,
                vram_byte_ranges=spans,ownership='currently_displayed' if addresses&protected else
                'new_packet_partial_or_ready' if referenced_new else 'retained_but_unreferenced',
                new_packet_references=referenced_new))
        longest=run=0
        for at in range(0x8000,0xA000):
            run=run+1 if at in free else 0;longest=max(longest,run)
        tiles={b[n:n+32] for key in required for b in [catalog[key]['data']] for n in range(0,256,32)}
        rows.append(dict(miss=miss,last_consumed_packet=consumed,blocks=blocks,
            resident_allocations=resident,optional_future_prefetch_bytes=0,
            block_accounting_bytes=sum(b['size'] for b in blocks),displayed_bytes=len(protected),
            free_from_displayed_bytes=len(free),largest_free_contiguous_byte_run=longest,
            queued_unconsumed_packets=[],inflight_transfers=[],
            unique_8x8_tile_bytes=len(tiles)*32,
            note='256-byte block sum is not a proof that overlapping identical 8x8 tile placements cannot fit.'))
    return dict(scope='ACTUAL_BLOCKED_BOUNDARIES; NO_MINIMUM_PLACEMENT_CLAIM',
                rom_sha256=hashlib.sha256(rom).hexdigest(),misses=rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--replacement',type=Path)
    args=parser.parse_args();result=audit(args.folder)
    if args.replacement:
        manifest,rom,catalog,frames=resources(args.replacement)
        live=set(frames[3])|set(frames[4])|set(frames[5])
        proof=json.loads((args.replacement/'stream-publication.json').read_text())
        blocks=[]
        for key in sorted(live):
            consumers=[dict(packet=name,**p['hardware_consumed']) for name,p in proof['packet_proofs'].items()
                       if any(key in frames[f] for f in p['frames'])]
            blocks.append(dict(sha256=key,size=256,source_frames=sorted(set(catalog[key]['frames'])),
                vram_ranges_by_frame={str(f):frames[f][key] for f in (3,4,5) if key in frames[f]},
                proven_hardware_consumers=consumers))
        result['replacement']=dict(rom_sha256=hashlib.sha256(rom).hexdigest(),
            simultaneous_frames=[3,4,5],blocks=blocks,bytes=len(live)*256,available=8192,
            readiness_misses=proof['readiness_miss_count'],transfers_safe=proof['transfers_safe'],
            packet_fences_pass=proof['packet_fences_pass'],
            transfer_completion_trace=proof['transfer_checks'],consumed_packets=proof['consumed_packets'],
            late_packet=proof['packet_proofs']['0:5,1:5'],
            note='Constructive placement upper bound, not a global minimum. Actual fences remain authoritative.')
    args.output.write_text(json.dumps(result,indent=2))
    print([(r['block_accounting_bytes'],r['displayed_bytes'],r['free_from_displayed_bytes'],r['largest_free_contiguous_byte_run'],r['unique_8x8_tile_bytes']) for r in result['misses']])
