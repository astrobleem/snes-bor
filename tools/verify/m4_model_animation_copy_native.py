"""Native cached animation inheritance; complete model switching remains unbound."""
import argparse,hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_model_switch_requirements import derive,pack_animation_cache
from source_model_switch_4086 import copy_cached_defaults,GLOBAL_NEGATIVE,ENTITY_NEGATIVE,RUN_FIELDS
from source_frame_effects_4086 import derive as frame_effects,pack as pack_effects
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffb80,0x7ffb82,0x7ffb84


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);source=Source(a.source)
    requirements=derive(source);cache=pack_animation_cache(requirements);count=len(requirements['models']);maximum=requirements['maximum_animations']
    frames=frame_effects(source);empty_handle=len(frames['animations'])+1
    frames['animations'].append(dict(handle=empty_handle,frames=[],events=dict(frames['animations'][0]['events'])))
    table=pack_effects(frames);framecounts={an['handle']:len(an['frames']) for an in frames['animations']}
    rows=[dict(old=old,new=new,flags=flags,fault=0) for old in range(count) for new in range(count) for flags in range(8)]
    for bad in ('ready','models','old','new','maximum','large_maximum','bytes','flags','old_handle','new_handle','table_ready','table_bank','table_bytes'):
        rows.append(dict(old=3,new=5,flags=0,fault=1,bad=bad))
    rows.append(dict(old=3,new=5,flags=0,fault=0,bad='empty_old_animation'))
    raw=bytearray(a.rom.read_bytes());sy=symbols(Path('src/main.sym'));entry=sy['Vm_SourceFrameGate'];first=39*32768
    if raw[first:first+32768]!=bytes(32768) or raw[60*32768:61*32768]!=bytes(32768):raise ValueError('MODEL_ANIMATION_PROOF_RESERVED_ROM')
    if raw[0x7fd8]!=8:raise ValueError('MODEL_ANIMATION_PROOF_BWRAM_HEADER')
    asm='''.snes
.bank 39
.org $8000
ModelCopyFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4EA
 bne ModelCopyFixture_Return
 lda #0
 sta.l REQUEST
 sta.l INDEX
 sta.l ERROR
ModelCopyFixture_Init:
.a16
.i16
 nop
ModelCopyFixture_Before:
.a16
.i16
 jsl APPLY
ModelCopyFixture_After:
.a16
.i16
 nop
 bcc ModelCopyFixture_Success
 lda.l EXPECTFAULT
 beq ModelCopyFixture_Bad
 bra ModelCopyFixture_Result
ModelCopyFixture_Success:
.a16
.i16
 lda.l EXPECTFAULT
 bne ModelCopyFixture_Bad
ModelCopyFixture_Result:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcc ModelCopyFixture_Init
 bra ModelCopyFixture_Done
ModelCopyFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
ModelCopyFixture_Done:
.a16
.i16
 lda #0
 sta.l OWNERREADY
 sta.l FRAMEREADY
ModelCopyFixture_Return:
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
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,APPLY=sy['SourceModelAnimationCopy4086_Apply'],
        EXPECTFAULT=REQUEST+6,CASES=len(rows),OWNERREADY=sy['SourceModelAnimationCopy4086_Ready'],
        FRAMEREADY=sy['SourceUpdateFrame4086_Ready'],RESUME=entry+5)
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',
        str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('MODEL_ANIMATION_PROOF_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');code=(folder/'fixture.bin').read_bytes()[first:]
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a'):raise ValueError('MODEL_ANIMATION_PROOF_GATE')
    raw[first:first+len(code)]=code;raw[60*32768:60*32768+len(table)]=table
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['ModelCopyFixture_Gate'])[:3]+b'\xea'
    rom=folder/'bor.sfc';rom.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    words=list(struct.unpack('<'+'H'*(len(cache)//2),cache));words+=[0xa5a5]*((8192-len(cache))//2)
    def model(values,flags):
        d=dict.fromkeys(['speed',*RUN_FIELDS,*GLOBAL_NEGATIVE,*ENTITY_NEGATIVE,'aimove','aiattack','health','mp','risetime.rise','weapnum'],0)
        d.update(model_flag=flags,animation={n:dict(handle=h,numframes=framecounts[h]) if h else None for n,h in enumerate(values)},weapon=None,numweapons=0)
        return d
    patches=[];initial_patches=[]
    for c in rows:
        initial=list(words);before=[]
        if c.get('bad') in ('old_handle','new_handle','empty_old_animation'):
            slot=(c['new'] if c['bad']=='new_handle' else c['old'])*maximum+1
            value=empty_handle if c['bad']=='empty_old_animation' else empty_handle+1
            initial[slot]=value;before.append([slot,value])
        expected=list(initial)
        if not c['fault']:
            old=model(initial[c['old']*maximum:(c['old']+1)*maximum],0)
            new=model(initial[c['new']*maximum:(c['new']+1)*maximum],c['flags'])
            copy_cached_defaults(old,new)
            for n,an in new['animation'].items():expected[c['new']*maximum+n]=an['handle'] if an else 0
        patches.append([[n,v] for n,v in enumerate(expected) if v!=words[n]])
        initial_patches.append(before)
    def luav(value):
        if isinstance(value,str):return json.dumps(value)
        if isinstance(value,list):return '{'+','.join(luav(v) for v in value)+'}'
        if isinstance(value,dict):return '{'+','.join(k+'='+luav(v) for k,v in value.items())+'}'
        return str(value)
    lua='local rows='+luav(rows)+'\nlocal patches='+luav(patches)+'\nlocal initial_patches='+luav(initial_patches)+'\nlocal cache='+luav(words)+'\n'
    lua+='local sy='+luav({k:v for k,v in sy.items() if k.startswith(('SourceModelAnimationCopy4086_','SourceUpdateFrame4086_'))})+'\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local cpu={};local start=0;local context_faults=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function set(k,v)put(sy['SourceModelAnimationCopy4086_'..k],v)end
emu.addMemoryCallback(function()
 local n=word(INDEX)+1;local c=rows[n]
 for i,v in ipairs(cache)do put(0x43c000+2*(i-1),v)end
 for _,v in ipairs(initial_patches[n])do put(0x43c000+2*v[1],v[2])end
 for i=0,63 do emu.write(0x43bfc0+i,0x7b,mt);emu.write(0x43e000+i,0x2d,mt)end
 set('Ready',0xb4e9);set('Models',MODELS);set('Maximum',MAXIMUM);set('Bytes',CACHEBYTES)
 set('OldModel',c.old);set('NewModel',c.new);set('Flags',c.flags);put(EXPECTFAULT,c.fault)
 put(sy.SourceUpdateFrame4086_Ready,0xb4e3);put(sy.SourceUpdateFrame4086_Base,0x8000)
 put(sy.SourceUpdateFrame4086_Bank,60);put(sy.SourceUpdateFrame4086_Bytes,TABLEBYTES)
 if c.bad=='ready'then set('Ready',0)
 elseif c.bad=='models'then set('Models',0)
 elseif c.bad=='old'then set('OldModel',MODELS)
 elseif c.bad=='new'then set('NewModel',MODELS)
 elseif c.bad=='maximum'then set('Maximum',0)
 elseif c.bad=='large_maximum'then set('Maximum',1025)
 elseif c.bad=='bytes'then set('Bytes',CACHEBYTES-2)
 elseif c.bad=='flags'then set('Flags',8)
 elseif c.bad=='table_ready'then put(sy.SourceUpdateFrame4086_Ready,0)
 elseif c.bad=='table_bank'then put(sy.SourceUpdateFrame4086_Bank,64)
 elseif c.bad=='table_bytes'then put(sy.SourceUpdateFrame4086_Bytes,16)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState();start=state.masterClock;cpu={};context_faults=0
 for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=state['cpu.'..k]end
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState()
 for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=state['cpu.'..k]then context_faults=context_faults+1 end end
 if cpu.sp+3~=state['cpu.sp'] or (cpu.ps&254)~=(state['cpu.ps']&254)then context_faults=context_faults+1 end
 emu.log('MODELCOPYCOST|'..word(INDEX)..'|'..(state.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=word(INDEX)+1;local expected={};local mismatch=0;local guards=0
 for i,v in ipairs(cache)do expected[i]=v end
 for _,v in ipairs(patches[n])do expected[v[1]+1]=v[2]end
 for i,v in ipairs(expected)do if word(0x43c000+2*(i-1))~=v then mismatch=mismatch+1 end end
 for i=0,63 do if emu.read(0x43bfc0+i,mt)~=0x7b then guards=guards+1 end;if emu.read(0x43e000+i,mt)~=0x2d then guards=guards+1 end end
 emu.log('MODELCOPYRESULT|'..word(INDEX)..'|'..word(sy.SourceModelAnimationCopy4086_Status)..'|'..mismatch..'|'..guards..'|'..context_faults)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    for k,v in dict(INDEX=INDEX,EXPECTFAULT=REQUEST+6,MODELS=count,MAXIMUM=maximum,CACHEBYTES=len(cache),TABLEBYTES=len(table),
        INIT=fs['ModelCopyFixture_Init'],APPLY=sy['SourceModelAnimationCopy4086_Apply'],AFTER=fs['ModelCopyFixture_After'],RESULT=fs['ModelCopyFixture_Result']).items():
        lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'observer.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter=Reporter('M4-MODEL-ANIMATION-CACHE',kind='GATE')
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        reporter.check('cold model animation cache disabled',startup.u16(m,sy['SourceModelAnimationCopy4086_Ready'])==0)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('MODEL_ANIMATION_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(REQUEST,0xb4ea)
        for _ in range(48):
            run_frames_exact(m,60)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native model cache batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];costs=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('MODELCOPYRESULT|',results),('MODELCOPYCOST|',costs)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('every cached handle and guard byte matches source policy',len(results)==len(rows) and
        all(r==[i,2 if c['fault'] else 1,0,0,0] for i,(r,c) in enumerate(zip(results,rows))))
    r=dict(schema='BYOR_4086_MODEL_ANIMATION_COPY_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(raw).hexdigest(),cache_sha256=hashlib.sha256(cache).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),
        models=count,maximum_animations=maximum,cache_bytes=len(cache),reserved_cache_bytes=8192,
        cases=len(rows),rejection_cases=sum(c['fault'] for c in rows),case_inputs=rows,results=results,cpu_costs=costs,
        bwram_range='43C000..43DFFF exclusive B4E9 lease; 43BFC0/43E000 guards in private fixture',
        complete_model_switch_bound=False,entity_modeldata_copy_bound=False,model_switch_callbacks_bound=False,
        foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
