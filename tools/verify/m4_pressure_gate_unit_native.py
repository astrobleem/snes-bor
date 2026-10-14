"""Cold-only native boundary/fallback unit probe; no synthetic picture published.
Temporarily backs up 344 tail-ref bytes in the dead I-RAM queue, restores them
before original cold production. Calls actual candidate gate and NbFree code.
"""
import json,os,shutil,subprocess
from pathlib import Path
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
import m4_nonblank_batch_native as batch
import m4_conditional_capacity_native as candidate
from m4_nonblank_component_native import sha
BASE=Path('out/byor-motu-conditional-capacity-regression-v1/native')

def transform(source):
    a=list(source)
    at=a.index('NbCold:')+3;a[at:at]=[' jsr NbProbeStart']
    for label,target in [('NbBeginRetry:','NbProbeFallbackReturned'),('NbAbort:','NbProbeSecondReturned')]:
        at=a.index(label)+3;tag=label[:-1]+'ProbeContinue'
        a[at:at]=[' lda.l $42D61E',f' beq {tag}',f' jmp {target}',tag+':','.a16','.i16']
    lines=['.org $B000','NbProbeStart:','.a16','.i16',' php',' pha',' phx',' phy',' phb',' lda $18',' pha',' lda $2E',' pha',' lda $70',' pha',' lda $72',' pha',' lda $74',' pha',' lda $76',' pha',' lda $78',' pha',
        ' lda #0',' sta.l $42D606',' sta.l $42D660',' sta.l $42D674',' sta.l $42D61E',
        ' phb',' lda #343',' ldx #$D4A8',' ldy #$3500',' mvn $00,$42',' plb','NbProbeBackup:']
    for free in (128,129,124,134):
        lines+= [f' lda #{free}',' jsr NbProbeSetRefs',' jsr NbCapacityPressureGate',f'NbProbeReturn{free}:','.a16','.i16',' lda #0',' adc #0',' sta $72',f'NbProbeChoice{free}:','.a16','.i16',' lda $72',f' beq NbProbeNoPrediction{free}',' jsr NbCapacityPredict',f'NbProbePredictionReturned{free}:','.a16','.i16',' nop',f'NbProbeNoPrediction{free}:','.a16','.i16']
    lines+=[' lda #1',' sta.l $42D61E',' lda #596',' sta $2E',' lda #0',' sta $72','NbProbeFirstLoop:','.a16','.i16',' jsr NbFree',' inc $72',' lda $72',' cmp #135',' bcc NbProbeFirstLoop','NbProbeUnexpected:',' jmp NbProbeUnexpected',
        'NbProbeFallbackReturned:','.a16','.i16',
        ' lda #596',' sta $2E',' lda #0',' sta $72','NbProbeSecondLoop:','.a16','.i16',' jsr NbFree',' inc $72',' lda $72',' cmp #135',' bcc NbProbeSecondLoop',' jmp NbProbeUnexpected',
        'NbProbeSecondReturned:','.a16','.i16',' lda #0',' sta.l $42D61E',' sta.l $42D674',
        ' phb',' lda #343',' ldx #$3500',' ldy #$D4A8',' mvn $42,$00',' plb','NbProbeRestored:','.a16','.i16',
        ' pla',' sta $78',' pla',' sta $76',' pla',' sta $74',' pla',' sta $72',' pla',' sta $70',' pla',' sta $2E',' pla',' sta $18',' plb',' ply',' plx',' pla',' plp',' rts',
        'NbProbeSetRefs:','.a16','.i16',' asl a',' sta $72',' ldx #0','NbProbeFill:','.a16','.i16',' cpx $72',' bcs NbProbeOccupied',' lda #$C000',' bra NbProbeStore','NbProbeOccupied:','.a16','.i16',' lda #$8001','NbProbeStore:','.a16','.i16',' sta.l $42D4A8,x',' inx',' inx',' cpx #344',' bcc NbProbeFill',' rts','NbProbeEnd:']
    at=a.index('.org $C000');a[at:at]=lines;return a

