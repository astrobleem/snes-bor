"""Lossless chunky tile serialization and type-1 SA-1 conversion descriptors.

Nintendo Book II sections 6.4/6.5 define conversion at S-CPU DMA speed and
exclusive S-CPU BW-RAM reads while active. Register setup is source-neutral.
This module does not grant a live runtime memory/channel lease.
"""
import numpy as np


def bitmap_bytes(tiles,bpp,columns):
    if bpp not in (2,4,8) or columns not in (1,2,4,8,16,32):raise ValueError('CHARCONV_FORMAT')
    tiles=np.asarray(tiles)
    if tiles.ndim!=3 or tiles.shape[1:]!=(8,8) or not len(tiles) or len(tiles)%columns:
        raise ValueError('CHARCONV_COMPLETE_TILE_ROWS')
    if np.any(tiles<0) or np.any(tiles>=(1<<bpp)):raise ValueError('CHARCONV_PIXEL_RANGE')
    canvas=tiles.reshape(-1,columns,8,8).transpose(0,2,1,3).reshape(-1,columns*8)
    groups=canvas.reshape(-1,8//bpp).astype(np.uint16)
    return np.bitwise_or.reduce(groups<<np.arange(0,8,bpp,dtype=np.uint16),axis=1).astype(np.uint8).tobytes()


def type1_descriptor(source,bpp,columns,tile_count,vram_byte_address,iram=0x3600):
    if bpp not in (2,4,8) or columns not in (1,2,4,8,16,32):raise ValueError('CHARCONV_FORMAT')
    if not tile_count or tile_count%columns:raise ValueError('CHARCONV_COMPLETE_TILE_ROWS')
    size=tile_count*8*bpp
    if source>>16 not in (0x40,0x41,0x42,0x43) or source%(8*bpp*columns):raise ValueError('CHARCONV_SOURCE_ALIGNMENT')
    if source+size>0x440000 or (source&65535)+size>65536:raise ValueError('CHARCONV_DMA_BANK_BOUNDARY')
    if iram%(bpp*16) or not 0x3000<=iram<=0x3800-bpp*16:raise ValueError('CHARCONV_IRAM_BUFFERS')
    if vram_byte_address%2 or not 0<=vram_byte_address<=65536-size:raise ValueError('CHARCONV_VRAM_RANGE')
    return dict(source=source,bytes=size,bpp=bpp,columns=columns,tile_count=tile_count,
                cdma=((columns.bit_length()-1)<<2)+{8:0,4:1,2:2}[bpp],iram=iram,
                vram_word_address=vram_byte_address//2,dcnt=0xb0,
                requires_sa1_setup=True,requires_chr_irq_ready=True,
                forbids_other_scpu_bwram_reads=True,native_admitted=False)
