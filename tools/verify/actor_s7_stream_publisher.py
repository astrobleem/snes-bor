"""Native source publication; optional shared-resource instance leases.

The accepted single-instance command remains the default. --instance-leases
selects the bounded static transport plan and immutable OAM packet path.
"""
import argparse
import hashlib
import io
import json
import re
import struct
import shutil
import subprocess
from types import SimpleNamespace
from pathlib import Path
from PIL import Image
from actor_s5_isolated import ROOT,parse_model
from actor_s7_native_publisher import prepare as entry_prepare,db
from source_actor_raster import compile_animation,encode_tile
from frame_packing import pack_image
from frame_publication import pack_descriptor


def prepare(folder,source,sym,*,instance_leases=False,compact_residency=False):
    result=entry_prepare(folder,source,sym,stream=True)
    model=parse_model(source,'data/chars/kula/kula.txt','Kula','s7-publisher','historical-bor')
    raster=compile_animation(source,model,'attack1',color_adapter='SNES_RGB555_TRUNCATE')
    mapping={v:i for i,v in enumerate(raster['manifest']['source_palette_indices'])}
    plan=None
    if instance_leases:
        from source_frame_transport import compile_frames,retained_working_set
        plan=compile_frames(source,raster['manifest'],group_future=True,compact=compact_residency)
    manifest=json.loads((folder/'publisher-frame.json').read_text())
    images=[];allpieces=bytearray();metadata=bytearray();frames=[]
    for index,frame in enumerate(raster['manifest']['frames']):
        raw=source.read(frame['source_path'])
        if compact_residency:
            from source_compact_packing import pack_compact
            packed=pack_compact(raw,frame['offset'])
        else:packed=pack_image(raw,frame['offset'])
        with Image.open(io.BytesIO(raw)) as original:original.load();image=original.copy()
        cells=[]
        for p in packed['pieces']:
            x,y=p['source_xy'];w,h=p['size']
            cells.extend((x+dx,y+dy) for dy in range(0,h,32) for dx in range(0,w,16))
        if len(cells)>16:raise ValueError('FRAME_4K_BUFFER_CAPACITY')
        data=bytearray(4096);chunks=[]
        for i,(x,y) in enumerate(cells):
            local=(i//8)*64+(i%8)*2;tile=local+(index%2)*128
            block=image.crop((x,y,x+16,y+32))
            for ty in range(4):
                for tx in range(2):
                    pixels=bytes(mapping[block.getpixel((tx*8+dx,ty*8+dy))]
                                 for dy in range(8) for dx in range(8))
                    at=(local+ty*16+tx)*32;data[at:at+32]=encode_tile(pixels)
            ox,oy=frame['offset']
            chunks.append(dict(right_xy=[x-ox,y-oy],left_xy=[ox-x-15,y-oy],tile=tile))
        if plan:chunks=plan['frames'][index]['chunks']
        _,pieces=pack_descriptor(dict(chunks=chunks),role=manifest['role_id'],index=index,map_selector=0,piece_address=0x20A100+len(allpieces))
        metadata+=struct.pack('<HH4x',len(allpieces),len(chunks))
        frames.append(dict(source=frame,chunks=chunks,piece_offset=len(allpieces),piece_bytes=len(pieces)))
        allpieces+=pieces;images.append(bytes(data))
    payload=images[0]+images[1]+raster['cgram']+bytes(96)+metadata
    jobs=[];jobdata=bytearray();table=bytearray()
    if plan:
        entry=bytearray(plan['entry_image'])
        for w in plan['frames'][1]['writes']:
            at=w['destination']-0x8000;entry[at:at+len(w['payload'])]=w['payload']
        payload=bytes(entry)+raster['cgram']+bytes(96)+metadata
        for f in plan['frames'][2:]:
            merged=[]
            for w in sorted(f['writes'],key=lambda w:w['destination']):
                if merged and merged[-1]['destination']+len(merged[-1]['payload'])==w['destination']:
                    merged[-1]['payload']+=w['payload']
                    merged[-1]['consumed_frame_at_least']=max(merged[-1]['consumed_frame_at_least'],w['consumed_frame_at_least'])
                else:merged.append(dict(w))
            for w in merged:
                assert len(w['payload'])+544<2816
                table+=struct.pack('<HHHBBBB',len(w['payload']),w['destination'],0x8000+len(jobdata),33,w['consumed_frame_at_least'],f['index'],0)
                jobs.append(dict(frame=f['index'],target=w['destination'],size=len(w['payload']),lease=w['consumed_frame_at_least'],source=0x8000+len(jobdata)))
                jobdata+=w['payload']
        assert len(jobs)*2<=192 and len(jobdata)<=32768
        manifest['jobs']=jobs
        manifest['resources']={
            'encoding_sha256':hashlib.sha256(bytes(entry)+jobdata+bytes(table)).hexdigest(),
            'palette_sha256':hashlib.sha256(raster['cgram']).hexdigest(),
            'map_selector':0,'instance_copies':1,
            'adjacent_retention':[retained_working_set(plan,[i],[i+1]) for i in range(5)],
            'three_frame_retention':[retained_working_set(plan,[i,i+1],[i+1,i+2]) for i in range(4)]}
    payload=payload.ljust(0x2100,b'\0')+allpieces
    (folder/'publisher-assets.bin').write_bytes(payload)
    (folder/'publisher-stream-images.bin').write_bytes(b''.join(images))
    manifest.update(frames=frames,scope='STREAM_CANDIDATE_NOT_DEADLINE_CERTIFIED')
    (folder/'publisher-frame.json').write_text(json.dumps(manifest,indent=2))
    code=result['assembly'].split('\n.bank 32\n.org $8000\n',1)[0]
    code=code.replace('    rtl\n\nS7Publisher_Entry:',
                      '    jsl S7Tile_Init\n    rtl\n\nS7Publisher_Entry:')
    if instance_leases:
        code=code.replace('S7Publisher_Capture:\n    rep #$30\n    .a16\n    .i16\n',
            'S7Publisher_Capture:\n    rep #$30\n    .a16\n    .i16\n    lda.l $7E173C\n    sta.l S7Pub_State+$E0\n')
        code=code.replace('Character_RenderPass:\n','Character_RenderPass:\n    jsl S7Packet_Begin\n    jsl S7Tile_Service\n')
    else:
        code=code.replace('    pld\n    rtl\nS7Publisher_EmitPieces:',
                          '    pld\n    jsl S7Tile_Service\n    rtl\nS7Publisher_EmitPieces:')
    code=code.replace('S7Publisher_EmitPieces:\n    .a16\n    .i16\n',
        'S7Publisher_EmitPieces:\n    .a16\n    .i16\n    lda.l Nmi_FrameCounter\n    sta.l S7Pub_State+$F6\n    lda.l S7Pub_State+42,x\n    inc a\n    sta.l S7Pub_State+$F8\n')
    native=(ROOT/('src/core/actor_source_instance_transport.pasm' if instance_leases else 'src/core/actor_source_tile_transport.pasm')).read_text()
    if instance_leases:
        native=native.replace('cmp #$08C0','cmp #$0B00')
        oam=(ROOT/'src/core/oam.pasm').read_text()
        clear=oam[oam.index('Core_Oam_ClearActive:\n'):oam.index('; Call once per frame after all sprites')]
        for label,width in (('main_loop','a16'),('main_skip','a16'),('hi_loop','a8')):
            clear=clear.replace(f'Core_Oam_ClearActive__{label}:\n',
                                f'Core_Oam_ClearActive__{label}:\n    .{width}\n    .i16\n')
        transform=oam[oam.index('Core_Oam_TransformHiOam:\n'):]
        native+='\n'+(ROOT/'src/core/actor_source_oam_packet.pasm').read_text()+'\n'+clear+transform
        native=native.replace('Core_Oam_ClearActive','S7Packet_ClearActive').replace('Core_Oam_TransformHiOam','S7Packet_TransformHiOam')
        tokens=set(re.findall(r'\b[A-Za-z_][A-Za-z_0-9]*\b',native))
        result['imports'].update({k:v for k,v in sym.items() if k in tokens})
    code=code.replace('\n.org $B000\n','\n'+native+'\n.org $B000\n')
    if plan:
        code='S7Plan_Table = $1FB100\nS7Plan_Count = '+str(len(jobs))+'\n'+code
        code+='\n.org $B100\n'+db(table)
    code+='\n.bank 32\n.org $8000\n'+db(payload)
    code+='\n.bank 33\n.org $8000\n'+db(jobdata if plan else b''.join(images))
    if plan:
        from source_instance_transport import emit_jobs
        code+='\n'+emit_jobs(jobs)
    # Source-generated tail seam: replaces the existing OAM call, not an
    # additional renderer. The small bank0 gate occupies audited zero padding
    # between nmi_handler_end and irq_handler. It is explicit link ownership.
    call=sym['Game_State_Play__done']-3;gate=0xFFA8
    code+=f'\n.bank 0\n.org ${call:04X}\n    jsr ${gate:04X}\n.org ${gate:04X}\n    jsl S7Tile_OamTail\n    rts\n'
    result['assembly']=code
    result['imports']['Oam_UploadFlag']=sym['Oam_UploadFlag']
    result['imports']['Core_Oam_Play_Long']=sym['Core_Oam_Play_Long']
    result['overlays']=[(call,bytes([0x20])+sym['Core_Oam_Play'].to_bytes(2,'little')),(gate,bytes(5))]
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--second-actor',action='store_true')
    parser.add_argument('--instance-leases',action='store_true')
    parser.add_argument('--compact-residency',action='store_true')
    parser.add_argument('--stagger-ticks',type=int,default=0)
    args=parser.parse_args();folder=args.output.resolve();folder.mkdir(parents=True,exist_ok=False)
    if args.compact_residency and not args.instance_leases:parser.error('--compact-residency requires --instance-leases')
    from actor_s6_production_world import build
    build(folder,'kula',resident=True,layout_dispatch=True,publisher=True,stream_publisher=True,deadline_wait=True,second_action=args.second_actor,instance_leases=args.instance_leases,stagger_ticks=args.stagger_ticks,compact_residency=args.compact_residency)
    from actor_s7_bg_validity import install as install_bg
    from actor_s7_fetch_unroll import install as install_fetch
    install_bg(folder);install_fetch(folder,address=False)
    rom=bytearray((folder/'bor.sfc').read_bytes());rom[0x7FDC:0x7FE0]=bytes((255,255,0,0))
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7FDC,checksum^65535,checksum)
    (folder/'bor.sfc').write_bytes(rom)
    link=json.loads((folder/'link.json').read_text())
    link['source_publisher']={'policy':'SOURCE_EXACT',
        'cohort':'independent-instance-snapshots' if args.instance_leases else 'shared-frame',
        'obj_vram_words':[0x4000,0x5000],
        'residency':'32 shared immutable SMALL blocks' if args.instance_leases else 'two 4096-byte buffers',
        'second_actor':args.second_actor,'fixed_stride':False,'instance_leases':args.instance_leases,'stagger_ticks':args.stagger_ticks,
        'compact_residency':args.compact_residency,
        'rom_sha256':hashlib.sha256(rom).hexdigest(),
        'msu_sha256':hashlib.sha256((folder/'bor.msu').read_bytes()).hexdigest()}
    (folder/'link.json').write_text(json.dumps(link,indent=2))
    if args.live:run(folder,second_actor=args.second_actor)
    print(folder)


