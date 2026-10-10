"""Native static underlay and source-derived OBJ math routing, not full raster.

Selects two source mask samples by palette eligibility and static capacity.
All source placement and RGB555 identities are preserved for the sampled pixels.
"""
import argparse,hashlib,json,shutil,struct,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_scene_bg import compose_rgb8
from source_bg_feasibility import rgb555,compile_canvas
from source_scene_obj_math import add_rgb555
from raster_obj_compact import unpack
from m4_bg_components_native import tiles
from _harness import McpSession,MESEN_EXE,_free_tcp_port


def compile_rom(source,stage,scene,schedule,output,opaque_bank=None,additive_bank=None):
    if opaque_bank is not None and opaque_bank not in range(4)or additive_bank is not None and additive_bank not in range(4,8):
        raise ValueError('MODE3_PALETTE_MATH_ELIGIBILITY')
    bg,metadata=compose_rgb8(source,stage,dict(scene,actors=[]));bg=rgb555(bg)
    complete,_=compose_rgb8(source,stage,scene);complete=rgb555(complete)
    if schedule['status']!='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN' or hashlib.sha256(complete.astype('<u2').tobytes()).hexdigest()!=schedule['source_rgb555_sha256']:
        raise ValueError('MODE3_SOURCE_SCHEDULE_IDENTITY')
    bgdir=output/'underlay';report=compile_canvas(bg,127,0,export=bgdir)
    if report['peak_hblank_writes']:raise ValueError('MODE3_STATIC_UNDERLAY_REQUIRED')
    indices=np.frombuffer((bgdir/'indices.bin').read_bytes(),dtype=np.uint8).reshape(224,256)
    bgchr,bgmap=tiles(indices,8)
    if len(bgchr)>0xc000 or len(bgchr)//64>1024:raise ValueError('MODE3_BG_CHR_CAPACITY')
    palette=np.zeros(256,dtype='<u2')
    for i,c in enumerate(json.loads((bgdir/'initial.json').read_text())):palette[i+1]=c or 0
    if np.any(indices>=128):raise AssertionError('MODE3_BG_OBJ_CGRAM_OVERLAP')
    state={b:[None]*15 for b in range(8)};states=[]
    for row in schedule['trace']:
        for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
        states.append({b:list(v)for b,v in state.items()})
    selected=[];expected=bg.copy();objchr=bytearray();oam=bytearray(544)
    for i in range(128):oam[i*4+1]=240
    candidates=sorted(zip(schedule['pieces'],schedule['piece_pixel_masks']),key=lambda pair:-int(np.count_nonzero(unpack(pair[1]))))
    for kind in (0,1):
        for p,mask in candidates:
            if int(p['bank']>=4)!=kind or (p['width'],p['height'])!=(8,8):continue
            image=unpack(mask);colors=set()
            for ly,lx in zip(*np.where(image!=0)):colors.add(states[int(p['y']+ly)][p['bank']][int(image[ly,lx])-1])
            if not colors or len(colors)>15:continue
            colors=sorted(colors);static=np.zeros((8,8),dtype=np.uint8);count=0
            for ly,lx in zip(*np.where(image!=0)):
                y,x=int(p['y']+ly),int(p['x']+lx);c=states[y][p['bank']][int(image[ly,lx])-1]
                static[ly,lx]=colors.index(c)+1
                value=c if kind==0 else add_rgb555(c,int(bg[y,x]))
                if value!=int(complete[y,x]):raise AssertionError('MODE3_SOURCE_ALPHA_IDENTITY')
                expected[y,x]=value;count+=1
            bank=(opaque_bank if kind==0 else additive_bank)
            if bank is None:bank=p['bank']
            for s,c in enumerate(colors,1):palette[128+bank*16+s]=c
            encoded,_=tiles(np.pad(static,((0,216),(0,248))),4)
            # Encode the selected tile directly; tiles() places it first.
            objchr.extend(encoded[:32]);i=len(selected);x=p['x']&511
            oam[i*4:i*4+4]=bytes([x&255,p['y']&255,i,0x30|bank<<1]);oam[512+i//4]|=(x>>8)<<(2*(i%4))
            selected.append(dict(piece=p,physical_bank=bank,colors=colors,source_pixels=count,math_kind='OPAQUE_BYPASS'if kind==0 else'ADDITIVE_SUBSCREEN'))
            break
        else:raise ValueError('MODE3_STATIC_SAMPLE_NOT_FOUND')
    rom=bytearray([255])*262144;code=bytearray.fromhex('78 18 fb c2 30 a2 ff 1f 9a e2 20')
    def store(address,value):code.extend(bytes([0xa9,value,0x8d,address&255,address>>8]))
    def dma(address,bank,dest,data,mode,target=None):
        if target is not None:store(0x2116,target&255);store(0x2117,target>>8)
        for a,v in [(0x4370,mode),(0x4371,dest),(0x4372,address&255),(0x4373,address>>8),(0x4374,bank),(0x4375,len(data)&255),(0x4376,len(data)>>8),(0x420b,128)]:store(a,v)
        at=bank*32768+address-0x8000;rom[at:at+len(data)]=data
    for a,v in [(0x4200,0),(0x420c,0),(0x2100,128),(0x2115,128)]:store(a,v)
    dma(0x8000,2,0x18,bgchr[:32768],1,0)
    if len(bgchr)>32768:dma(0x8000,3,0x18,bgchr[32768:],1)
    dma(0x8000,4,0x18,bgmap,1,0x7800)
    dma(0x8800,4,0x18,objchr,1,0x6000)
    store(0x2102,0);store(0x2103,0);dma(0x9000,4,0x04,oam,0)
    store(0x2121,0);dma(0x9400,4,0x22,palette.tobytes(),0)
    for a,v in [(0x2101,0x23),(0x2105,3),(0x2107,0x78),(0x210b,0),(0x210d,0),(0x210d,0),(0x210e,255),(0x210e,255),(0x212c,17),(0x212d,1),(0x2130,2),(0x2131,16),(0x2132,0xe0),(0x2133,0)]:store(a,v)
    code.extend(bytes.fromhex('ad 12 42 29 80 f0 f9'));store(0x2100,15);code.extend(bytes.fromhex('80 fe'))
    rom[:4]=bytes.fromhex('5c 00 80 01');rom[0x8000:0x8000+len(code)]=code
    rom[0x7fc0:0x7fd5]=b'M3 SOURCE OBJ MATH'.ljust(21);rom[0x7fd5:0x7fdc]=bytes([0x20,0,8,0,1,0,0]);rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    (output/'expected.rgb555').write_bytes(expected.astype('<u2').tobytes())
    return bytes(rom),expected,palette.tobytes(),bytes(oam),dict(bg_mode=3,bg_chr_bytes=len(bgchr),bg_unique_tiles=len(bgchr)//64,bg_map_base=0xf000,obj_chr_base=0xc000,obj_chr_bytes=len(objchr),obj_entries=2,bg_static_colors=report['full_frame_colors'],bg_cgram_below=128,bg_raster_writes=0,selected=selected,source_underlay_metadata=metadata)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','stage','scene','schedule','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--opaque-bank',type=int);p.add_argument('--additive-bank',type=int)
    a=p.parse_args();output=Path(a.output).resolve();output.mkdir(parents=True,exist_ok=True)
    scene=json.loads(Path(a.scene).read_text());schedule=json.loads(Path(a.schedule).read_text())
    rom,expected,palette,oam,resources=compile_rom(Source(a.source),a.stage,scene,schedule,output,a.opaque_bank,a.additive_bank)
    path=output/'proof.sfc';path.write_bytes(rom);lua=output/'observer.lua'
    lua.write_text("""local shown=false;local oam={};local cg={}
emu.addMemoryCallback(function(a,v)if not shown then oam[#oam+1]=string.format('%02x',v)end end,emu.callbackType.write,0x2104,0x2104,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if not shown then cg[#cg+1]=string.format('%02x',v)end end,emu.callbackType.write,0x2122,0x2122,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)if v==15 and not shown then shown=true;emu.log('MODE3OAM|'..table.concat(oam,''));emu.log('MODE3CGRAM|'..table.concat(cg,''))end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()if shown then emu.log('MODE3FLAGS|'..emu.read(0x213e,emu.memType.snesMemory))end end,emu.eventType.endFrame)
""")
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=output/'mesen.log')as m:
        advanced=0;progress=[]
        for _ in range(32):
            step=m.tool('run_frames',{'count':1});progress.append(step);advanced+=step['framesAdvanced']
            if advanced>=3:break
        shot=m.tool('take_screenshot',{'format':'path'});cg=m.read_memory('SnesCgRam',0,512)
    shutil.copyfile(shot['path'],output/'screenshot.png')
    actual=rgb555(np.array(Image.open(output/'screenshot.png').convert('RGB')))
    cg=bytes.fromhex(cg['hex'])if isinstance(cg,dict)else bytes(cg)
    log=(output/'mesen.log').read_text();flags=[int(s.split('MODE3FLAGS|')[1])for s in log.splitlines()if'MODE3FLAGS|'in s]
    def observed(label):return [s.split(label+'|')[1]for s in log.splitlines()if label+'|'in s]
    passed=advanced>=3 and np.array_equal(actual,expected)and cg==palette and observed('MODE3OAM')==[oam.hex()]and observed('MODE3CGRAM')==[palette.hex()]and bool(flags)and not any(v&192 for v in flags)
    report=dict(schema='BYOR_MODE3_SOURCE_OBJ_MATH_NATIVE_V1',status='PASS'if passed else'FAIL',resources=resources,rom_sha256=hashlib.sha256(rom).hexdigest(),input_schedule_sha256=hashlib.sha256(Path(a.schedule).read_bytes()).hexdigest(),expected_sha256=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest(),completed_fields=advanced,progress=progress,pixel_mismatches=int(np.count_nonzero(actual!=expected))if actual.shape==expected.shape else None,cgram_ram_identity_verified=cg==palette,cgram_observer_verified=observed('MODE3CGRAM')==[palette.hex()],oam_observer_verified=observed('MODE3OAM')==[oam.hex()],obj_status=flags,source_alpha_sample_identity_verified=True,full_effect_rendered=False,raster_schedule_executed=False,production_runtime_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ('status','completed_fields','pixel_mismatches','cgram_ram_identity_verified','oam_observer_verified','obj_status')}))
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
