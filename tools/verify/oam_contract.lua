-- Isolated OAM subjects only. No hardware OBSEL/OAM writes: production init,
-- ClearAll, Play/packing and queued DMA remain the code under test.
local s = @SYMS@
local mt = emu.memType.snesMemory
local phase = -1
local count = 0
local function read(a) return emu.read(a, mt) end
local function write(a,v) emu.write(a,v,mt) end
local function word(a,v) write(a,v%256);write(a+1,math.floor(v/256)) end
local function dump(a,n,t)
 local b={}; for i=0,n-1 do b[#b+1]=string.format('%02x',emu.read(a+i,t or mt)) end
 return table.concat(b)
end
local function log(tag, extra)
 local p=emu.getState()
 emu.log('OAMPROOF|'..tag..'|'..phase..'|'..tostring(p['ppu.oamBaseAddress'])..'|'..
 tostring(p['ppu.oamMode'])..'|'..tostring(p['ppu.oamAddressOffset'])..'|'..(extra or ''))
end
local function hook(a,f)
 emu.addMemoryCallback(f,emu.callbackType.exec,a,a,emu.cpuType.snes,emu.memType.snesPrgRom)
end
hook(s.clearReturn,function()
 if phase==21 or phase==31 then
  log('CLEAR_RETURN',dump(s.guard,5))
 end
end)
hook(s.dma,function()
 if phase>=0 then
  local st=emu.getState(); local x=st['cpu.x']
  log('DMA',dump(s.queue+x,8))
 end
end)
emu.addMemoryCallback(function(a,v)
 log('OBSEL',tostring(v)..','..tostring(emu.getState()['ppu.forcedBlank']))
 local st=emu.getState(); log('OBSEL_PC',tostring(st['cpu.k'])..','..tostring(st['cpu.pc']))
end,emu.callbackType.write,0x2101,0x2101,emu.cpuType.snes,mt)
-- OAM fixture stops normal sprite emission after its accepted-sprite control.
-- RTS entry is derived/checked by host; no instructions or production ROM edited.
hook(s.setSprite,function()
 if phase>=20 then emu.setState({['cpu.pc']=s.rts}) end
end)
hook(s.play,function()
 if read(s.gameState)~=s.playing then return end
 count=count+1; phase=count
 if phase==18 then
  log('KNOWN',dump(s.buffer,32)..','..dump(s.expanded,8))
  for i=0,7 do if read(s.buffer+4*i+1)<224 then
   s.knownTile=read(s.buffer+4*i+2); s.knownAttr=read(s.buffer+4*i+3); break
  end end
 end
 if phase==20 or phase==30 then
  -- Same accepted tile/palette already loaded by ordinary gameplay; no asset injection.
  local large=phase==20
  local i=large and 127 or 0
  write(s.buffer+4*i,64);write(s.buffer+4*i+1,80)
  write(s.buffer+4*i+2,s.knownTile);write(s.buffer+4*i+3,s.knownAttr)
  write(s.expanded+i,large and 2 or 0)
  word(s.cursor,large and 512 or 4)
  log(large and 'LARGE' or 'SMALL',dump(s.buffer+4*i,4)..','..read(s.expanded+i))
 elseif phase==21 or phase==31 then
  for i=0,4 do write(s.guard+i,0xA5+i) end
  -- Enter REAL ClearAll instead of Play, preserving its normal bank-0 RTS caller.
  emu.setState({['cpu.pc']=s.clearAll})
 elseif phase==22 or phase==32 then
  log('CLEARED',dump(s.buffer,544)..','..dump(s.expanded,128)..','..dump(s.guard,16))
 end
end)
emu.addEventCallback(function()
 if phase==19 or phase==21 or phase==23 or phase==31 or phase==33 or phase==36 then
  log('HARDWARE',dump(0,544,emu.memType.snesSpriteRam))
  log('STATUS77',tostring(read(0x213e)))
 end
end,emu.eventType.endFrame)
