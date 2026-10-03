; Logical campaign resolver. This lives in bank 12 so separating campaign
; progression does not consume the bank-0 runtime/vector budget.
.include "../../tools/audio/campaign_config.pasm"
.include "../../tools/audio/audio_music_ids.pasm"

; Source startup scene adaptation. The PAK's LOGO.TXT displays senile.gif,
; then INTRO.TXT displays city.gif followed by flashes.gif. Preserve that
; ordering and input-advance contract with two full-row text cards; the GIF
; pixel animation remains a documented presentation adaptation.
Game_State_Play__intro:
    php
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l SceneVideo_Continuation
    rep #$31
.a16
.i16
    ; L3A's external frame-test request reuses the existing INTRO dispatch as
    ; a bounded bank-12 entry point; no gameplay/campaign route is changed.
    jsl SceneVideo_TestService
    bcs Game_State_Play__intro_done
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

; Resolve the next logical typed campaign entry.  The result is written to
; Game_Campaign_ResolvedKind/Value; carry set means the campaign has ended.
; Stage values are physical catalog indices; scene values are generated scene
; IDs.  Game_StageIndex is deliberately untouched for scene entries.
Game_Campaign_ResolveNext:
    sep #$20
.a8
    lda.l Game_CampaignId
    cmp #CAMPAIGN_BOR_ORIGINAL
    beq Game_Campaign_ResolveNext__bor
    cmp #CAMPAIGN_TMNT
    beq Game_Campaign_ResolveNext__tmnt
    cmp #CAMPAIGN_BOR_NORMAL_DEV
    bne Game_Campaign_ResolveNext__not_bor_normal_dev
    brl Game_Campaign_ResolveNext__bor_normal_dev
Game_Campaign_ResolveNext__not_bor_normal_dev:
    jmp Game_Campaign_ResolveNext__standalone
Game_Campaign_ResolveNext__bor:
    .a8
    lda.l Game_CampaignOrdinal
    cmp #$FF
    beq Game_Campaign_ResolveNext__bor_first
    inc a
    cmp #Campaign_Bor_EntryCount
    bcs Game_Campaign_ResolveNext__bor_end
    sta.l Game_CampaignOrdinal
    tax
    lda.l Campaign_Bor_EntryKinds,x
    sta.l Game_Campaign_ResolvedKind
    lda.l Campaign_Bor_EntryValues,x
    sta.l Game_Campaign_ResolvedValue
    lda.l Game_Campaign_AdvanceCount
    inc a
    sta.l Game_Campaign_AdvanceCount
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
    lda.l Campaign_Bor_EntryKinds,x
    sta.l Game_Campaign_ResolvedKind
    lda.l Campaign_Bor_EntryValues,x
    sta.l Game_Campaign_ResolvedValue
    lda.l Game_Campaign_AdvanceCount
    inc a
    sta.l Game_Campaign_AdvanceCount
    clc
    rtl
Game_Campaign_ResolveNext__tmnt:
    .a8
    lda.l Game_CampaignOrdinal
    cmp #$FF
    beq Game_Campaign_ResolveNext__tmnt_first
    inc a
    cmp #Campaign_Tmnt_EntryCount
    bcs Game_Campaign_ResolveNext__tmnt_end
    sta.l Game_CampaignOrdinal
    tax
    lda.l Campaign_Tmnt_EntryKinds,x
    sta.l Game_Campaign_ResolvedKind
    lda.l Campaign_Tmnt_EntryValues,x
    sta.l Game_Campaign_ResolvedValue
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
    lda.l Campaign_Tmnt_EntryKinds,x
    sta.l Game_Campaign_ResolvedKind
    lda.l Campaign_Tmnt_EntryValues,x
    sta.l Game_Campaign_ResolvedValue
    clc
    rtl
Game_Campaign_ResolveNext__bor_normal_dev:
    .a8
    lda.l Game_CampaignOrdinal
    cmp #$FF
    beq Game_Campaign_ResolveNext__bor_normal_dev_first
    inc a
    bra Game_Campaign_ResolveNext__source_index
Game_Campaign_ResolveNext__bor_normal_dev_first:
    lda #0
