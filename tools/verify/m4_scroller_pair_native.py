"""Two real authored constructor handoffs in one controlled catch-up scroller.

Uses the source-derived private constructor fixture builder; no constructor or
script service is mocked. Camera/position is held at the second record's AT.
This is pool/continuation proof, not an authored live camera trajectory.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_stage_queue_4086 import derive,pack,unpack
from source_model_registry import derive as registry
from source_profile import document
from PIL import Image
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--drop-context',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    source=Source(a.source);models=registry(source);stage=derive(source)['stages'][0];rows=unpack(pack(derive(source)),len(models['models']))[:2]
    if any(r['kind']!='spawn'or r['stage_id']!=1 for r in rows)or rows[0]['model']!=rows[1]['model']:raise ValueError('PAIR_FIXTURE_REQUIRES_FIRST_TWO_SAME_MODEL_SPAWNS')
    if stage['records'][2]['at']<=rows[1]['at']:raise ValueError('PAIR_FIXTURE_REQUIRES_BOUNDED_NEXT_AT')
    panels=[r['values'][0]for r in document(source,stage['source_path'])['directives']if r['directive']=='panel']
    if len(panels)!=1:raise ValueError('PAIR_FIXTURE_PANEL_SHAPE')
    with Image.open(io.BytesIO(source.read(panels[0])))as image:width,height=image.size
    command=[sys.executable,'tools/verify/m4_animation_callback_owner_native.py','--source',str(a.source),'--rom',str(a.rom),'--output',str(folder),'--effects-runner','--default-owner','--ctor-owner','--ctor-state','--ctor-factors','--ctor-model','--script-clone','--queue-producer','--smartspawn','--stage-queue-index','0','--drop-context',str(a.drop_context),'--emit-only']
    subprocess.run(command,check=True)
    sy=symbols(Path('src/main.sym'));asm=(folder/'callback_fixture.pasm').read_text()
    asm=asm.replace(' jsl '+str(sy['SourceStageProducer4086_Next']),' jsl '+str(sy['SourceScrollerOwner4086_Begin']))
    asm=asm.replace(' jsl '+str(sy['SourceStageProducer4086_AckSpawn']),' jsl '+str(sy['SourceScrollerOwner4086_Continue']))
    ctor_call=' jsl '+str(sy['SourceCtorOwner4086_Begin']);at=asm.index(ctor_call);start=asm.rfind(' lda #',0,at);asm=asm[:start]+'PairFixture_CtorStart:\n.a16\n.i16\n'+asm[start:]
    marker='CallbackFixture_QueuePublished:\n.a16\n.i16\n nop'
    asm=asm.replace(marker,marker+'''\n cmp #0
 beq PairFixture_Done
 cmp #1
 beq PairFixture_Next
 jmp CallbackFixture_Bad
PairFixture_Next:
.a16
.i16
 jmp PairFixture_CtorStart
PairFixture_Done:
.a16
.i16
''')
    # Run one catch-up invocation. Preserve all pool data between constructors.
    needle=' lda.l 8387458\n inc a\n sta.l 8387458\n cmp #2'
    if needle not in asm:raise ValueError('PAIR_FIXTURE_CASE_COUNTER')
    asm=asm.replace(needle,needle[:-1]+'1')
    (folder/'pair.pasm').write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(folder/'pair.pasm'),'--output',str(folder/'pair.bin'),'--symbols',str(folder/'pair.sym')],capture_output=True,text=True);(folder/'pair-build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('PAIR_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'pair.sym');base=39*32768;rom=bytearray((folder/'bor.sfc').read_bytes());code=(folder/'pair.bin').read_bytes()[base:];rom[base:base+len(code)]=code;rom[offset(sy['Vm_SourceFrameGate']):offset(sy['Vm_SourceFrameGate'])+5]=b'\x5c'+struct.pack('<I',fs['CallbackFixture_Gate'])[:3]+b'\xea';path=folder/'bor.sfc';path.write_bytes(rom)
    lua=(folder/'callback_owner.lua').read_text()
    # Original observer hooks refer to the old private wrapper addresses.
    old=symbols(folder/'callback_fixture.sym')
    for name,value in old.items():
        if name in fs:lua=re.sub(r'\b'+str(value)+r'\b',str(fs[name]),lua)
    # Append only caller context and readonly observers. Existing source builder
    # performs actual metadata installation; both births use native services.
    controls=dict(SourceScrollerOwner4086_Ready=0xb5dd,SourceScrollerOwner4086_State=0,SourceScrollerPrefix4086_Ready=0xb5d7,SourceScrollerPrefix4086_State=0,SourceStageCompletion4086_Ready=0xb5d8,SourceWait4086_Ready=0xb5d9,SourceWait4086_Status=0,SourceCameraBounds4086_Ready=0xb5da,SourceCameraBounds4086_MaxPlayers=4,SourceCameraBounds4086_CameraType=0,SourceCameraMotion4086_Ready=0xb5db,SourceCameraMotion4086_Status=0,SourceCameraMotion4086_Direction=2,SourceCameraMotion4086_Width=width,SourceCameraMotion4086_Height=height,SourceCameraMotion4086_HRes=320,SourceCameraMotion4086_VRes=240,SourceCameraMotion4086_Rocking=0)
    wide=dict(SourceScrollerPrefix4086_AdvanceTime=47,SourceScrollerPrefix4086_FreezeAll=0,SourceScrollerPrefix4086_Completed=0,SourceStageCompletion4086_LevelType=0,SourceWait4086_NoReset=0,SourceWait4086_SetTime=100,SourceWait4086_TimeLeft=-77,SourceCameraMotion4086_Speed=65536,SourceCameraMotion4086_OffsetX=0,SourceCameraMotion4086_OffsetZ=0,SourceCameraMotion4086_MinX=0,SourceCameraMotion4086_MaxX=(width-320)*65536,SourceCameraMotion4086_MinZ=0,SourceCameraMotion4086_MaxZ=height*65536,SourceCameraMotion4086_Blockade=0,VmSourceWorld_AdvanceX=rows[1]['at']*65536,SourceStageProducer4086_Position=rows[1]['at'])
    extra="\nlocal births=0;local retained={};local pair_completed=0\nemu.addMemoryCallback(function()\n"+'\n'.join(" set('"+k+"',"+str(v)+")"for k,v in controls.items())+'\n'+'\n'.join(" set('"+k+"',"+str(v)+",4)"for k,v in wide.items())+f"\n for i=0,8191 do emu.write(0x409000+i,0,mt)end -- fresh calloc relation/script state for every pool slot\n for i=0,3 do put(0x43fd84+i*4,0,4)end\nend,emu.callbackType.exec,{fs['CallbackFixture_Init']},{fs['CallbackFixture_Init']},emu.cpuType.snes,mt)\n"
    extra+=f'''emu.addMemoryCallback(function()
 local slot=word(sy.SourceSpawnSlot4086_Slot);local changed=0
 if births==1 then for addr,v in pairs(retained)do if emu.read(addr,mt)~=v then changed=changed+1 end end end
 emu.log('PAIRBIRTH|'..births..'|'..slot..'|'..dw(sy.VmNativeVariant_Result+4)..'|'..dw(0x414034+slot*80)..'|'..dw(0x41403c+slot*80)..'|'..dw(0x414024+slot*80)..'|'..dw(0x40c03c+slot*96)..'|'..changed)
 if births==0 then for _,r in ipairs({{{{0x414000,80}},{{0x40c000,96}},{{0x416800,64}},{{0x439000,80}},{{0x433800,64}},{{0x409000,64}}}})do for j=0,r[2]-1 do retained[r[1]+j]=emu.read(r[1]+j,mt)end end end
 births=births+1
end,emu.callbackType.exec,{fs['CallbackFixture_PropertiesPublished']},{fs['CallbackFixture_PropertiesPublished']},emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 pair_completed=pair_completed+1
 emu.log('PAIRDONE|'..births..'|'..word(sy.SourceScrollerOwner4086_State)..'|'..word(sy.SourceStageProducer4086_State)..'|'..word(sy.SourceStageQueue4086_Index)..'|'..word(sy.SourceWait4086_Status)..'|'..word(sy.SourceCameraMotion4086_Status)..'|'..word(sy.SourceClock4086_Due)..'|'..dw(sy.SourceClock4086_TimeLo))
end,emu.callbackType.exec,{fs['PairFixture_Done']},{fs['PairFixture_Done']},emu.cpuType.snes,mt)
'''
    for label in ('SourceCtorOwner4086_BeginBad','SourceCtorModel4086_Bad','SourceScriptClone4086_Bad','SourceCtorState4086_Bad','SourceDefaultOwner4086_Bad'):
        if label in sy:
            extra+=f"emu.addMemoryCallback(function()emu.log('PAIRFAULT|{label}|'..word(sy.SourceSpawnSlot4086_Slot)..'|'..word(sy.SourceCtorOwner4086_Phase)..'|'..word(sy.SourceCtorState4086_Status)..'|'..word(sy.SourceCtorModel4086_Status)..'|'..word(sy.SourceScriptClone4086_Status)..'|'..word(sy.SourceDefaultInit4086_Phase))end,emu.callbackType.exec,{sy[label]},{sy[label]},emu.cpuType.snes,mt)\n"
    script=folder/'pair.lua';script.write_text(lua+extra)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    r=Reporter('M4-SCROLLER-PAIR',kind='GATE')
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log')as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,r)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('PAIR_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(0x7ffb82,0);m.write_u16(0x7ffb84,0);m.write_u16(0x7ffb80,0xb4e7)
        for _ in range(2000):
            run_frames_exact(m,1)
            if startup.u16(m,0x7ffb82)==1 or startup.u16(m,0x7ffb84):break
        r.check('bounded single scroller invocation completed',startup.u16(m,0x7ffb82)==1 and startup.u16(m,0x7ffb84)==0)
    log=(folder/'mesen.log').read_text();births=[list(map(int,line.split('PAIRBIRTH|',1)[1].split('|')))for line in log.splitlines()if 'PAIRBIRTH|'in line];done=[list(map(int,line.split('PAIRDONE|',1)[1].split('|')))for line in log.splitlines()if 'PAIRDONE|'in line]
    expected=[]
    for i,row in enumerate(rows):
        health=row['health'][0]or models['models'][row['model']]['maxhealth'];expected.append([i,i,0x414000+i*80,(row['coords_q16'][0]+rows[1]['at']*65536)&0xffffffff,row['coords_q16'][1]&0xffffffff,health&0xffffffff,health&0xffffffff,0])
    r.check('actual two constructors/properties preserve first entity while publishing distinct source-sized second entity',births==expected)
    r.check('future source AT stops same invocation with WAIT/camera retired and logical clock still held',done==[[2,4,4,2,2,2,1,48]])
    d=dict(schema='BYOR_4086_SCROLLER_PAIR_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',births=births,expected=expected,done=done,rom_sha256=hashlib.sha256(rom).hexdigest(),source_rows=rows,controlled_catchup_position=rows[1]['at'],camera_and_drop_context_instrumented=True,full_world_backend_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
