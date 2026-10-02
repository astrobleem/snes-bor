"""Read-only native water journal and offline source-derived hardware oracle.

No emulator launch here. HDMA transfer writes traverse Mesen's WriteDma ->
ProcessMemoryWrite callback path, unlike merely reading an enabled shadow.
"""
import json
from pathlib import Path
from game_s8_stage_bounds import lorom_offset


def script(s, path):
    names=('Game_StageIndex','Game_State','Game_CampaignId','StageWater_Frame',
           'StageWater_ActiveOffset','StageWater_WriteOffset','StageWater_Pending',
           'StageWater_Enabled','StageWater_Held','StageWater_RockY','Nmi_Bg1ScrollX',
           'Nmi_Bg1ScrollY','Nmi_FrameBusy','Nmi_Busy')
    addresses=','.join(f'{n}={s[n]}' for n in names)
    return '''
local output=OUTPUT
local a={ADDRESSES}
local byte={Game_CampaignId=true,StageWater_Pending=true,StageWater_Enabled=true,
 StageWater_Held=true,Nmi_FrameBusy=true,Nmi_Busy=true}
local function rd(addr,n)
 local v=0;for i=0,n-1 do v=v+emu.read(addr+i,emu.memType.snesMemory)*256^i end;return v
end
local function val(n) return rd(a[n],byte[n] and 1 or 2) end
local function hex(addr,n)
 local t={};for i=0,n-1 do t[#t+1]=string.format('%02x',rd(addr+i,1)) end;return table.concat(t)
end
local function emit(kind,t)
 local parts={kind};for k,v in pairs(t) do
  parts[#parts+1]=k..'='..(type(v)=='number' and string.format('%d',v) or tostring(v))
 end
 local f=assert(io.open(output,'a'));f:write(table.concat(parts,'|'),'\\n');f:close()
end
local function snapshot()
 return {stage=val('Game_StageIndex'),state=val('Game_State'),campaign=val('Game_CampaignId'),
 frame=val('StageWater_Frame'),active=val('StageWater_ActiveOffset'),pending=val('StageWater_Pending'),
 enabled=val('StageWater_Enabled'),held=val('StageWater_Held'),x=val('Nmi_Bg1ScrollX'),y=val('Nmi_Bg1ScrollY'),shadow=rd(HDMA_SHADOW,1)}
end
local pending=nil
local committed=nil
local field=nil
local writes={}
local mask=0
local count=0
local arm=0
local ylow=nil
local hardware_y=-1
local oam=nil
emu.addMemoryCallback(function(addr,value) mask=value end,emu.callbackType.write,0x420c,0x420c,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(addr,value)
 if ylow==nil then ylow=value else hardware_y=ylow+value*256;ylow=nil end
end,emu.callbackType.write,0x210e,0x210e,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()
 pending=nil
 if val('Game_CampaignId')==3 and val('StageWater_Enabled')~=0 and val('StageWater_Pending')==1
 and val('Nmi_FrameBusy')==0 and val('Nmi_Busy')==0 then pending=snapshot() end
end,emu.callbackType.exec,NMI_ENTRY,NMI_ENTRY,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 if pending then
  local t=snapshot();t.phase=(t.frame+5759)%5760;t.shadow_before=pending.shadow
  t.table=hex(BUFFER+t.active,673);t.dma=hex(0x4360,11)
  if arm>0 then t.arm=arm;emit('commit',t) end;committed=t;pending=nil
 end
end,emu.callbackType.exec,NMI_DONE,NMI_DONE,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 committed=nil;field=nil;writes={};emit('reset',snapshot())
end,emu.callbackType.exec,RESET,RESET,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 oam=nil
 if arm>0 and val('Game_CampaignId')==3 and val('StageWater_Enabled')~=0 then
  oam=snapshot();oam.before=rd(OAM_Y,1);oam.rock=val('StageWater_RockY')
 end
end,emu.callbackType.exec,OAM_ENTRY,OAM_ENTRY,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function()
 if oam then oam.after=rd(OAM_Y,1);emit('oam',oam);oam=nil end
end,emu.callbackType.exec,OAM_DONE,OAM_DONE,emu.cpuType.snes,emu.memType.snesPrgRom)
emu.addMemoryCallback(function(addr,value)
 local cpu=emu.getState()
 local line=assert(cpu['ppu.scanline'],'missing ppu.scanline')
 -- Only raster-time writes; NMI's ordinary scroll-register restore is
 -- outside these scanlines. Two real BG1HOFS bytes per HDMA row.
 if arm>0 and line>=0 and line<224 and val('Game_CampaignId')==3 and val('StageWater_Enabled')~=0 then
  if not field then
   field=snapshot();field.arm=arm;field.mask=mask;field.dma=hex(0x4360,11)
   field.bus_y=hardware_y
   field.table=hex(BUFFER+field.active,673)
   field.phase=committed and committed.phase or -1
   field.base=committed and committed.x or -1
  end
  writes[#writes+1]=string.format('%02x',value)
 end
end,emu.callbackType.write,0x210d,0x210d,emu.cpuType.snes,emu.memType.snesMemory)
emu.addEventCallback(function()
 if field then
  count=count+1
  if count>10000 then error('water journal bound exceeded') end
  field.bus=table.concat(writes);emit('raster',field)
 end
 field=nil;writes={}
 if arm>0 then local t=snapshot();t.arm=arm;t.mask=mask;emit('frame',t) end
 local f=io.open(OUTPUT..'.arm','r');if f then arm=tonumber(f:read('*a')) or 0;f:close() end
end,emu.eventType.endFrame)
'''.replace('OUTPUT',json.dumps(Path(path).as_posix())).replace('ADDRESSES',addresses).replace(
        'NMI_ENTRY',str(lorom_offset(s['StageWater_Nmi']))).replace('NMI_DONE',str(lorom_offset(s['StageWater_Nmi__done']))).replace(
        'RESET',str(lorom_offset(s['StageWater_Reset']))).replace('BUFFER',str(s['StageWater_Buffer'])).replace(
        'OAM_ENTRY',str(lorom_offset(s['StageWater_ApplyOamY']))).replace('OAM_DONE',str(lorom_offset(s['StageWater_ApplyOamY__done']))).replace('OAM_Y',str(s['OamSetSprite_Y'])).replace('HDMA_SHADOW',str(s['Nmi_HdmaEnable']))


