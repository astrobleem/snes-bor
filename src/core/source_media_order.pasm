; One existing media visit per presentation, before composition in C3 stage0.
; No new jobs, readiness or ownership rules. Outside that scope, preserve
; the existing after-submission visit. Before always clears stale state.
SourceMedia_Prepared = $7E46EE
SourceMedia_BeforeCompose:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda #0
    sta.l SourceMedia_Prepared
    lda.l $7E46DE
    bne SourceMedia_BeforeCompose__done
    jsr SourceNpc_Scope
    bcc SourceMedia_BeforeCompose__done
    lda.l Game_StageIndex
    bne SourceMedia_BeforeCompose__done
    lda #1
    sta.l SourceMedia_Prepared
SourceMedia_BeforeCompose__job:
.a16
.i16
    jsl SourceMedia_Bridge_Service
SourceMedia_BeforeCompose__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
SourceMedia_AfterSubmit:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceMedia_Prepared
    cmp #1
    beq SourceMedia_AfterSubmit__skip
    pla
    plp
    jml SourceMedia_Bridge_Service
SourceMedia_AfterSubmit__skip:
.a16
.i16
    pla
    plp
    rtl
SourceMedia_OrderEnd:
