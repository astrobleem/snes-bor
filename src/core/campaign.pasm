; Logical campaign resolver. This lives in bank 12 so separating campaign
; progression does not consume the bank-0 runtime/vector budget.
.include "../../tools/audio/campaign_config.pasm"

; Source startup scene adaptation. The PAK's LOGO.TXT displays senile.gif,
; then INTRO.TXT displays city.gif followed by flashes.gif. Preserve that
; ordering and input-advance contract with two full-row text cards; the GIF
; pixel animation remains a documented presentation adaptation.
Game_State_Play__intro:
    php
    rep #$31
.a16
.i16
    ; This boot-time zero-init is deferred into the first source startup
    ; frame to keep the fixed bank-0 boot window within its hard boundary.
    lda #0
    sta.l Player_InvulnFrames
    sep #$20
.a8
    lda.l Intro_Step
    cmp #2
    bcs Game_State_Play__intro_wait
    cmp #1
    beq Game_State_Play__intro_story
    lda #10
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_IntroLogo - Text_StringPool)
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    lda #1
    sta.l Intro_Step
    plp
    rtl
Game_State_Play__intro_story:
    sep #$20
.a8
    lda #10
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_IntroStory - Text_StringPool)
    jsl Core_Text_DrawString_Long
    sep #$20
.a8
    lda #2
    sta.l Intro_Step
    plp
    rtl
Game_State_Play__intro_wait:
    rep #$31
.a16
.i16
    lda.l Input_trigger
    ora.l Input_trigger+1
    beq Game_State_Play__intro_done
    rep #$31
.a16
.i16
    lda #GAME_STATE_TITLE
    sta.l Game_State
    sep #$20
.a8
    lda #0
    sta.l Intro_Step
Game_State_Play__intro_done:
    plp
    rtl

; Resolve the next physical catalog index from the active logical campaign.
; Entry is .a16/.i16; carry set means the campaign has ended. The caller
; reasserts its width after this long return.
Game_Campaign_ResolveNext:
    sep #$20
.a8
    lda.l Game_CampaignId
    cmp #CAMPAIGN_BOR_ORIGINAL
    beq Game_Campaign_ResolveNext__bor
    cmp #CAMPAIGN_TMNT
    beq Game_Campaign_ResolveNext__tmnt
    bra Game_Campaign_ResolveNext__standalone
Game_Campaign_ResolveNext__bor:
    .a8
    lda.l Game_CampaignOrdinal
    cmp #$FF
    beq Game_Campaign_ResolveNext__bor_first
    inc a
    cmp #Campaign_Bor_StageCount
    bcs Game_Campaign_ResolveNext__bor_end
    sta.l Game_CampaignOrdinal
    tax
    lda.l Campaign_Bor_StageMap,x
    sta.l Game_StageIndex
    clc
    rtl
Game_Campaign_ResolveNext__bor_end:
    sec
    rtl
Game_Campaign_ResolveNext__bor_first:
    .a8
    .i16
    ldx #0
    lda #0
    sta.l Game_CampaignOrdinal
    lda.l Campaign_Bor_StageMap,x
    sta.l Game_StageIndex
    clc
    rtl
Game_Campaign_ResolveNext__tmnt:
    .a8
    lda.l Game_CampaignOrdinal
    cmp #$FF
    beq Game_Campaign_ResolveNext__tmnt_first
    inc a
    cmp #Campaign_Tmnt_StageCount
    bcs Game_Campaign_ResolveNext__tmnt_end
    sta.l Game_CampaignOrdinal
    tax
    lda.l Campaign_Tmnt_StageMap,x
    sta.l Game_StageIndex
    clc
    rtl
Game_Campaign_ResolveNext__tmnt_end:
    sec
    rtl
Game_Campaign_ResolveNext__tmnt_first:
    .a8
    .i16
    ldx #0
    lda #0
    sta.l Game_CampaignOrdinal
    lda.l Campaign_Tmnt_StageMap,x
    sta.l Game_StageIndex
    clc
    rtl
Game_Campaign_ResolveNext__standalone:
    .a8
    lda.l Game_CampaignOrdinal
    cmp #$FF
    beq Game_Campaign_ResolveNext__standalone_first
    inc a
    cmp #Campaign_Standalone_StageCount
    bcs Game_Campaign_ResolveNext__standalone_end
    sta.l Game_CampaignOrdinal
    tax
    lda.l Campaign_Standalone_StageMap,x
    sta.l Game_StageIndex
    clc
    rtl
Game_Campaign_ResolveNext__standalone_end:
    sec
    rtl
Game_Campaign_ResolveNext__standalone_first:
    .a8
    .i16
    ldx #0
    lda #0
    sta.l Game_CampaignOrdinal
    lda.l Campaign_Standalone_StageMap,x
    sta.l Game_StageIndex
    clc
    rtl

; Handle a logical campaign end without allowing a physical catalog tail to
; become an accidental continuation. BOR/standalone use the temporary TITLE
; boundary; TMNT retains the existing ending presentation.
Game_Campaign_HandleEnd:
    sep #$20
.a8
    lda.l Game_CampaignId
    cmp #CAMPAIGN_TMNT
    beq Game_Campaign_HandleEnd__tmnt
    lda #GAME_STATE_TITLE
    sta.l Game_State
    rtl
Game_Campaign_HandleEnd__tmnt:
    .a8
    jsl Music_SelectEndingTrack_Long
    lda #GAME_STATE_ENDING
    sta.l Game_State
    rtl
