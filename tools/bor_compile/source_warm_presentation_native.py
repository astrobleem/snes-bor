"""Opt-in warm presentation of coherent, naturally committed source snapshots.

The accepted publisher is copied to a checked empty bank. Its pair staging,
capacity fallback, atomic map publication and reference collector stay intact.
Only the pose front end and lossless indexed-row provider change. Cooperative
tick calls are made outside DMA/map/collector transactions, on the same stack.
"""
from __future__ import annotations

import re

from source_warm_presentation_assets import CONTROL, RENDER_PIN, DISPLAY_PIN, TILE_ROWS

# Full renderer DP, restoration records and all seven staged DMA pairs.
# Three disjoint pieces fit the explicitly leased old SceneVideo staging.
YIELD_GUARDS=((0x003400,0x7e9860,512),(0x003600,0x7e9580,128),(0x003680,0x7e8340,96))


def _relax(text, prefix):
    inverse={'beq':'bne','bne':'beq','bcc':'bcs','bcs':'bcc','bmi':'bpl','bpl':'bmi'}
    serial=0
    def sub(m):
        nonlocal serial
        serial+=1; label=f'{prefix}_Skip{serial}'
        return f' {inverse[m[1]]} {label}\n jmp {m[2]}\n{label}:\n.a16\n.i16'
    return re.sub(r'^ (beq|bne|bcc|bcs|bmi|bpl) ('+prefix+r'\w+)$',sub,text,flags=re.M)


