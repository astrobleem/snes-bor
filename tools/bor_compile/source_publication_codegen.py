"""Native lookup/capture for explicitly admitted multi-model publication keys."""

def capture_code(count, runtime_ids, slot_mask=63):
    if slot_mask&~63:raise ValueError('PUBLICATION_SLOT_MASK_WIDTH')
    out=['S7Publisher_Capture:', '    rep #$30', '.a16', '.i16',
         '    jsl Depth_Sort_ComputeOrder','    phd',
         '    lda.l Depth_RenderOrder','    sta.l S7Pub_State+$F4',
         '    lda.l Depth_RenderOrder+2','    sta.l S7Pub_State+$F6',
         '    lda.l Depth_RenderOrder+4','    sta.l S7Pub_State+$F8',
         '    lda #0','    sta.l S7Pub_State+$E8',
         '    lda.l S7Pub_State+$F2','    sta.l S7Pub_State+$FA',
         '    lda.l $7E173C','    sta.l S7Pub_State+$E0']
    for slot in range(6):
        dest=0x7F8C20+slot*32;row=slot*133;ctx=0x1900+slot*256
        if not (slot_mask&(1<<slot)):
            # Explicit fixture viewport membership, not a model-lookup fallback.
            out += ['    lda #0',f'    sta.l ${dest+6:06X}']
            continue
        nxt=f'S7Multi_Capture_{slot}_done'
        out += [f'    lda #0',f'    sta.l ${dest+6:06X}',
                '    lda.l S7Pub_State+6',f'    beq {nxt}',
                '    lda.l S7Pub_State+$F2',f'    bne {nxt}',
                f'    lda.l S6Bridge_Policy+{row}','    and #255','    cmp #3',f'    bcs {nxt}',
                f'    lda #${ctx:04X}','    tcd','    lda $F6',f'    beq {nxt}',
                '    lda $FC',f'    bne {nxt}',
                f'    lda.l $7E0A00+CHAR_MAP_INDEX+{row}','    and #255','    sta.l S7Pub_State+$E2',
                f'    lda.l $7E0A00+CHAR_ROSTER_INDEX+{row}','    and #255','    sta.l S7Pub_State+$E4',
                '    jsl S7Multi_Lookup',f'    bcs S7Multi_Capture_{slot}_found',
                '    jsl S7Multi_Missing',f'    brl {nxt}',
                f'S7Multi_Capture_{slot}_found:','.a16','.i16',
                '    lda.l $20C008,x',f'    sta.l ${dest+22:06X}',
                '    lda.l $20C00A,x',f'    sta.l ${dest+24:06X}',
                '    lda.l $20C00C,x',f'    sta.l ${dest+26:06X}',
                f'    lda #{row}','    sta $7A',
                '    lda $14','    jsl S6Bridge_ProjectPolicy','    sec','    sbc.l Screen_PosX',f'    sta.l ${dest:06X}',
                '    lda $16','    jsl S6Bridge_ProjectPolicy','    sec','    sbc $18',f'    sta.l ${dest+2:06X}',
                '    lda $1A',f'    sta.l ${dest+4:06X}',
                '    lda $E4',f'    sta.l ${dest+8:06X}','    lda $06',f'    sta.l ${dest+10:06X}',
                '    lda.l S7Pub_State+$E0',f'    sta.l ${dest+12:06X}',
                '    lda.l S7Pub_State+$E2',f'    sta.l ${dest+14:06X}',
                '    lda.l S7Pub_State+$E4',f'    sta.l ${dest+16:06X}',
                '    lda.l Screen_PosX',f'    sta.l ${dest+18:06X}',
                '    lda $18',f'    sta.l ${dest+20:06X}',
                '    lda #1',f'    sta.l ${dest+6:06X}',nxt+':','.a16','.i16']
    out+=['S7Multi_CaptureComplete:','.a16','.i16','    pld','    rtl','S7Multi_Lookup:','    rep #$30','.a16','.i16','    ldx #0',
          'S7Multi_Lookup__loop:','.a16','.i16',
          '    lda.l $20C000,x','    cmp.l S7Pub_State+$E4','    bne S7Multi_Lookup__next',
          '    lda.l $20C002,x','    cmp $E4','    bne S7Multi_Lookup__next',
          '    lda.l $20C004,x','    cmp $06','    bne S7Multi_Lookup__next',
          '    lda.l $20C006,x','    cmp.l S7Pub_State+$E2','    bne S7Multi_Lookup__next',
          '    sec','    rtl','S7Multi_Lookup__next:','.a16','.i16',
          '    txa','    clc','    adc #16','    tax',f'    cpx #{count*16}',
          '    bcc S7Multi_Lookup__loop','    clc','    rtl']
    # Explicit long branches over capture bodies, not assembler-width guesses.
    import re
    serial=[0]
    def branch(m):
        serial[0]+=1;label=f'S7Multi_Branch{serial[0]}'
        inverse={'beq':'bne','bne':'beq','bcc':'bcs'}[m[1]]
        return f'    {inverse} {label}\n    brl {m[2]}\n{label}:\n.a16\n.i16'
    out+=['S7Multi_Missing:','    rep #$30','.a16','.i16']
    out += ['S7Multi_Missing__admitted_model:','.a16','.i16','    lda #1',
            '    sta.l S7Pub_State+$E8','    lda $E4','    sta.l S7Pub_State+$EA',
            '    lda $06','    sta.l S7Pub_State+$EC','    rtl']
    return re.sub(r'    (beq|bne|bcc) (S7Multi_Capture_\d+_done)',branch,'\n'.join(out))+'\n'
