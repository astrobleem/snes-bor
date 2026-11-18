"""Restart handoff plus address-equivalent faster physical source rows."""
import hashlib
import edit_bor_restart_v900 as restart
R=restart.R
NAME='src/core/dma.pasm'
ORIGINAL=dict(restart.ORIGINAL,**{NAME:'9fb0038cc30fceb34064003aa9a60ef3872e4f68ef704cbbe60ba1e48f58ce45'})

def transformed(raw,reverse=False):
    eol=b'\r\n' if b'\r\n' in raw else b'\n'
    at=raw.index(b'Core_Dma_TransferSourceBlock:');prefix=raw[:at];part=raw[at:]
    mask=b'    and #$7FFF'+eol
    oldpad=b'    .db $EA,$EA,$EA,$EA'
    newpad=b'    .db '+b','.join([b'$EA']*13)
    if reverse:
        assert part.count(mask)==0 and part.count(newpad)==1
        step=b'    adc #256'+eol+b'    tay'
        assert part.count(step)==3
        part=part.replace(step,b'    adc #256'+eol+mask+b'    tay').replace(newpad,oldpad)
    else:
        assert part.count(mask)==3 and part.count(oldpad)==1
        part=part.replace(mask,b'').replace(oldpad,newpad)
    return prefix+part

def proof():
    # VMADDH masks bit15; verify the actual local emulator implementation.
    from pathlib import Path
    p=Path('E:/gh/Mesen2/Core/SNES/SnesPpu.cpp').read_text()
    assert '_state.VramAddress = (_state.VramAddress & 0x00FF) | ((value & 0x7F) << 8);' in p
    for target in range(65536):
        old=target>>1;new=old
        for row in range(4):
            assert old==(new&0x7fff)
            if row<3:old=(old+256)&0x7fff;new=(new+256)&65535
    print('PASS_ADDRESS_PROOF262144: all16-bit byte targets/four rows map identically; four64-byte transfers retained')

def change(reverse=False):
    path=R/NAME;raw=path.read_bytes()
    if reverse:
        old=transformed(raw,True)
        assert hashlib.sha256(old).hexdigest()==ORIGINAL[NAME]
        path.write_bytes(old);restart.change(reverse=True)
    else:
        assert hashlib.sha256(raw).hexdigest()==ORIGINAL[NAME]
        new=transformed(raw);assert transformed(new,True)==raw
        restart.change();path.write_bytes(new)
    print('RESTORED_DMA_MASK_PATCH' if reverse else 'APPLIED_DMA_MASK_PATCH')

if __name__=='__main__':proof()
