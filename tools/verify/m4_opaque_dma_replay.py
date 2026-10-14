"""Replay actual native DMA descriptors against captured physical VRAM."""
import json
from pathlib import Path
import numpy as np


def verify(folder):
    native=folder/'native';result=json.loads((folder/'result.json').read_text())
    packets=json.loads((native/'dma-packets.json').read_text());rom=(native/'bor.sfc').read_bytes()
    vram=bytearray((native/'initial-vram.bin').read_bytes());palette=bytearray(512)
    authority=Path('out/byor-motu-online-v3/assets');hi=(authority/'high.chr').read_bytes();lo=(authority/'low.chr').read_bytes()
    rows=[]
    for obs in result['observations']:
        epoch=obs['epoch'];batch=[p for p in packets if p['epoch']==epoch]
        for p in batch:
            if p['source']>=0xc00000:data=rom[p['source']-0xc00000:p['source']-0xc00000+p['bytes']]
            else:data=bytes.fromhex(p['payload'])
            if len(data)!=p['bytes']:raise ValueError('ACTUAL_DMA_PAYLOAD_LENGTH')
            if p['target']==0x18:
                at=p['vram_word']*2
                if at+len(data)>65536:raise ValueError('ACTUAL_DMA_BOUNDARY')
                vram[at:at+len(data)]=data
            elif p['target']==0x22:
                if epoch or len(data)!=512:raise ValueError('UNEXPECTED_WARM_PALETTE_DMA')
                palette[:]=data
            else:raise ValueError('ACTUAL_DMA_TARGET')
        expected=(native/f'vram-{epoch:02d}.bin').read_bytes()
        if vram!=expected:raise ValueError('ACTUAL_SPARSE_DMA_REPLAY:'+str(epoch))
        if palette!=(native/f'cgram-{epoch:02d}.bin').read_bytes():raise ValueError('ACTUAL_PALETTE_REPLAY')
        directory=np.frombuffer((native/f'directory-{epoch:02d}.bin').read_bytes(),dtype='<u2')
        tilemap=np.frombuffer(expected[0xf000:0xf800],dtype='<u2')
        if not np.array_equal(directory&0x3fff,np.bincount(tilemap,minlength=768)):raise ValueError('ACTUAL_DIRECTORY_REFS')
        for slot in range(len(hi)//64):
            if not directory[slot]&0x8000:
                if expected[slot*64:slot*64+64]!=hi[slot*64:slot*64+64] or expected[0xc000+slot*16:0xc000+slot*16+16]!=lo[slot*16:slot*16+16]:raise ValueError('ACTUAL_HOME_IDENTITY')
        rows.append(dict(epoch=epoch,bytes=sum(p['bytes'] for p in batch),descriptors=len(batch),full_vram_matches=True,home_identities_verified=True))
    if any(p['epoch']>=len(rows) for p in packets):raise ValueError('REJECTED_CONTEXT_TRANSFERRED_DATA')
    return dict(status='PASS',epochs=rows,verified_vram_bytes=len(rows)*65536)
