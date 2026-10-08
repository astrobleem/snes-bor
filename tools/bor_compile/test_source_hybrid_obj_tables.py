from pathlib import Path
import tempfile
from source_hybrid_residency import static_obj_atlas


def test_second_obj_name_table_preserves_each_piece():
    count=40
    data=bytearray(10240);oam=bytearray(544)
    for i in range(128):oam[i*4+1]=224
    for i in range(count):
        base=(i//8)*64+(i%8)*2
        oam[i*4:i*4+4]=bytes([i,10,base&255,0x28|(base>>8)])
        for ty in range(4):
            for tx in range(2):
                slot=base+ty*16+tx
                data[slot*32:(slot+1)*32]=bytes([i+1])*32
    with tempfile.TemporaryDirectory()as directory:
        p=Path(directory);(p/'oam.bin').write_bytes(oam);(p/'obj_chr.bin').write_bytes(data)
        # No per-frame objects are culled in this test.
        (p/'promoted.bin').write_bytes(bytes(28*32))
        report=dict(static_obj_assignment_sha256='fixed',obj_static_palettes=[[1]],native_obj_entries=count)
        atlas,target,entries=static_obj_atlas([p],[report])
    assert entries==count and len(atlas)==10240
    assert target[32*4+3]&1
    for i in range(count):
        base=target[i*4+2]+((target[i*4+3]&1)<<8)
        assert target[i*4+3]&0x0e==0x08
        for ty in range(4):
            for tx in range(2):
                slot=base+ty*16+tx
                assert atlas[slot*32:(slot+1)*32]==bytes([i+1])*32
