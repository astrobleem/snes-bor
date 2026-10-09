"""Ordered source jump input branch through actual tryjump/JUMPDELAY owner.

Readonly jump fields are compiled per model, including the binary32 running
product. Nonzero jumpmovez and alternate jump/slide roles require other owners.
"""
import struct
from source_model_core_4086 import binary32
from source_player_run_4086 import KEYS


def emit(work, pending, tryjump, history, input_owner, input_magic, profile, roles, symbols, code_bank):
    if not 1 <= code_bank <= 0x7d:
        raise ValueError('PLAYER_JUMP_ENTRY_ROM_BANK')
    count = len(profile['models'])
    if profile.get('capability') != 'READONLY_ABSENT_SLIDE_AND_ALTERNATE_JUMP' or not 1 <= count <= 16:
        raise ValueError('PLAYER_JUMP_ENTRY_CAPABILITY')
    for i, model in enumerate(profile['models']):
        if model['id'] != i or model['fields']['jumpmovez'] != 0:
            raise ValueError('PLAYER_JUMP_ENTRY_ZERO_JUMPMOVEZ_REQUIRED')
    spans=((work,32),(pending,64),(tryjump,64),(history,1024),(input_owner,2))
    for i,(a,n) in enumerate(spans):
        if not 0 <= a <= 0x1000000-n or any(a<b+m and b<a+n for b,m in spans[i+1:]):
            raise ValueError('PLAYER_JUMP_ENTRY_LAYOUT')
    if history & 255 or not 1 <= input_magic <= 65535:
        raise ValueError('PLAYER_JUMP_ENTRY_INPUT')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerJumpEntry_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PlayerJumpEntry_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PlayerJumpEntry_'+n+'\n'+skip+':\n.a16\n.i16')
    def entry(n):label(n);put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B694');branch('bne')
    def offset(dest,stride):
        put(' lda #0')
        for bit in range(stride.bit_length()-1,-1,-1):
            put(' asl a')
            if stride&(1<<bit):put(f' clc\n adc.l {work}+4')
        put(f' sta.l {work}+{dest}')
    def resolve(role,suffix=''):
        put(f' lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{roles[role]}\n sta.l {symbols["SourceAnimationInit4086_Number"]}')
        label('Query_'+role+suffix);put(f' jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
    def absent(role,suffix=''):
        resolve(role,suffix);put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','Absent_'+role+suffix)
        put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('bne')
        label('Absent_'+role+suffix)
    def jump(suffix,missing):
        resolve('jump',suffix);put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq',missing)
        put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('beq',missing)
    def held(mask):put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+216,x\n and #{mask}')
    entry('Begin');put(f' lda.l {input_owner}\n cmp #{input_magic}');branch('bne')
    put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('beq','Ready');put(' cmp #4');branch('bne')
    label('Ready');put(f' lda #1\n sta.l {work}+2\n lda.l {work}+6\n cmp #4');branch('bcs')
    put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+224,x\n and #{KEYS["jump"]}');branch('beq','Continue')
    put(f' lda.l {work}+8');branch('beq','Continue')
    put(f' lda.l {history}+224,x\n and #{(~KEYS["jump"])&65535}\n sta.l {history}+224,x')
    put(f' lda.l {symbols["VmSourceWorld_Count"]}');branch('beq');put(' cmp #129');branch('bcs')
    put(f' lda.l {work}+4\n cmp.l {symbols["VmSourceWorld_Count"]}');branch('bcs')
    offset(12,64);offset(14,24);offset(16,80)
    put(f' lda.l {symbols["SourceModelEntityCopy4086_Ready"]}\n cmp #$B4EB');branch('bne')
    put(f' lda.l {symbols["SourceModelEntityCopy4086_Models"]}\n cmp #{count}');branch('bne')
    put(f' lda.l {work}+12\n tax\n lda.l $416800,x\n cmp #{count}');branch('bcs')
    put(f' sta.l {pending}+6\n sta.l {work}+10\n lda.l {work}+4\n sta.l {pending}+4\n jsl PendingJump_Read');branch('bcs')
    put(f' lda.l {work}+16\n tax\n lda.l $414018,x\n cmp #1');branch('bne');put(' lda.l $41401A,x');branch('bne')
    put(f' lda.l {work}+14\n tax\n lda.l $42F404,x\n ora.l $42F406,x');branch('beq','Standing')
    held(KEYS['movedown']);branch('beq','RunSlideDone');absent('runslide');label('RunSlideDone')
    absent('runjump');absent('forwardjump','Running');jump('Running','Return')
    put(f' lda #8\n sta.l {work}+18\n lda #12\n sta.l {work}+20\n jmp PlayerJumpEntry_Try')
    label('Standing');held(KEYS['movedown']);branch('beq','SlideDone');absent('slide');label('SlideDone')
    held(KEYS['moveleft']|KEYS['moveright']);branch('bne','Moving')
    jump('Standing','Moving');put(f' lda #0\n sta.l {work}+18\n lda #$FFFF\n sta.l {work}+20\n jmp PlayerJumpEntry_Try')
    label('Moving');held(KEYS['moveleft']);branch('beq','Right')
    put(f' lda.l {work}+16\n tax\n lda #0\n sta.l $41401C,x\n sta.l $41401E,x\n jmp PlayerJumpEntry_DirectionDone')
    label('Right');held(KEYS['moveright']);branch('beq','DirectionDone')
    put(f' lda.l {work}+16\n tax\n lda #1\n sta.l $41401C,x\n lda #0\n sta.l $41401E,x')
    label('DirectionDone');absent('forwardjump','Moving');jump('Moving','Return')
    put(f' lda #0\n sta.l {work}+18\n lda #4\n sta.l {work}+20')
    label('Try');put(f' lda.l {work}+4\n sta.l {tryjump}+4\n lda #{roles["jump"]}\n sta.l {tryjump}+6\n lda.l {work}+10\n asl a\n asl a\n asl a\n asl a\n clc\n adc.l {work}+18\n tax')
    for at in (0,2):put(f' lda.l PlayerJumpEntry_Fields+{at}+{code_bank<<16},x\n sta.l {tryjump}+{8+at}')
    put(f' lda #0\n sta.l {tryjump}+12\n sta.l {tryjump}+14\n sta.l {tryjump}+16\n sta.l {tryjump}+18\n lda.l {work}+20\n cmp #$FFFF');branch('beq','TryBegin')
    put(f' clc\n lda.l {work}+10\n asl a\n asl a\n asl a\n asl a\n clc\n adc.l {work}+20\n tax')
    for at in (0,2):put(f' lda.l PlayerJumpEntry_Fields+{at}+{code_bank<<16},x\n sta.l {tryjump}+{12+at}')
    label('TryBegin');put(' jsl TryJump_Begin');branch('bcs')
    label('TryResult');put(f' lda.l {tryjump}+2\n cmp #4');branch('beq','Return');put(' cmp #5');branch('beq','DoRequired');put(' cmp #3');branch('bne')
    put(f' lda #3\n sta.l {work}+2\n lda #$8001\n jmp PlayerJumpEntry_Exit')
    entry('FinishFrame');put(f' lda.l {work}+2\n cmp #3');branch('bne')
    put(f' lda.l {tryjump}+4\n cmp.l {work}+4');branch('bne')
    put(f' lda.l {tryjump}+6\n cmp #{roles["jump"]}');branch('bne')
    put(' jsl TryJump_FinishFrame');branch('bcs');put(' jmp PlayerJumpEntry_TryResult')
    label('Continue');put(f' lda #2\n sta.l {work}+2\n lda #1\n jmp PlayerJumpEntry_Exit')
    label('DoRequired');put(f' lda #5\n sta.l {work}+2\n lda #$8002\n jmp PlayerJumpEntry_Exit')
    label('Return');put(f' lda #4\n sta.l {work}+2\n lda #0')
    label('Exit');put(' ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #6\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    label('Fields')
    for model in profile['models']:
        f=model['fields'];values=(f['jumpheight'],f['jumpspeed'],f['runjumpheight'],binary32(f['jumpspeed']*f['runjumpdist']))
        raw=struct.pack('<4f',*values);put(' .word '+','.join(str(v) for v in struct.unpack('<8H',raw)))
    return '\n'.join(lines)+'\n'
