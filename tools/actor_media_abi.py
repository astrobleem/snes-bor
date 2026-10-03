"""Shared resource contract: actor frame/palette pointers are 24-bit.

MSU directory and scene seeks can be wider. They do not widen the actor's
stored stream pointers, so a valid container offset can still be invalid here.
"""
ACTOR_MEDIA_ADDRESS_BITS=24


def check_actor_media_extent(offset, size, *, project='', model=''):
    limit=1 << ACTOR_MEDIA_ADDRESS_BITS
    if (not isinstance(offset,int) or not isinstance(size,int) or
        offset<0 or size<=0 or offset+size>limit):
        raise ValueError(f'ACTOR_MEDIA_ADDRESS_RANGE: project={project}, model={model}, '
                         f'offset={offset}, bytes={size}, address_bits={ACTOR_MEDIA_ADDRESS_BITS}, limit={limit}')
    return dict(offset=offset,bytes=size,end_exclusive=offset+size,address_bits=ACTOR_MEDIA_ADDRESS_BITS)
