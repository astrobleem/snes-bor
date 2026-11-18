"""Private recomposition of the retained ground-attack publisher and physical OAM probe."""
import hashlib
import os

DONORS = (
    ('candidate-v1282', 'a7449523b74791f9e5bdc7b0f4c8ca394b07d7a7b5b0e08b161fe160837e0474'),
    ('candidate-v1283', 'b87a288031e7cca3ce0784085f8678459f860f4c76b2874f7f2dfc0448390f2b'),
)
HOOKS = (
    ('phase0yes', 0x309a50, '7a6828386b7a6828186b'),
    ('phase1yes', 0x309b40, '7a6828386b7a6828186b'),
    ('phase0no', 0x309a55, '7a6828186b08c230485a'),
    ('transfer', 0x31c4a3, '22218b30688f76430068'),
    ('transferred', 0x31c4a7, '688f764300688f754300'),
    ('directseal', 0x30a868, 'af0294438f08a543af04'),
    ('queueseal', 0x31e5a2, 'af0294438f08a543af04'),
    ('capture', 0x31a025, 'af00a5430f44a843f003'),
)

def compose(root, baseline, private):
    images = []
    for name, expected in DONORS:
        path = root / 'inputs' / name / 'bor.sfc'
        stat = path.stat()
        if path.is_symlink() or not path.is_file() or stat.st_uid != os.getuid() or stat.st_size != len(baseline):
            raise ValueError('unexpected donor identity')
        data = bytearray(path.read_bytes())
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('donor content changed')
        data[0x7fdc:0x7fe0] = baseline[0x7fdc:0x7fe0]
        images.append(data)
    before, after = images
    result = bytearray(private)
    changes = 0
    for offset in range(0, len(result), 256):
        span = slice(offset, offset+256)
        old, new = before[span], after[span]
        if old == new:
            continue
        if old != baseline[span] or old != private[span]:
            raise ValueError('publisher intersects a changed destination page')
        changes += sum(a!=b for a,b in zip(old,new))
        result[span] = new
    if changes != 53273:
        raise ValueError('unexpected publisher delta')
    result[0x7fdc:0x7fe0] = bytes.fromhex('ffff0000')
    checksum = sum(result) & 65535
    result[0x7fdc:0x7fe0] = (65535-checksum).to_bytes(2,'little') + checksum.to_bytes(2,'little')
    return bytes(result)

def observer(source, reset, raw, read):
    body = """local hp=nil;local impacts=0;local ob=-1;local calls=0
local function hex(a,n,t)local o={} for i=0,n-1 do o[#o+1]=string.format('%02x',emu.read(a+i,t))end return table.concat(o)end
local function snap(tag,vt,id,old,v)
 print(tag..'|'..id..'|'..n..'|'..old..'|'..v..'|'..ob..'|'..hex(0,544,emu.memType.snesSpriteRam)..'|'..hex(256,256,emu.memType.snesCgRam))
 for z=0,3 do print(vt..'|'..id..'|'..z..'|'..hex(32768+z*4096,4096,emu.memType.snesVideoRam))end
end
local function log(k,a,v)
 if ((n>=341 and n<=376) or (n>=463 and n<=482)) and calls<384 then
  local s=emu.getState();calls=calls+1
  print('AH40|'..k..'|'..n..'|'..tostring(s.masterClock or s.masterclock)..'|'..a..'|'..v)
 end
end
local function ex(a,k)emu.addMemoryCallback(function()log(k,0,0)end,emu.callbackType.exec,a,a,emu.cpuType.snes,emu.memType.snesPrgRom) end
emu.addMemoryCallback(function(a,v)ob=v end,emu.callbackType.write,0x2101,0x2101,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(a,v)log('actor',a,v)end,emu.callbackType.write,0x11904,0x11907,emu.cpuType.sa1,emu.memType.snesSaveRam)
emu.addMemoryCallback(function(a,v)
 if n>=300 and n<510 and (v==59 or v==54) and (hp==nil or v<hp) and impacts<2 then
  impacts=impacts+1;log('damage',a,v);snap('IM37','VR37',impacts,hp or -1,v)
 end
 hp=v
end,emu.callbackType.write,0x11bf0,0x11bf0,emu.cpuType.sa1,emu.memType.snesSaveRam)
"""
    names=[]
    for name,(address,sig) in STAGES.items():
        if read(raw,address,5).hex()!=sig:raise ValueError('foreground hook differs '+name)
        names.append(str((address>>16)*32768+(address&32767)))
    body+="""local bins={}
for idx,a in ipairs({LOC}) do local id=idx
 emu.addMemoryCallback(function()
 if not ((n>=367 and n<=398) or (n>=523 and n<=553)) then return end
 local key=n*64+id;local count=(bins[key] or 0)+1;bins[key]=count
 if count<=32 then local q=emu.getState();print('FG47|'..n..'|'..id..'|'..q.masterClock..'|'..q['cpu.d']..'|'..emu.read(0x4b6a,emu.memType.snesWorkRam)..'|'..q['cpu.sp']) end
 end,emu.callbackType.exec,a,a,emu.cpuType.snes,emu.memType.snesPrgRom)
end
""".replace('LOC',','.join(names))
    points={'poll':(0x078197,'c231ad1242290100'),'visual':(0x10b2bd,'2280fe10c230'),'queueEnd':(0xc44b,'c2319c7a0460'),'nmi':(0xd231,'c23048da5a8b0b')}
    offsets=[]
    for label,(addr,sig) in points.items():
        if read(raw,addr,len(bytes.fromhex(sig)))!=bytes.fromhex(sig):raise ValueError('timing seam '+label)
        offsets.append((label,(addr>>16)*32768+(addr&32767)))
    extra="""local wmax=-1;local writes=0;local late=0;local active=false;local ending=-1
local function watch(k)
 local q=emu.getState();local sl=q['ppu.scanline']
 if k=='nmi' then active=true end
 if k=='queueEnd' and active and n>=247 and sl>ending then ending=sl end
 if (k=='poll' or k=='visual') and n>=360 and n<=397 then print('IP45|'..k..'|'..n..'|'..tostring(q.masterClock)..'|'..sl)end
end
for k,a in pairs({@points@}) do local key=k;emu.addMemoryCallback(function()watch(key)end,emu.callbackType.exec,a,a,emu.cpuType.snes,emu.memType.snesPrgRom)end
emu.addMemoryCallback(function(a,v)if n>=247 and active then local sl=emu.getState()['ppu.scanline'];writes=writes+1;if sl>wmax then wmax=sl end;if sl>=260 or sl<224 then late=late+1 end end end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)
"""
    body+=extra.replace('@points@',','.join(f'{k}={a}' for k,a in offsets))
    template=source(reset)
    token='emu.addEventCallback(function()'
    template=template.replace(token,body+token,1)
    token="if n==558 then print('BORBASE1415_END|558') end"
    if template.count(token)!=1:raise ValueError('missing field boundary')
    template=template.replace(token,"if n>=349 and n<=360 then snap('EF40','EV40',n,0,0)end;if n==558 then print('PP45|'..writes..'|'..late..'|'..wmax..'|'..ending)end;active=false;"+token)
    if len(template.encode())>=4096:raise ValueError('observer cap')
    return template

