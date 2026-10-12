"""Noninterlaced OBJ scanline admission in viewport coordinates.

Mesen SpriteInfo::IsVisible evaluates the preceding PPU scanline when fetching
the next rendered row. OAM Y is therefore the viewport row and wraps at 256.
Transparent padding still participates in sprite evaluation. Fully clipped
eight-pixel slivers are skipped by FetchSpritePosition/FetchSpriteAttributes.
"""


def active_on_line(piece, y):
    x=piece['x']
    return (x==-256 or x+piece['width']>0) and ((y-piece['y'])&255)<piece['height']


def tile_slivers(piece):
    x=piece['x']
    if x==-256:return piece['width']//8
    return sum(-8<x+8*i<256 for i in range(piece['width']//8))
