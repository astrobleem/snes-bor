"""Remaining model alpha/combostyle installation without resetting dynamics.

Service 2 requires the completed real entity copier and a caller-supplied
X/Y canvas generation. Existing birth rows and controller arena are reused.
"""
import re
from source_ctor_state import derive as ctor
from source_attack_body_profile import derive as attack_body


def derive(source):
    cr=ctor(source);ar=attack_body(source);models=[]
    for c,a in zip(cr['models'],ar['models']):
        if(c['id'],c['identity'],c['source_sha256'])!=(a['index'],a['identity'],a['source_sha256']):
            raise ValueError('MODEL_SCALAR_SOURCE_PAIR')
        models.append(dict(id=c['id'],identity=c['identity'],source_sha256=c['source_sha256'],alpha=c['alpha'],combostyle=a['fields']['combostyle']))
    if len(models)!=len(cr['models'])or len(models)!=len(ar['models']):raise ValueError('MODEL_SCALAR_SOURCE_COUNT')
    return dict(schema='BYOR_4086_MODEL_ALPHA_COMBOSTYLE_V1',models=models,
                source_policy='set_model_ex shallow copies modeldata.alpha and modeldata.combostyle; entity lifetime/name/dynamics are retained',
                renderer_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)


def emit(report,styles,symbols):
    from source_foreign_state_layout import layout
    arena=layout(symbols['SOURCE_FOREIGN_WORK_BASE'],symbols['SOURCE_FOREIGN_WORK_BYTES'])
    if styles!=next(r['address']for r in arena['regions']if r['name']=='entity_combostyle'):
        raise ValueError('MODEL_SCALAR_STYLE_ARENA')
    count=len(report['models'])
    if not 1<=count<=16 or [m['id']for m in report['models']]!=list(range(count)):
        raise ValueError('MODEL_SCALAR_DIRECTORY')
    code='''
ModelScalarService_Apply2:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceForeignWork_Check
 bcs ModelScalarService_Bad
 lda.l SourceModelTransition4086_Ready
 cmp #$B4F0
 bne ModelScalarService_Bad
 lda.l SourceModelTransition4086_State
 cmp #1
 bne ModelScalarService_Bad
 lda.l SourceModelTransition4086_Service
 cmp #2
 bne ModelScalarService_Bad
 lda.l SourceModelTransition4086_Acknowledged
 bne ModelScalarService_Bad
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 bne ModelScalarService_Bad
 lda.l SourceModelEntityCopy4086_Status
 cmp #1
 bne ModelScalarService_Bad
 lda.l SourceModelEntityCopy4086_Models
 cmp #COUNT
 bne ModelScalarService_Bad
 lda.l SourceCtorState4086_Ready
 cmp #$B5C2
 bne ModelScalarService_Bad
 lda.l SourceCtorState4086_Models
 cmp #COUNT
 bne ModelScalarService_Bad
 lda.l SourceModelTransition4086_New
 cmp #COUNT
 bcs ModelScalarService_Bad
 cmp.l SourceModelEntityCopy4086_Model
 bne ModelScalarService_Bad
 lda.l SourceModelTransition4086_Slot
 cmp.l SourceModelEntityCopy4086_Slot
 bne ModelScalarService_Bad
 cmp #128
 bcs ModelScalarService_Bad
 cmp.l VmSourceWorld_Count
 bcs ModelScalarService_Bad
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne ModelScalarService_Bad
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 bne ModelScalarService_Bad
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 bne ModelScalarService_Bad
 lda.l VmSourceWorld_Count
 beq ModelScalarService_Bad
 cmp #129
 bcs ModelScalarService_Bad
 cmp.l SourceModelEntityCopy4086_Entities
 bne ModelScalarService_Bad
 lda.l VmSourceWorld_TemplateCount
 cmp #COUNT
 bne ModelScalarService_Bad
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
 bne ModelScalarService_Bad
 cmp.l SourceModelEntityCopy4086_Entity
 bne ModelScalarService_Bad
 lda.l SourceModelTransition4086_Temp
 lsr a
 sta.l SourceModelTransition4086_Temp
 asl a
 asl a
 clc
 adc.l SourceModelTransition4086_Temp
 clc
 adc #$4000
 cmp.l SourceModelEntityCopy4086_View
 bne ModelScalarService_Bad
 tax
 cmp.l $410000,x
 bne ModelScalarService_Bad
 lda.l $410002,x
 cmp #$41
 bne ModelScalarService_Bad
 lda.l SourceModelTransition4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tay
 clc
 adc #$6800
 cmp.l SourceModelTransition4086_Side
 bne ModelScalarService_Bad
 tax
 lda.l $410000,x
 cmp.l SourceModelTransition4086_New
 bne ModelScalarService_Bad
 tya
 tax
 lda.l $43383E,x
 cmp #$B5C2
 bne ModelScalarService_Bad
 lda.l SourceModelTransition4086_New
 asl a
 tax
 lda.l ModelScalarService_Alpha,x
 pha
 lda.l SourceModelTransition4086_Side
 tax
 pla
 sta.l $41001E,x
 lda.l SourceModelTransition4086_New
 asl a
 asl a
 tax
 lda.l ModelScalarService_Styles,x
 pha
 lda.l ModelScalarService_Styles+2,x
 pha
 lda.l SourceModelTransition4086_Slot
 asl a
 asl a
 tax
 pla
 sta.l STYLES+2,x
 pla
 sta.l STYLES,x
 lda #2
 sta.l SourceModelTransition4086_Acknowledged
 jsl SourceModelTransition4086_Ack
 bcs ModelScalarService_Bad
 ply
 plx
 plp
 clc
 rtl
ModelScalarService_Bad:
.a16
.i16
 lda #3
 sta.l SourceModelTransition4086_State
 ply
 plx
 plp
 sec
 rtl
ModelScalarService_Alpha:
'''.replace('COUNT',str(count)).replace('STYLES',str(styles))
    if any(not 0<=m['alpha']<=6 or not -2147483648<=m['combostyle']<=2147483647 for m in report['models']):
        raise ValueError('MODEL_SCALAR_DOMAIN')
    code+=' .dw '+','.join(str(m['alpha'])for m in report['models'])+'\nModelScalarService_Styles:\n .dw '+','.join(str(v)for m in report['models']for v in(m['combostyle']&65535,(m['combostyle']>>16)&65535))+'\n'
    serial=[0]
    def relax(m):
        serial[0]+=1;label='ModelScalarService_Guard'+str(serial[0])
        return m[1]+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[m[2]]+' '+label+'\n jmp '+m[3]+'\n'+label+':\n.a16\n.i16'
    code=re.sub(r'^(\s+)(beq|bne|bcc|bcs) (ModelScalarService_\w+)$',relax,code,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith(('Source','Vm')):code=re.sub(r'\b'+re.escape(name)+r'\b',str(symbols[name]),code)
    return code
