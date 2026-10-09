"""Finish model transitions under the checked animation-only B5SC capability.

B5SC compilation rejects onmodelcopy and every other non-animation script
kind. An entity constructed/copied exclusively under that lease has no model
copy callback to execute or snapshot to release. No other service is admitted.
"""
import re


def emit(symbols):
    code='''
ModelCallbackService_FinishAbsent:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceModelTransition4086_Ready
 cmp #$B4F0
 bne ModelCallbackService_Bad
 lda.l SourceModelTransition4086_State
 cmp #1
 bne ModelCallbackService_Bad
 lda.l SourceModelTransition4086_Service
 cmp #7
 bne ModelCallbackService_Bad
 lda.l SourceModelTransition4086_Acknowledged
 bne ModelCallbackService_Bad
 lda.l SourceScriptClone4086_Status
 cmp #2
 bne ModelCallbackService_Bad
 lda.l SourceModelTransition4086_Slot
 cmp.l SourceScriptClone4086_Slot
 bne ModelCallbackService_Bad
 lda.l SourceModelTransition4086_New
 cmp.l SourceScriptClone4086_Model
 bne ModelCallbackService_Bad
 jsl SourceScriptClone4086_CheckModelProgram
 bcs ModelCallbackService_Bad
 lda.l SourceScriptClone4086_Relation
 clc
 adc #$6800
 cmp.l SourceModelTransition4086_Side
 bne ModelCallbackService_Bad
 tax
 lda.l $410000,x
 cmp.l SourceModelTransition4086_New
 bne ModelCallbackService_Bad
 lda.l SourceScriptClone4086_Relation
 tax
 lda.l $40902C,x
 cmp #2
 bcs ModelCallbackService_Bad
 lda.l $40902E,x
 ora.l $409030,x
 ora.l $409032,x
 ora.l $409034,x
 ora.l $409036,x
 bne ModelCallbackService_Bad
 lda.l SourceScriptClone4086_Relation
 lsr a
 clc
 adc.l SourceScriptClone4086_Relation
 clc
 adc #$C000
 cmp.l SourceModelTransition4086_Core
 bne ModelCallbackService_Bad
 tax
 lda.l $400048,x
 cmp.l SourceModelTransition4086_OldTypeLo
 bne ModelCallbackService_Bad
 lda.l $40004A,x
 cmp.l SourceModelTransition4086_OldTypeHi
 bne ModelCallbackService_Bad
 lda #7
 sta.l SourceModelTransition4086_Acknowledged
 jsl SourceModelTransition4086_Ack
 bcs ModelCallbackService_Bad
 ply
 plx
 plp
 clc
 rtl
ModelCallbackService_Bad:
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
        serial[0]+=1;label='ModelCallbackService_Guard'+str(serial[0])
        return m[1]+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[m[2]]+' '+label+'\n jmp '+m[3]+'\n'+label+':\n.a16\n.i16'
    code=re.sub(r'^(\s+)(beq|bne|bcc|bcs) (ModelCallbackService_\w+)$',relax,code,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith(('Source','Vm')):code=re.sub(r'\b'+re.escape(name)+r'\b',str(symbols[name]),code)
    return code