def audit(rom,native):
    old=(BASE/'bor.sfc').read_bytes();wanted=transform((BASE/'publisher.pasm').read_text().splitlines())
    if (native/'publisher.pasm').read_text().splitlines()!=wanted:raise ValueError('PRESSURE_UNIT_SOURCE')
    sy=symbols(native/'publisher.sym');compiled=(native/'publisher.bin').read_bytes()
    from m4_restore_spill_native import audit_branches
    audit_branches([' iny' if x.strip()=='dey' else x for x in wanted],sy,compiled)
    if sy['NbCodeEnd']>=0x39b000 or sy['NbProbeEnd']>=0x39c000:raise ValueError('PRESSURE_UNIT_CODE_LEASE')
    if any(old[offset(0x39b000):offset(sy['NbProbeEnd'])]):raise ValueError('PRESSURE_UNIT_NONZERO_LEASE')
    expected=bytearray(old)
    for begin,end in [(0x398000,0x39a000),(0x39a000,sy['NbCodeEnd']),(0x39b000,sy['NbProbeEnd'])]:expected[offset(begin):offset(end)]=compiled[offset(begin):offset(end)]
    if expected!=rom:raise ValueError('PRESSURE_UNIT_UNAUTHORIZED_ROM_CHANGE')
    return dict(status='PASS',diagnostic_only=True,queue_backup=[0x3500,0x3658],temporary_ref_table=[0x42d4a8,0x42d600],temporary_header_flag=0x42d61e,restored_before_cold_production=True)