def helper(config, symbols):
    """Bank-43 helper; the world/tile decoder remain separate linked routines."""
    c=CONTROL;p=RENDER_PIN;d=DISPLAY_PIN
    lines=['.snes','.bank 43','.org $8000']
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put(n+':\n.a16\n.i16')
    def store(at,v):put(f' lda #{v}\n sta.l ${at:06X}')
    fields=symbols.get('SourceClock4086_FieldsLo',0x7ffa02)
    def clock_sample(name):
        label(name)
        # Same read/verify contract as SourceClock4086_Observe: foreground
        # cannot execute halfway through NMI; re-reading low detects a carry.
        put(f' lda.l ${fields:06X}\n sta.l ${c+0x116:06X}\n lda.l ${fields+2:06X}\n sta.l ${c+0x118:06X}\n lda.l ${fields:06X}\n cmp.l ${c+0x116:06X}\n bne {name}')
    label('WarmMain')
    # Only reached from LiveWorld_Outer after guarded acquisition, cold image,
    # real constructor and actual audio/clock startup. Never resume old scene.
    put(' rep #$38\n lda #0\n tcd')
    for off in range(16,24,2):store(0x7e7700+off,0)
    put(' ldx #0')
    label('WarmMain_CopyCold')
    put(f' lda.l $7FBA00,x\n sta.l ${d:06X},x\n inx\n inx\n cpx #146\n bcc WarmMain_CopyCold')
    store(d+146,0)
    label('WarmMain_Ready');put(' nop')
    label('WarmMain_Loop')
    put(' jsl LiveTick_Service\n bcs WarmMain_Fault\n jsl WarmTryPublish\n bcs WarmMain_Fault\n jmp WarmMain_Loop')
    label('WarmMain_Fault');store(c+0x100,3)
    label('WarmMain_Stop');put(' wai\n jmp WarmMain_Stop')

    # Service preserves renderer P/A/X/Y/DP/DBR. Its providers use their own
    # declared rows; renderer DP $3400..347F and IRAM stages are not borrowed.
    label('WarmYield')
    put(' php\n rep #$38\n pha\n phx\n phy\n phb\n phd\n lda #0\n tcd\n sep #$20\n.a8\n lda #0\n pha\n plb\n rep #$20\n.a16')
    # Empty scan cells are not time quanta. Service once when real rendering
    # has crossed a new NMI field, then remember the physical counter after
    # that source service. Its own several-field cost must not immediately
    # trigger another service before the renderer gets execution again.
    put(f' lda.l ${c+0x102:06X}\n bne WarmYield_Good')
    clock_sample('WarmYield_ClockBefore')
    put(f' lda.l ${c+0x116:06X}\n cmp.l ${c+0x110:06X}\n bne WarmYield_Due\n lda.l ${c+0x118:06X}\n cmp.l ${c+0x112:06X}\n beq WarmYield_Good')
    label('WarmYield_Due')
    # Runtime alias guard supplements the closed-provider static audit. A
    # changed byte faults and restores the renderer before its rollback path.
    for i,(src,dst,size) in enumerate(YIELD_GUARDS):
        put(' ldx #0');label(f'WarmYield_Save{i}')
        put(f' lda.l ${src:06X},x\n sta.l ${dst:06X},x\n inx\n inx\n cpx #{size}\n bcc WarmYield_Save{i}')
    store(c+0x104,1)
    put(' jsl LiveTick_Service\n bcc WarmYield_Compare')
    store(c+0x102,1)
    label('WarmYield_Compare')
    for i,(src,dst,size) in enumerate(YIELD_GUARDS):
        put(' ldx #0');label(f'WarmYield_Compare{i}')
        put(f' lda.l ${src:06X},x\n cmp.l ${dst:06X},x\n bne WarmYield_AliasFault\n inx\n inx\n cpx #{size}\n bcc WarmYield_Compare{i}')
    put(' jmp WarmYield_GuardDone')
    label('WarmYield_AliasFault')
    store(c+0x102,1);store(c+0x106,1)
    for i,(src,dst,size) in enumerate(YIELD_GUARDS):
        put(' ldx #0');label(f'WarmYield_Restore{i}')
        put(f' lda.l ${dst:06X},x\n sta.l ${src:06X},x\n inx\n inx\n cpx #{size}\n bcc WarmYield_Restore{i}')
    label('WarmYield_GuardDone');store(c+0x104,0)
    clock_sample('WarmYield_ClockAfter')
    put(f' lda.l ${c+0x116:06X}\n sta.l ${c+0x110:06X}\n lda.l ${c+0x118:06X}\n sta.l ${c+0x112:06X}\n lda.l ${c+0x11a:06X}\n inc a\n sta.l ${c+0x11a:06X}')
    label('WarmYield_Good')
    put(' pld\n plb\n ply\n plx\n pla\n plp\n rtl')
    label('WarmYield_Scan')
    put(' php\n rep #$30\n pha\n lda $18\n and #31\n bne WarmYield_ScanDone\n jsl WarmYield')
    label('WarmYield_ScanDone');put(' pla\n plp\n rtl')

    label('WarmTryPublish')
    put(' php\n rep #$38\n pha\n phx\n phy\n phb\n phd\n lda #0\n tcd\n sep #$20\n.a8\n lda #0\n pha\n plb\n rep #$20\n.a16')
    put(f' lda.l $7E7890\n ora.l $7E7892\n beq WarmTryPublish_Unchanged')
    # Compare only the source fields which determine this bounded picture.
    # Fractional positions may advance without changing integer raster anchors.
    for off in (0x50,0x54,0x56,0x1c,0x1e,0x36,0x3e,0x0c,0x0e):
        put(f' lda.l ${0x7e7800+off:06X}\n cmp.l ${d+off:06X}\n bne WarmTryPublish_Changed')
    label('WarmTryPublish_Unchanged')
    put(' pld\n plb\n ply\n plx\n pla\n plp\n clc\n rtl')
    label('WarmTryPublish_Changed');put(' ldx #0')
    label('WarmTryPublish_Pin')
    put(f' lda.l $7E7800,x\n sta.l ${p:06X},x\n inx\n inx\n cpx #148\n bcc WarmTryPublish_Pin')
    # No nested source call occurs in this copy. NMI does not write snapshots.
    store(c+0x0c,0);store(c+0x102,0);store(c+0x100,1)
    label('WarmPublish')
    put(' jsl $2E8000\n bcs WarmTryPublish_Failed')
    put(f' lda.l ${c+0x102:06X}\n bne WarmTryPublish_Failed')
    store(c+0x100,2)
    label('WarmRenderRetired')
    put(' nop\n pld\n plb\n ply\n plx\n pla\n plp\n clc\n rtl')
    label('WarmTryPublish_Failed');store(c+0x100,4)
    put(' pld\n plb\n ply\n plx\n pla\n plp\n sec\n rtl')
    # Both physical map DMAs have completed. Reference bookkeeping may span
    # active display, so publish the picture's immutable identity here rather
    # than delaying it until that nonvisual bookkeeping has retired.
    label('WarmDisplayLatch')
    put(' php\n rep #$30\n pha\n phx\n ldx #0')
    label('WarmDisplayLatch_Copy')
    put(f' lda.l ${p:06X},x\n sta.l ${d:06X},x\n inx\n inx\n cpx #148\n bcc WarmDisplayLatch_Copy')
    label('WarmPublished');put(' nop\n plx\n pla\n plp\n rtl')
    put('WarmHelper_CodeEnd:\n.a16\n.i16')
    return _relax('\n'.join(lines)+'\n','Warm')


