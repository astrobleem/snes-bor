"""Build a private warm-presentation candidate over the audited audio/world ROM."""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import re

from compiler import Source
from m4_live_world_native import assemble, require, sha
from m4_input_controller_native import offset
from source_warm_presentation_assets import prepare, LEASE_END
from source_warm_presentation_native import helper, relocate
from source_live_tick_service import emit as tick_service
from source_warm_row_decode_native import emit as row_decoder

BASE=Path('out/byor-motu-live-world-v1/audio-full-v15')
BASE_SHA='8964ddc6587b35fb233c0aea7f53eb2daff479d95872110c151a5286826d629b'
PUBLISHER=Path('out/byor-motu-abort-copy-v1/success/native/publisher.pasm')
PUBLISHER_SHA='d3c15883fea47dea3cca8dfee6f722f995a4de39830b2c6b62ddc5c66c5d69cf'


def build(source, folder):
    require(not folder.exists(),'WARM_FRESH_OUTPUT');folder.mkdir(parents=True)
    baseline=(BASE/'bor.sfc').read_bytes();require(sha(baseline)==BASE_SHA,'WARM_BASE_SHA')
    contract=json.loads((BASE/'contract.json').read_text());sy=contract['symbols']
    text=PUBLISHER.read_text();require(sha(PUBLISHER.read_bytes())==PUBLISHER_SHA,'WARM_PUBLISHER_SHA')
    writes,config=prepare(Source(source),baseline)
    from source_warm_tile_native import emit as tile
    h=helper(config,sy)+tick_service(sy,sy).replace('jsl LiveWorldDispatch_Run',f"jsl ${sy['LiveWorldDispatch_Run']:06X}")
    h+=row_decoder()+tile(config['lut_cpu'],planes_cpu=config['color_planes_cpu'])+'\nWarmNative_CodeEnd:\n.a16\n.i16\n'
    binary,hs=assemble(h,folder,'warm-helper')
    require(hs['WarmMain']==0x2b8000 and hs['WarmNative_CodeEnd']<=0x2c0000,'WARM_CODE_EXTENT')
    renderer=relocate(text,config,hs)
    sections=[]
    def section(m):
        prefix=''
        if sections:prefix=f'WarmSectionEnd{len(sections)-1}:\n.a16\n.i16\n'
        sections.append(dict(start=0x2e0000+int(m[2],16)))
        return prefix+m[1]
    annotated=re.sub(r'((?:\.bank 46\n)?\.org \$([A-F0-9]+)\n)',section,renderer)
    annotated+=f'\nWarmSectionEnd{len(sections)-1}:\n.a16\n.i16\n'
    rb,rs=assemble(annotated,folder,'warm-publisher')
    require(rs['OnlinePublish']==0x2e8000,'WARM_RENDER_ENTRY')
    for i,item in enumerate(sections):
        item['end']=rs[f'WarmSectionEnd{i}']
        require(0x2e8000<=item['start']<=item['end']<=0x2f0000,'WARM_RENDER_SECTION_EXTENT')
    ordered=sorted(sections,key=lambda r:r['start'])
    require(all(a['end']<=b['start']for a,b in zip(ordered,ordered[1:])),
            'WARM_RENDER_SECTION_OVERLAP')
    require(all(0x2e8000<=v<=0x2f0000 for v in rs.values()),'WARM_RENDER_SYMBOL_BANK')
    # An unchanged byte-for-byte critical algorithm is certified by source
    # blocks, while ordinary branch relocation and explicit yield hooks are
    # visible in the retained PASM. Do not change the guarded batch policy.
    for a,b in (('WarmDirectPair:','.org $E000'),('NbQueueDirectPair:','NbCapacityPredict:'),
                ('CfFuse:',None)):
        before=text[text.index(a):text.index(b,text.index(a)) if b else len(text)]
        after=renderer[renderer.index(a):renderer.index(b,renderer.index(a)) if b else len(renderer)]
        if a=='CfFuse:':
            # This final source block includes subsequent abort-copy section.
            before=before.replace('.bank 57\n','.bank 46\n')
        require(before==after,'WARM_CRITICAL_SOURCE:'+a)
    # No returned abort/fault/yield is reachable after the first map DMA.
    # This is a two-map visible transaction; instruction interruption during
    # it is unqualified rather than claimed to retain an old complete frame.
    for a,b in (('NbMapCommit:','NbAbort:'),('CfFuse:','CfCodeEnd:')):
        tail=renderer[renderer.index(a):renderer.index(b,renderer.index(a))]
        require(not re.search(r'\b(?:NbAbort|OnlineReject|WarmYield)\b',tail),
                'WARM_POST_MAP_FAULT_OR_YIELD')
    require(' jsr SpReadyBoundary\n jsr NbFreshVblank_WithoutYield\n' in renderer,
            'WARM_FINAL_WAIT_YIELDS_AFTER_GUARD')
    raw=bytearray(baseline);ranges=[]
    def write(at,data,reason,empty=False):
        require(0<=at<at+len(data)<=len(raw),'WARM_WRITE_EXTENT')
        if empty:require(not any(raw[at:at+len(data)]),'WARM_WRITE_NONZERO:'+reason)
        if any(at<r['offset']+r['bytes'] and r['offset']<at+len(data)for r in ranges):
            raise ValueError('WARM_WRITE_OVERLAP:'+reason)
        raw[at:at+len(data)]=data;ranges.append(dict(offset=at,bytes=len(data),sha256=sha(data),reason=reason))
    for w in writes:write(w['offset'],w['data'],w.get('reason',f"source image {w.get('image')}"),True)
    start=43*32768;write(start,binary[start:offset(hs['WarmNative_CodeEnd'])],'warm presentation, real tick service and lossless row decoder',True)
    start=46*32768;write(start,rb[start:start+32768],'relocated accepted publisher with source row front end',True)
    at=offset(sy['LiveWorld_Outer'])
    require(raw[at:at+3]==bytes.fromhex('a90000'),'WARM_OUTER_ENTRY')
    write(at,b'\x5c'+hs['WarmMain'].to_bytes(3,'little'),'actual world loop hands foreground to warm scheduler')
    # Extend the exact same exclusive old-scene acquisition, including its
    # full clear, through the original SceneVideo row end. No old producer or
    # foreground resumes after the existing ownership marker is published.
    clear=offset(sy['LiveWorld_ClearRetiredVideo']);end=clear+32
    old_extent=contract['config']['retired_scene_video'][1]-0x7e6200
    needle=b'\xe0'+old_extent.to_bytes(2,'little')
    hits=[i for i in range(clear,end)if raw[i:i+3]==needle]
    require(len(hits)==1,'WARM_CLEAR_EXTENT_SHAPE')
    write(hits[0],b'\xe0'+(LEASE_END-0x7e6200).to_bytes(2,'little'),'extend guarded retired SceneVideo clear and exclusive lease')
    config.update(native_integration=True,retained_original_cold_publisher=True,
                  renderer_range=[0x2e8000,max(r['end']for r in sections)],
                  renderer_sections=sections,
                  yield_iram_guard_range=[0x003400,0x0036e0],
                  yield_iram_guard_bytes=736,
                  returned_failure_checks_before_map_dma=True,
                  interrupted_visible_transaction_qualified=False,
                  cooperative_yield_sites=['whole scan cell every32','before fresh vblank wait'],
                  minimum_batch_map_safety_clocks=10000,
                  published_snapshot=0x7e9700,latest_snapshot=0x7e7800,
                  baseline_source_publisher_sha256=PUBLISHER_SHA,
                  critical_pair_and_fused_collector_source_unchanged=True,
                  limitations=['one naturally born He_Man SELECT/IDLE/WALK, map0, zero camera and altitude',
                               'private single foreground owner, unsupported poses stop visibly',
                               'native pixels/input/timing certification pending; no target frame rate claim'])
    report=copy.deepcopy(contract)
    report.update(schema='BYOR_WARM_WORLD_BUILD_V1',status='STATIC_CANDIDATE',
                  accepted_audio_world_sha256=BASE_SHA,rom_sha256=sha(raw),warm_ranges=ranges,
                  symbols={**sy,**hs,**{'WarmRenderer_'+k:v for k,v in rs.items()}})
    report['config']['warm']=config
    report['config']['retired_scene_video'][1]=LEASE_END
    report['renderer_bank_unchanged']=raw[57*32768:58*32768]==baseline[57*32768:58*32768]
    require(report['renderer_bank_unchanged'],'WARM_ORIGINAL_COLD_CHANGED')
    (folder/'bor.sfc').write_bytes(raw)
    os.link((BASE/'bor.msu').resolve(),folder/'bor.msu')
    (folder/'contract.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=build(a.source,a.output)
    print(json.dumps(dict(status=r['status'],rom_sha256=r['rom_sha256'],writes=len(r['warm_ranges']))))
