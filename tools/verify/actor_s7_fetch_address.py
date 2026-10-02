"""Exact fixed-format 16-bit tile ID times32, existing24-bit seek ABI."""
def emit(sym, finish):
    def mem(name):return f'${sym[name]:06X}'
    return f'''S7Fetch_Address:
    rep #$31
.a16
.i16
    lda.l {mem('StreamStage_TileId')}
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l {mem('StreamStage_TileOffLo')}
    lda.l {mem('StreamStage_TileId')}
    xba
    lsr a
    lsr a
    lsr a
    and #$001F
    sep #$20
.a8
    sta.l {mem('StreamStage_TileOffHi')}
    rep #$31
.a16
.i16
    ldx #0
    lda.l {mem('StreamStage_TilesBaseLo')}
    clc
    adc.l {mem('StreamStage_TileOffLo')}
    sta.l {mem('StreamStage_SeekTmpLo')}
    sep #$20
.a8
    lda.l {mem('StreamStage_TilesBaseHi')}
    adc.l {mem('StreamStage_TileOffHi')}
    sta.l {mem('StreamStage_SeekTmpHi')}
    lda.l {mem('StreamStage_SeekTmpLo')}
    {finish}
'''
