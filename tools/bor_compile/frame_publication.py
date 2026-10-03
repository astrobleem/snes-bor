"""Source-derived publication records for the existing mode-6 OAM consumer.

Packing/OAM oracle only: a transfer fence and production compositor consumer
are required before publication is certified. No accepted-frame fallback.
"""
import struct

PIECE_BYTES = 8  # signed right X, signed left X, signed Y, tile9 | LARGE bit15
HEADER_BYTES = 12  # role, frame, pieces, map byte, flags byte, piece pointer


def piece_word(tile, size=(16,32)):
    """Mode-6 name-table footprint; no row or name-table wrapping allowed."""
    size=tuple(size)
    if size not in ((16,32),(32,64)):
        raise ValueError('MODE6_OBJ_SIZE')
    width,height=size
    if (not 0 <= tile <= 511 or tile%16+width//8>16 or
            (tile%256)//16+height//8>16):
        raise ValueError('MODE6_TILE_FOOTPRINT')
    return tile | (0x8000 if size==(32,64) else 0)


def pack_descriptor(frame, *, role, index, map_selector, piece_address):
    if not 0 <= map_selector <= 255:
        raise ValueError('MAP_SELECTOR_WIDTH')
    if not 0 <= role <= 65535 or not 0 <= index <= 65535:
        raise ValueError('FRAME_ID_WIDTH')
    if not 0 <= piece_address <= 0xffffff:
        raise ValueError('PIECE_ADDRESS_WIDTH')
    chunks = frame['chunks']
    if len(chunks) > 128:
        raise ValueError(f'RESOURCE_OAM: required={len(chunks)}, available=128')
    pieces = bytearray()
    for chunk in chunks:
        right, left = chunk['right_xy'], chunk['left_xy']
        if right[1] != left[1]:
            raise ValueError('FACING_VERTICAL_MISMATCH')
        coordinates = right[0], left[0], right[1]
        if any(not -32768 <= v <= 32767 for v in coordinates):
            raise ValueError('PIECE_COORDINATE_WIDTH')
        tile = chunk['tile']
        pieces.extend(struct.pack('<hhhH', *coordinates,
                                  piece_word(tile,chunk.get('size',(16,32)))))
    header = struct.pack('<HHHBBI', role,index,len(chunks),map_selector,0,piece_address)
    return header,bytes(pieces)


def oam_oracle(pieces, *, anchor_x, anchor_y, facing_left, palette_slot):
    """Expected active OAM records; placement is an explicit caller contract.

    No world/camera/altitude conversion is invented here. Slot palette != source
    map selector: the CGRAM linker resolves that indirection independently.
    """
    if len(pieces) % PIECE_BYTES or len(pieces)//PIECE_BYTES > 128:
        raise ValueError('PIECE_RECORD_EXTENT')
    if not 0 <= palette_slot <= 7:
        raise ValueError('OBJ_PALETTE_SLOT')
    result=[]
    for right,left,dy,word in struct.iter_unpack('<hhhH',pieces):
        if word & 0x7e00:
            raise ValueError('PIECE_RESERVED_BITS')
        large=bool(word & 0x8000)
        width,height=(32,64) if large else (16,32)
        tile=word & 511
        piece_word(tile,(width,height))
        x=anchor_x+(left if facing_left else right)
        y=anchor_y+dy
        if x <= -width or x >= 256 or y <= -height or y >= 224:
            continue
        attr=0x30 | palette_slot<<1 | tile>>8 | (0x40 if facing_left else 0)
        result.append(dict(low=bytes((x&255,y&255,tile&255,attr)),
                           high=((x>>8)&1) | (2 if large else 0), x=x,y=y))
    return result


def transfer_requirement(frame, *, byte_limit, slot_limit, reserved_bytes, reserved_slots):
    required=sum(w['size'] for w in frame['writes'])
    slots=len(frame['writes'])
    # Production CheckLength rejects equality as well as greater-than.
    fits=required+reserved_bytes<byte_limit and slots+reserved_slots<=slot_limit
    return dict(status='SINGLE_BATCH_FITS' if fits else 'RESOURCE_TRANSFER_BATCH',
        required_bytes=required,required_slots=slots,byte_limit_exclusive=byte_limit,
        slot_limit=slot_limit,reserved_bytes=reserved_bytes,reserved_slots=reserved_slots,
        deadline_certified=False, note='No multi-field streaming/deadline inference')