Game_Campaign_ResolveNext__source_index:
    rep #$30
.a16
.i16
    and #$00FF
    jsl Game_Campaign_SourceIndex
    bcs Game_Campaign_ResolveNext__bor_normal_dev_end
    sep #$20
.a8
    sta.l Game_CampaignOrdinal
    lda.l Campaign_Source_Kinds,x
    sta.l Game_Campaign_ResolvedKind
    lda.l Campaign_Source_Values,x
    sta.l Game_Campaign_ResolvedValue
    clc
    rtl
Game_Campaign_ResolveNext__bor_normal_dev_end:
    sec
    rtl
; ABI 3 is the shared persistent source-world campaign family. Selected
; source identity, ordinal and generated offsets resolve the actual route.
; A16/I16: A = proposed ordinal; return A unchanged, X = flattened entry,
; carry set for an invalid source set or ordinal. No physical adjacency.
Game_Campaign_SourceIndex:
.a16
.i16
    pha
    lda.l BorSet_Selected
    and #$00FF
    tax
    cpx #BOR_SET_COUNT
    bcs Game_Campaign_SourceIndex__invalid
    lda.l Campaign_Source_Counts,x
    and #$00FF
    cmp $01,s
    beq Game_Campaign_SourceIndex__invalid
    bcc Game_Campaign_SourceIndex__invalid
    lda.l Campaign_Source_Offsets,x
    and #$00FF
    clc
    adc $01,s
    tax
    pla
    clc
    rtl
Game_Campaign_SourceIndex__invalid:
    pla
    sec
    rtl
Game_Campaign_ResolveNext__standalone:
    .a8
    lda.l Game_CampaignOrdinal
    cmp #$FF
    beq Game_Campaign_ResolveNext__standalone_first
    inc a
    cmp #Campaign_Standalone_EntryCount
    bcs Game_Campaign_ResolveNext__standalone_end
    sta.l Game_CampaignOrdinal
    tax
    lda.l Campaign_Standalone_EntryKinds,x
    sta.l Game_Campaign_ResolvedKind
    lda.l Campaign_Standalone_EntryValues,x
    sta.l Game_Campaign_ResolvedValue
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
    lda.l Campaign_Standalone_EntryKinds,x
    sta.l Game_Campaign_ResolvedKind
    lda.l Campaign_Standalone_EntryValues,x
    sta.l Game_Campaign_ResolvedValue
    clc
    rtl

; ----------------------------------------------------------------------
; BOR source-set state.  Set IDs are positional IDs emitted from the
; authoritative DATA/LEVELS.TXT parser. Carry set means the requested
; predicate is true; invalid IDs are false.  Availability is deliberately
; independent from source unlock state so unported sets cannot become a
; fake playable campaign.
; ----------------------------------------------------------------------
BorSet_IsUnlocked:
    rep #$30
.a16
.i16
    and #$00FF
    tax
    sep #$20
.a8
    cmp #BOR_SET_COUNT
    bcs BorSet_IsUnlocked__false
    lda.l Bor_TimesCompleted+1
    ora.l Bor_TimesCompleted+2
    ora.l Bor_TimesCompleted+3
    bne BorSet_IsUnlocked__true
    lda.l Bor_TimesCompleted
    cmp.l BorSet_IfComplete,x
    bcs BorSet_IsUnlocked__true
BorSet_IsUnlocked__false:
    clc
    rtl
BorSet_IsUnlocked__true:
    sec
    rtl

BorSet_IsAvailable:
    rep #$30
.a16
.i16
    and #$00FF
    tax
    sep #$20
.a8
    cmp #BOR_SET_COUNT
    bcs BorSet_IsAvailable__false
    lda.l BorSet_ContentAvailable,x
    beq BorSet_IsAvailable__false
    lda.l BorSet_CampaignMap,x
    cmp #BOR_SET_UNMAPPED
    beq BorSet_IsAvailable__false
    sec
    rtl
BorSet_IsAvailable__false:
    clc
    rtl

BorSet_IsSelectable:
.a8
    pha
    jsl BorSet_IsUnlocked
    bcc BorSet_IsSelectable__false_pop
    pla
    jsl BorSet_IsAvailable
    rtl
