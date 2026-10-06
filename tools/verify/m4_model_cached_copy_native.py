"""Mutable cached scalar and weapon-pointer inheritance against pinned C."""
import argparse,hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_model_switch_4086 import CACHED_FIELDS
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_animation_init_native import luav
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffd80,0x7ffd82,0x7ffd84


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authority',type=Path,required=True)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text())
    if authority['status']!='PASS' or authority['functions_sha256']!='b986f6344bb027ff9bbc61f30375b49503941b5088906fd09aa7dc564b3d0c35':raise ValueError('MODEL_CACHED_C_AUTHORITY_REQUIRED')
    rows=[];floats={'speed','runspeed','runjumpheight','runjumpdist'}
    def row(fields,type_):
        b=bytearray(b'\xa5'*160)
        for i,(name,v) in enumerate(zip(CACHED_FIELDS,fields)):struct.pack_into('<f' if name in floats else '<i',b,4*i,float(v) if name in floats else int(v))
        struct.pack_into('<i',b,156,type_);return list(b)
    for ar in authority['results']:
        c=ar['case']
        if c['number']!=1:continue
        old=list(range(10,49));new=[110+i if c['variant'] and i%3==0 else 0 if f in ('speed','runspeed','health','mp') else -1 for i,f in enumerate(CACHED_FIELDS)]
        for field in ('health','mp'):
            if c['boundary'] in (3,4,5):new[CACHED_FIELDS.index(field)]={3:-1,4:0x7fffffff,5:-0x80000000}[c['boundary']]
        if c['boundary']==6:
            for field in ('aimove','aiattack','risetime.rise'):new[CACHED_FIELDS.index(field)]=-2
        if c['boundary'] in (7,8):
            for field in ('speed','runspeed'):new[CACHED_FIELDS.index(field)]=-0.0 if c['boundary']==7 else 1.1754943508222875e-38
        for oldid,newid in ((0,1),(15,0),(1,15)):
            before=bytearray(b'\xa5'*2560);before[160*oldid:160*(oldid+1)]=bytes(row(old,c['oldtype']));before[160*newid:160*(newid+1)]=bytes(row(new,c['newtype']))
            after=bytearray(before);after[160*newid:160*(newid+1)]=bytes(row(ar['actual']['state'][17:56],c['newtype']))
            meta=bytearray(b'\xa5'*512);struct.pack_into('<HH',meta,32*oldid,oldid,2);struct.pack_into('<HHH',meta,32*newid,65535,0,c['flags'])
            want=bytearray(meta)
            if not c['flags']&3:struct.pack_into('<HH',want,32*newid,oldid,2)
            rows.append(dict(old=oldid,new=newid,flags=c['flags'],before=list(before),after=list(after),meta=list(meta),want=list(want),fault=0,bad='',boundary=c['boundary']))
    base=rows[0]
    for bad in ('ready','entity_ready','models_zero','models_large','old','new','flags','new_null_count','old_list','new_list'):
        b=dict(base,fault=1,bad=bad,after=base['before'],want=base['meta'])
        if bad in ('new_null_count','old_list','new_list'):
            meta=bytearray(b['meta']);at=32*(b['old'] if bad=='old_list' else b['new'])
            struct.pack_into('<HH',meta,at,65535 if bad=='new_null_count' else 16,2)
            b.update(meta=list(meta),want=list(meta))
        rows.append(b)
    for flags in (1,2):
        b=dict(next(r for r in rows if r['flags']==flags and not r['fault']),bad='unused_metadata')
        meta=bytearray(b['meta'])
        for model in (b['old'],b['new']):struct.pack_into('<HH',meta,32*model,16,129)
        b.update(meta=list(meta),want=list(meta));rows.append(b)
    sy=symbols(Path('src/main.sym'));entry=sy['Vm_SourceFrameGate'];first=39*32768;raw=bytearray(a.rom.read_bytes())
    if raw[first:first+32768]!=bytes(32768) or raw[0x7fd8]!=8:raise ValueError('MODEL_CACHED_PROOF_RESERVATION')
    asm='''.snes
.bank 39
.org $8000
CachedCopyFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4EC
 bne CachedCopyFixture_Return
CachedCopyFixture_Init:
.a16
.i16
 nop
 jsl APPLY
CachedCopyFixture_After:
.a16
.i16
 nop
 bcc CachedCopyFixture_Success
 lda.l EXPECTFAULT
 beq CachedCopyFixture_Bad
 bra CachedCopyFixture_Result
CachedCopyFixture_Success:
.a16
.i16
 lda.l EXPECTFAULT
 bne CachedCopyFixture_Bad
CachedCopyFixture_Result:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcs CachedCopyFixture_Done
 and #7
 bne CachedCopyFixture_Init
 bra CachedCopyFixture_Return
CachedCopyFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
CachedCopyFixture_Done:
.a16
.i16
 lda #0
 sta.l REQUEST
 sta.l READY
 sta.l ENTITYREADY
CachedCopyFixture_Return:
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
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,APPLY=sy['SourceModelCachedCopy4086_Apply'],
        EXPECTFAULT=REQUEST+6,CASES=len(rows),READY=sy['SourceModelCachedCopy4086_Ready'],
        ENTITYREADY=sy['SourceModelEntityCopy4086_Ready'],RESUME=entry+5)
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',
        str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('MODEL_CACHED_PROOF_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');code=(folder/'fixture.bin').read_bytes()[first:]
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a'):raise ValueError('MODEL_CACHED_PROOF_GATE')
    raw[first:first+len(code)]=code;raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['CachedCopyFixture_Gate'])[:3]+b'\xea'
    rom=folder/'bor.sfc';rom.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    lua='local rows='+luav(rows)+'\nlocal sy='+luav({k:v for k,v in sy.items() if k.startswith(('SourceModelCachedCopy4086_','SourceModelEntityCopy4086_'))})+'\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local cpu={};local start=0;local ctx=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function set(k,v)put(sy['SourceModelCachedCopy4086_'..k],v)end
local function copy(a,t)for i,v in ipairs(t)do emu.write(a+i-1,v,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 copy(0x40b000,c.before);copy(0x40ba00,c.meta)
 for i=0,63 do emu.write(0x40afc0+i,0x79,mt);emu.write(0x40bc00+i,0x2d,mt)end
 set('Ready',0xb4ee);set('Models',16);set('Old',c.old);set('New',c.new);set('Flags',c.flags);put(EXPECTFAULT,c.fault)
 put(sy.SourceModelEntityCopy4086_Ready,0xb4eb)
 if c.bad=='ready'then set('Ready',0)
 elseif c.bad=='entity_ready'then put(sy.SourceModelEntityCopy4086_Ready,0)
 elseif c.bad=='models_zero'then set('Models',0)
 elseif c.bad=='models_large'then set('Models',17)
 elseif c.bad=='old'then set('Old',16)
 elseif c.bad=='new'then set('New',16)
 elseif c.bad=='flags'then set('Flags',8)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();start=s.masterClock;ctx=0;cpu={}
 for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('CACHEDCOPYCOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local mismatch=0
 for i,v in ipairs(c.after)do if emu.read(0x40b000+i-1,mt)~=v then mismatch=mismatch+1 end end
 for i,v in ipairs(c.want)do if emu.read(0x40ba00+i-1,mt)~=v then mismatch=mismatch+1 end end
 for i=0,63 do if emu.read(0x40afc0+i,mt)~=0x79 then mismatch=mismatch+1 end;if emu.read(0x40bc00+i,mt)~=0x2d then mismatch=mismatch+1 end end
 emu.log('CACHEDCOPYRESULT|'..word(INDEX)..'|'..word(sy.SourceModelCachedCopy4086_Status)..'|'..mismatch..'|'..ctx)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    for k,v in dict(INDEX=INDEX,EXPECTFAULT=REQUEST+6,INIT=fs['CachedCopyFixture_Init'],APPLY=sy['SourceModelCachedCopy4086_Apply'],AFTER=fs['CachedCopyFixture_After'],RESULT=fs['CachedCopyFixture_Result']).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'observer.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    reporter=Reporter('M4-MODEL-CACHED-COPY',kind='GATE')
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        reporter.check('cold cached model copy disabled',startup.u16(m,sy['SourceModelCachedCopy4086_Ready'])==0)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('MODEL_CACHED_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(INDEX,0);m.write_u16(ERROR,0);m.write_u16(REQUEST,0xb4ec)
        for _ in range(1500):
            run_frames_exact(m,1)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native cached model copy batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];costs=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('CACHEDCOPYRESULT|',results),('CACHEDCOPYCOST|',costs)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('C-derived scalar bits and weapon aliases preserve complete cache and CPU context',len(results)==len(rows) and all(r==[i,2 if c['fault'] else 1,0,0] for i,(r,c) in enumerate(zip(results,rows))))
    report=dict(schema='BYOR_4086_MODEL_CACHED_COPY_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_report_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cases=len(rows),results=results,cpu_costs=costs,
        cache_range='40B000..40B9FF',metadata_range='40BA00..40BBFF',negative_zero_and_minimum_normal_float_checked=True,
        full_model_switch_bound=False,authored_cache_loader_bound=False,live_presentation_contention_proven=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
