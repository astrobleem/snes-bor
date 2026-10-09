"""Bind ordered model transition service 5 to checked method-0 scripts/factors.

No new control storage. The caller must have installed the new model and
restored the old entity type. Other transition services remain separate owners.
"""
import re
from source_script_model_copy_native import emit as script_copy


def emit(symbols, repository=None):
    code='''
ModelScriptsService_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceModelTransition4086_Ready
 cmp #$B4F0
 bne ModelScriptsService_Bad
 lda.l SourceModelTransition4086_State
 cmp #1
 bne ModelScriptsService_Bad
 lda.l SourceModelTransition4086_Service
 cmp #5
 bne ModelScriptsService_Bad
 lda.l SourceModelTransition4086_Acknowledged
 bne ModelScriptsService_Bad
 lda.l SourceModelTransition4086_Flags
 and #$FFF8
 bne ModelScriptsService_Bad
 lda.l SourceScriptClone4086_Status
 cmp #3
 beq ModelScriptsService_Bad
 lda.l SourceFactors4086_Status
 cmp #3
 beq ModelScriptsService_Bad
 lda.l SourceModelTransition4086_Slot
 cmp.l VmSourceWorld_Count
 bcs ModelScriptsService_Bad
 cmp #128
 bcs ModelScriptsService_Bad
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 clc
 adc #$6800
 cmp.l SourceModelTransition4086_Side
 bne ModelScriptsService_Bad
 tax
 lda.l $410000,x
 cmp.l SourceModelTransition4086_New
 bne ModelScriptsService_Bad
 lda.l SourceModelTransition4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceModelTransition4086_Temp
 asl a
 clc
 adc.l SourceModelTransition4086_Temp
 clc
 adc #$C000
 cmp.l SourceModelTransition4086_Core
 bne ModelScriptsService_Bad
 tax
 lda.l $400048,x
 cmp.l SourceModelTransition4086_OldTypeLo
 bne ModelScriptsService_Bad
 lda.l $40004A,x
 cmp.l SourceModelTransition4086_OldTypeHi
 bne ModelScriptsService_Bad
 lda.l SourceModelTransition4086_Slot
 sta.l SourceScriptClone4086_Slot
 lda.l SourceModelTransition4086_New
 sta.l SourceScriptClone4086_Model
 lda.l SourceModelTransition4086_Flags
 and #4
 beq ModelScriptsService_Copy
 jsl ModelScriptCopy_Clear0
 bcs ModelScriptsService_Bad
ModelScriptsService_Copy:
.a16
.i16
 jsl ModelScriptCopy_Copy0
 bcs ModelScriptsService_Bad
 jsl SourceFactors4086_Apply
 bcs ModelScriptsService_Bad
 lda #5
 sta.l SourceModelTransition4086_Acknowledged
 jsl SourceModelTransition4086_Ack
 bcs ModelScriptsService_Bad
 ply
 plx
 plp
 clc
 rtl
ModelScriptsService_Bad:
.a16
.i16
 lda #3
 sta.l SourceModelTransition4086_State
 ply
 plx
 plp
 sec
 rtl
'''
    serial=[0]
    def relax(m):
        serial[0]+=1
        label='ModelScriptsService_Guard'+str(serial[0])
        return m[1]+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[m[2]]+' '+label+'\n jmp '+m[3]+'\n'+label+':\n.a16\n.i16'
    code=re.sub(r'^(\s+)(beq|bne|bcc|bcs) (ModelScriptsService_\w+)$',relax,code,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith(('Source','Vm')):
            code=re.sub(r'\b'+re.escape(name)+r'\b',str(symbols[name]),code)
    return code+script_copy(symbols,repository)
