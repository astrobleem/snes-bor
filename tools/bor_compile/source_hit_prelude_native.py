"""Checked empty ondoattack events and source ownership rejection.

Hit controls +36..43 reuse completed gate/identity scratch for suspended
old self, didhit and B6A7. Gate/identity may not reenter while pending. Accepted
targets leave global self on the defender and demand a real hit-body owner.
No externally supplied response or world acknowledgement API exists.
"""
from source_hit_contact_layout import layout
from source_hit_state_layout import layout as hits
HIT_RESPONSE_REQUIRED = 0x8112


def emit(requirements, plan, sy, script_bank=59, script_bytes=152):
    if plan != layout(plan['entities']) or requirements['capability'] != 'SOURCE_EMPTY_ONDOATTACK_ZERO_GROUND':
        raise ValueError('HIT_PRELUDE_NATIVE_REQUIREMENTS')
    w = plan['controls']; h = hits(plan['entities'])['controls']; lines=[];serial=0;size=48
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('HitPrelude_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1; l='HitPrelude_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {l}\n jmp HitPrelude_{n}\n{l}:\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    def offset(src, stride, dst):
        put(f' lda ${src:02X}')
        if stride==64:put(' asl a\n asl a\n asl a\n asl a\n asl a\n asl a')
        else:raise ValueError('HIT_PRELUDE_OFFSET')
        put(f' sta ${dst:02X}')
    label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $28\n sty $2A')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs')
    for at,v in ((w,0xb6a3),(w+52,0xb6a4),(w+60,2),(h,0xb6a0),(h+60,1),(h+62,0),
                 (sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),
                 (sy['SourceWorldTick4086_Phase'],8),(sy['SourceWorldTick4086_Pending'],1),(sy['SourceWorldTick4086_Fault'],0),
                 (sy['SourceRetirement4086_Ready'],0xb4f8),
                 (sy['SourceSelf4086_Ready'],0xb4f6),(sy['SourceSelf4086_Fault'],0),(sy['SourceSelf4086_Active'],0),
                 (sy['SourceScriptClone4086_Ready'],0xb5c1),(sy['SourceScriptClone4086_Base'],0x8000),
                 (sy['SourceScriptClone4086_Bank'],script_bank),(sy['SourceScriptClone4086_Bytes'],script_bytes),
                 (sy['SourceScriptClone4086_Models'],len(requirements['models']))):require(at,v)
    for op,off in (('txa',8),('tya',10)):
        put(f' {op}\n cmp.l {w}+{off}');branch('bne');put(f' cmp.l {h}+{off}');branch('bne')
    for off in (0,2):
        put(f' lda.l {sy["SourceWorldTick4086_TimeLo"]}+{off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
    put(f' lda.l {h}+4\n cmp.l {sy["SourceWorldTick4086_Slot"]}');branch('bne');put(' sta $00')
    put(f' lda.l {w}+58\n cmp.l {w}+56');branch('bne');put(f' cmp.l {h}+26');branch('bne');put(' sta $02')
    for src in (0,2):
        put(f' lda ${src:02X}\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs')
    # Validate current old-self pointer before any source-global publication.
    for off,n in ((0,'Low'),(2,'High')):
        put(f' lda.l {sy["SourceSelf4086_Global"+n]}\n sta ${8+off:02X}\n sta.l {sy["SourceRetirement4086_Arg"+("Lo" if off==0 else "Hi")]}')
    put(f' jsl {sy["SourceRetirement4086_ResolvePointer"]}');branch('bcs')
    put(' cmp #$FFFF');branch('beq')
    put(' lda $08\n tax\n cmp.l $410000,x');branch('bne');put(' lda $0A\n cmp.l $410002,x');branch('bne')
    # Every relevant live entity must retain the closed animation-only mask and
    # its actual model's immutable program pairing. No fabricated callback.
    for src in (0,2):
        offset(src,64,4);put(f' tax\n lda.l $40902C,x\n and #$FFFE');branch('bne')
        for off in (46,48,50,52,54):put(f' lda.l $409000+{off},x');branch('bne')
        put(f' lda ${src:02X}\n sta.l {sy["SourceScriptClone4086_Slot"]}\n lda.l $416800,x\n sta.l {sy["SourceScriptClone4086_Model"]}\n jsl {sy["SourceScriptClone4086_CheckModelProgram"]}');branch('bcs')
        put(f' lda $04\n tax\n lda.l $40902C,x\n cmp.l {sy["SourceScriptClone4086_Mask"]}');branch('bne')
    # Target top owner uses actual aligned token resolver, including dead owners.
    put(' lda $02\n sta $0C\n lda #0\n sta $0E')
    label('OwnerLoop');put(f' inc $0E\n lda $0E\n cmp #{plan["entities"]+1}');branch('bcs')
    offset(12,64,4);put(' tax\n lda.l $40903A,x\n cmp #$B638');branch('bne')
    put(' lda.l $409008,x\n sta $10\n lda.l $40900A,x\n sta $12\n ora $10');branch('beq','OwnerDone')
    for off,n in ((0,'Lo'),(2,'Hi')):put(f' lda ${16+off:02X}\n sta.l {sy["SourceRetirement4086_Arg"+n]}')
    put(f' jsl {sy["SourceRetirement4086_ResolvePointer"]}');branch('bcs');put(' cmp #$FFFF');branch('beq');put(' sta $0C\n jmp HitPrelude_OwnerLoop')
    label('OwnerDone');put(f' lda $0C\n cmp.l {w}+54');branch('beq','Rejected')
    offset(0,64,4);put(' tax\n lda.l $409008,x\n ora.l $40900A,x');branch('beq','Accepted')
    offset(2,64,4);put(' tax\n lda.l $409008,x\n ora.l $40900A,x');branch('bne','Rejected')
    label('Accepted')
    # Both empty dispatchers return without touching global self or contact.
    # The next real owner resumes at if(didhit), with self still the defender.
    for off in (0,2):put(f' lda ${8+off:02X}\n sta.l {h}+{36+off}')
    put(f' lda #1\n sta.l {h}+40\n lda #$B6A7\n sta.l {h}+42')
    put(' lda $02\n asl a\n asl a\n asl a\n asl a\n sta $04\n asl a\n asl a\n clc\n adc $04\n adc #$4000')
    put(f' sta.l {sy["SourceSelf4086_GlobalLow"]}\n lda #$41\n sta.l {sy["SourceSelf4086_GlobalHigh"]}\n lda #{HIT_RESPONSE_REQUIRED}\n jmp HitPrelude_Good')
    label('Rejected');put(f' lda #0\n sta.l {h}+40\n sta.l {h}+42\n jmp HitPrelude_Good')
    label('Good');put(f' tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' tsc\n clc\n adc #{size}\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