def build(folder):
    n=folder/'native';n.mkdir(parents=True,exist_ok=True);lines=transform((BASE/'publisher.pasm').read_text().splitlines());(n/'publisher.pasm').write_text('\n'.join(lines)+'\n')
    p=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(n/'publisher.pasm'),'--output',str(n/'publisher.bin'),'--symbols',str(n/'publisher.sym'),'--no-pansy'],capture_output=True,text=True);(n/'publisher-build.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise ValueError('PRESSURE_UNIT_POPPY')
    rom=bytearray((BASE/'bor.sfc').read_bytes());rom[57*32768:58*32768]=(n/'publisher.bin').read_bytes()[57*32768:58*32768].ljust(32768,b'\0');audit(rom,n);(n/'bor.sfc').write_bytes(rom)
    c=json.loads((BASE.parent/'contract.json').read_text());sy=symbols(n/'publisher.sym');c['native_symbols']={k:v for k,v in sy.items() if k.startswith(('Nb','Online','Astra','Warm','Capacity','Spill'))};(folder/'contract.json').write_text(json.dumps(c,indent=2)+'\n');shutil.copyfile(BASE/'callback_owner.lua',n/'callback_owner.lua')
    if not (n/'bor.msu').exists():os.link(BASE/'bor.msu',n/'bor.msu')

def observer(script,contract):
    candidate.observer(script,contract);sy=contract['native_symbols']
    with script.open('a') as f:
        def cb(name,body):f.write(f'emu.addMemoryCallback(function(){body} end,emu.callbackType.exec,{sy[name]},{sy[name]},emu.cpuType.snes,emu.memType.snesMemory)\n')
        f.write('local probeRefs=nil;local probeLive=false\n')
        cb('NbProbeStart',"probeLive=true;probeRefs={};for i=0,343 do probeRefs[#probeRefs+1]=emu.read(0x42d4a8+i,emu.memType.snesMemory)end")
        for free in (128,129,124,134):
            cb(f'NbProbeReturn{free}',"cgRunning=false;for i=0x480,0x6df do if emu.read(i,emu.memType.sa1InternalRam)~=cgStorage[i-0x480+1]then nbLog('FAULT','PROBE_GATE_STORAGE')end end;nbLog('GATE_UNIT',"+str(free)+" ..'|'..nbWord(0x3470)..'|'..cgReads..'|'..(emu.getState()['masterClock']-cgStart))")
            cb(f'NbProbeChoice{free}',f"nbLog('GATE_CHOICE','{free}|'..nbWord(0x3472))")
        for free in (128,129,124,134):
            cb(f'NbProbePredictionReturned{free}',f"ecRunning=false;nbLog('GATE_PREDICTOR','{free}|'..nbWord(0x3470))")
        for name in ('NbProbeFallbackReturned','NbProbeSecondReturned'):
            cb(name,f"nbLog('GATE_FALLBACK','{name}|'..nbWord(0x3472)..'|'..nbWord(0x42d674))")
        for cpu in ('snes','sa1'):
            for memory,begin,end in [('sa1InternalRam',0x500,0x657),('snesSaveRam',0x2d4a8,0x2d5ff)]:
                f.write("emu.addMemoryCallback(function(a,v)if probeLive then local s=emu.getState();local pc=s['cpu.pc']+65536*s['cpu.k'];if '"+cpu+"'~='snes' or pc<"+str(sy['NbProbeStart'])+" or pc>="+str(sy['NbProbeEnd'])+" then nbLog('FAULT','PROBE_MEMORY_OWNER:"+cpu+"|'..a)end end end,emu.callbackType.write,"+str(begin)+","+str(end)+",emu.cpuType."+cpu+",emu.memType."+memory+")\n")
        cb('NbProbeRestored',"probeLive=false;for i=0,343 do if emu.read(0x42d4a8+i,emu.memType.snesMemory)~=probeRefs[i+1]then nbLog('FAULT','PROBE_REF_RESTORE')end end;nbLog('GATE_RESTORED','344')")

def run(folder,source,sy,contract,fault_mode=1):
    original=batch.observer
    def wrapped(script,c):
        with patch.object(batch,'observer',original):observer(script,c)
    with patch.object(batch,'audit_rom',audit),patch.object(batch,'observer',wrapped):batch.run(folder,source,sy,contract,fault_mode)
    result=certify(folder);(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')

def certify(folder):
    text=(folder/'native/mesen.log').read_text(errors='replace');records=[]
    for line in text.splitlines():
        if 'NB_GATE_' in line:records.append(line[line.index('NB_GATE_'):].split('|'))
    units=[r for r in records if r[0]=='NB_GATE_UNIT'];choices=[r for r in records if r[0]=='NB_GATE_CHOICE'];fallback=[r for r in records if r[0]=='NB_GATE_FALLBACK']
    if len(units)!=4 or len(choices)!=4 or len(fallback)!=2 or not any(r[0]=='NB_GATE_RESTORED' for r in records):raise ValueError('PRESSURE_UNIT_INCOMPLETE')
    predictions=[r for r in records if r[0]=='NB_GATE_PREDICTOR']
    if [int(r[4]) for r in predictions]!=[128,124]:raise ValueError('PRESSURE_UNIT_FULL_PREDICTION_DECISIONS')
    for r in units:
        free,count,reads,clocks=map(int,r[4:])
        if count!=min(129,free) or reads!=(344 if free<=128 else 258):raise ValueError('PRESSURE_UNIT_BOUNDARY')
    for r in choices:
        free,run_prediction=map(int,r[4:])
        if run_prediction!=int(free<=128):raise ValueError('PRESSURE_UNIT_CARRY')
    if any(r[5:]!=['134','1'] for r in fallback):raise ValueError('PRESSURE_UNIT_FALLBACK_NOT_REAL_EXHAUSTION')
    r=json.loads((folder/'result.json').read_text());r['classification']='CONDITIONAL_PRESSURE_NATIVE_UNIT_PASS';r['capacity_admission']='Cold native instruction probe only; real source-owned rescue verified separately.';r['native_unit_events']=records;r['native_gate_boundaries_verified']=[124,128,129,134];r['false_negative_134_free_safe_retry_and_second_exhaustion']=True;return r

if __name__=='__main__':
    import argparse
    from compiler import Source
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--build-only',action='store_true');a=p.parse_args();folder=a.output.resolve();build(folder)
    if not a.build_only:run(folder,Source(Path('Masters of the Universe [v.3.0 Build 4086].pak')),symbols(Path('src/main.sym')),json.loads((folder/'contract.json').read_text()))
