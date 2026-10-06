"""Native per-entity modeldata fallback and signed clamps against pinned C."""
import argparse,hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_model_switch_4086 import CACHED_FIELDS,ENTITY_CORE_FIELDS
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffb80,0x7ffb82,0x7ffb84


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authority',type=Path,required=True)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text())
    if authority['status']!='PASS' or authority['functions_sha256']!='b986f6344bb027ff9bbc61f30375b49503941b5088906fd09aa7dc564b3d0c35':
        raise ValueError('MODEL_ENTITY_PINNED_C_AUTHORITY_REQUIRED')
    if len(CACHED_FIELDS)!=39 or len(ENTITY_CORE_FIELDS)!=18 or CACHED_FIELDS[20:38]!=ENTITY_CORE_FIELDS:
        raise ValueError('MODEL_ENTITY_NATIVE_FIELD_ABI')
    rows=[]
    floats={'speed','runspeed','runjumpheight','runjumpdist'}
    for ar in authority['results']:
        c=ar['case']
        if c['number']!=1:continue
        actual=ar['actual']['state'];cachefields=actual[17:56];core=actual[82:100]
        cache=bytearray(b'\xa5'*2560)
        for i,(field,value) in enumerate(zip(CACHED_FIELDS,cachefields)):
            struct.pack_into('<f' if field in floats else '<i',cache,160+4*i,float(value) if field in floats else int(value))
        struct.pack_into('<i',cache,160+156,c['newtype'])
        old=[10+CACHED_FIELDS.index(field)+60 for field in ENTITY_CORE_FIELDS]
        current=-0x80000000 if c['boundary']==1 else 0x7fffffff if c['boundary']==2 else 500
        before=struct.pack('<20i',*old,c['oldtype'],current)+b'\xa5'*16
        after=struct.pack('<20i',*[int(n) for n in core],c['newtype'],int(actual[3]))+b'\xa5'*16
        for slot in (0,1,127):
            view=bytearray(b'\xa5'*80);struct.pack_into('<IHH',view,0,0x414000+80*slot,1,0)
            struct.pack_into('<HHi',view,32,1,0,current);struct.pack_into('<HHi',view,64,1,0,777)
            want=bytearray(view);struct.pack_into('<i',want,36,int(actual[2]));struct.pack_into('<i',want,68,int(core[15]))
            rows.append(dict(slot=slot,cache=list(cache),before=list(before),after=list(after),view=list(view),want=list(want),
                oldtype=c['oldtype'],fault=0,bad='',boundary=c['boundary']))
    base=rows[0]
    for bad in ('ready','world_ready','world_base','entities','slot','models','model','health_tag','max_tag','health_reserved','max_reserved'):
        rows.append(dict(base,fault=1,bad=bad,after=base['before'],want=base['view']))
    sy=symbols(Path('src/main.sym'));entry=sy['Vm_SourceFrameGate'];first=39*32768;raw=bytearray(a.rom.read_bytes())
    if raw[first:first+32768]!=bytes(32768) or raw[0x7fd8]!=8:raise ValueError('MODEL_ENTITY_PROOF_RESERVED_ROM_OR_BWRAM')
    asm='''.snes
.bank 39
.org $8000
EntityCopyFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4EC
 bne EntityCopyFixture_Return
 lda #0
 sta.l REQUEST
 sta.l INDEX
 sta.l ERROR
EntityCopyFixture_Init:
.a16
.i16
 nop
 jsl APPLY
EntityCopyFixture_After:
.a16
.i16
 nop
 bcc EntityCopyFixture_Success
 lda.l EXPECTFAULT
 beq EntityCopyFixture_Bad
 bra EntityCopyFixture_Result
EntityCopyFixture_Success:
.a16
.i16
 lda.l EXPECTFAULT
 bne EntityCopyFixture_Bad
EntityCopyFixture_Result:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcc EntityCopyFixture_Init
 bra EntityCopyFixture_Done
EntityCopyFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
EntityCopyFixture_Done:
.a16
.i16
 lda #0
 sta.l READY
 sta.l WORLDREADY
EntityCopyFixture_Return:
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
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,APPLY=sy['SourceModelEntityCopy4086_Apply'],
        EXPECTFAULT=REQUEST+6,CASES=len(rows),READY=sy['SourceModelEntityCopy4086_Ready'],
        WORLDREADY=sy['VmSourceWorld_Ready'],RESUME=entry+5)
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',
        str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('MODEL_ENTITY_PROOF_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');code=(folder/'fixture.bin').read_bytes()[first:]
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a'):raise ValueError('MODEL_ENTITY_PROOF_GATE')
    raw[first:first+len(code)]=code;raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['EntityCopyFixture_Gate'])[:3]+b'\xea'
    rom=folder/'bor.sfc';rom.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    def luav(value):
        if isinstance(value,str):return json.dumps(value)
        if isinstance(value,list):return '{'+','.join(luav(v) for v in value)+'}'
        if isinstance(value,dict):return '{'+','.join(k+'='+luav(v) for k,v in value.items())+'}'
        return str(value)
    lua='local rows='+luav(rows)+'\nlocal sy='+luav({k:v for k,v in sy.items() if k.startswith(('SourceModelEntityCopy4086_','VmSourceWorld_'))})+'\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local cpu={};local start=0;local context_faults=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function set(k,v)put(sy['SourceModelEntityCopy4086_'..k],v)end
local function copy(a,t)for i,v in ipairs(t)do emu.write(a+i-1,v,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 for i=0,12287 do emu.write(0x40c000+i,0xa5,mt)end
 for i=0,10239 do emu.write(0x414000+i,0xa5,mt)end
 copy(0x40b000,c.cache);copy(0x40c000+96*c.slot,c.before);copy(0x414000+80*c.slot,c.view)
 for i=0,63 do emu.write(0x40bfc0+i,0x7b,mt);emu.write(0x40f000+i,0x2d,mt)end
 set('Ready',0xb4eb);set('Entities',128);set('Models',2);set('Slot',c.slot);set('Model',1);put(EXPECTFAULT,c.fault)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,128)
 if c.bad=='ready'then set('Ready',0)
 elseif c.bad=='world_ready'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='world_base'then put(sy.VmSourceWorld_PoolBase,0x4002)
 elseif c.bad=='entities'then set('Entities',0)
 elseif c.bad=='slot'then set('Slot',128)
 elseif c.bad=='models'then set('Models',17)
 elseif c.bad=='model'then set('Model',2)
 elseif c.bad=='health_tag'then put(0x414020+80*c.slot,2);c.want[33]=2
 elseif c.bad=='max_tag'then put(0x414040+80*c.slot,2);c.want[65]=2
 elseif c.bad=='health_reserved'then put(0x414022+80*c.slot,1);c.want[35]=1
 elseif c.bad=='max_reserved'then put(0x414042+80*c.slot,1);c.want[67]=1 end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState();start=state.masterClock;cpu={};context_faults=0
 for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=state['cpu.'..k]end
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState()
 for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=state['cpu.'..k]then context_faults=context_faults+1 end end
 if cpu.sp+3~=state['cpu.sp'] or (cpu.ps&254)~=(state['cpu.ps']&254)then context_faults=context_faults+1 end
 emu.log('ENTITYCOPYCOST|'..word(INDEX)..'|'..(state.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=word(INDEX)+1;local c=rows[n];local mismatch=0;local guards=0;local cachefault=0
 for i=0,12287 do local r=i-96*c.slot;local v=r>=0 and r<96 and c.after[r+1] or 0xa5;if emu.read(0x40c000+i,mt)~=v then mismatch=mismatch+1 end end
 for i=0,10239 do local r=i-80*c.slot;local v=r>=0 and r<80 and c.want[r+1] or 0xa5;if emu.read(0x414000+i,mt)~=v then mismatch=mismatch+1 end end
 for i,v in ipairs(c.cache)do if emu.read(0x40b000+i-1,mt)~=v then cachefault=cachefault+1 end end
 for i=0,63 do if emu.read(0x40bfc0+i,mt)~=0x7b then guards=guards+1 end;if emu.read(0x40f000+i,mt)~=0x2d then guards=guards+1 end end
 emu.log('ENTITYCOPYRESULT|'..word(INDEX)..'|'..word(sy.SourceModelEntityCopy4086_Status)..'|'..mismatch..'|'..guards..'|'..cachefault..'|'..context_faults..'|'..word(sy.SourceModelEntityCopy4086_OldTypeLo)..'|'..word(sy.SourceModelEntityCopy4086_OldTypeHi))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    for k,v in dict(INDEX=INDEX,EXPECTFAULT=REQUEST+6,INIT=fs['EntityCopyFixture_Init'],APPLY=sy['SourceModelEntityCopy4086_Apply'],
        AFTER=fs['EntityCopyFixture_After'],RESULT=fs['EntityCopyFixture_Result']).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'observer.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter=Reporter('M4-MODEL-ENTITY-COPY',kind='GATE')
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        reporter.check('cold entity model copy disabled',startup.u16(m,sy['SourceModelEntityCopy4086_Ready'])==0)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('MODEL_ENTITY_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(REQUEST,0xb4ec)
        for _ in range(24):
            run_frames_exact(m,60)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native entity model copy batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];costs=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('ENTITYCOPYRESULT|',results),('ENTITYCOPYCOST|',costs)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('C-derived entity core and signed clamps preserve all unrelated bytes',len(results)==len(rows) and
        all(r[:6]==[i,2 if c['fault'] else 1,0,0,0,0] and (c['fault'] or r[6:]==[c['oldtype'],0]) for i,(r,c) in enumerate(zip(results,rows))))
    r=dict(schema='BYOR_4086_MODEL_ENTITY_COPY_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(raw).hexdigest(),authority_report_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),
        cases=len(rows),rejection_cases=sum(c['fault'] for c in rows),results=results,cpu_costs=costs,
        core_fields=ENTITY_CORE_FIELDS,cache_fields=CACHED_FIELDS,cache_range='40B000..40B9FF',entity_range='40C000..40EFFF',
        source_type_policy='Install new model type now; return original entity type for restoration after source animation initialization.',
        full_model_switch_bound=False,animation_initialization_bound=False,live_presentation_contention_proven=False,
        motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
