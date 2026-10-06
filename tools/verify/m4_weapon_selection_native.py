"""Native weapon selection against pinned set_weapon with transition observed."""
import argparse,hashlib,json,os,re,struct,subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_animation_init_native import luav
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffd80,0x7ffd82,0x7ffd84


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authority',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text())
    if authority['status']!='PASS' or authority['function_sha256']!='f3aa6e1c2fb5b0ec566b70df86ed487502be6905af07cfff3e4656803052d295':raise ValueError('WEAPON_SELECTION_C_AUTHORITY')
    rows=[]
    for ar in authority['results']:
        c=ar['case'];lists=[[],[2,0],[0,1],[-1,2]];owner=65535 if c['weapon'] is None else lists.index(c['weapon'])
        rows.append(dict(c,owner=owner,slot=(0,1,127)[len(rows)%3],wanted=ar['actual'],fault=int(ar['expected']['unsafe']),bad=''))
    for bad in ('ready','world','pool','entities','slot','models','players','bank','base','bytes','player_tag','player_reserved','player_high','player_index','owner','count','default'):
        base=next(r for r in rows if r['type']==1 and r['number']==1 and r['owner']==1 and not r['fault'])
        rows.append(dict(base,fault=1,bad=bad))
    table=struct.pack('<4s6H',b'B4MW',1,4,8,16,32,0)
    table+=b''.join(struct.pack('<4H',i,0 if i==0 else 2,48 if i<2 else 52 if i==2 else 56,0) for i in range(4))+struct.pack('<6h',2,0,0,1,-1,2)
    sy=symbols(Path('src/main.sym'));entry=sy['Vm_SourceFrameGate'];first=39*32768;raw=bytearray(a.rom.read_bytes())
    if raw[first:first+32768]!=bytes(32768) or raw[59*32768:60*32768]!=bytes(32768) or raw[0x7fd8]!=8:raise ValueError('WEAPON_SELECTION_PRIVATE_RESERVATION')
    asm='''.snes
.bank 39
.org $8000
WeaponFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4F1
 bne WeaponFixture_Return
WeaponFixture_Init:
.a16
.i16
 nop
 jsl APPLY
WeaponFixture_After:
.a16
.i16
 nop
 bcc WeaponFixture_Success
 lda.l EXPECTFAULT
 beq WeaponFixture_Bad
 bra WeaponFixture_Result
WeaponFixture_Success:
.a16
.i16
 lda.l EXPECTFAULT
 bne WeaponFixture_Bad
WeaponFixture_Result:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcs WeaponFixture_Done
 and #7
 bne WeaponFixture_Init
 bra WeaponFixture_Return
WeaponFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
WeaponFixture_Done:
.a16
.i16
 lda #0
 sta.l REQUEST
 sta.l READY
 sta.l WORLDREADY
WeaponFixture_Return:
.a16
.i16
 ply
 plx
 plp
 php
 rep #$31
 phx
 phy
 jml RESUME
'''
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,EXPECTFAULT=REQUEST+6,READY=sy['SourceWeapon4086_Ready'],WORLDREADY=sy['VmSourceWorld_Ready'],APPLY=sy['SourceWeapon4086_Resolve'],CASES=len(rows),RESUME=entry+5)
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('WEAPON_SELECTION_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');code=(folder/'fixture.bin').read_bytes()[first:];raw[first:first+len(code)]=code;raw[59*32768:59*32768+len(table)]=table
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a'):raise ValueError('WEAPON_SELECTION_GATE')
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['WeaponFixture_Gate'])[:3]+b'\xea'
    rom=folder/'bor.sfc';rom.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    lua='local rows='+luav(rows)+'\nlocal sy='+luav({k:v for k,v in sy.items() if k.startswith(('SourceWeapon4086_','VmSourceWorld_'))})+'\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local ctx=0;local start=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function long(a,v)put(a,v&65535);put(a+2,(v>>16)&65535)end
