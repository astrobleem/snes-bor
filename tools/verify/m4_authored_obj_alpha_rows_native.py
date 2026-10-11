"""Native source-alpha arithmetic and bank routing, one static source row at a time.

Every row uses its real source position and fixed OAM bank. Palette and window
registers are installed while blanked. This is not a raster transfer proof.
"""
import argparse,copy,hashlib,json,shutil,struct,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_scene_obj_raster import prepare
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555
from source_obj_underlay import compile_underlay
from source_scene_obj_joint import scanline_controls
from raster_slot_greedy import demand
from raster_obj_compact import unpack
from raster_obj_chr import compile as compile_chr
from raster_obj_math_cover import apply_math
from raster_math_windows import evaluate,compile_mask
from _harness import McpSession,MESEN_EXE,_free_tcp_port


def compile_row(schedule,y,background,complete,states,modes,windows,obj_screen='main'):
    if obj_screen not in('main','subscreen'):raise ValueError('ALPHA_ROW_OBJ_SCREEN')
    if obj_screen=='subscreen' and(schedule.get('color_math')!='subscreen-additive' or modes[y]!='add'):raise ValueError('ALPHA_ROW_SUBSCREEN_ADD_REQUIRED')
    _,_,colors=demand(schedule);sample=copy.deepcopy(schedule);masks=[];count=0
    expected=background.copy();descriptor=windows[y];mode=modes[y]
    for p,mask,words in zip(schedule['pieces'],schedule['piece_pixel_masks'],colors):
        image=unpack(mask).copy()
        for ly in range(p['height']):
            if p['y']+ly!=y:image[ly]=0
        for ly,lx in zip(*np.where(image)):
            x=p['x']+int(lx);word=int(words[ly,lx]);value=word
            if obj_screen=='subscreen' or p['bank']>=4 and evaluate(descriptor,x):value=apply_math(word,int(background[y,x]),mode)
            if value!=int(complete[y,x]):raise AssertionError('ALPHA_ROW_SOURCE_IDENTITY')
            expected[y,x]=value;count+=1
        flat=image.flatten();masks.append(dict(width=p['width'],height=p['height'],pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
    sample['piece_pixel_masks']=masks
    chr_report,objchr,oam=compile_chr(sample)
    underlay,bgchr,bgmap,lower=compile_underlay(background)
    palette=bytearray(lower+bytes(256))
    for b in range(8):
        for slot,c in enumerate(states[y][b],1):
            if c is not None:struct.pack_into('<H',palette,2*(128+16*b+slot),c)
    raw=bytearray([255])*262144;code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    registers=[]
    def store(address,value):code.extend([0xa9,value,0x8d,address&255,address>>8]);registers.append([address,value])
    def dma(address,bank,dest,blob,mode,target=None):
        if target is not None:store(0x2116,target&255);store(0x2117,target>>8)
        for a,v in((0x4370,mode),(0x4371,dest),(0x4372,address&255),(0x4373,address>>8),(0x4374,bank),(0x4375,len(blob)&255),(0x4376,len(blob)>>8),(0x420b,128)):store(a,v)
        at=bank*32768+address-0x8000;raw[at:at+len(blob)]=blob
    for a,v in((0x4200,0),(0x420c,0),(0x2100,128),(0x2115,128)):store(a,v)
    dma(0x8000,2,0x18,bgchr[:32768],1,0)
    if len(bgchr)>32768:dma(0x8000,3,0x18,bgchr[32768:],1)
    dma(0x8000,4,0x18,bgmap,1,0x5800)
    dma(0x8800,4,0x18,objchr,1,0x6000)
    # Keep variable CHR separate from OAM/palette in the asset bank.
    store(0x2102,0);store(0x2103,0);dma(0xc800,4,4,oam,0);store(0x2121,0);dma(0xcc00,4,0x22,palette,0)
    math=(1 if obj_screen=='subscreen' else 0x10)|{'add':0,'half-add':0x40,'subtract':0x80,'half-subtract':0xc0}[mode]
    for a,v in((0x2101,3|(chr_report['obj_size_mode']<<5)),(0x2105,3),(0x2107,0x58),(0x210b,0),
                (0x210d,0),(0x210d,0),(0x210e,255),(0x210e,255),(0x212c,1 if obj_screen=='subscreen' else 17),(0x212d,16 if obj_screen=='subscreen' else 1),
                (0x212e,0),(0x212f,0),(0x2125,descriptor['wobjsel_color_bits']),
                (0x212b,descriptor['wobjlog_color_bits']),(0x2130,2 if obj_screen=='subscreen' else 0x12),(0x2131,math),(0x2132,0xe0),(0x2133,0)):
        store(a,v)
    for i,v in enumerate(sum(descriptor['bounds'],[])):store(0x2126+i,v)
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'));store(0x2100,15);code.extend(bytes.fromhex('80 fe'))
    raw[:4]=bytes.fromhex('5c 00 80 01');raw[0x8000:0x8000+len(code)]=code
    raw[0x7fc0:0x7fd5]=b'M4 SOURCE ALPHA ROW'.ljust(21);raw[0x7fd5:0x7fdc]=bytes([0x20,0,8,0,1,0,0]);raw[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    owned=[r for r in registers if 0x2125<=r[0]<=0x2131]
    return bytes(raw),expected,bytes(palette),oam,bgchr,bgmap,objchr,dict(scanline=y,mode=mode,window=descriptor,source_obj_pixels=count,
        underlay=underlay,obj=chr_report,expected_register_writes=owned,obj_operand_screen=obj_screen,main_obj_disabled=obj_screen=='subscreen',native_raster_timing_proven=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('source','stage','scene','schedule','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--controls');p.add_argument('--obj-screen',choices=('main','subscreen'),default='main')
    p.add_argument('--rows',type=int,nargs=2,help='Optional bounded subset, inclusive.')
    a=p.parse_args();folder=Path(a.output).resolve();folder.mkdir(parents=True,exist_ok=True)
    source=Source(a.source);scene=json.loads(Path(a.scene).read_text());schedule=json.loads(Path(a.schedule).read_text())
    actors,metadata,expected=prepare(source,a.stage,scene);complete=rgb555(expected)
    digest=hashlib.sha256(complete.astype('<u2').tobytes()).hexdigest()
    if a.obj_screen=='subscreen':
        if a.controls or schedule.get('color_math')!='subscreen-additive' or not schedule.get('main_screen_obj_disabled'):raise ValueError('ALPHA_NATIVE_SUBSCREEN_ROUTING_REQUIRED')
        rows={p['y']+ly for p,image in zip(schedule['pieces'],demand(schedule)[2])for ly,row in enumerate(image)if np.any(row>=0)}
        modes={y:'add'for y in rows};windows={y:compile_mask([True]*256,fixed_positive_union=True)for y in rows}
    else:
        if not a.controls:raise ValueError('ALPHA_NATIVE_CONTROLS_REQUIRED')
        modes,windows,_=scanline_controls(json.loads(Path(a.controls).read_text()),metadata,digest,len(complete))
        if not schedule.get('scanline_math_controls_source_bound') or any(schedule['selected_modes'].get(str(y))!=m for y,m in modes.items())or{int(y):d for y,d in schedule['compiled_color_window_descriptors'].items()}!=windows:raise ValueError('ALPHA_NATIVE_SCHEDULE_CONTROL_IDENTITY')
    if schedule.get('metadata')!=metadata or schedule.get('source_rgb555_sha256')!=digest:
        raise ValueError('ALPHA_NATIVE_SCHEDULE_CONTROL_IDENTITY')
    background=rgb555(compose_rgb8(source,a.stage,dict(scene,actors=[]))[0]);demand(schedule)
    state={b:[None]*15 for b in range(8)};states=[]
    for row in schedule['trace']:
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        states.append(copy.deepcopy(state))
    rows=sorted(modes)
    if a.rows:rows=[y for y in rows if a.rows[0]<=y<=a.rows[1]]
    if not rows:raise ValueError('ALPHA_NATIVE_ROWS_EMPTY')
    reconstructed=background.copy();results=[]
    lua=folder/'observer.lua';lua.write_text('''local shown=false;local cg={};local oam={};local regs={}
emu.addMemoryCallback(function(a,v)if not shown then cg[#cg+1]=string.format('%02x',v)end end,emu.callbackType.write,0x2122,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if not shown then oam[#oam+1]=string.format('%02x',v)end end,emu.callbackType.write,0x2104,0x2104,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if not shown then regs[#regs+1]=a..','..v end end,emu.callbackType.write,0x2125,0x2131,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if v==15 and not shown then shown=true;emu.log('ALPHACG|'..table.concat(cg,''));emu.log('ALPHAOAM|'..table.concat(oam,''));emu.log('ALPHAREG|'..table.concat(regs,';'))end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()if shown then emu.log('ALPHAFLAGS|'..emu.read(0x213e,emu.memType.snesMemory))end end,emu.eventType.endFrame)
''')
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--Snes.DisableFrameSkipping=true','--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    for y in rows:
        raw,want,palette,oam,bgchr,bgmap,objchr,resources=compile_row(schedule,y,background,complete,states,modes,windows,a.obj_screen)
        path=folder/'proof.sfc';path.write_bytes(raw);log_path=folder/f'row{y}.log'
        with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=log_path)as m:
            advanced=0
            for _ in range(12):
                advanced+=m.run_frames(1)['framesAdvanced']
                if advanced>=3:break
            shot=m.tool('take_screenshot',{'format':'path','path':str(folder/f'row{y}.png')})
            cg=m.read_memory('SnesCgRam',0,512);obj=m.read_memory('SnesSpriteRam',0,544)
            bg_data=m.read_memory('SnesVideoRam',0,len(bgchr));mapping=m.read_memory('SnesVideoRam',0xb000,len(bgmap));chr_data=m.read_memory('SnesVideoRam',0xc000,len(objchr))
        retained=folder/f'row{y}.png'
        if Path(shot['path']).resolve()!=retained:shutil.copyfile(shot['path'],retained)
        actual=rgb555(np.asarray(Image.open(retained).convert('RGB')))
        log=log_path.read_text()
        def observed(label):return[line.split(label+'|')[1]for line in log.splitlines()if label+'|'in line]
        flags=list(map(int,observed('ALPHAFLAGS')));registers=[list(map(int,r.split(',')))for r in observed('ALPHAREG')[0].split(';')]if len(observed('ALPHAREG'))==1 else[]
        exact=actual.shape==want.shape and np.array_equal(actual,want)
        row=dict(resources,status='PASS'if exact and advanced>=3 and cg==palette and obj==oam and bg_data==bgchr and mapping==bgmap and chr_data==objchr and observed('ALPHACG')==[palette.hex()]and observed('ALPHAOAM')==[oam.hex()]and registers==resources['expected_register_writes']and flags and not any(v&192 for v in flags)else'FAIL',
            rom_sha256=hashlib.sha256(raw).hexdigest(),expected_rgb555_sha256=hashlib.sha256(want.astype('<u2').tobytes()).hexdigest(),completed_fields=advanced,
            pixel_mismatches=int(np.count_nonzero(actual!=want))if actual.shape==want.shape else None,cgram_identity=cg==palette,oam_identity=obj==oam,
            vram_identity=bg_data==bgchr and mapping==bgmap and chr_data==objchr,cgram_observer_identity=observed('ALPHACG')==[palette.hex()],
            oam_observer_identity=observed('ALPHAOAM')==[oam.hex()],register_observer_identity=registers==resources['expected_register_writes'],obj_flags=flags)
        results.append(row);print(json.dumps({k:row[k]for k in('scanline','mode','status','pixel_mismatches')}),flush=True)
        if actual.shape==want.shape:reconstructed[y]=actual[y]
        if row['status']!='PASS':break
    full=rows==sorted(modes)and len(results)==len(rows)
    passed=all(r['status']=='PASS'for r in results)and len(results)==len(rows)
    aggregate=full and np.array_equal(reconstructed,complete)
    report=dict(schema='BYOR_NATIVE_AUTHORED_OBJ_ALPHA_ROWS_V1',status='PASS'if passed and(not full or aggregate)else'FAIL',
        input_schedule_sha256=hashlib.sha256(Path(a.schedule).read_bytes()).hexdigest(),source_rgb555_sha256=digest,
        input_controls_sha256=hashlib.sha256(Path(a.controls).read_bytes()).hexdigest()if a.controls else None,obj_operand_screen=a.obj_screen,
        source_metadata=metadata,rows=results,all_source_rows_sampled=full,assembled_static_row_pixels_exact=aggregate,
        assembled_rgb555_sha256=hashlib.sha256(reconstructed.astype('<u2').tobytes()).hexdigest(),
        source_alpha_policy='EXACT_BOR4086_SCREEN_RGB8_THEN_RGB555',raster_schedule_executed=False,
        palette_transfer_timing_proven=False,concurrent_actors_proven=False,production_runtime_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
