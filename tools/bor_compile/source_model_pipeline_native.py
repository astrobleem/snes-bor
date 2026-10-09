"""Native continuation for admitted synchronized source model transitions.

X/Y carry the independent expected 32-bit canvas generation. Service 4
requires a nested frame owner and rejects here. This emitter owns no table
installation, frame dispatch, entity birth, or presentation publication.
"""
import re


def emit(symbols):
    assembly="""ModelPipeline_Resume:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceModelTransition4086_Ready
 cmp #$B4F0
 bne ModelPipeline_Bad
ModelPipeline_Loop:
.a16
.i16
 lda.l SourceModelTransition4086_State
 cmp #2
 beq ModelPipeline_Done
 cmp #1
 bne ModelPipeline_Bad
 lda.l SourceModelTransition4086_Service
 cmp #1
 beq ModelPipeline_Snapshot
 cmp #2
 beq ModelPipeline_Scalars
 cmp #3
 beq ModelPipeline_FirstMap
 cmp #5
 beq ModelPipeline_Scripts
 cmp #6
 beq ModelPipeline_LastMap
 cmp #7
 beq ModelPipeline_Callback
 jmp ModelPipeline_Bad
ModelPipeline_Snapshot:
.a16
.i16
 jsl ModelSnapshotService_BeginAbsent
 bra ModelPipeline_After
ModelPipeline_Scalars:
.a16
.i16
 lda 3,s
 tax
 lda 1,s
 tay
 jsl ModelScalarService_Apply2
 bra ModelPipeline_After
ModelPipeline_FirstMap:
.a16
.i16
 jsl ModelPaletteService3_Apply3
 bra ModelPipeline_After
ModelPipeline_Scripts:
.a16
.i16
 jsl ModelScriptsService_Apply
 bra ModelPipeline_After
ModelPipeline_LastMap:
.a16
.i16
 jsl ModelPaletteService_Apply6
 bra ModelPipeline_After
ModelPipeline_Callback:
.a16
.i16
 jsl ModelCallbackService_FinishAbsent
ModelPipeline_After:
.a16
.i16
 bcs ModelPipeline_Bad
 jmp ModelPipeline_Loop
ModelPipeline_Done:
.a16
.i16
 lda.l SourceModelTransition4086_Service
 bne ModelPipeline_Bad
 ply
 plx
 plp
 clc
 rtl
ModelPipeline_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
"""
    serial=[0]
    def relax(match):
        serial[0]+=1;label='ModelPipeline_Guard'+str(serial[0])
        return ' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[match[1]]+' '+label+'\n jmp '+match[2]+'\n'+label+':\n.a16\n.i16'
    assembly=re.sub(r'^ (beq|bne|bcc|bcs) (ModelPipeline_\w+)$',relax,assembly,flags=re.M)
    assembly=re.sub(r'^ bra (ModelPipeline_\w+)$',r' jmp \1',assembly,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith('Source'):assembly=re.sub(r'\b'+name+r'\b',str(symbols[name]),assembly)
    return assembly
