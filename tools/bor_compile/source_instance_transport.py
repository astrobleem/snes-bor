"""Resolve immutable transport job addresses once, at link time."""

def emit_jobs(jobs):
    if not jobs or len(jobs)>96:
        raise ValueError('INSTANCE_JOB_STATE_CAPACITY: 96 words before $7F9000')
    if [j['frame'] for j in jobs]!=sorted(j['frame'] for j in jobs):
        raise ValueError('INSTANCE_JOB_FRAME_ORDER')
    if len({j['source'] for j in jobs})!=len(jobs):
        raise ValueError('INSTANCE_JOB_FENCE_IDENTITY')
    for j in jobs:
        if (not 0<j['size']<2816-544 or j['size']%2 or j['target']%2 or
                not 0x8000<=j['target']<j['target']+j['size']<=0xC000 or
                not 0x8000<=j['source']<j['source']+j['size']<=0x10000 or
                not 0<=j['lease']<=j['frame']<=255):
            raise ValueError('INSTANCE_JOB_RESOURCE_ABI')
    out=['.bank 34', '.org $8000', 'S7Plan_Poll:', '    rep #$30', '.a16', '.i16']
    for i,j in enumerate(jobs):
        nxt=f'S7Plan_Poll_{i}'
        out += [f'    lda.l ${0x7F8F40+2*i:06X}',f'    beq {nxt}',
                '    cmp #$FFFF',f'    beq {nxt}','    and #63','    tax',
                '    lda.l DmaQueue+4,x','    and #$40',f'    beq {nxt}_done',
                '    lda.l DmaQueue+5,x',f'    cmp #${j["source"]:04X}',f'    beq {nxt}',
                nxt+'_done:', '.a16','.i16','    lda #$FFFF',f'    sta.l ${0x7F8F40+2*i:06X}',
                nxt+':','.a16','.i16']
    out += ['    rtl','S7Plan_Schedule:','    rep #$30','.a16','.i16']
    for i,j in enumerate(jobs):
        nxt=f'S7Plan_Schedule_{i}'
        if i==0 or j['frame']!=jobs[i-1]['frame']:
            out += ['    lda.l $7F8F2C',f'    cmp #{j["frame"]}',f'    bcs {nxt}_group','    rtl',nxt+'_group:','.a16','.i16']
        out += [f'    lda.l ${0x7F8F40+2*i:06X}',f'    bne {nxt}',
                '    lda.l $7F8F2E',f'    cmp #{j["lease"]}',f'    bcc {nxt}',
                '    lda.l DmaQueue_BudgetTotal','    clc',f'    adc #{j["size"]}','    adc.l $7F8F2A',
                '    cmp #$0B00',f'    bcs {nxt}',
                f'    lda #{j["size"]}','    sta.l DmaRequest_Length',
                f'    lda #${j["target"]:04X}','    sta.l DmaRequest_TargetAddr',
                f'    lda #${j["source"]:04X}','    sta.l DmaRequest_SourceAddrLow',
                '    sep #$20','.a8','    lda #33','    sta.l DmaRequest_SourceBank',
                '    lda #0','    sta.l DmaRequest_TypeFlags','    rep #$30','.a16','.i16',
                '    jsl Core_Dma_Enqueue_Long',f'    bcc {nxt}','    txa','    ora #$8000',
                f'    sta.l ${0x7F8F40+2*i:06X}',nxt+':','.a16','.i16']
    out += ['    rtl','S7Plan_Check:','    rep #$30','.a16','.i16']
    for i,j in enumerate(jobs):
        nxt=f'S7Plan_Check_{i}'
        if i==0 or j['frame']!=jobs[i-1]['frame']:
            out += ['    lda.l S7Pub_State+$EE',f'    cmp #{j["frame"]}',f'    bcs {nxt}_group','    sec','    rtl',nxt+'_group:','.a16','.i16']
        out += [f'    lda.l ${0x7F8F40+2*i:06X}',f'    bne {nxt}','    clc','    rtl',nxt+':','.a16','.i16']
    return '\n'.join(out+['    sec','    rtl'])+'\n'