local function set(k,v)put(sy['SourceWeapon4086_'..k],v)end
local ranges={{0x414000,10240},{0x416800,8192},{0x40c000,12288},{0x43e1c0,2176}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local e=0x40c000+96*c.slot;local meta=0x43e200+16*c.slot
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0xa5,mt)end end
 put(v+40,1);put(v+42,0);long(v+44,c.player);put(s+2,3);long(e+72,c.type)
 put(meta,c.owner);put(meta+2,c.weapon and #c.weapon or 0);long(meta+4,c.loss);long(meta+8,-1);long(meta+12,0)
 for i=0,3 do long(0x43ea00+4*i,77)end
 set('Ready',0xb4f1);set('Slot',c.slot);set('NumberLo',c.number&65535);set('NumberHi',(c.number>>16)&65535);set('AnimFlagLo',c.anim_flag&65535);set('AnimFlagHi',(c.anim_flag>>16)&65535)
 set('Base',0x8000);set('Bank',59);set('Bytes',TABLEBYTES);set('Models',4);set('Entities',128);set('Players',4);set('LevelWeaponLo',5);set('LevelWeaponHi',0);set('Selected',65535);set('Sync',65535)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,128);put(EXPECTFAULT,c.fault)
 if c.bad=='ready'then set('Ready',0)
 elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='pool'then put(sy.VmSourceWorld_PoolBase,0x4002)
 elseif c.bad=='entities'then set('Entities',127)
 elseif c.bad=='slot'then set('Slot',128)
 elseif c.bad=='models'then set('Models',17)
 elseif c.bad=='players'then set('Players',5)
 elseif c.bad=='bank'then set('Bank',64)
 elseif c.bad=='base'then set('Base',0x7ffe)
 elseif c.bad=='bytes'then set('Bytes',14)
 elseif c.bad=='player_tag'then put(v+40,2)
 elseif c.bad=='player_reserved'then put(v+42,1)
 elseif c.bad=='player_high'then put(v+46,1)
 elseif c.bad=='player_index'then long(v+44,4)
 elseif c.bad=='owner'then put(meta,4)
 elseif c.bad=='count'then put(meta+2,129)
 elseif c.bad=='default'then put(meta,65535);put(s+2,4)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();start=s.masterClock;ctx=0;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('WEAPONCOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local w=c.wanted
 local function expectlong(a,n)for i=0,3 do before[a+i]=(n>>(8*i))&255 end end
 if c.bad==''then for i=0,3 do expectlong(0x43ea00+4*i,w[4+i])end
 elseif c.bad=='owner' or c.bad=='count' or c.bad=='default'then expectlong(0x43ea00+4*c.player,c.loss==3 and c.number or 5)end
 local mismatch=0;for addr,value in pairs(before)do if emu.read(addr,mt)~=value then mismatch=mismatch+1 end end
 local selection=0;if c.fault==0 and (word(sy.SourceWeapon4086_Selected)~=w[1] or word(sy.SourceWeapon4086_Sync)~=w[2])then selection=1 end
 emu.log('WEAPONRESULT|'..word(INDEX)..'|'..word(sy.SourceWeapon4086_Status)..'|'..mismatch..'|'..ctx..'|'..selection)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    values.update(INIT=fs['WeaponFixture_Init'],AFTER=fs['WeaponFixture_After'],RESULT=fs['WeaponFixture_Result'],TABLEBYTES=len(table))
    for k,v in values.items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'observer.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    reporter=Reporter('M4-WEAPON-SELECTION',kind='GATE')
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('WEAPON_SELECTION_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(INDEX,0);m.write_u16(ERROR,0);m.write_u16(REQUEST,0xb4f1)
        for _ in range(2000):
            run_frames_exact(m,1)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native weapon selection batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];costs=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('WEAPONRESULT|',results),('WEAPONCOST|',costs)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('selection/player bookkeeping match C and preserve all unrelated bytes/context',len(results)==len(rows) and all(r==[i,2 if c['fault'] else 1,0,0,0] for i,(r,c) in enumerate(zip(results,rows))))
    report=dict(schema='BYOR_4086_WEAPON_SELECTION_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),results=results,cpu_costs=costs,source_undefined_rejections=authority['source_undefined_rejections'],authority_report_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),entity_weapon_metadata_install_bound=False,model_transition_bound=False,motu_gameplay_proven=False,live_presentation_contention_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
