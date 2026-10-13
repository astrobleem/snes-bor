"""Real controller -> persistent native source player -> component input.

Bounded host snapshot bridge, not a continuous native compositor. Uses existing
constructor/ground/frame/velocity/check_move owners and component compiler.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
from actor_s5_entity_fixture import symbols
import game_bor_startup_select as startup
from m4_live_ground_owner import REQUEST,EPOCH,SNAPSHOT
from compiler import Source
from source_animation_init_4086 import derive as animation_inputs
from source_model_registry import derive as model_inputs
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from bg_components import compile_frame
from m4_bg_components_native import compile_rom


def sha(raw):return hashlib.sha256(raw).hexdigest()


def check_motion(samples):
    """Independent signed product and stable-token checks on sealed epochs."""
    raw=[Path(s['snapshot']).read_bytes() for s in samples]
    if any(len(r)!=146 or sha(r)!=s['sha256'] for r,s in zip(raw,samples)):
        raise ValueError('MOVEMENT_SNAPSHOT_IDENTITY')
    token=raw[0][:4];checks=[]
    for i,(old,new) in enumerate(zip(raw,raw[1:]),1):
        mobility,vx,vz=struct.unpack_from('<3i',new,112)
        dx,dz=(vx*mobility)//131072,(vz*mobility)//131072
        before=struct.unpack_from('<i',old,52)[0],struct.unpack_from('<i',old,60)[0]
        after=struct.unpack_from('<i',new,52)[0],struct.unpack_from('<i',new,60)[0]
        label=samples[i]['label'];physical={'right':0x100,'up':0x800,'released':0}[label]
        checks.append(dict(epoch=i,dx_q16=dx,dz_q16=dz,
            exact=(after==(before[0]+dx,before[1]+dz) and new[:4]==token and
                   samples[i]['raw_controller']==physical and struct.unpack_from('<H',new,144)[0]==i)))
    if not checks or not all(c['exact'] for c in checks):raise ValueError('MOVEMENT_SOURCE_DELTA_OR_CONTROLLER_MISMATCH')
    return checks


def capture(folder,sy):
    fixture=folder/'world';script=fixture/'callback_owner.lua'
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kw):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kw)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    samples=[];reporter=Reporter('MOTU-LIVE-GROUND',kind='GATE')
    with Observed(rom=fixture/'bor.sfc',mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=fixture/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('LIVE_GROUND_BOOTSTRAP')
        run_frames_exact(m,12)
        # Explicit S-CPU write permission for the private BW-RAM service lease.
        m.write_u8(0x2226,0x80);m.write_u8(0x2228,0)
        for n in ('StageWater_Enabled','StageWater_Pending','StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'):m.write_u8(sy[n],0)
        m.write_u16(REQUEST,0xb4e7)
        for _ in range(100):
            run_frames_exact(m,1)
            raw=m.read_memory('SnesMemory',SNAPSHOT,146)
            if struct.unpack_from('<I',raw,4)[0]==1:break
        else:raise ValueError('LIVE_GROUND_CONSTRUCTOR_TIMEOUT')
        def read_sample(label):
            raw=m.read_memory('SnesMemory',SNAPSHOT,146)
            path=folder/f'snapshot-{len(samples):02d}.bin';path.write_bytes(raw)
            samples.append(dict(label=label,epoch=struct.unpack_from('<H',raw,144)[0],
                raw_controller=startup.u16(m,sy['SourceInputController_Raw1']),
                x_q16=struct.unpack_from('<i',raw,52)[0],z_q16=struct.unpack_from('<i',raw,60)[0],
                snapshot=str(path),sha256=sha(raw)))
        read_sample('birth')
        # Actual input API controls JOY1. Only the request word is debugger-written.
        for label,buttons in [('right',m.BTN_RIGHT)]*4+[('released',0)]+[('up',m.BTN_UP)]*5+[('released',0)]:
            m.hold_input(buttons,port=0)
            run_frames_exact(m,2)
            old=startup.u16(m,SNAPSHOT+144);m.write_u16(REQUEST,0xb4e8)
            for _ in range(100):
                run_frames_exact(m,1)
                if startup.u16(m,0x7ffb84):
                    (folder/'fault-state.json').write_text(json.dumps(m.get_cpu_state(),indent=2))
                    raise ValueError('LIVE_GROUND_NATIVE_FAULT')
                if startup.u16(m,SNAPSHOT+144)==old+1:break
            else:raise ValueError('LIVE_GROUND_STEP_TIMEOUT')
            read_sample(label)
        m.hold_input(0,port=0)
    (folder/'snapshots.json').write_text(json.dumps(samples,indent=2)+'\n')
    return samples


def scene_from_snapshot(raw,source):
    if len(raw)!=146 or struct.unpack_from('<I',raw,4)[0]!=1:raise ValueError('SNAPSHOT_NOT_LIVE')
    model_id,_,handle,frame=struct.unpack_from('<4H',raw,80)
    model=next(m for m in model_inputs(source)['models'] if m['id']==model_id)
    anim=next(a for a in animation_inputs(source)['animations'] if a['handle']==handle and a['model']==model['identity'])
    def q(at):return struct.unpack_from('<i',raw,at)[0]/65536
    return dict(viewport=[256,224],camera=[0,0],actors=[dict(model=model['identity'],animation=anim['role'],frame=frame,
        position=[q(52),q(60),q(12)],direction=struct.unpack_from('<I',raw,28)[0],order=0,map=0)])


def prepare_samples(folder,source,stage,samples):
    results=[];last=None
    for i,sample in enumerate(samples):
        raw=Path(sample['snapshot']).read_bytes()
        if sha(raw)!=sample['sha256']:raise ValueError('SNAPSHOT_IDENTITY_CHANGED')
        assets=folder/f'frame-{i:02d}';assets.mkdir(exist_ok=True)
        scene=scene_from_snapshot(raw,source);canvas,metadata=compose_rgb8(source,stage,scene)
        pixels=rgb555(canvas).astype('<u2')
        (assets/'scene.json').write_text(json.dumps(scene,indent=2)+'\n')
        (assets/'source.json').write_text(json.dumps(metadata,indent=2)+'\n')
        compiled=compile_frame(pixels,(0,1,1),236,7)
        if not isinstance(compiled,tuple):raise ValueError('SNAPSHOT_COMPONENT_SCHEDULE_UNPROVEN')
        report,high,low=compiled
        # Keep the authorized 64-KiB component canvas allocation. A smaller
        # bounded CHR payload does not move BG2 into the BG1 arena.
        if report['high_chr_bytes']>49152 or report['low_chr_bytes']>12288:
            raise ValueError('SNAPSHOT_FULL_COMPONENT_CANVAS_CAPACITY')
        report['low_chr_vram_base']=49152
        for name,data in [('indices.bin',high.tobytes()),('low_indices.bin',low.tobytes()),('expected.rgb555',pixels.tobytes())]:(assets/name).write_bytes(data)
        (assets/'initial.json').write_text(json.dumps(report.pop('initial'))+'\n')
        (assets/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        # Compile the existing renderer input, then verify actual presentation
        # once through the integrated native owner below.
        rom,trace,resources=compile_rom(report,assets,offset_alias=True)
        changed=int(np.count_nonzero(pixels!=last)) if last is not None else 0
        results.append(dict(epoch=sample['epoch'],snapshot_sha256=sample['sha256'],scene=scene,
            changed_source_pixels=changed,pixels=int(pixels.size),
            expected_sha256=sha(pixels.tobytes()),rom_sha256=sha(rom),resources=resources))
        last=pixels
    return results


def integrated(folder,source,sy,samples):
    from m4_bounded_component_publisher import build,READY,DISPLAY_EPOCH
    native=folder/'integrated';native.mkdir(exist_ok=True)
    args=[sys.executable,'tools/verify/m4_animation_callback_owner_native.py','--source',str(source.path.resolve()),
          '--rom',str(folder/'base/bor.sfc'),'--output',str(native)]
    args+=['--'+n for n in ('effects-runner','frame-owner','initial-select','default-owner','ctor-owner','ctor-state',
           'ctor-factors','ctor-model','script-clone','player-state-birth','run-tuple-birth','ground-walk','live-ground','live-ground-display','emit-only')]
    subprocess.run(args,check=True)
    assets=[folder/f'frame-{i:02d}' for i in range(len(samples))]
    raw,contract=build((native/'bor.sfc').read_bytes(),sy,native,assets,samples)
    (native/'bor.sfc').write_bytes(raw)
    script=native/'callback_owner.lua'
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kw):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kw)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter=Reporter('MOTU-NATIVE-MOVEMENT-DISPLAY',kind='GATE');observed=[]
    with Observed(rom=native/'bor.sfc',mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=native/'mesen.log') as m:
        m.write_u16(READY,0)
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('INTEGRATED_BOOTSTRAP')
        run_frames_exact(m,12)
        for n in ('StageWater_Enabled','StageWater_Pending','StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'):m.write_u8(sy[n],0)
        m.write_u16(0x7ffb84,0);m.write_u16(0x7ffb82,0)
        for i,sample in enumerate(samples):
            label=sample['label'];m.hold_input({'birth':0,'right':m.BTN_RIGHT,'up':m.BTN_UP,'released':0}[label],port=0)
            run_frames_exact(m,2)
            m.write_u16(REQUEST,0xb4e7 if i==0 else 0xb4e8)
            fields=0
            for _ in range(100):
                run_frames_exact(m,1);fields+=1
                if startup.u16(m,0x7ffb84):raise ValueError('INTEGRATED_CONTEXT_OR_SERVICE_FAULT')
                if startup.u16(m,READY)==0xb4b8 and startup.u16(m,DISPLAY_EPOCH)==i:break
            else:raise ValueError('INTEGRATED_PUBLICATION_TIMEOUT')
            # A complete visible field follows the final DMA/palette publication.
            run_frames_exact(m,2)
            snapshot=m.read_memory('SnesMemory',SNAPSHOT,146)
            (native/f'world-{i:02d}.bin').write_bytes(snapshot)
            golden=Path(sample['snapshot']).read_bytes()
            keymatch=all(snapshot[a:a+2]==golden[a:a+2] for a in contract['key_offsets'])
            if not keymatch:raise ValueError('INTEGRATED_WORLD_TUPLE_DIFFERS')
            shot=m.tool('take_screenshot',{'format':'path'});dest=native/f'display-{i:02d}.png';shutil.copyfile(shot['path'],dest)
            actual=rgb555(np.asarray(Image.open(dest).convert('RGB')))
            expected=np.fromfile(assets[i]/'expected.rgb555',dtype='<u2').reshape(224,256)
            mismatches=int(np.count_nonzero(actual!=expected)) if actual.shape==expected.shape else None
            observed.append(dict(epoch=i,label=label,x_q16=struct.unpack_from('<i',snapshot,52)[0],
                z_q16=struct.unpack_from('<i',snapshot,60)[0],tuple_matches=True,pixel_mismatches=mismatches,
                publication_wait_fields=fields,snapshot_sha256=sha(snapshot),pixels=int(expected.size)))
            (native/'observations.json').write_text(json.dumps(observed,indent=2)+'\n')
            if mismatches!=0:
                (native/'cpu-state.json').write_text(json.dumps(m.get_cpu_state(),indent=2))
                (native/'ppu-state.json').write_text(json.dumps(m.get_ppu_state(),indent=2))
                raise ValueError('INTEGRATED_DISPLAY_MISMATCH:'+str(i)+':'+str(mismatches))
        # A real unsupported left move must fault admission, not select a
        # nearby context or publish artwork for a different source snapshot.
        m.hold_input(m.BTN_LEFT,port=0);run_frames_exact(m,2)
        old=startup.u16(m,DISPLAY_EPOCH);m.write_u16(REQUEST,0xb4e8)
        run_frames_exact(m,4)
        rejected=startup.u16(m,0x7ffb84)==1 and startup.u16(m,DISPLAY_EPOCH)==old
        shot=m.tool('take_screenshot',{'format':'path'});shutil.copyfile(shot['path'],native/'context-miss.png')
        missed=rgb555(np.asarray(Image.open(native/'context-miss.png').convert('RGB')))
        retained=np.fromfile(assets[-1]/'expected.rgb555',dtype='<u2').reshape(224,256)
        retained_display=missed.shape==retained.shape and np.array_equal(missed,retained)
        rejected=rejected and retained_display
        m.release_input(port=0)
    result=dict(status='PASS' if rejected else 'FAIL',rom_sha256=sha(raw),observations=observed,
                verified_pixels=sum(r['pixels'] for r in observed),pixel_mismatches=sum(r['pixel_mismatches'] for r in observed),
                context_miss_rejected=rejected,context_miss_retains_display=retained_display,contract=contract,
                scope='One native ROM: real JOY1 -> persistent authored constructor -> source history/ground/frame/velocity/check_move -> sealed world tuple -> bounded admitted component context -> native DMA/PPU display. Forced-blank publication; host supplies input and requests only. General online composition, 200-Hz traversal, breath, HUD and Demo remain unproven.')
    (native/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    if not rejected:raise ValueError('INTEGRATED_CONTEXT_MISS_NOT_REJECTED')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stage',default='DATA/LEVELS/GUILE2.TXT');p.add_argument('--resume-snapshots',action='store_true')
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    sy=symbols(Path('src/main.sym'))
    if not a.resume_snapshots:
        base=folder/'base';base.mkdir(exist_ok=True)
        # Link the already assembled source with its header/vectors. Calling
        # assemble here would overwrite the user's protected main.bin/sym.
        import build_rom
        with patch.object(build_rom,'assemble',return_value=None):baseline=build_rom.link_rom()
        (base/'bor.sfc').write_bytes(baseline)
        if not(base/'bor.msu').exists():
            media=Path('out/byor-motu-player-controller-native/bor.msu').resolve()
            try:os.link(media,base/'bor.msu')
            except OSError as exc:
                if getattr(exc,'winerror',None)!=1142:raise
                shutil.copyfile(media,base/'bor.msu')
        args=[sys.executable,'tools/verify/m4_animation_callback_owner_native.py','--source',str(a.source.resolve()),
              '--rom',str(base/'bor.sfc'),'--output',str(folder/'world')]
        args += ['--'+n for n in ('effects-runner','frame-owner','initial-select','default-owner','ctor-owner','ctor-state',
                  'ctor-factors','ctor-model','script-clone','player-state-birth','run-tuple-birth','ground-walk','live-ground','emit-only')]
        subprocess.run(args,check=True)
        samples=capture(folder,sy)
    else:samples=json.loads((folder/'snapshots.json').read_text())
    motion=check_motion(samples)
    results=prepare_samples(folder,Source(a.source),a.stage,samples)
    joined=integrated(folder,Source(a.source),sy,samples)
    movement=all(b['x_q16']>a['x_q16'] for a,b in zip(samples,samples[1:]) if b['label']=='right')
    released=all(b['x_q16']==a['x_q16'] and b['z_q16']==a['z_q16'] for a,b in zip(samples,samples[1:]) if b['label']=='released')
    up=all(b['z_q16']<a['z_q16'] for a,b in zip(samples,samples[1:]) if b['label']=='up')
    actual_snapshots_exact=all(r['snapshot_sha256']==s['sha256'] for r,s in zip(joined['observations'],samples))
    # A constant WALK/frame/direction comparison isolates movement from pose changes.
    movement_pixels=[i for i in range(1,len(results)) if results[i]['scene']['actors'][0]['animation']==results[i-1]['scene']['actors'][0]['animation']=='walk' and results[i]['changed_source_pixels']>0]
    passed=movement and released and up and actual_snapshots_exact and bool(movement_pixels) and joined['status']=='PASS'
    report=dict(schema='BYOR_MOTU_NATIVE_MOVEMENT_COMPONENT_BRIDGE_V1',status='PASS' if passed else 'FAIL',
        source_pak_sha256=sha(a.source.read_bytes()),native_world_rom_sha256=sha((folder/'world/bor.sfc').read_bytes()),
        samples=samples,compiled_contexts=results,right_movement=movement,release_stops=released,up_movement=up,
        actual_snapshots_match_compiler_inputs=actual_snapshots_exact,movement_only_pixel_pairs=movement_pixels,
        independent_movement_checks=motion,
        native_integrated_display=joined,
        verified_pixels=joined['verified_pixels'],pixel_mismatches=joined['pixel_mismatches'],
        continuous_native_compositor=False,full_world_tick=False,simulation_200hz=False,
        scope='Bounded native controller-to-world-to-component display slice. Source-derived sealed snapshots compile a finite admitted context set; replay publishes it in the same ROM from actual native world tuples. Closed ground/empty collision service scope, forced-blank publication, no general online compositor, full controller/world traversal, HUD, breath lifecycle or Demo admission.')
    (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('samples','compiled_contexts','native_integrated_display','independent_movement_checks')},indent=2))
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
