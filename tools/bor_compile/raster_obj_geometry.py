"""Noninterlaced OBJ scanline admission in viewport coordinates.

Mesen SpriteInfo::IsVisible evaluates the preceding PPU scanline when fetching
the next rendered row. OAM Y is therefore the viewport row and wraps at 256.
Transparent padding still participates in sprite evaluation. Tile counts use
the full width conservatively; horizontally clipped slivers may cost less.
"""


def active_on_line(piece, y):
    x=piece['x']
    return (x==-256 or x+piece['width']>0) and ((y-piece['y'])&255)<piece['height']