def run(folder,*,second_actor=False):
    from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact
    from game_bor_startup_select import cold_to_title,select_case
    from unittest.mock import patch
    from actor_s5_isolated import Source
    from frame_publication import oam_oracle
    source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
    manifest=json.loads((folder/'publisher-frame.json').read_text())
    assets=(folder/'publisher-assets.bin').read_bytes();images=(folder/'publisher-stream-images.bin').read_bytes()
    palette=source.read('data/pal.act');snapshots={};proofs={};observations=[];pending=None
    u=lambda b,o:struct.unpack_from('<H',b,o)[0]
    lua=folder/'raster-observer.lua'
    script='''local mt=emu.memType.snesMemory
local count=0
local function w(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end
emu.addEventCallback(function()
 local ok,err=pcall(function()
 if w(0x7f8c06)~=1 or count>=30 then return end
 emu.log("S7RASTER|"..count)
 count=count+1
 local b=emu.getScreenBuffer()
 for y=0,(#b//256)-1 do
  local row={};for x=1,256 do row[x]=string.format("%06x",b[y*256+x]) end
  emu.log("S7ROW|"..count.."|"..y.."|"..table.concat(row))
 end
 local a={};for i=0,543 do a[#a+1]=string.format("%02x",emu.read(i,emu.memType.snesSpriteRam)) end
 local s=emu.getState()
 emu.log("S7OAM|"..count.."|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..table.concat(a))
 local regions={{0xa000,8192},{0xd000,2048}}
 local offset=0
 for _,region in ipairs(regions) do
  for at=0,region[2]-1,256 do
   local bytes={};for i=0,255 do bytes[#bytes+1]=string.format("%02x",emu.read(region[1]+at+i,emu.memType.snesVideoRam)) end
   emu.log("S7MASK|"..count.."|"..offset.."|"..table.concat(bytes));offset=offset+256
  end
 end
 local bytes={};for i=0,63 do bytes[#bytes+1]=string.format("%02x",emu.read(i,emu.memType.snesCgRam)) end
 for i=0,3 do bytes[#bytes+1]=string.format("%02x",emu.read(0x7e501f+i,mt)) end
 emu.log("S7MASK|"..count.."|10240|"..table.concat(bytes))
 end)
 if not ok then emu.log("S7RASTER_ERROR|"..tostring(err)) end
end,emu.eventType.endFrame)
emu.addMemoryCallback(function(a,v)
 if v~=1 then return end
 local row={};for i=0,31 do row[#row+1]=string.format("%02x",emu.read(0x7f8c20+i,mt)) end
 local s=emu.getState();emu.log("S7SNAP|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..table.concat(row))
end,emu.callbackType.write,0x18c26,0x18c26,emu.cpuType.snes,emu.memType.snesWorkRam)
'''
    from actor_s5_entity_fixture import symbols
    syms=symbols(folder/'world.sym');production=symbols(ROOT/'src/main.sym')
    if 'jobs' in manifest:
        addr=syms['S7Tile_OamTail__miss'];off=(addr>>16)*32768+(addr&65535)-32768
        script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();local rows={{}};local jobs={{}}
 for i=0,191 do rows[#rows+1]=string.format("%02x",emu.read(0x7f8c20+i,mt)) end
 for i=0,{len(manifest['jobs'])-1} do jobs[#jobs+1]=tostring(w(0x7f8f40+i*2)) end
 emu.log("S7MISS|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..w(0x7f8ce0).."|"..w(0x7f8f24).."|"..w(0x7f8f28).."|"..table.concat(rows).."|"..table.concat(jobs,","))
end,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    for name in ('S7Publisher_EmitPieces','S7Tile_OamTail','Core_Dma_ProcessQueue__next',*(('S7Packet_Submit',) if 'jobs' in manifest else ())):
        addr=(syms if name in syms else production)[name];off=(addr>>16)*32768+(addr&65535)-32768
        script+=f'''emu.addMemoryCallback(function()
 if w(0x7f8c06)~=1 then return end
 local s=emu.getState();local q=0x7e0480+s["cpu.x"]
 emu.log("S7EVENT|{name}|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..w(0x7f8c2a).."|"..w(q).."|"..w(q+2).."|"..w(0x7f8cfe).."|"..w(q+5).."|"..emu.read(q+7,mt).."|"..emu.read(q+4,mt).."|"..w(0x7f8c16))
end,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
        if name=='S7Packet_Submit':
            script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();local rows={{}}
 for i=0,191 do rows[#rows+1]=string.format("%02x",emu.read(0x7f8c20+i,mt)) end
 emu.log("S7PACK|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..table.concat(rows))
end,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
        if name=='Core_Dma_ProcessQueue__next':
            script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();local q=0x7e0480+s["cpu.x"]
 if emu.read(q+7,mt)==0x7f and w(q+5)==0x8d00 and w(q)==544 then
  local bad=0;local colors={{}}
  for i=0,543 do
   if emu.read(0x7f8d00+i,mt)~=emu.read(i,emu.memType.snesSpriteRam) then bad=bad+1 end
  end
  for i=448,479 do colors[#colors+1]=string.format("%02x",emu.read(i,emu.memType.snesCgRam)) end
  emu.log("S7CONSUMED|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..w(0x7f8f34).."|"..w(0x7f8f36).."|"..bad.."|"..table.concat(colors))
 end
 if emu.read(q+7,mt)~=33 then return end
 local n=w(q);local target=w(q+2);local source=33*65536+w(q+5);local bad=0;local live=0
 for i=0,n-1 do
  if emu.read(source+i,mt)~=emu.read(target+i,emu.memType.snesVideoRam) then bad=bad+1 end
 end
 for i=0,127 do
  local y=emu.read(i*4+1,emu.memType.snesSpriteRam)
  local tile=emu.read(i*4+2,emu.memType.snesSpriteRam)
  local attr=emu.read(i*4+3,emu.memType.snesSpriteRam)
  if y<224 and (attr&14)==12 then
   for row=0,3 do
    local first=0x8000+(tile+row*16)*32
    if target<first+64 and target+n>first then live=live+1 end
   end
  end
 end
 emu.log("S7TRANSFER|"..s["masterClock"].."|"..n.."|"..target.."|"..bad.."|"..live)
end,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    lua.write_text(script)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            # MCP runs at MaximumSpeed; without this setting Mesen may skip
            # rasterization while continuing PPU/OAM execution. That makes a
            # stale image unsuitable as a publication oracle.
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--snes.disableFrameSkipping=true',str(lua)],**kwargs)
            proxy=SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)
            with patch.object(module,'subprocess',proxy):return super().__enter__()
    with Observed(rom=folder/'bor.sfc',mesen=MESEN_EXE,cwd=folder,
                    port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        reporter=Reporter('S7-STREAM')
        with patch.object(m,'reset_emulator',lambda:None):cold_to_title(m,reporter)
        m.write_memory('snesMemory',0x7E1700,bytes(256).hex())
        m.write_memory('snesMemory',0x7E1900,bytes(1536).hex())
        select_case(m,reporter,'KULA','KULA' if second_actor else None);m.write_u16(0x7E1770,1)
        for field in range(110):
            run_frames_exact(m,1)
            if pending:
                index,snap=pending;pending=None
                shot=m.take_screenshot();path=folder/f'source-frame{index}.png';shutil.copyfile(shot['path'],path)
                screen=Image.open(path).convert('RGB');meta=manifest['frames'][index]['source']
                src=Image.open(io.BytesIO(source.read(meta['source_path'])));ox,oy=meta['offset'];matched=0;bad=0
                for y in range(src.height):
                    for x in range(src.width):
                        color=src.getpixel((x,y))
                        if not color:continue
                        xx=u(snap,32)+x-ox;yy=u(snap,34)+y-oy
                        rgb=tuple(((v>>3)<<3)|((v>>3)>>2) for v in palette[3*color:3*color+3])
                        if screen.getpixel((xx,yy))==rgb:matched+=1
                        else:bad+=1
                proofs[index]=dict(field=field,snapshot_tick=u(snap,44),matched_pixels=matched,bad_pixels=bad)
            state=m.read_memory('snesMemory',0x7F8C00,256)
            world=m.read_memory('snesMemory',0x7E1700,256)
            observations.append(dict(field=field,tick=u(world,60),mode=u(world,96),error=u(world,100),
                valid=u(state,38),frame=u(state,42),snapshot_tick=u(state,44),ready=u(state,6),
                resident=[u(state,224),u(state,226)],staging=u(state,228),halves=u(state,230),
                pending=u(state,234),misses=u(state,240),fault=u(state,254)))
            if u(state,6)==1 and u(state,38) and u(state,42)<6:
                snapshots[u(state,42)]=bytes(state)
            oam=m.read_memory('snesSpriteRam',0,544)
            for index,snap in snapshots.items():
                if index in proofs:continue
                meta=manifest['frames'][index];at=0x2100+meta['piece_offset']
                expected=oam_oracle(assets[at:at+meta['piece_bytes']],anchor_x=u(snap,32),anchor_y=u(snap,34),
                                    facing_left=not u(snap,36),palette_slot=6)
                wanted=b''.join(p['low'] for p in expected)
                if wanted and oam[:len(wanted)]==wanted:
                    if 'jobs' in manifest:
                        vram=m.read_memory('snesVideoRam',0x8000,8192);same=True
                        for i,piece in enumerate(meta['chunks']):
                            original=(i//8)*64+(i%8)*2
                            for row in range(4):
                                a=(piece['tile']+row*16)*32;b=index*4096+(original+row*16)*32
                                same &= vram[a:a+64]==images[b:b+64]
                    else:
                        vram=m.read_memory('snesVideoRam',0x8000+(index%2)*4096,4096)
                        same=vram==images[index*4096:(index+1)*4096]
                    if not same:
                        observations[-1]['tile_mismatch_for_oam']=index
                        continue
                    assert m.read_memory('snesCgRam',448,32)==assets[8192:8224]
                    (folder/f'frame{index}-oam.bin').write_bytes(oam)
                    pending=(index,snap)
                    break
            if len(proofs)==6:break
        (folder/'final-publisher-state.bin').write_bytes(state)
    result=dict(proofs=proofs,observations=observations,all_six_pixels= len(proofs)==6 and all(p['bad_pixels']==0 for p in proofs.values()),
                deadlines_certified=False)
    raster_proofs={};rasters={};captures=[];events=[];transfers=[];packets=[];masks={};consumed=[];misses=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        if line.startswith('S7MASK|'):
            _,n,offset,data=line.split('|');masks.setdefault(int(n),{})[int(offset)]=bytes.fromhex(data)
        elif line.startswith('S7MISS|'):
            fields=line.split('|');raw=bytes.fromhex(fields[6]);states=list(map(int,fields[7].split(',')))
            misses.append(dict(zip(('clock','field','snapshot_tick','consumed_min_frame','pending_min_frame'),map(int,fields[1:6])),
                instances=[dict(slot=i,frame=u(raw,i*32+10),tick=u(raw,i*32+12)) for i in range(6) if u(raw,i*32+6)],
                unfinished_jobs=[dict(manifest['jobs'][i],state=state) for i,state in enumerate(states) if state!=65535]))
        elif line.startswith('S7CONSUMED|'):
            fields=line.split('|')
            consumed.append(dict(zip(('clock','field','snapshot_tick','sequence','bad_oam_bytes'),map(int,fields[1:6])),
                                 palette_match=bytes.fromhex(fields[6])==assets[8192:8224]))
        elif line.startswith('S7PACK|'):
            _,clock,field,data=line.split('|');packets.append(dict(clock=int(clock),field=int(field),rows=data))
        elif line.startswith('S7TRANSFER|'):
            transfers.append(dict(zip(('clock','bytes','target','bad_bytes','live_overwrite'),map(int,line.split('|')[1:]))))
        elif line.startswith('S7SNAP|'):
            _,clock,field,data=line.split('|');snap=bytes(32)+bytes.fromhex(data)
            snapshots[u(snap,42)]=snap
            captures.append(dict(clock=int(clock),field=int(field),frame=u(snap,42),tick=u(snap,44)))
        elif line.startswith('S7EVENT|'):
            fields=line.split('|');events.append(dict(zip(
                ('name','clock','field','frame','length','target','fault','source','bank','flags','snapshot_tick'),
                [fields[1],*map(int,fields[2:])])) )
        elif line.startswith('S7ROW|'):
            _,n,y,data=line.split('|');rasters.setdefault(int(n),{})[int(y)]=bytes.fromhex(data)
        elif line.startswith('S7OAM|'):
            _,n,clock,field,data=line.split('|');rows=rasters.get(int(n),{})
            if not rows:continue
            stem=folder/f'raster-{int(n):02d}'
            stem.with_suffix('.ppm').write_bytes(f'P6\n256 {len(rows)}\n255\n'.encode()+b''.join(rows[y] for y in range(len(rows))))
            stem.with_suffix('.oam').write_bytes(bytes.fromhex(data))
            stem.with_suffix('.json').write_text(json.dumps(dict(master_clock=int(clock),field=int(field))))
    for path in sorted(folder.glob('raster-*.ppm')):
        screen=Image.open(path).convert('RGB');oam=path.with_suffix('.oam').read_bytes()
        # Mesen SnesPpu centers the non-overscan224 raster at row7 of239.
        assert screen.size==(256,239)
        screen=screen.crop((0,7,256,231))
        for index,snap in snapshots.items():
            meta=manifest['frames'][index];at=0x2100+meta['piece_offset']
            expected=oam_oracle(assets[at:at+meta['piece_bytes']],anchor_x=u(snap,32),anchor_y=u(snap,34),
                                facing_left=not u(snap,36),palette_slot=6)
            wanted=b''.join(p['low'] for p in expected)
            if not wanted or oam[:len(wanted)]!=wanted:continue
            src=Image.open(io.BytesIO(source.read(meta['source']['source_path'])));ox,oy=meta['source']['offset'];matched=0;bad=0
            for y in range(src.height):
                for x in range(src.width):
                    color=src.getpixel((x,y))
                    if not color:continue
                    rgb=tuple(((v>>3)<<3)|((v>>3)>>2) for v in palette[3*color:3*color+3])
                    if screen.getpixel((u(snap,32)+x-ox,u(snap,34)+y-oy))==rgb:matched+=1
                    else:bad+=1
            if bad==0:
                screen.save(folder/f'verified-frame{index}.png')
                raster_proofs[index]=dict(raster=path.name,matched=matched,bad=bad)
    result['end_frame_pixel_proofs']=raster_proofs
    result['gui_all_six_pixels']=result['all_six_pixels']
    result['all_six_pixels']=len(raster_proofs)==6
    result['native_faults']=sorted({r['fault'] for r in observations if r['ready']==1 and r['fault']})
    result['transfer_checks']=transfers
    result['transfers_safe']=len(transfers)==len(manifest.get('jobs',range(8))) and all(not t['bad_bytes'] and not t['live_overwrite'] for t in transfers)
    result['captures']=captures;result['events']=events
    result['readiness_misses']=misses
    result['consumed_packets']=consumed
    result['packet_fences_pass']=bool(consumed) and all(not c['bad_oam_bytes'] and c['palette_match'] for c in consumed) if 'jobs' in manifest else None
    for n,parts in masks.items():
        (folder/f'raster-{n:02d}.bg.bin').write_bytes(b''.join(data for _,data in sorted(parts.items())))
    packet_proofs={}
    for path in sorted(folder.glob('raster-*.ppm')):
        screen=Image.open(path).convert('RGB').crop((0,7,256,231));oam=path.with_suffix('.oam').read_bytes()
        for packet in packets:
            raster_clock=json.loads(path.with_suffix('.json').read_text())['master_clock']
            if packet['clock']>raster_clock:continue
            raw=bytes.fromhex(packet['rows']);actors=[];wanted=b'';high=[]
            for slot in range(6):
                r=raw[slot*32:(slot+1)*32]
                if u(r,6)!=1:continue
                index=u(r,10);meta=manifest['frames'][index];at=0x2100+meta['piece_offset']
                expected=oam_oracle(assets[at:at+meta['piece_bytes']],anchor_x=u(r,0),anchor_y=u(r,2),facing_left=not u(r,4),palette_slot=6)
                wanted+=b''.join(p['low'] for p in expected);high.extend(p['high'] for p in expected);actors.append((slot,index,r))
            if not wanted or oam[:len(wanted)]!=wanted:continue
            if any(((oam[512+i//4]>>(2*(i%4)))&3)!=bits for i,bits in enumerate(high)):continue
            completion=next((c for c in consumed if packet['clock']<c['clock']<=raster_clock
                            and c['snapshot_tick']==u(actors[0][2],12)),None)
            if 'jobs' in manifest and completion is None:continue
            # Lower OAM index wins overlapping OBJ pixels. Compare the composed
            # visible source pixels, without treating occlusion as data loss.
            pixels={}
            for slot,index,r in reversed(actors):
                meta=manifest['frames'][index]['source'];src=Image.open(io.BytesIO(source.read(meta['source_path'])));ox,oy=meta['offset']
                for y in range(src.height):
                    for x in range(src.width):
                        c=src.getpixel((x,y))
                        if not c:continue
                        xx=u(r,0)+(x-ox if u(r,4) else ox-x);yy=u(r,2)+y-oy
                        pixels[xx,yy]=(slot,tuple(((v>>3)<<3)|((v>>3)>>2) for v in palette[3*c:3*c+3]))
            mask=path.with_suffix('.bg.bin').read_bytes();occluded=[];bad=False
            for xy,(_,rgb) in pixels.items():
                actual=screen.getpixel(xy)
                if actual==rgb:continue
                # Actual high-priority BG3 HUD may cover source pixels. Decode
                # its hardware tile/palette, never mask a guessed rectangle.
                x=(xy[0]+u(mask,10304))&255;y=(xy[1]+u(mask,10306)+1)&255
                word=u(mask,8192+((y//8)*32+x//8)*2);tile=word&1023
                if not word&8192 or tile>=512:bad=True;break
                px=x&7;py=y&7
                if word&16384:px=7-px
                if word&32768:py=7-py
                a=tile*16+py*2;color=((mask[a]>>(7-px))&1)|(((mask[a+1]>>(7-px))&1)<<1)
                packed=u(mask,10240+(((word>>10)&7)*4+color)*2)
                bg=tuple((((packed>>shift)&31)<<3)|(((packed>>shift)&31)>>2) for shift in (0,5,10))
                if not color or bg!=actual:bad=True;break
                occluded.append(xy)
            if bad:continue
            key=','.join(f'{s}:{i}' for s,i,_ in actors)
            if key in packet_proofs:continue
            counts={str(s):sum(owner==s and xy not in occluded for xy,(owner,_) in pixels.items()) for s,_,_ in actors}
            shot=f'packet-{key.replace(":","-").replace(",","_")}.png';screen.save(folder/shot)
            packet_proofs[key]=dict(snapshot_ticks=[u(r,12) for _,_,r in actors],frames=[i for _,i,_ in actors],
                prepared_clock=packet['clock'],prepared_field=packet['field'],
                hardware_consumed=completion,
                raster=json.loads(path.with_suffix('.json').read_text()),visible_pixels=counts,hud_occluded_pixels=len(occluded),oam_pieces=len(high),screenshot=shot)
    result['packet_proofs']=packet_proofs
    result['readiness_miss_count']=max((o['misses'] for o in observations),default=0)
    result['independent_frame_pairs']=[p['frames'] for p in packet_proofs.values() if len(set(p['frames']))>1]
    result['both_instances_all_six_synchronized']=all(
        any(p['frames']==[frame,frame] for p in packet_proofs.values()) for frame in range(6)) if second_actor else None
    result['both_instances_all_six']=all(
        any(len(p['frames'])==2 and p['frames'][slot]==frame for p in packet_proofs.values())
        for slot in range(2) for frame in range(6)) if second_actor else None
    staggered=json.loads((folder/'link.json').read_text())['source_publisher'].get('stagger_ticks',0)!=0
    result['scope']='BOUNDED_NATIVE_PUBLICATION; NOT_STRICT_LATENCY_OR_WHOLE_MODEL_CERTIFICATION'
    (folder/'stream-publication.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('observations','captures','events')},indent=2))
    assert result['all_six_pixels'] and result['transfers_safe'] and not result['native_faults'] and not result['readiness_miss_count'] and (
        not second_actor or (result['both_instances_all_six'] if staggered else result['both_instances_all_six_synchronized'])) and (
        'jobs' not in manifest or result['packet_fences_pass']), 'NATIVE_PUBLICATION_WORKLOAD_BLOCKED; see stream-publication.json'


if __name__=='__main__':main()