BorSet_IsSelectable__false_pop:
    pla
    clc
    rtl

; Compatibility entry for callers explicitly requesting source-default Easy.
; The real prompt/new-game path uses BeginSelectedRun and retains its cursor.
BorSet_BeginEasyRun:
    sep #$20
.a8
    lda #0
    sta.l BorSet_Selected
    jml BorSet_BeginSelectedRun

; Revalidate at the actual new-run boundary. No unavailable/unlocked-only
; selection may become a playable campaign. Resolve typed logical entry 0,
; never a hardcoded physical catalog index. A8/I16 out, C=success.
BorSet_BeginSelectedRun:
    sep #$20
.a8
    lda.l BorSet_Selected
    jsl BorSet_IsSelectable
    bcc BorSet_BeginSelectedRun__no
    lda.l BorSet_CampaignMap,x
    sta.l Game_CampaignId
    lda #$FF
    sta.l Game_CampaignOrdinal
    lda #0
    sta.l Game_Campaign_AdvanceCount
    jsl Game_Campaign_ResolveNext
    bcs BorSet_BeginSelectedRun__no
    lda.l Game_Campaign_ResolvedKind
    cmp #CAMPAIGN_ENTRY_SCENE+1
    bcs BorSet_BeginSelectedRun__no
    lda #0
    sta.l BorSet_CompletionCredited
    lda #1
    sta.l BorSet_RunActive
    sec
    rtl
BorSet_BeginSelectedRun__no:
.a8
    lda #0
    sta.l BorSet_RunActive
    clc
    rtl

; BOR.C load_levelorder() attaches `next` to the preceding typed entry;
; playgame() calls showcomplete() only for that entry's gonext flag.
; Normal returns authored next; Easy uses the explicit S7 presentation
; compatibility lowering (including pending nonterminal scene continuation).
; Return carry clear for other campaigns or an
; invalid ordinal. Entry/exit A16/I16; mask byte cells before indexing so
; the hidden accumulator high byte cannot become part of X.
Game_Campaign_HasNextFlag:
    rep #$31
.a16
.i16
    lda.l Game_CampaignOrdinal
    and #$00FF
    tax
    lda.l Game_CampaignId
    and #$00FF
    cmp #CAMPAIGN_BOR_ORIGINAL
    beq Game_Campaign_HasNextFlag__easy
    cmp #CAMPAIGN_BOR_NORMAL_DEV
    bne Game_Campaign_HasNextFlag__false
    txa
    jsl Game_Campaign_SourceIndex
    bcs Game_Campaign_HasNextFlag__false
    lda.l Campaign_Source_CompleteFlags,x
    bra Game_Campaign_HasNextFlag__test
Game_Campaign_HasNextFlag__easy:
.a16
.i16
    cpx #Campaign_Bor_EntryCount
    bcs Game_Campaign_HasNextFlag__false
    lda.l Campaign_Bor_CompleteFlags,x
Game_Campaign_HasNextFlag__test:
.a16
    and #$00FF
    beq Game_Campaign_HasNextFlag__false
    sec
    rtl
Game_Campaign_HasNextFlag__false:
    clc
    rtl

; Credit one completed BOR set. The run latch prevents repeated
; end-handler processing from turning one completion into multiple counts.
; Campaign 3 retains its compatibility name but represents source set 1
; (Normal) once all 16 typed entries exist. Availability is a separate gate.
BorSet_CreditCompletion:
.a8
    lda.l Game_CampaignId
    cmp #CAMPAIGN_BOR_ORIGINAL
    beq BorSet_CreditCompletion__run
    cmp #CAMPAIGN_BOR_NORMAL_DEV
    beq BorSet_CreditCompletion__source
    rtl
BorSet_CreditCompletion__source:
    ; Credit only the terminal authored entry of the selected linked set.
    rep #$30
.a16
.i16
    lda.l Game_CampaignOrdinal
    and #$00FF
    jsl Game_Campaign_SourceIndex
    bcc BorSet_CreditCompletion__valid
    rtl
