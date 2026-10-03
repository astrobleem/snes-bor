"""Link palette/OAM transactions to the audited two-packet native ABI.

The immutable palette source is in the frame descriptor. Capture binds physical
CGRAM slots to the two admitted instance slots, never to source model names.
"""


def link_packet_palettes(code, symbols, native, *, staging_cache=False):
    if symbols['StreamCacheFp_Slot2Tile']<0x7FA8E0:
        raise ValueError('PALETTE_PACKET_WRAM_OWNERSHIP')
    code=code.replace('adc #544','adc #608').replace(
        '    lda #544\n    sta.l DmaRequest_Length','    lda #608\n    sta.l DmaRequest_Length')
    if staging_cache:
        reset='    sta.l S7Pub_State+$F2\n    ldx #0'
        if code.count(reset)!=1:raise ValueError('PALETTE_PACKET_RESET_BOUNDARY')
        code=code.replace(reset,'    sta.l S7Pub_State+$F2\n    lda #$FFFF\n'+
            ''.join(f'    sta.l ${address:06X}\n' for address in range(0x7FA8D0,0x7FA8D8,2))+
            '    lda #0\n    ldx #0')
    code+='\n.bank 31\n.org $C000\n'
    for prefix,base in (('S7Packet',0x7FA840),('S7Packet2',0x7FA880)):
        marker=f'{prefix}_Submit__free:\n'
        if code.count(marker)!=1:raise ValueError('PALETTE_PACKET_TEMPLATE_BOUNDARY')
        code=code.replace(marker,marker+f'.a16\n.i16\n    jsl {prefix}_PreparePalette\n')
        block=[f'{prefix}_PreparePalette:', '    rep #$30','.a16','.i16','    phx','    phy',
               '    phb','    sep #$20','.a8','    lda #$7F','    pha','    plb','    rep #$20','.a16']
        for slot in (0,1):
            loop=f'{prefix}_PreparePalette_{slot}'
            destination=(base+slot*32)&65535
            key=0x7FA8D0+(4 if prefix=='S7Packet2' else 0)+slot*2
            # Cache describes bytes in this private, unowned staging buffer,
            # never hardware readiness. The immutable ROM address is its key.
            if staging_cache:
                block += [f'    lda.l ${0x7F8C20+slot*32+6:06X}',f'    beq {loop}_absent',
                      f'    lda.l ${0x7F8C20+slot*32+28:06X}',f'    bra {loop}_key',
                      loop+'_absent:','.a16','.i16','    lda #0',loop+'_key:','.a16','.i16',
                      f'    cmp.l ${key:06X}',f'    beq {loop}_done','    pha',
                      '    cmp #0',f'    beq {loop}_empty']
            else:
                block += [f'    lda.l ${0x7F8C20+slot*32+6:06X}',f'    beq {loop}_empty',
                          f'    lda.l ${0x7F8C20+slot*32+28:06X}']
            block += ['    tax','    ldy #0',loop+':','.a16','.i16',
                      '    lda.l $200000,x',f'    sta.w ${destination:04X},y',
                      '    inx','    inx','    iny','    iny','    cpy #32',f'    bcc {loop}',f'    bra {loop}_'+('stored' if staging_cache else 'done'),
                      loop+'_empty:','.a16','.i16','    lda #0','    ldy #0',loop+'_clear:','.a16','.i16',
                      f'    sta.w ${destination:04X},y','    iny','    iny','    cpy #32',f'    bcc {loop}_clear']
            if staging_cache:block += [loop+'_stored:','.a16','.i16','    pla',f'    sta.l ${key:06X}']
            block += [loop+'_done:','.a16','.i16']
        block += ['    plb','    ply','    plx',prefix+'_PreparePalette__done:','.a16','.i16','    rtl']
        code+='\n'+'\n'.join(block)+'\n'
    code+='\n'+native
    address=symbols['Core_Dma_TransferOam']
    code+=f'\n.bank 0\n.org ${address:04X}\n    jsl S7Palette_Transfer\n    rts\n'
    # Checked against the actual original before applying the opt-in source hook.
    return code,[(address,bytes.fromhex('c231bf8504'))]