def parse(text):
    rows=[]
    for line in text.splitlines():
        parts=line.split('|'); row={'event':parts[0]}
        if row['event'] not in ('commit','raster','reset','frame','oam'): raise AssertionError('unknown water journal event')
        for part in parts[1:]:
            k,v=part.split('=',1); row[k]=v if k in ('table','dma','bus') else int(v)
        rows.append(row)
    return rows


def check(events, plans, buffer_address):
    from stage_water import WaterMetadata, raster
    indexed={r['stage']:r for r in plans}
    counts={stage:dict(commits=0,rasters=0,phases=set(),tables=set(),paused=0,resumed=0,oam=0,frames=0) for stage in indexed}
    for e in events:
        if e['event']=='reset' or e['stage'] not in indexed: continue
        row=WaterMetadata(**indexed[e['stage']]['water'])
        if e['event']=='oam':
            if e['after']!=(e['before']-e['rock'])&255:
                raise AssertionError('native OAM rocking adjustment mismatch')
            counts[e['stage']]['oam']+=1
            continue
        if e['event']=='frame':
            counts[e['stage']]['frames']+=1
            if not row.active and (e['enabled'] or e['mask']&0x40):
                raise AssertionError('inactive control enabled hardware water')
            continue
        if not row.active: raise AssertionError('inactive control unexpectedly published water')
        if e['active'] not in (0,674) or e['phase']<0: raise AssertionError('unbound raster publication')
        base=e['x'] if e['event']=='commit' else e['base']
        expected,y=raster(row,e['phase'],base)
        actual=bytes.fromhex(e['table']); dma=bytes.fromhex(e['dma'])
        if actual!=expected or e['y']!=y: raise AssertionError('HDMA/VOFS differs from source-derived raster')
        address=int.from_bytes(dma[2:5],'little')
        if dma[0]!=2 or dma[1]!=0x0d or address!=buffer_address+e['active']:
            raise AssertionError('actual channel6 mode/target/source mismatch')
        c=counts[e['stage']]
        if e['event']=='commit':
            if e['pending'] or e['held']: raise AssertionError('NMI committed incomplete producer')
            if (e['shadow_before']^e['shadow'])&0xbf: raise AssertionError('water NMI changed another HDMA channel owner')
            c['commits']+=1
        else:
            if not e['mask']&0x40: raise AssertionError('HDMA channel6 not enabled in actual write mask')
            bus=b''.join(expected[i+1:i+3] for i in range(0,672,3))
            if bytes.fromhex(e['bus'])!=bus: raise AssertionError('actual raster BG1HOFS writes differ from published table')
            if e['bus_y']!=y: raise AssertionError('actual BG1VOFS write differs from rocking phase')
            c['rasters']+=1; c['phases'].add(e['phase']);c['tables'].add(e['table'])
            c['paused']+=int(e['state']==3)
            c['resumed']+=int(e.get('arm')==3 and e['state']==0)
    for stage,c in counts.items():
        if c['frames']<2: raise AssertionError('missing hardware frame observations: '+indexed[stage]['name'])
        if not WaterMetadata(**indexed[stage]['water']).active: continue
        if c['commits']<2 or c['rasters']<2 or len(c['phases'])<2 or len(c['tables'])<2 or c['paused']<2 or c['resumed']<2 or not c['oam']:
            raise AssertionError('missing actual motion/paused HDMA coverage: '+indexed[stage]['name'])
    return {stage:dict(c,phases=len(c['phases']),tables=len(c['tables'])) for stage,c in counts.items()}