def relocate(publisher, config, helper_symbols):
    """Retain the accepted transactional core, substituting its source rows."""
    if publisher.count('.bank 57\n')!=7:
        raise ValueError('WARM_PUBLISHER_BANK_SHAPE')
    s=publisher.replace('.bank 57\n','.bank 46\n')
    # All immutable actor/side reads use the current render pin; latest can
    # advance during a cooperative yield without invalidating this picture.
    def pin(m):
        n=int(m[0]);return str(RENDER_PIN+n-0x7fba00) if 0x7fba00<=n<0x7fba94 else m[0]
    s=re.sub(r'\b\d{7}\b',pin,s)
    s=s.replace('$7FBA90',f'${RENDER_PIN+144:06X}').replace('jsl $398000','jsl $2E8000')
    begin=s.index('OnlinePublish:');end=s.index('OnlinePreflight:')
    c=CONTROL;p=RENDER_PIN;meta=config['metadata_cpu']+config['metadata_header_bytes']
    lines=['OnlinePublish:','.a16','.i16',' php',' rep #$38',' pha',' phx',' phy',' phb',' phd',
           ' lda #$3400',' tcd',' sep #$20','.a8',' lda #0',' pha',' plb',' rep #$20','.a16']
    def put(t):lines.extend(t.strip().splitlines())
    def guard(at,value):put(f' lda.l ${at:06X}\n cmp #{value}\n bne WarmEntry_Reject')
    guard(0x7ffb96,0xb4b8)
    guard(p,0x4000);guard(p+2,0x41);guard(p+4,1);guard(p+6,0)
    guard(p+0x50,config['model_id']);guard(p+0x0c,0);guard(p+0x0e,0);guard(p+0x1e,0)
    put(f' lda.l ${p+0x1c:06X}\n cmp #2\n bcs WarmEntry_Reject\n sta.l ${c+8:06X}')
    # Bound to the zero-camera physical viewport admitted by the source owner.
    put(f' lda.l ${p+0x36:06X}\n cmp #256\n bcs WarmEntry_Reject\n lda.l ${p+0x3e:06X}\n cmp #224\n bcs WarmEntry_Reject')
    put(f' lda.l ${p+0x54:06X}')
    for g in config['groups']:
        put(f' cmp #{g["handle"]}\n beq WarmEntry_Handle{g["handle"]}')
    put(' jmp WarmEntry_Reject')
    for g in config['groups']:
        put(f'WarmEntry_Handle{g["handle"]}:\n.a16\n.i16\n lda.l ${p+0x56:06X}\n cmp #{g["count"]}\n bcs WarmEntry_Reject\n clc\n adc #{g["first"]}\n jmp WarmEntry_Pose')
    put('WarmEntry_Pose:\n.a16\n.i16\n asl a\n asl a\n asl a\n asl a\n asl a\n tax')
    # Metadata is source-derived, in a read-only, full-bank CPU ROM window.
    for off,target in ((8,c+4),(10,c+6),(24,c+0x20),(26,c+0x22),(28,c+0x24),(8,c+0x28),(10,c+0x2a)):
        put(f' lda.l ${meta+off:06X},x\n sta.l ${target:06X}')
    put(f' lda.l ${c+8:06X}\n bne WarmEntry_Normal\n lda.l ${c+4:06X}\n sec\n sbc.l ${meta+12:06X},x\n jmp WarmEntry_OffsetReady\nWarmEntry_Normal:\n.a16\n.i16\n lda.l ${meta+12:06X},x\nWarmEntry_OffsetReady:\n.a16\n.i16\n sta $00\n lda.l ${p+0x36:06X}\n sec\n sbc $00\n sta.l ${c:06X}\n sta $00\n lda.l ${p+0x3e:06X}\n sec\n sbc.l ${meta+14:06X},x\n sta.l ${c+2:06X}\n sta $02')
    # Inclusive clipped tile bounds for the full source raster. Transparent
    # pixels are tested by the real mask, including capacity fallback.
    for target,at,size,end_edge,limit in ((0x10,c,4,False,256),(0x12,c,4,True,256),
                                        (0x14,c+2,6,False,224),(0x16,c+2,6,True,224)):
        tag=f'WarmEntry_Bounds{target}'
        put(f' lda.l ${at:06X}')
        if end_edge:put(f' clc\n adc.l ${c+size:06X}\n dec a')
        put(f' bpl {tag}Positive\n lda #0\n{tag}Positive:\n.a16\n.i16\n cmp #{limit}\n bcc {tag}Ready\n lda #{limit-1}\n{tag}Ready:\n.a16\n.i16\n lsr a\n lsr a\n lsr a\n sta ${target:02X}')
    put(' jmp NbBegin\nWarmEntry_Reject:\n.a16\n.i16\n jmp OnlineReject\n')
    s=s[:begin]+_relax('\n'.join(lines)+'\n','WarmEntry')+s[end:]
    # The existing row consumer still owns front-panel occlusion and backdrop.
    row=f'''OnlineRowPointers:
.a16
.i16
 lda #1
 sta.l ${CONTROL+0x0e:06X}
 jmp OnlineRowCommon
OnlineColorPointers:
.a16
.i16
 lda #0
 sta.l ${CONTROL+0x0e:06X}
OnlineRowCommon:
.a16
.i16
 lda $18
 asl a
 tax
 lda.l $E18000,x
 sta $5C
 asl a
 asl a
 clc
 adc $5C
 asl a
 asl a
 asl a
 asl a
 sta $0C
 lda #$F3
 sta $0E
 lda $18
 asl a
 asl a
 asl a
 sta $54
 jsl ${helper_symbols['WarmTile_Prepare']:06X}
 bcc WarmEntry_RowGood
 lda #1
 sta.l ${CONTROL+0x102:06X}
 lda #0
 ldx #0
WarmEntry_RowClear:
.a16
.i16
 sta.l ${TILE_ROWS:06X},x
 inx
 inx
 cpx #96
 bcc WarmEntry_RowClear
 lda #$9800
 sta $08
 lda #$7E
 sta $0A
 lda #12
 sta $48
 lda #8
 sta $46
 lda #0
 sta $56
WarmEntry_RowGood:
.a16
.i16
 rts
'''
    a=s.index('OnlineRowPointers:');b=s.index('OnlineRowMask:',a);s=s[:a]+row+s[b:]
    actor_color=' jsr OnlineRowPointers\n jsl AstraOpaqueTile\n'
    if s.count(actor_color)!=2:raise ValueError('WARM_COLOR_CONSUMER_SHAPE')
    s=s.replace(actor_color,' jsr OnlineColorPointers\n jsl AstraOpaqueTile\n')
    presence=f'''WarmSourcePresence:
.a16
.i16
 jsr OnlineRowPointers
 lda #0
 ldx #0
WarmSourcePresence_Or:
 ora.l ${TILE_ROWS:06X},x
 pha
 txa
 clc
 adc #12
 tax
 pla
 cpx #96
 bcc WarmSourcePresence_Or
 rts
'''
    a=s.index('WarmSourcePresence:');b=s.index('.org $D400',a);s=s[:a]+presence+s[b:]
    # Disable the old private queued-movement experiment at this boundary.
    a=s.index('SpReadyBoundary:');b=s.index('SpLatched:',a)
    retained=s[a:b]+' rts\n'
    s=s[:a]+retained+s[b:]
    # Yield only between complete scan cells, or before starting a fresh
    # vblank wait. No yield inside a pair DMA, map DMA or reference commit.
    for label in ('NbMarkNext','NbRestorePlanNext','NbActorPlanNext','NbActorProduceNext'):
        needle=label+':\n.a16\n.i16\n'
        if s.count(needle)!=1:raise ValueError('WARM_YIELD_LABEL:'+label)
        hook=f" jsl ${helper_symbols['WarmYield_Scan']:06X}\n"
        s=s.replace(needle,needle+hook)
    needle='NbFreshVblank:\n.a16\n.i16\n'
    s=s.replace(needle,needle+f" jsl ${helper_symbols['WarmYield']:06X}\nNbFreshVblank_WithoutYield:\n.a16\n.i16\n")
    # All final fault checks precede this call. The commit's fresh-field wait
    # must therefore bypass the ordinary staging-time cooperative yield.
    commit_wait=' jsr SpReadyBoundary\n jsr NbFreshVblank\n'
    if s.count(commit_wait)!=1:raise ValueError('WARM_COMMIT_WAIT_SHAPE')
    s=s.replace(commit_wait,' jsr SpReadyBoundary\n jsr NbFreshVblank_WithoutYield\n')
    map_done='NbMapsComplete:\n.a16\n.i16\n'
    if s.count(map_done)!=1:raise ValueError('WARM_DISPLAY_LATCH_SHAPE')
    s=s.replace(map_done,map_done+f" jsl ${helper_symbols['WarmDisplayLatch']:06X}\n")
    # A fault in source service is sticky but must not strand partially staged
    # renderer references; abort at the existing reversible boundary.
    needle='RvContinue:\n'
    s=s.replace(needle,needle+f' lda.l ${CONTROL+0x102:06X}\n beq WarmYield_PrecommitGood\n jmp NbAbort\nWarmYield_PrecommitGood:\n.a16\n.i16\n')
    if '.bank 57' in s or '$7FBA90' in s:raise ValueError('WARM_RELOCATION_LITERAL')
    return s