BorSet_CreditCompletion__valid:
    inc a
    pha
    lda.l BorSet_Selected
    and #$00FF
    tax
    lda.l Campaign_Source_Counts,x
    and #$00FF
    cmp $01,s
    beq BorSet_CreditCompletion__terminal
    pla
    rtl
BorSet_CreditCompletion__terminal:
    pla
    sep #$20
.a8
BorSet_CreditCompletion__run:
.a8
    lda.l BorSet_RunActive
    beq BorSet_CreditCompletion__done
    lda.l BorSet_CompletionCredited
    bne BorSet_CreditCompletion__done
    ; Derive the completed source set from the actual campaign, including
    ; internal Normal starts which bypass the Easy-only new-run selector.
    lda.l Game_CampaignId
    cmp #CAMPAIGN_BOR_NORMAL_DEV
    beq BorSet_CreditCompletion__normal
    lda #0
    bra BorSet_CreditCompletion__selected
BorSet_CreditCompletion__normal:
.a8
    lda.l BorSet_Selected
BorSet_CreditCompletion__selected:
.a8
    sta.l BorSet_Selected
    lda.l Bor_TimesCompleted
    inc a
    sta.l Bor_TimesCompleted
    bne BorSet_CreditCompletion__store
    lda.l Bor_TimesCompleted+1
    inc a
    sta.l Bor_TimesCompleted+1
    bne BorSet_CreditCompletion__store
    lda.l Bor_TimesCompleted+2
    inc a
    sta.l Bor_TimesCompleted+2
    bne BorSet_CreditCompletion__store
    lda.l Bor_TimesCompleted+3
    inc a
    sta.l Bor_TimesCompleted+3
BorSet_CreditCompletion__store:
.a8
    lda #1
    sta.l BorSet_CompletionCredited
    jsl Options_SaveBorCompletion
BorSet_CreditCompletion__done:
    rtl

; Convert a resolved typed entry to the existing stage-clear caller's small
; contract.  A contains the physical stage index and carry is clear for a
; stage.  A scene request is performed here in bank 12 and returns carry set;
; this keeps the fixed bank-0 stage loader unchanged.
Game_Campaign_DispatchResolved:
    sep #$20
.a8
    lda.l Game_Campaign_ResolvedKind
    cmp #CAMPAIGN_ENTRY_SCENE
    beq Game_Campaign_DispatchResolved__scene
    lda.l Game_Campaign_ResolvedValue
    sta.l Game_StageIndex
    clc
    rtl
Game_Campaign_DispatchResolved__scene:
    sep #$20
.a8
    lda.l Game_Campaign_ResolvedValue
    ldx #SCENE_CONTINUE_CAMPAIGN
    jsl SceneVideo_Request
    sec
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
    jsl BorSet_CreditCompletion
    rep #$31
.a16
.i16
    lda #GAME_STATE_TITLE
    sta.l Game_State
    sta.l $7E2752
    rtl
Game_Campaign_HandleEnd__tmnt:
    .a8
    jsl Music_SelectEndingTrack_Long
    lda #GAME_STATE_ENDING
    sta.l Game_State
    rtl

; Called by the shared scene-video cleanup after natural completion or skip.
; It advances the logical entry ordinal rather than hard-coding TITLE in the
; scene implementation. Rewinding leaves the completed scene as the current
; entry: its generated zero next flag prevents a second completion bonus
; before loading the following stage (or dispatching another scene).
Game_Campaign_AdvanceAfterScene:
    rep #$31
.a16
.i16
    lda.l Game_Campaign_EndCount
    inc a
    sta.l Game_Campaign_EndCount
    jsl Game_Campaign_ResolveNext
    bcs Game_Campaign_AdvanceAfterScene__end
    ; The ordinary stage-clear path will resolve the same next stage again.
    ; Rewind the ordinal so its single increment consumes, rather than skips,
    ; the entry already selected here.
    lda.l Game_CampaignOrdinal
    dec a
    sta.l Game_CampaignOrdinal
    sep #$20
.a8
    lda #1
    sta.l Stage_LoadPending
    lda #GAME_STATE_STAGECLEAR
    sta.l Game_State
    rtl
Game_Campaign_AdvanceAfterScene__end:
    jsl Game_Campaign_HandleEnd
    rtl
