"""Retire the port-only in-game stage-number row at its own dirty writer."""
from bor_sealed_selector_v1508 import correct as combat
from bor_restart_burst_v1494 import offset
def correct(image,symbols):
    raw=bytearray(combat(image,symbols))
    site=symbols[0]['Hud_Play__text_banked_check_stage'];assert site==0x0587a0
    a=offset(site)
    old=bytes.fromhex('c231af58277e1acf6a237ef01a8f6a237e8f4c277ee220a903c210a20000a067042286e900386b186b')
    assert raw[a:a+len(old)]==old
    # Keep stage dirty tracking and take the original no-text return. Do not
    # enqueue a blank row: opponent names and health belong in this region.
    raw[a+17:a+21]=bytes.fromhex('5cc78705')
    raw[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');crc=sum(raw)&65535
    raw[0x7fdc:0x7fe0]=(65535-crc).to_bytes(2,'little')+crc.to_bytes(2,'little')
    return bytes(raw)
