"""BOR exit geometry for the existing integer, 4/5-scale actor adapter.

This is metadata generation, not catalog mutation or a capability certificate.
Source float player bounds use inverse target coordinates (5*x/4, 5*y/4).
checkhole(int,int) truncates those nonnegative coordinates BEFORE testing.
The lost fractions of previously rounded spawn coordinates are unrecoverable.
"""
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class Bounds:
    source_width: int
    blocked: bool = False
    endhole: bool = False

    def words(self):
        w = self.source_width
        if not isinstance(w, int) or not 262 <= w <= 81000:
            raise ValueError('bounds width outside unsigned compat threshold domain')
        # Greatest integer target X satisfying the source float clamp.
        block = (4*w - 1048)//5
        # y=4*q+r: trunc(5*y/4)=5*q+r. First hole X is
        # ceil(4*(w-232+trunc(5*y/4)+1)/5), hence y + intercept[r].
        holes = tuple((4*(w-231+r)+4)//5-r for r in range(4))
        if max(block, *holes) + 255 > 65535:
            raise ValueError('bounds thresholds overflow compat world X')
        return (int(self.blocked) | (int(self.endhole) << 1), block, *holes, 0, 0)

    def clamp(self, x, depth):
        _coords(x, depth)
        return min(x, self.words()[1]+depth) if self.blocked else x

    def hole(self, x, depth):
        _coords(x, depth)
        return 2 if self.endhole and x >= self.words()[2+(depth & 3)]+depth else 0


def _coords(x, depth):
    if not isinstance(x, int) or not isinstance(depth, int) or not 0 <= x <= 65535 or not 0 <= depth <= 255:
        raise ValueError('expected unsigned compat world X and byte depth')


def grounded(base_fraction, base_integer, altitude_q8):
    """BOR !inair(): abs(a-base)<.1 source pixel, not velocity==0."""
    if not -32768 <= altitude_q8 <= 32767:
        raise ValueError('expected signed Q8.8 altitude')
    return base_fraction == base_integer == 0 and abs(altitude_q8) <= 20


def import_q8(value):
    if not isinstance(value, int) or not -32768 <= value <= 32767:
        raise ValueError('expected signed Q8.8 value')
    return (1 if value >= 0 else -1)*(abs(value)*25//256)


def snapshot_checks(bounds, depth):
    """Recommended live integration assertions; never reads/writes an emulator."""
    _coords(0, depth)
    words = bounds.words()
    first = words[2+(depth & 3)]+depth
    return dict(clamp_max_x=words[1]+depth,
                endhole_last_safe_x=first-1, endhole_first_x=first,
                entering=dict(state=1, entry_depth=depth, depth=123,
                              height=3080-25*depth, velocity=0, draw_y=depth,
                              base_integer=-800, base_fraction=0,
                              grab_target=255, grabbed_by=255, obj_priority=0),
                retired=dict(state=2, damage_calls=1, source_damage=10000,
                             oam_y=240, shadow=False),
                reset=dict(state=0, height=0, velocity=0, base_integer=0,
                           base_fraction=0))


def from_ir(ir):
    """Panel order determines source width; repeated directives are last-wins."""
    if ir.diagnostics:
        raise ValueError(ir.diagnostics)
    width = 0
    for c in ir.order:
        i = ord(c.lower())-ord('a')
        if not 0 <= i < len(ir.panels):
            raise ValueError('invalid source panel order')
        width += ir.dimensions[ir.panels[i][0]][0]
    result = Bounds(width, bool(ir.environment.get('blocked', [0])[-1]),
                    bool(ir.environment.get('endhole', [0])[-1]))
    result.words()
    return result


def encode(rows):
    """Physical-stage order, None for unaffected/non-BOR entries; 16 bytes/row."""
    if not 1 <= len(rows) <= 256:
        raise ValueError('expected 1..256 physical stages')
    return b''.join(struct.pack('<8H', *(r.words() if r is not None else (0,)*8)) for r in rows)


def emit_pasm(rows, *, bank):
    """Caller places this table in the stated ROM bank; never writes files."""
    encode(rows)
    if not isinstance(bank, int) or not 0 <= bank <= 255:
        raise ValueError('invalid ROM bank')
    lines = ['; Generated source bounds: flags, clamp intercept, four hole intercepts, reserved.',
             f'StageBounds_RecordCount = {len(rows)}',
             f'StageBounds_DataBank = ${bank:02X}0000', 'StageBounds_Records:']
    lines.extend('    .dw ' + ', '.join(str(v) for v in (r.words() if r else (0,)*8)) for r in rows)
    return '\n'.join(lines)+'\n'


@dataclass
class Pit:
    """Executable compat lifecycle oracle; units are 1/25 target pixel.

    One tick is BOR's GAME_SPEED/100 gravity event, supplied by the caller.
    Integer arithmetic exactly represents source decimal .1 and -6 after
    scaling; this is not a claim of IEEE float or display-frame timing identity.
    """
    height: int
    velocity: int = 0
    dead: bool = False
    depth: int = 123
    base: int = -20000
    linked: bool = False

    @classmethod
    def enter(cls, depth, *, altitude_q8=0, velocity_q8=0):
        _coords(0, depth)
        if not grounded(0, 0, altitude_q8):
            raise ValueError('airborne entry')
        # Source PANEL_Z-1 = 154, scaled height = 123.2 target pixels.
        return cls(3080-25*depth+import_q8(altitude_q8), import_q8(velocity_q8))

    def tick(self):
        if self.dead:
            return
        self.height = max(self.base, self.height+self.velocity)
        if self.velocity > -120:
            self.velocity -= 2
        self.dead = self.height < -5000  # source strict a < PIT_DEPTH=-250

    @property
    def screen_y(self):
        return self.depth - self.height//25

    @property
    def shadow(self):
        return False

    @property
    def obj_priority(self):
        return 0  # Mode 1: behind panel BG1/BG2, retain palette/flip bits
