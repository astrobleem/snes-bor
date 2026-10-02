"""Explicit multi-model publisher fixture; production policy remains unchanged."""
import json
import re
import struct
from actor_s5_isolated import ROOT
from source_publication_set import oam_resource_report
from source_publication_native import prepare

def run(folder):
    import io,shutil,subprocess
    from types import SimpleNamespace
    from unittest.mock import patch
    from PIL import Image
    from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact
    from game_bor_startup_select import cold_to_title,select_case
    from actor_s5_entity_fixture import symbols
    from actor_s5_isolated import Source
    from frame_publication import oam_oracle
    source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
    manifest=json.loads((folder/'publisher-multi.json').read_text())
    config=json.loads((folder/'multi-config.json').read_text()) if (folder/'multi-config.json').exists() else {}
    horizon=config.get('source_tick_horizon',19)
    assets=(folder/'publisher-assets.bin').read_bytes()
    syms=symbols(folder/'world.sym');production=symbols(ROOT/'src/main.sym')
    lua=folder/'multi-observer.lua'
    script='''local mt=emu.memType.snesMemory
local function w(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end
local function bytes(a,n,t) local b={} for i=0,n-1 do b[#b+1]=string.format("%02x",emu.read(a+i,t)) end return table.concat(b) end
local preparing=0
local owned={}
emu.addMemoryCallback(function(a,v)
 if (a-0x7e0484)%8~=0 or (v&0x40)==0 then return end
 local q=a-4;local source=w(q+5)
 if emu.read(q+7,mt)~=127 or (source~=0x8d00 and source~=0xa600) then return end
 local control=preparing==0xa600 and 0x7fa834 or 0x7f8f34
 local s=emu.getState()
 emu.log("QUEUED|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..preparing.."|"..source.."|"..w(control).."|"..w(control+2))
 owned[source]=true
end,emu.callbackType.write,0x7e0484,0x7e04bc,emu.cpuType.snes)
for _,base in ipairs({0x8d00,0xa600}) do
 emu.addMemoryCallback(function()
  if owned[base] then emu.log("LIVE_PACKET_OVERWRITE|"..base) end
end,emu.callbackType.write,0x7f0000+base,0x7f0000+base,emu.cpuType.snes)
end
for i,base in ipairs({0xa840,0xa880}) do
 emu.addMemoryCallback(function()
  local packet=i==1 and 0x8d00 or 0xa600
  if owned[packet] then emu.log("LIVE_PALETTE_OVERWRITE|"..base) end
 end,emu.callbackType.write,0x7f0000+base,0x7f0000+base+63,emu.cpuType.snes)
end
local captures=0
emu.addEventCallback(function()
 if w(0x7f8c06)~=1 or captures>=CAPTURE_LIMIT then return end
 captures=captures+1
 local s=emu.getState();local b=emu.getScreenBuffer()
 emu.log("RASTER|"..captures.."|"..s["masterClock"].."|"..s["ppu.frameCount"])
 for y=0,(#b//256)-1 do
  local row={} for x=1,256 do row[x]=string.format("%06x",b[y*256+x]) end
  emu.log("ROW|"..captures.."|"..y.."|"..table.concat(row))
 end
end,emu.eventType.endFrame)
'''
    script=script.replace('CAPTURE_LIMIT',str(horizon//3+30))
    if 'S7Multi_PublishSnapshot__completed' in syms:
        script+='\nlocal publication_call=nil\n'
        for phase in ('entry','completed'):
            name='S7Multi_PublishSnapshot'+('' if phase=='entry' else '__completed')
            a=syms[name];off=(a>>16)*32768+(a&65535)-32768
            body='publication_call=s' if phase=='entry' else '''local bad=0
 for _,key in ipairs({"cpu.d","cpu.dbr","cpu.x","cpu.y","cpu.sp","cpu.ps"}) do
 if publication_call[key]~=s[key] then bad=bad+1 end end
 emu.log("PUBLICATION_CALL|"..(s["masterClock"]-publication_call["masterClock"]).."|"..bad)
'''
            script+=f'emu.addMemoryCallback(function() local s=emu.getState();{body}\nend,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
    if manifest.get('packet_palettes'):
        script+='\nlocal palette_calls={}\n'
        for prefix in ('S7Packet','S7Packet2'):
            for phase in ('entry','done'):
                name=prefix+'_PreparePalette'+('' if phase=='entry' else '__done')
                a=syms[name];off=(a>>16)*32768+(a&65535)-32768
                body=(f'palette_calls["{prefix}"]=s' if phase=='entry' else f'''
 local old=palette_calls["{prefix}"];local bad=0
 for _,key in ipairs({{"cpu.d","cpu.dbr","cpu.x","cpu.y","cpu.sp"}}) do if old[key]~=s[key] then bad=bad+1 end end
 if (s["cpu.ps"]&0x30)~=0 then bad=bad+1 end
 emu.log("PALETTE_CALL|"..(s["masterClock"]-old["masterClock"]).."|"..bad)
''')
                script+=f'emu.addMemoryCallback(function() local s=emu.getState();{body}\nend,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
        a=syms['S7Palette_Transfer__completed'];off=(a>>16)*32768+(a&65535)-32768
        script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();local q=0x7e0480+s["cpu.x"]
 local base=w(q+5)==0x8d00 and 0x7fa840 or 0x7fa880
 local bad=0;for i=0,63 do if emu.read(base+i,mt)~=emu.read(448+i,emu.memType.snesCgRam) then bad=bad+1 end end
 emu.log("PALETTE_COMPLETED|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..w(q+5).."|"..bad.."|"..tostring(s["ppu.scanline"]).."|"..w(q))
end,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    for name in ('S7Multi_CaptureComplete','S7Packet_Submit__source','S7Packet2_Submit__source','Core_Dma_ProcessQueue__next','S7Packet_Submit__fault','S7Packet2_Submit__fault','S7Multi_OamTail__budget','S7Multi_OamTail__busy','S7Multi_OamTail__missing'):
        a=syms.get(name,production.get(name));off=(a>>16)*32768+(a&65535)-32768
        body=(f'preparing={0xA600 if name=="S7Packet2_Submit__source" else 0x8D00}; emu.log("PACK|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..bytes(0x7f8c20,192,mt).."|"..preparing.."|"..w(0x7f8cf2).."|"..bytes(0x7f8cf4,6,mt))' if name in ('S7Packet_Submit__source','S7Packet2_Submit__source') else '''
 local q=0x7e0480+s["cpu.x"]
 if (emu.read(q+4,mt)&3)~=1 and w(0x7fad32)==1 then return end
 if (emu.read(q+4,mt)&3)==1 and w(q)<=544 and w(q+2)==0 then
 local address=65536*emu.read(q+7,mt)+w(q+5)
 if address~=0x7f8d00 and address~=0x7fa600 then
 local bad=0;for i=0,w(q)-1 do if emu.read(address+i,mt)~=emu.read(i,emu.memType.snesSpriteRam) then bad=bad+1 end end
 emu.log("COMPAT_OAM|"..s["masterClock"].."|"..w(q).."|"..bad)
 end end
 if emu.read(q+7,mt)==32 then
 local t=emu.memType.snesVideoRam;if (emu.read(q+4,mt)&3)==2 then t=emu.memType.snesCgRam end
 local bad=0;for i=0,w(q)-1 do if emu.read(0x200000+w(q+5)+i,mt)~=emu.read(w(q+2)+i,t) then bad=bad+1 end end
 emu.log("TRANSFER|"..s["masterClock"].."|"..w(q).."|"..w(q+2).."|"..w(q+5).."|"..emu.read(q+4,mt).."|"..bad) end
 if emu.read(q+7,mt)==127 and (w(q+5)==0x8d00 or w(q+5)==0xa600) then
 local control=0x7f8f34;if w(q+5)==0xa600 then control=0x7fa834 end
 if w(control+10)~=0 then
 emu.log("REJECTED_PACKET|"..s["masterClock"].."|"..w(q+5).."|"..w(control+2))
 owned[w(q+5)]=false;return end
 local bad=0;for i=0,543 do if emu.read(0x7f0000+w(q+5)+i,mt)~=emu.read(i,emu.memType.snesSpriteRam) then bad=bad+1 end end
 emu.log("CONSUMED|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..w(control).."|"..w(control+2).."|"..bytes(0,544,emu.memType.snesSpriteRam).."|"..bytes(448,64,emu.memType.snesCgRam).."|"..w(q+5).."|"..bad)
 owned[w(q+5)]=false
 end
''')
        if name=='S7Multi_CaptureComplete':body='emu.log("SNAPSHOT|"..s["masterClock"].."|"..s["ppu.frameCount"].."|"..w(0x7f8ce0).."|"..w(0x7f8cf2))'
        if name=='S7Multi_OamTail__missing':body='emu.log("ADMISSION_BLOCKED|"..s["masterClock"].."|"..w(0x7f8ce0).."|"..w(0x7f8cea).."|"..w(0x7f8cec))'
        if name.endswith(('__fault','__budget','__busy')):body='emu.log("FAULT|"..s["masterClock"].."|"..w(0x7f8f20).."|"..w(0x7f8f22))'
        script+=f'''emu.addMemoryCallback(function() local s=emu.getState()
{body}
end,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    for name in ('S7Oam_Order__swapped','S7Admission_Scanlines__blocked','S7Admission_Owners__blocked','S7Admission_Scanlines__cached','S7Admission_Scanlines__compute','S7Admission_Scanlines__result'):
        if name not in syms:continue
        a=syms[name];off=(a>>16)*32768+(a&65535)-32768
        script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState()
 emu.log("ADMIT_EVENT|{name}|"..s["masterClock"].."|"..w(0x7f8ce0).."|"..w(0x7f8c1c).."|"..w(0x7f8c1e))
end,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    if config.get('compat_slots'):
        a=production['Core_Dma_ProcessQueue__next'];off=(a>>16)*32768+(a&65535)-32768
        script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();local q=0x7e0480+s["cpu.x"]
 if w(0x7fad32)==1 then return end
 if (emu.read(q+4,mt)&3)~=0 or w(q+2)<0x8000 or w(q+2)>=0xa000 or emu.read(q+7,mt)==32 then return end
 local src=65536*emu.read(q+7,mt)+w(q+5);local bad=0
 for i=0,w(q)-1 do if emu.read(src+i,mt)~=emu.read(w(q+2)+i,emu.memType.snesVideoRam) then bad=bad+1 end end
 emu.log("COMPAT_TILE|"..s["masterClock"].."|"..w(q+2).."|"..w(q).."|"..bad)
end,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)
'''
    if config.get('guard_probes'):
        script+='\nlocal owner_injected=false;local owner_saved=nil;local framing_injected=false;local framing_saved=nil;local framing_oam=nil;local framing_pal=nil\n'
        owner_address=(0x7E0A00+133+production['CHAR_TILE_COLUMN'] if config.get('compat_slots') else syms['S6Bridge_Policy']+266)
        owner_value=2 if config.get('compat_slots') else 0
        hooks={
            'S7Admission_Owners':f'''if not owner_injected and w(0x7f8c06)==1 then
 owner_saved=emu.read({owner_address},mt);emu.write({owner_address},{owner_value},mt);owner_injected=true
end''',
            'S7Admission_Owners__blocked':f'''if owner_saved~=nil then
 emu.write({owner_address},owner_saved,mt);owner_saved=nil;emu.log("OWNER_GUARD_REJECTED") end''',
            'S7Framing_Admit':f'''local q=0x7e0480+s["cpu.x"];local src=w(q+5)
 local control=src==0x8d00 and 0x7f8f34 or 0x7fa834
 if not framing_injected and (src==0x8d00 or src==0xa600) and w(control)>=6 and w(control+8)~=0 then
 framing_saved=w({production['Nmi_Bg1ScrollX']});framing_oam=bytes(0,544,emu.memType.snesSpriteRam);framing_pal=bytes(448,64,emu.memType.snesCgRam)
 emu.write({production['Nmi_Bg1ScrollX']},(framing_saved~1)&255,mt);framing_injected=true end''',
            'S7Palette_Transfer__rejected':f'''if framing_saved~=nil then
 local bad_oam=bytes(0,544,emu.memType.snesSpriteRam)~=framing_oam and 1 or 0
 local bad_pal=bytes(448,64,emu.memType.snesCgRam)~=framing_pal and 1 or 0
 emu.write({production['Nmi_Bg1ScrollX']},framing_saved&255,mt);framing_saved=nil
 emu.log("FRAMING_GUARD_REJECTED|"..bad_oam.."|"..bad_pal) end'''}
        for name,body in hooks.items():
            a=syms[name];off=(a>>16)*32768+(a&65535)-32768
            script+=f'emu.addMemoryCallback(function() local s=emu.getState();{body}\nend,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
    # A one-shot diagnostic input, armed only after the positive workload.
    # Change the framing at the actual NMI boundary, including a field with
    # no new source packet; never inject a replacement image or source state.
    if config.get('retirement_probe')=='framing':
        script+='\nlocal retire_before=nil;local retire_pal=nil\n'
        hooks={
            'S7Framing_ScrollX':f'''if w(0x7faa0a)==1 and w(0x7fad22)~=0 then
 emu.write(0x7faa0a,2,mt);retire_before=bytes(0,544,emu.memType.snesSpriteRam);retire_pal=bytes(448,64,emu.memType.snesCgRam)
 emu.log("FRAMING_ENTRY|"..s["masterClock"].."|"..s["ppu.scanline"].."|"..bytes(0x7fab00,544,mt).."|"..retire_before)
 emu.write({production['Nmi_Bg1ScrollX']},(w({production['Nmi_Bg1ScrollX']})~1)&255,mt)
end''',
            'S7Framing_ScrollX__retired':'''if retire_before~=nil then
 local expected={};for i=1,544 do expected[i]=tonumber(retire_before:sub(2*i-1,2*i),16) end
 for i=0,127 do if ((expected[4*i+4]>>1)&7)>=6 then expected[4*i+1]=0;expected[4*i+2]=224 end end
 local bad=0;for i=0,543 do if emu.read(i,emu.memType.snesSpriteRam)~=expected[i+1] then bad=bad+1 end end
 local palbad=bytes(448,64,emu.memType.snesCgRam)~=retire_pal and 1 or 0
 emu.log("DISPLAY_RETIRED|"..s["masterClock"].."|"..bad.."|"..palbad.."|"..s["ppu.scanline"])
 emu.log("RETIRE_OAM|"..bytes(0,544,emu.memType.snesSpriteRam))
 retire_before=nil
end'''}
        for name,body in hooks.items():
            a=syms[name];off=(a>>16)*32768+(a&65535)-32768
            script+=f'emu.addMemoryCallback(function() local s=emu.getState();{body}\nend,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
    if 'S7Lease_Admit__denied' in syms:
        script+='\nlocal lease_vram=nil;local lease_cgram=nil\n'
        for name in ('S7Lease_TransferVram','S7Lease_TransferCgram','S7Lease_Admit__denied'):
            a=syms[name];off=(a>>16)*32768+(a&65535)-32768
            body=('''if w(0x7faa0a)==1 then lease_vram=bytes(0x8000,8192,emu.memType.snesVideoRam);lease_cgram=bytes(0,512,emu.memType.snesCgRam) end'''
                  if name!='S7Lease_Admit__denied' else '''local q=0x7e0480+w(0x7fad30)
 local vb=bytes(0x8000,8192,emu.memType.snesVideoRam)~=lease_vram and 1 or 0
 local cb=bytes(0,512,emu.memType.snesCgRam)~=lease_cgram and 1 or 0
 emu.log("LEASE_DENIED|"..s["masterClock"].."|"..(emu.read(q+4,mt)&3).."|"..w(q+2).."|"..w(q).."|"..vb.."|"..cb)''')
            script+=f'emu.addMemoryCallback(function() local s=emu.getState();{body}\nend,emu.callbackType.exec,{off},{off},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
    lua.write_text(script)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--snes.disableFrameSkipping=true',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    observations=[];epoch_events=[];reopened=False
    mixed=bool(config.get('compat_slots'))
    def retired_picture(oam):
        visible=[i for i in range(128) if oam[4*i:4*i+2]!=bytes((0xC0,0xE0))]
        if not mixed:return not visible
        # Source uses palettes6/7; retained accepted slot1 owns palette1,
        # tile4 and LARGE size. This is the unchanged production descriptor.
        return bool(visible) and all((oam[4*i+3]>>1)&7==1 and oam[4*i+2]==4 and
            ((oam[512+i//4]>>(2*(i%4)))&2)==2 for i in visible)
    with Observed(rom=folder/'bor.sfc',mesen=MESEN_EXE,cwd=folder,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        reporter=Reporter('S7-MULTI')
        with patch.object(m,'reset_emulator',lambda:None):cold_to_title(m,reporter)
        m.write_memory('snesMemory',0x7E1700,bytes(256).hex())
        m.write_memory('snesMemory',0x7E1900,bytes(1536).hex())
        m.write_u16(0x7FAA0A,0)
        select_case(m,reporter,'KULA','MARY');m.write_u16(0x7E1770,1)
        for field in range(75+horizon//2):
            run_frames_exact(m,1)
            state=m.read_memory('snesMemory',0x7F8C00,256)
            u=lambda o:struct.unpack_from('<H',state,o)[0]
            observations.append(dict(field=field,ready=u(6),p1=[u(38),u(40),u(42),u(44)],p2=[u(70),u(72),u(74),u(76)],fault=u(254)))
            if config['case']=='scanline-block' and u(254)==0xD70A:break
            if config.get('epoch_reuse_probe') and not reopened and u(6)==1 and u(38)==1 and u(44)>=80:
                # An invalid open request must not revoke a live lease.
                m.write_u16(0x7FA8C0,2)
                for _ in range(3):
                    run_frames_exact(m,1)
                    if m.read_memory('snesMemory',0x7FA8C0,2)==bytes(2):break
                assert m.read_memory('snesMemory',0x7F8CFE,2)==bytes.fromhex('07d7')
                assert m.read_memory('snesMemory',0x7F8CF2,2)==bytes(2)
                m.write_u16(0x7FA8C0,1)
                for _ in range(10):
                    run_frames_exact(m,1)
                    phase=int.from_bytes(m.read_memory('snesMemory',0x7F8CF2,2),'little')
                    pending=[m.read_memory('snesMemory',a,2).hex() for a in (0x7F8F20,0x7FA820)]
                    epoch_events.append(dict(event='close',phase=phase,pending=pending))
                    if phase==3:break
                assert phase==3 and pending==['0000','0000']
                oam=m.read_memory('snesSpriteRam',0,544)
                assert retired_picture(oam),'Source retirement must preserve accepted OAM'
                if mixed:
                    shot=m.take_screenshot();shutil.copyfile(shot['path'],folder/'compat-while-source-closed.png')
                    (folder/'compat-while-source-closed.oam').write_bytes(oam)
                # No state reset, replay injection, or VRAM oracle injection.
                m.write_u16(0x7FA8C0,2)
                for _ in range(20):
                    run_frames_exact(m,1)
                    phase=int.from_bytes(m.read_memory('snesMemory',0x7F8CF2,2),'little')
                    generation=int.from_bytes(m.read_memory('snesMemory',0x7FA8C4,2),'little')
                    epoch_events.append(dict(event='reopen',phase=phase,generation=generation))
                    if generation==1:break
                assert generation==1 and phase==0
                reopened=True
            if u(6) and (u(38) or u(70)):
                shot=m.take_screenshot();shutil.copyfile(shot['path'],folder/f'observed-{field}.png')
                (folder/f'observed-{field}.vram').write_bytes(m.read_memory('snesVideoRam',0x8000,8192))
                (folder/f'observed-{field}.oam').write_bytes(m.read_memory('snesSpriteRam',0,544))
                (folder/f'observed-{field}.cgram').write_bytes(m.read_memory('snesCgRam',448,64))
            # This map-only probe admits idle frame0 through tick19. A
            # render snapshot can lag the completed clock; waiting for its
            # stale valid bit after frame0 ends would accidentally run forever
            # through intentionally unlinked later frames. No simulation stop
            # or expected state is injected; close uses the normal API.
            if config['case']=='map-switch' and u(6) and int.from_bytes(
                    m.read_memory('snesMemory',0x7E1774,2),'little')>=horizon:break
            if u(6)==1 and u(38)==1 and u(44)>=horizon:break
        # Close the publication epoch explicitly; do not free resources merely
        # because the observer stopped. Simulation continues during this fence.
        retirement=config.get('retirement_probe')
        if retirement=='framing':
            m.write_u16(0x7FAA0A,1)
            for _ in range(4):
                run_frames_exact(m,1)
                if m.read_memory('snesMemory',0x7FAA0A,2)==bytes.fromhex('0200'):break
            assert m.read_memory('snesMemory',0x7FAA0A,2)==bytes.fromhex('0200')
            shot=m.take_screenshot();shutil.copyfile(shot['path'],folder/'framing-retired.png')
        elif retirement=='owner':
            assert mixed
            m.write_memory('snesMemory',0x7E0A00+133+production['CHAR_TILE_COLUMN'],'02')
        elif retirement=='dma':
            # Two explicit malformed *requests*, not expected OAM or actor
            # state. Publish ACTIVE last in currently free queue slots and
            # account their bytes in the existing budget. Actual native DMA
            # dispatch must refuse both while the source epoch owns them.
            block=next(iter(manifest['blocks'].values()))['slot']
            tile=(block//8)*64+(block%8)*2
            m.write_u16(0x7FAA0A,1)
            for kind,target in ((0,0x8000+tile*32),(2,448)):
                queue=m.read_memory('snesMemory',0x7E0480,64)
                cursor=int.from_bytes(m.read_memory('snesMemory',production['DmaQueue_CurrentSlot'],2),'little')&63
                free=next((cursor+i*8)&63 for i in range(8) if not queue[((cursor+i*8)&63)+4]&64)
                budget=int.from_bytes(m.read_memory('snesMemory',production['DmaQueue_BudgetTotal'],2),'little')
                assert budget+32<2816
                m.write_memory('snesMemory',0x7E0480+free,struct.pack('<HHBHB',32,target,kind,0x5100,0x7E).hex())
                m.write_u16(production['DmaQueue_BudgetTotal'],budget+32)
                m.write_memory('snesMemory',0x7E0484+free,bytes([kind|64]).hex())
                run_frames_exact(m,2)
            m.write_u16(0x7FAA0A,0)
        if int.from_bytes(m.read_memory('snesMemory',0x7F8CF2,2),'little')==0:
            m.write_u16(0x7FA8C0,1)
        teardown=[]
        for _ in range(8):
            run_frames_exact(m,1)
            st=m.read_memory('snesMemory',0x7F8C00,256)
            phase=struct.unpack_from('<H',st,242)[0]
            pending=[m.read_memory('snesMemory',a,2).hex() for a in (0x7F8F20,0x7FA820)]
            oam=m.read_memory('snesSpriteRam',0,544)
            hidden=(all(oam[4*i:4*i+2]==bytes((0xC0,0xE0)) for i in range(128))
                    if retirement=='owner' else retired_picture(oam))
            teardown.append(dict(phase=phase,pending=pending,hardware_hidden=hidden))
            if phase==3:break
        (folder/'teardown.json').write_text(json.dumps(teardown,indent=2))
        assert teardown[-1]['phase']==3 and teardown[-1]['hardware_hidden'] and teardown[-1]['pending']==['0000','0000'],'Pinned lease released before hidden OAM completion'
        if 'S7Lease_Admit' in syms:
            armed=int.from_bytes(m.read_memory('snesMemory',0x7FAD28,2),'little')
            assert armed==0,'Native transfer lease did not follow hardware retirement'
            (folder/'dma-lease-release.json').write_text(json.dumps(dict(phase=3,armed=armed,source_references=0),indent=2))
    (folder/'multi-observations.json').write_text(json.dumps(observations,indent=2))
    if config.get('epoch_reuse_probe'):
        assert reopened
        (folder/'epoch-reuse.json').write_text(json.dumps(epoch_events,indent=2))
    print(observations[-12:])
    analyze(folder)


def analyze(folder):
    import io
    from PIL import Image
    config=json.loads((folder/'multi-config.json').read_text())
    from actor_s5_isolated import Source
    from frame_publication import oam_oracle
    source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
    manifest=json.loads((folder/'publisher-multi.json').read_text());assets=(folder/'publisher-assets.bin').read_bytes()
    packets=[];consumed=[];rasters={};transfers=[];faults=[];queued=[];overwrites=[];snapshots=[];admission=[];palette_completions=[];palette_calls=[];compat_oam=[];compat_tiles=[]
    staged_references={};pending_references={};displayed_references=False;vram_lease_violations=[];publication_calls=[];rejected_packets=[];admit_events=[];guard_rejections=[];display_retirements=[];lease_denials=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        a=line.split('|')
        if a[0]=='PACK':
            packets.append(dict(clock=int(a[1]),field=int(a[2]),rows=bytes.fromhex(a[3]),buffer=int(a[4]) if len(a)>4 else None,closing=int(a[5]) if len(a)>5 else False,order=list(bytes.fromhex(a[6])) if len(a)>6 else list(range(6))))
            p=packets[-1]
            staged_references[p['buffer']]=not p['closing'] and any(struct.unpack_from('<H',p['rows'],slot*32+6)[0] for slot in range(6))
        elif a[0]=='CONSUMED':
            consumed.append(dict(clock=int(a[1]),field=int(a[2]),tick=int(a[3]),sequence=int(a[4]),oam=bytes.fromhex(a[5]),cgram=bytes.fromhex(a[6]),buffer=int(a[7]) if len(a)>7 else None,bad_bytes=int(a[8]) if len(a)>8 else None))
            c=consumed[-1];displayed_references=pending_references.pop((c['buffer'],c['sequence']))
        elif a[0]=='REJECTED_PACKET':
            rejected_packets.append(list(map(int,a[1:])))
            pending_references.pop((int(a[2]),int(a[3])))
        elif a[0]=='DISPLAY_RETIRED':
            display_retirements.append(list(map(int,a[1:])))
            displayed_references=False
        elif a[0]=='LEASE_DENIED':lease_denials.append(list(map(int,a[1:])))
        elif a[0]=='ADMIT_EVENT':admit_events.append([a[1],*map(int,a[2:])])
        elif a[0] in ('OWNER_GUARD_REJECTED','FRAMING_GUARD_REJECTED'):guard_rejections.append(a)
        elif a[0]=='TRANSFER':
            transfers.append(list(map(int,a[1:])))
            if (int(a[5])&3)==0 and (displayed_references or any(pending_references.values())):
                vram_lease_violations.append(int(a[1]))
        elif a[0]=='FAULT':faults.append(list(map(int,a[1:])))
        elif a[0]=='QUEUED':
            queued.append(list(map(int,a[1:])))
            q=queued[-1];pending_references[(q[3],q[5])]=staged_references[q[3]]
        elif a[0]=='LIVE_PACKET_OVERWRITE':overwrites.append(a[1:])
        elif a[0]=='LIVE_PALETTE_OVERWRITE':overwrites.append(a[1:])
        elif a[0]=='PALETTE_COMPLETED':palette_completions.append(list(map(int,a[1:])))
        elif a[0]=='PALETTE_CALL':palette_calls.append(list(map(int,a[1:])))
        elif a[0]=='PUBLICATION_CALL':publication_calls.append(list(map(int,a[1:])))
        elif a[0]=='COMPAT_OAM':compat_oam.append(list(map(int,a[1:])))
        elif a[0]=='COMPAT_TILE':compat_tiles.append(list(map(int,a[1:])))
        elif a[0]=='SNAPSHOT':snapshots.append(list(map(int,a[1:])))
        elif a[0]=='ADMISSION_BLOCKED':admission.append(list(map(int,a[1:])))
        elif a[0]=='RASTER':rasters[int(a[1])]=dict(clock=int(a[2]),field=int(a[3]),rows=[])
        elif a[0]=='ROW':rasters[int(a[1])]['rows'].append(bytes.fromhex(a[3]))
    proofs=[];packet_latencies=[];shared_resources=[]
    for c in consumed:
        qs=[q for q in queued if q[3]==c['buffer'] and q[4:]==[c['tick'],c['sequence']] and q[0]<c['clock']]
        assert len(qs)==1,'Completion must resolve one immutable queued identity'
        q=qs[0]
        packet_latencies.append(dict(snapshot=c['tick'],buffer=c['buffer'],sequence=c['sequence'],queued=q[0],consumed=c['clock'],queue_field=q[1],consumed_field=c['field']))
        objects=[(c['oam'][4*i+1],64 if ((c['oam'][512+i//4]>>(2*(i%4)))&2) else 32) for i in range(128)]
        lines=[(sum(((y-start)&255)<height for start,height in objects),
                sum(height//16 for start,height in objects if ((y-start)&255)<height)) for y in range(224)]
        maximum=tuple(map(max,zip(*lines)))
        entries=[e for e in admit_events if e[0]=='S7Admission_Scanlines__result' and e[1]<q[0] and e[2]==c['tick']]
        if entries:
            actual=entries[-1][3:5]
            assert list(maximum)==actual,'Native shared OAM admission differs from hardware packet geometry'
            assert maximum[0]<=32 and maximum[1]<=34,'Unsafe shared packet reached hardware'
            shared_resources.append(dict(snapshot=c['tick'],consumed=c['clock'],maximum_objs=maximum[0],maximum_slivers=maximum[1]))
    regressions=[dict(previous=a,current=b) for a,b in zip(packet_latencies,packet_latencies[1:]) if b['queued']<a['queued']]
    for number,r in rasters.items():
        if any(event[0]<r['clock'] for event in display_retirements):continue
        cs=[c for c in consumed if c['field']==r['field'] and c['clock']<r['clock']]
        if not cs:continue
        c=max(cs,key=lambda c:c['clock']);ps=[p for p in packets if p['clock']<c['clock'] and p['buffer']==c['buffer'] and
            any(struct.unpack_from('<H',p['rows'],slot*32+6)[0] and struct.unpack_from('<H',p['rows'],slot*32+12)[0]==c['tick'] for slot in range(6))]
        if not ps:continue
        p=max(ps,key=lambda p:p['clock']);expected=[];pixels={};identities=[]
        if p['closing']:continue
        ss=[s for s in snapshots if s[0]<p['clock'] and s[2]==c['tick']]
        snapshot=ss[-1] if ss else None
        if snapshot and snapshot[3]:continue  # Explicit hidden epoch-close packet.
        for slot in p['order']:
            row=p['rows'][slot*32:(slot+1)*32];u=lambda o:struct.unpack_from('<H',row,o)[0]
            if not u(6):continue
            fs=[f for f in manifest['frames'] if (f['model'],f['role'],f['frame'],f['map'])==(u(16),u(8),u(10),u(14))]
            assert len(fs)==1
            f=fs[0];identities.append([slot,u(16),u(10),u(14)])
            assert u(12)==c['tick'],'Mixed snapshot'
            palette_slot=u(26)
            assert palette_slot==(6+slot if manifest.get('packet_palettes') else f['palette_slot'])
            cg=bytes.fromhex(manifest['palettes'][f['palette']]);off=(palette_slot-6)*32
            assert c['cgram'][off:off+32]==cg,'Palette not completed at OAM consumption'
            at=0x2100+f['piece_offset'];expected+=oam_oracle(assets[at:at+f['piece_bytes']],anchor_x=u(0),anchor_y=u(2),facing_left=not u(4),palette_slot=palette_slot)
            image=Image.open(io.BytesIO(source.read(f['source']['source_path'])));ox,oy=f['source']['offset']
            mapping={v:i for i,v in enumerate(f['source_palette_indices'])}
            for y in range(image.height):
                for x in range(image.width):
                    index=image.getpixel((x,y))
                    if not index:continue
                    xx=u(0)+(x-ox if u(4) else ox-x);yy=u(2)+y-oy
                    word=struct.unpack_from('<H',cg,mapping[index]*2)[0]
                    rgb=tuple((((word>>shift)&31)<<3)|(((word>>shift)&31)>>2) for shift in (0,5,10))
                    if 0<=xx<256 and 0<=yy<224:pixels.setdefault((xx,yy),(slot,rgb))
        if not identities:continue
        wanted=b''.join(piece['low'] for piece in expected)
        assert c['oam'][:len(wanted)]==wanted,('Native OAM does not match source descriptors',c['field'],c['tick'],identities,c['oam'][:16].hex(),wanted[:16].hex())
        for i,piece in enumerate(expected):
            assert ((c['oam'][512+i//4]>>(2*(i%4)))&3)==piece['high'],'OAM high-bit ownership'
        raw=b''.join(r['rows']);height=len(raw)//768
        screen=Image.frombytes('RGB',(256,height),raw)
        if height==239:screen=screen.crop((0,7,256,231))
        bad=[xy for xy,(_,rgb) in pixels.items() if screen.getpixel(xy)!=rgb]
        path=f'publication-{number}.png';screen.save(folder/path)
        lines=[sum(piece['y']<=y<piece['y']+32 for piece in expected) for y in range(224)]
        resource=oam_resource_report(expected)
        proofs.append(dict(instances=identities,snapshot=c['tick'],snapshot_capture=snapshot[0] if snapshot else None,prepared=p['clock'],consumed=c['clock'],field=c['field'],raster=r['clock'],pixels=len(pixels),bad_pixels=len(bad),screenshot=path,
            oam_pieces=len(expected),max_scanline_pieces=max(lines),max_scanline_slivers=max(lines)*2,
            captured_field=snapshot[1] if snapshot else None,
            captured_next_field_consumption=c['field']==snapshot[1]+1 if snapshot else None,
            prepared_field=p['field'],next_field_consumption=c['field']==p['field']+1,resource=resource,
            bad_pixel_samples=[dict(xy=xy,expected=pixels[xy],actual=screen.getpixel(xy)) for xy in bad[:40]]))
    coverage={str(slot):sorted({a[2] for p in proofs for a in p['instances'] if a[0]==slot}) for slot in (0,1)}
    result=dict(proofs=proofs,transfer_completions=transfers,publication_faults=faults,
        palette_completions=palette_completions,
        palette_prepare_calls=palette_calls,publication_calls=publication_calls,rejected_packets=rejected_packets,admit_events=admit_events,guard_rejections=guard_rejections,shared_resources=shared_resources,
        vram_live_reference_violations=vram_lease_violations,
        terminal_source_references=dict(displayed=displayed_references,queued=sum(pending_references.values())),
        compat_oam_transfers=compat_oam,compat_tile_transfers=compat_tiles,
        queued_packets=queued,packet_latencies=packet_latencies,publication_order_regressions=regressions,live_packet_overwrites=overwrites,admission_blocked=admission,
        missed_next_field_opportunities=[dict(snapshot=p['snapshot'],prepared=p['prepared'],prepared_field=p['prepared_field'],consumed=p['consumed'],consumed_field=p['field']) for p in proofs if not p['next_field_consumption']],
        resource_status='RESOURCE_BLOCKED' if any(p['resource']['status']!='PASS' for p in proofs) or any(e[0]=='S7Admission_Scanlines__blocked' for e in admit_events) else 'PASS',
        frame_coverage=coverage,publication_queue_timing='BLOCKED' if faults else 'NO_BUSY_REJECTIONS_OBSERVED',
        strict_snapshot_next_field_timing='NOT_EVALUATED_NO_SOURCE_PUBLICATION' if not proofs else 'NOT_CERTIFIED' if rejected_packets or any(p['captured_next_field_consumption']!=True for p in proofs) else 'PASS_BOUNDED',
        scope='BOUNDED_PINNED_PUBLICATION_NOT_ENGINE_CERTIFICATION')
    (folder/'multi-proof.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('proofs','queued_packets','packet_latencies','palette_prepare_calls','palette_completions','publication_calls','admit_events','compat_tile_transfers','shared_resources')},indent=2))
    if config['case']=='scanline-block':
        assert not proofs and result['resource_status']=='RESOURCE_BLOCKED'
        assert any(e[0]=='S7Admission_Scanlines__blocked' and e[4]>34 for e in admit_events)
        assert not vram_lease_violations and not displayed_references and not any(pending_references.values())
        assert transfers and all(t[-1]==0 for t in transfers)
        return
    probe=json.loads((folder/'multi-config.json').read_text()).get('animation_only_probe',False) if (folder/'multi-config.json').exists() else False
    if config.get('compat_slots'):
        assert any(len(p['instances'])==1 and not p['bad_pixels'] for p in proofs)
        reserved_bytes=set()
        for slot in manifest['reserved_slots']:
            tile=(slot//8)*64+(slot%8)*2
            for row in range(4):reserved_bytes.update(range(0x8000+(tile+row*16)*32,0x8000+(tile+row*16)*32+64))
        for t in transfers:
            if t[4]&3==0:
                assert not reserved_bytes.intersection(range(t[3],t[3]+t[1])),'Source transfer overwrote accepted lease'
        assert any(p['snapshot']>150 for p in proofs),'Source publication must resume after lease reload'
        assert compat_tiles and all(t[3]==0 for t in compat_tiles),'Accepted tile transport byte mismatch'
    else:
        assert any(len(p['instances'])==2 and (probe or p['instances'][0][2]!=p['instances'][1][2]) and not p['bad_pixels'] for p in proofs)
    assert all(not p['bad_pixels'] for p in proofs),'Source pixel mismatch in an admitted packet'
    assert result['resource_status']=='PASS','Emitted OAM workload exceeds target resource limits'
    config=json.loads((folder/'multi-config.json').read_text())
    if config['case'] in ('cycles','epoch-reuse'):
        assert coverage=={'0':list(range(8)),'1':list(range(6))},'Full independently timed animation coverage'
        assert not faults,'Full-cycle packet admission failure'
        if config['case']=='epoch-reuse':
            assert len(transfers)==16,'Two complete entry-residency loads required'
            assert all(p[3]==0 and 225<=p[4]<=261 for p in palette_completions)
            assert all(p[1]==0 for p in palette_calls)
    assert not vram_lease_violations and not displayed_references and not any(pending_references.values()),'Live VRAM overwrite or unfinished epoch release'
    if compat_oam:assert all(c[2]==0 for c in compat_oam),'Ordinary OAM path changed by the source transaction consumer'
    if config['case']=='map-switch':
        states={tuple(a[3] for a in sorted(p['instances'])) for p in proofs}
        assert {(0,4),(4,0)}<=states,'Both actual map-owner states must be consumed'
    if config['case'] in ('palette-stream','palette-phase'):
        assert {a[3] for p in proofs for a in p['instances'] if a[0]==1}>={0,1,4},'All streamed remap identities consumed'
        assert not faults,'Palette transaction admission failure'
        assert not admission,'All captured palette-stream frames must be admitted'
        assert palette_completions and all(p[3]==0 and 225<=p[4]<=261 and p[5]==608 for p in palette_completions),'CGRAM bytes / VBlank / admission accounting'
        assert palette_calls and all(p[1]==0 for p in palette_calls),'Palette preparation D/DBR/X/Y/SP/width convention'
        for c in consumed:
            ps=[p for p in palette_completions if p[2]==c['buffer'] and p[0]<c['clock']]
            assert ps and ps[-1][1]==c['field'],'Palette/OAM transaction crossed a hardware field'
        if config['case']=='palette-phase' and not config.get('retirement_probe'):
            assert coverage=={'0':[0,1,2],'1':[0,1]},'Independent animation phases must both advance'
    assert transfers and all(t[-1]==0 for t in transfers),'Transfer bytes mismatch'
    if config.get('retirement_probe')=='dma':
        assert len(lease_denials)==2 and {d[1] for d in lease_denials}=={0,2}
        assert all(d[-2:]==[0,0] for d in lease_denials)
        (folder/'dma-lease-rejection.json').write_text(json.dumps(lease_denials,indent=2))
    else:assert not lease_denials,'Unexpected native graphics-lease rejection'
    if config.get('retirement_probe')=='framing':
        assert len(display_retirements)==1 and display_retirements[0][1:3]==[0,0]
        assert 225<=display_retirements[0][3]<=261
        (folder/'display-retirement.json').write_text(json.dumps(display_retirements,indent=2))
    if config.get('guard_probes'):
        assert ['OWNER_GUARD_REJECTED'] in guard_rejections
        assert ['FRAMING_GUARD_REJECTED','0','0'] in guard_rejections
        assert len(rejected_packets)==1
    elif config.get('retirement_probe')!='framing':assert not rejected_packets,'Unexpected framing rejection'
    assert not regressions,'Hardware publication reversed producer snapshot order'
    if publication_calls:assert all(c[1]==0 for c in publication_calls),'Early publication calling convention'
    assert queued and all(q[2]==q[3] for q in queued),'Queued source differs from selected immutable packet'
    assert not overwrites and all(c['bad_bytes']==0 for c in consumed),'In-flight packet ownership failure'


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',choices=('players','bonus','highmap','lobster-maps','map-switch','cycles','palette-stream','palette-phase','epoch-reuse','mixed-epoch','scanline-block'),default='players')
    parser.add_argument('--live',action='store_true');parser.add_argument('--existing',action='store_true')
    parser.add_argument('--palette-staging-cache',action='store_true',help='Measured experiment; not the selected default')
    parser.add_argument('--facing-left-slot',type=int,choices=(0,1),help='Explicit source-world initial facing control')
    parser.add_argument('--guard-probes',action='store_true',help='Explicit negative owner/framing protocol injection; not a timing benchmark')
    parser.add_argument('--retirement-probe',choices=('owner','framing','dma'),help='Persistent negative boundary after the positive workload')
    args=parser.parse_args();folder=args.output.resolve()
    if not args.existing:
        folder.mkdir(exist_ok=False)
        from actor_s6_production_world import build
        requests=[dict(name='Kula',path='data/chars/kula/kula.txt',runtime_id=22,role='attack1',frames=[0],maps=[0],action_slot=0,action_tick=6),
                  dict(name='Mary',path='data/chars/mary/mary.txt',runtime_id=24,role='attack1',frames=[0,1],maps=[1],action_slot=1,action_tick=1)]
        if args.case!='players':
            requests=[dict(name='Crab',path='data/chars/crab/crab.txt',runtime_id=45,role='idle',frames=[0],maps=[0],action_slot=0,animation_only_probe=True),
                      dict(name='Lobster' if args.case=='bonus' else 'Angel',path='data/chars/lobster/lobster.txt' if args.case=='bonus' else 'data/chars/angel/angel.txt',runtime_id=46 if args.case=='bonus' else 29,role='idle',frames=[0],maps=[4],action_slot=1,animation_only_probe=True)]
        if args.case in ('lobster-maps','scanline-block'):
            requests=[dict(name='Lobster',path='data/chars/lobster/lobster.txt',runtime_id=46,role='idle',frames=[0],maps=[selector],action_slot=slot,animation_only_probe=True) for slot,selector in enumerate((0,4))]
        if args.case=='map-switch':
            requests=[dict(name='Lobster',path='data/chars/lobster/lobster.txt',runtime_id=46,role='idle',frames=[0],maps=[0,4],initial_map=selector,map_events=[(7,4-selector)],position=[100 if slot==0 else 180,132 if slot==0 else 216],action_slot=slot,animation_only_probe=True) for slot,selector in enumerate((0,4))]
        if args.case in ('cycles','epoch-reuse'):
            requests=[dict(name='Crab',path='data/chars/crab/crab.txt',runtime_id=45,role='walk',frames=list(range(8)),maps=[0],action_slot=0,animation_only_probe=True),
                      dict(name='Gold',path='data/chars/misc/gold.txt',runtime_id=18,role='idle',frames=list(range(6)),maps=[0],action_slot=1,animation_only_probe=True)]
            if args.case=='epoch-reuse':
                for r in requests:r.update(epoch_reuse_probe=True,packet_palettes=True)
        if args.case=='palette-stream':
            requests=[dict(name='Gold',path='data/chars/misc/gold.txt',runtime_id=18,role='idle',frames=list(range(6)),maps=[0],action_slot=0,animation_only_probe=True,packet_palettes=True),
                      dict(name='Angel',path='data/chars/angel/angel.txt',runtime_id=29,role='pain',frames=[0,1],maps=[0,1,4],initial_map=0,map_events=[(20,1),(40,4),(60,0)],position=[180,216],action_slot=1,animation_only_probe=True,packet_palettes=True)]
        if args.case=='palette-phase':
            requests=[dict(name='Crab',path='data/chars/crab/crab.txt',runtime_id=45,role='walk',frames=[0,1,2],maps=[0],action_slot=0,animation_only_probe=True,packet_palettes=True),
                      dict(name='Angel',path='data/chars/angel/angel.txt',runtime_id=29,role='pain',frames=[0,1],maps=[0,1,4],initial_map=0,map_events=[(3,1),(10,4),(23,0)],position=[180,216],action_slot=1,animation_only_probe=True,packet_palettes=True)]
        if args.case=='mixed-epoch':
            requests=[dict(name='Crab',path='data/chars/crab/crab.txt',runtime_id=45,role='walk',frames=list(range(8)),maps=[0],action_slot=0,animation_only_probe=True,packet_palettes=True,epoch_reuse_probe=True,compat_slots=[1],position=[100,200])]
        horizon=570 if args.case in ('cycles','epoch-reuse') else 220 if args.case=='mixed-epoch' else 80 if args.case=='palette-stream' else 34 if args.case=='palette-phase' else 19
        if args.palette_staging_cache:
            for r in requests:r['palette_staging_cache']=True
        if args.facing_left_slot is not None:
            for r in requests:
                if r['action_slot']==args.facing_left_slot:r['facing_left']=True
        (folder/'multi-config.json').write_text(json.dumps(dict(case=args.case,animation_only_probe=args.case!='players',source_tick_horizon=horizon,requests=requests,epoch_reuse_probe=args.case in ('epoch-reuse','mixed-epoch'),compat_slots=[1] if args.case=='mixed-epoch' else [],guard_probes=args.guard_probes,retirement_probe=args.retirement_probe),indent=2))
        build(folder,'kula',resident=True,layout_dispatch=True,publisher=True,stream_publisher=True,deadline_wait=True,publication_requests=requests)
    if args.live:run(folder)