def evidence(lines):
    fields=[];damage=[];chunks=0
    for line in lines:
        if line.startswith(b'EF40|'):fields.append(int(line.split(b'|',2)[1]))
        if line.startswith(b'IM37|'):damage.append(int(line.split(b'|',3)[2]))
        if line.startswith((b'EV40|',b'VR37|')):chunks+=1
    if fields!=list(range(349,361)) or chunks!=4*(len(fields)+len(damage)):
        raise ValueError('physical capture incomplete')
    return dict(fields=fields,damage_fields=damage,chunks=chunks)

STAGES={'Core_Input_Poll': [491927, 'c231ad1242'], 'SourceVisual_PollInput': [1094333, '2280fe10c2'], 'SourceVisual_EarlySubmit': [1098252, '08c23048da'], 'SourceVisual_ServicePending': [1094928, '08c23048da'], 'SourceVisual_ServiceNpcsAfterSubmit': [1098300, '0bafd2467e'], 'SourceVisual_ServiceFirstNpcBeforeRepeat': [1098753, 'afd2467ec9'], 'SourceVisual_RenderCurrent': [1085775, '088b0bda5a'], 'SourceVisual_LoadPendingEntry': [1087326, 'c231af624b'], 'SourceVisual_ReadEntry': [1089110, '20eb9dc231'], 'SourceVisual_ReadPieces': [1090239, 'c2312049d0'], 'SourceVisual_PrepareBlocks': [1090290, 'c231af6a4b'], 'SourceVisual_LoadResourcesBody': [1089223, 'c23020c9b4'], 'SourceVisual_AllocatePalettes': [1088244, 'c231af0e48'], 'SourceVisual_QueuePalettes': [1092212, 'e220a90e8f'], 'SourceVisual_CompletedObserve': [1096678, 'c23120cdbb'], 'SourceVisual_EmitCompleted': [1097384, 'c2317bc900'], 'SourceVisual_Emit': [1093219, 'c2312259ec'], 'SourceRom_Resolve': [1106194, '08c231da5a'], 'SourcePrefetch_TryOne': [3986841, '08c230d848'], 'SourceStandby_Prepare': [4039013, '08c23048da'], 'SourceWarm_TryOne': [4044479, '0848a90000'], 'SourceVisual_BucketEnsure': [1094743, 'afec4b7ec9'], 'SourceVisual_ReadSelectedPieces': [1106666, 'af10487e8f'], 'SourceVisual_PrewarmAttackPalette': [3992626, '08c23048da'], 'Hud_Play__text_banked': [362296, 'c231afd158'], 'Core_Screen_Play': [53575, '08c231af1c'], 'SourceWarm_Plan': [4041413, '08c230d848'], 'SourceVisual_ServiceCurrent': [1085758, '088b0bda5a'], 'SourceVisual_BeginPresentationFrame': [1098227, '08c2304822']}
