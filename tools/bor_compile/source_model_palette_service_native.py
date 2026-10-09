"""Source-derived map identities for ordered model-transition colour service 6.

Identity publication is separate from CGRAM/CHR admission. SOURCE_PER_FRAME
retains the model identity so the renderer can resolve its frame palette.
"""
import re
import struct
from source_profile import discover,document
from compiler import key
from source_palette import model_palettes
from dialect_4086 import ENGINE_COMMIT


def derive(source):
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    structure=discover(source,docs)
    models=[]
    for i,m in enumerate(structure['models']):
        p=model_palettes(source,m)
        if len(p['alternates'])>65535:raise ValueError('MODEL_PALETTE_MAP_CAPACITY')
        if m['properties'].get('remap') or m['properties'].get('globalmap'):
            raise ValueError('MODEL_PALETTE_REMAP_BACKEND_REQUIRED')
        models.append(dict(id=i,identity=m['declaration'],source_sha256=docs[key(m['source_path'])]['sha256'],maps_loaded=len(p['alternates']),palettes=p))
    if not 1<=len(models)<=16:raise ValueError('MODEL_PALETTE_MODEL_CAPACITY')
    return dict(schema='BYOR_4086_MODEL_PALETTE_IDENTITY_V1',engine_commit=ENGINE_COMMIT,models=models,
                pixel_policy='RGB8_HIGH_BITS_TO_RGB555; source index zero transparent; no color-count reduction',
                cgram_admission_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)


def pack(report):
    """B5MP model directory plus exact 256-entry RGB555 palette vectors."""
    models=report['models'];directory=bytearray();body=bytearray()
    if not 1<=len(models)<=16:raise ValueError('MODEL_PALETTE_MODEL_CAPACITY')
    start=16+8*len(models)
    for i,m in enumerate(models):
        p=m['palettes']
        if m['id']!=i or m['maps_loaded']!=len(p['alternates']):
            raise ValueError('MODEL_PALETTE_IDENTITY_DIRECTORY')
        if p['policy']=='SOURCE_PER_FRAME':
            if p['base']is not None or p['alternates']:raise ValueError('MODEL_PALETTE_PER_FRAME_DOMAIN')
            directory.extend(struct.pack('<4H',i,0,65535,1))
        elif p['policy']=='SOURCE_MODEL_INDEXED':
            offset=start+len(body)
            directory.extend(struct.pack('<4H',i,m['maps_loaded'],offset,0))
            for palette in [p['base'],*p['alternates']]:
                values=palette['rgb555']
                if len(values)!=256 or values[0]!=0 or any(not 0<=v<=32767 for v in values):
                    raise ValueError('MODEL_PALETTE_RGB555_DOMAIN')
                body.extend(struct.pack('<256H',*values))
        else:raise ValueError('MODEL_PALETTE_POLICY_UNBOUND')
    if start+len(body)>65535:raise ValueError('MODEL_PALETTE_TABLE_CAPACITY')
    return struct.pack('<4s6H',b'B5MP',1,len(models),8,16,512,0)+directory+body


def emit(report,symbols):
    count=len(report['models'])
    if not 1<=count<=16 or [m['id']for m in report['models']]!=list(range(count)):
        raise ValueError('MODEL_PALETTE_IDENTITY_DIRECTORY')
    code='''
ModelPaletteService_Apply6:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceModelTransition4086_Ready
 cmp #$B4F0
 bne ModelPaletteService_Bad
 lda.l SourceModelTransition4086_State
 cmp #1
 bne ModelPaletteService_Bad
 lda.l SourceModelTransition4086_Service
 cmp #6
 bne ModelPaletteService_Bad
 lda.l SourceModelTransition4086_Acknowledged
 bne ModelPaletteService_Bad
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne ModelPaletteService_Bad
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 bne ModelPaletteService_Bad
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 bne ModelPaletteService_Bad
 lda.l VmSourceWorld_TemplateCount
 cmp #COUNT
 bne ModelPaletteService_Bad
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 bne ModelPaletteService_Bad
 lda.l SourceModelEntityCopy4086_Models
 cmp #COUNT
 bne ModelPaletteService_Bad
 lda.l SourceCtorState4086_Ready
 cmp #$B5C2
 bne ModelPaletteService_Bad
 lda.l SourceCtorState4086_Models
 cmp #COUNT
 bne ModelPaletteService_Bad
 lda.l VmSourceWorld_Count
 beq ModelPaletteService_Bad
 cmp #129
 bcs ModelPaletteService_Bad
 cmp.l SourceModelEntityCopy4086_Entities
 bne ModelPaletteService_Bad
 lda.l SourceModelTransition4086_Slot
 cmp.l VmSourceWorld_Count
 bcs ModelPaletteService_Bad
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
 bne ModelPaletteService_Bad
 tax
 lda.l $410000,x
 cmp.l SourceModelTransition4086_New
 bne ModelPaletteService_Bad
 cmp #COUNT
 bcs ModelPaletteService_Bad
 lda.l SourceModelTransition4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceModelTransition4086_Temp
 tya
 clc
 adc.l SourceModelTransition4086_Temp
 clc
 adc #$4000
 tax
 cmp.l $410000,x
 bne ModelPaletteService_Bad
 lda.l $410002,x
 cmp #$41
 bne ModelPaletteService_Bad
 tya
 lsr a
 clc
 adc.l SourceModelTransition4086_Side
 clc
 adc #$5800
 cmp.l SourceModelTransition4086_Core
 bne ModelPaletteService_Bad
 tax
 lda.l $400048,x
 cmp.l SourceModelTransition4086_OldTypeLo
 bne ModelPaletteService_Bad
 lda.l $40004A,x
 cmp.l SourceModelTransition4086_OldTypeHi
 bne ModelPaletteService_Bad
 lda.l SourceModelTransition4086_New
 asl a
 tax
 lda.l ModelPaletteService_Maps,x
 pha
 tya
 tax
 lda.l $43383E,x
 cmp #$B5C2
 bne ModelPaletteService_RowBad
 lda.l $433832,x
 cmp #COUNT
 bcs ModelPaletteService_RowBad
 pla
 cmp.l $433830,x
 bcs ModelPaletteService_MapValid
 lda #0
 sta.l $433830,x
ModelPaletteService_MapValid:
.a16
.i16
 lda.l SourceModelTransition4086_New
 sta.l $433832,x
 lda #6
 sta.l SourceModelTransition4086_Acknowledged
 jsl SourceModelTransition4086_Ack
 bcs ModelPaletteService_Bad
 ply
 plx
 plp
 clc
 rtl
ModelPaletteService_RowBad:
.a16
.i16
 pla
ModelPaletteService_Bad:
.a16
.i16
 lda #3
 sta.l SourceModelTransition4086_State
 ply
 plx
 plp
 sec
 rtl
ModelPaletteService_Maps:
'''.replace('COUNT',str(count))
    code+=' .dw '+','.join(str(m['maps_loaded'])for m in report['models'])+'\n'
    serial=[0]
    def relax(m):
        serial[0]+=1;label='ModelPaletteService_Guard'+str(serial[0])
        return m[1]+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[m[2]]+' '+label+'\n jmp '+m[3]+'\n'+label+':\n.a16\n.i16'
    code=re.sub(r'^(\s+)(beq|bne|bcc|bcs) (ModelPaletteService_\w+)$',relax,code,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith(('Source','Vm')):code=re.sub(r'\b'+re.escape(name)+r'\b',str(symbols[name]),code)
    return code
