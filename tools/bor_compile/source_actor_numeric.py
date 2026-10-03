"""S6 observational numeric references, not a runtime/ModelIR implementation.

Start with exact discrete decisions and rational observations. The optional
integer-only binary32 store oracle produces conditional counterexamples, NOT
an emulation or certification of the original C compiler/FPU environment.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import re

PINNED_BOR_SHA256 = '68c54a190c5713b1a42b75898ae9ff5246896de0ded3f8c1247c507681735f41'
PINNED_RNG_SHA256 = {
    'RAND32.ASM': 'a89ddbf982072216d971fdc6a739b51fb1655bd0131b8aeeaa4abfb999ce6a0a',
    'RAND32.H': '41ab7452bc9200e4ed54482307586f384e4fa54392a09224fda7cc9bd61e6950',
}
EXACT = 'EXACT_DISCRETE_SEMANTIC'
VISIBLE = 'NUMERIC_APPROXIMATION_VISIBLE'
INTERNAL = 'IMPLEMENTATION_DETAIL_NOT_OBSERVABLE'
INITIAL_SEED = 1234567890


def verify_source(path):
    digest = sha256(Path(path).read_bytes()).hexdigest()
    if digest != PINNED_BOR_SHA256:
        raise ValueError(f'unpinned BOR.C: {digest}')
    return digest


def random32_step(seed):
    if not 0 <= seed <= 0xFFFFFFFF:
        raise ValueError('seed must be unsigned32')
    wide = seed * 1103515245 + 12345
    return wide & 0xFFFFFFFF, (wide >> 16) & 0xFFFFFFFF


def verify_rng_sources(folder):
    result = {}
    for name, expected in PINNED_RNG_SHA256.items():
        digest = sha256((Path(folder) / name).read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f'unpinned {name}: {digest}')
        result[name] = digest
    return result


def rng_instructions(assembly):
    """Extract the actual pinned routine, not a handwritten instruction list."""
    body = assembly.lower().split('rand32_ proc near', 1)[1].split('rand32_ endp', 1)[0]
    return tuple(line.split(';', 1)[0].replace(',', ' ').split()
                 for line in body.splitlines() if line.split(';', 1)[0].strip())


def random32_x86(seed, instructions, with_trace=False):
    """Small unsigned32 instruction/CF interpreter for the audited routine.

    Independent of the wide recurrence and 16-bit limb implementation. Rejects
    unhandled opcodes rather than silently skipping source instructions.
    """
    if not 0 <= seed <= 0xFFFFFFFF:
        raise ValueError('seed must be unsigned32')
    regs = {'seed': seed, 'eax': 0, 'edx': 0}
    carry = 0
    trace = []

    def operand(token):
        return regs[token] if token in regs else int(token[:-1], 16) if token.endswith('h') else int(token)

    for instruction in instructions:
        op, *args = instruction
        if op == 'mov':
            regs[args[0]] = operand(args[1]) & 0xFFFFFFFF
        elif op == 'mul':
            product = regs['eax'] * operand(args[0])
            regs['eax'], regs['edx'] = product & 0xFFFFFFFF, product >> 32
            carry = int(regs['edx'] != 0)
        elif op in ('add', 'adc'):
            result = regs[args[0]] + operand(args[1]) + (carry if op == 'adc' else 0)
            regs[args[0]], carry = result & 0xFFFFFFFF, int(result > 0xFFFFFFFF)
        elif op in ('shl', 'shr'):
            value, count = regs[args[0]], operand(args[1])
            if not 1 <= count < 32:
                raise ValueError('unsupported shift count')
            carry = ((value >> (32 - count)) if op == 'shl' else (value >> (count - 1))) & 1
            regs[args[0]] = ((value << count) if op == 'shl' else (value >> count)) & 0xFFFFFFFF
        elif op in ('and', 'or'):
            value = operand(args[1])
            regs[args[0]] = (regs[args[0]] & value) if op == 'and' else (regs[args[0]] | value)
            carry = 0
        elif op != 'ret':
            raise ValueError(f'unhandled x86 instruction: {instruction}')
        trace.append({'instruction': ' '.join(instruction), **regs, 'carry': carry})
        if op == 'ret':
            break
    result = regs['seed'], regs['eax']
    return (result, trace) if with_trace else result


def audit_bor_rng_calls(source):
    """Lexical source inventory, not a dynamic shared-call-order proof."""
    # Preserve line numbers while removing comments and quoted literals.
    clean = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',
                   lambda m: '\n' * m.group(0).count('\n'), source, flags=re.S)
    calls = {}
    for name in ('rand32', 'srand32', 'srand', 'randomize'):
        calls[name] = tuple(clean.count('\n', 0, m.start()) + 1
                            for m in re.finditer(r'\b' + name + r'\s*\(', clean))
    calls['direct_seed_identifier'] = bool(re.search(r'\bseed\b', clean))
    return calls


def random32_limbs(seed):
    """16-bit carry recipe suitable for a 65816 implementation reference."""
    if not 0 <= seed <= 0xFFFFFFFF:
        raise ValueError('seed must be unsigned32')
    lo, hi = seed & 65535, seed >> 16
    p0 = lo * 0x4E6D + 12345
    p1 = hi * 0x4E6D + lo * 0x41C6 + (p0 >> 16)
    p2 = hi * 0x41C6 + (p1 >> 16)
    return ((p0 & 65535) | ((p1 & 65535) << 16),
            (p1 & 65535) | ((p2 & 65535) << 16))


def unsigned_mod1000(word):
    """Bit-serial exact remainder; no signed divide or low16 truncation."""
    if not 0 <= word <= 0xFFFFFFFF:
        raise ValueError('return must be unsigned32')
    remainder = 0
    for bit in range(31, -1, -1):
        remainder = remainder * 2 + ((word >> bit) & 1)
        if remainder >= 1000:
            remainder -= 1000
    return remainder


@dataclass(frozen=True)
class RandomDecision:
    seed_before: int
    seed_after: int
    returned_word: int | None
    residue: int | None
    nominal_value: F
    consumed: bool


def randf_decision(seed, maximum):
    """Nominal rational value, exact sample/call decision; NOT C-float value."""
    maximum = F(maximum)
    if maximum == 0:
        if not 0 <= seed <= 0xFFFFFFFF:
            raise ValueError('seed must be unsigned32')
        return RandomDecision(seed, seed, None, None, F(0), False)
    after, word = random32_step(seed)
    residue = unsigned_mod1000(word)
    return RandomDecision(seed, after, word, residue, maximum * residue / 1000, True)


def drift_velocity(speed, residue, authored_x):
    if not 0 <= residue < 1000:
        raise ValueError('sample must be in 0..999')
    magnitude = F(speed) + F(3 * residue, 1000)
    return magnitude if authored_x < 160 else -magnitude


def drift_step(x, velocity, camera=0, alive=True):
    """Source bounds BEFORE motion; flip is not an input."""
    x, velocity, camera = F(x), F(velocity), F(camera)
    if not alive or x < camera - 80 or x > camera + 400:
        return x, False
    return x + velocity, True


def pixel(x, policy='truncate'):
    """Explicit observer; positive witnesses do not depend on floor vs trunc."""
    x = F(x)
    if policy == 'truncate':
        return int(x)
    if policy == 'floor':
        return x.numerator // x.denominator
    raise ValueError('observer must be floor or truncate')


def source_tick_batch(time, elapsed_ticks, paused=False):
    """BOR timer interval supplied externally; range is pre-increment time."""
    if elapsed_ticks < 0:
        raise ValueError('nonnegative timer interval required')
    return tuple(range(time, time + (0 if paused else min(elapsed_ticks, 100))))


def think_due_times(ticks, nextthink):
    """Ordinary think default; callback-specific rescheduling is out of scope."""
    due = []
    for tick in ticks:
        if tick == nextthink:
            due.append(tick)
            nextthink = tick + 2
    return tuple(due), nextthink


def rational_clock_frames(master_intervals, master_rate, rate=200):
    """Lossless partitioning reference, NOT proof of BOR timer_getinterval."""
    remainder = 0
    ticks = []
    for interval in master_intervals:
        count, remainder = divmod(remainder + interval * rate, master_rate)
        ticks.append(count)
    return tuple(ticks), remainder


def exactly_representable(value, fractional_bits=23):
    """Exact finite binary significand test (bounded normal values only)."""
    value = abs(F(value))
    if not value:
        return True
    if value.denominator & (value.denominator - 1):
        return False
    numerator = value.numerator
    while numerator % 2 == 0:
        numerator //= 2
    return numerator.bit_length() <= fractional_bits + 1


def certify_exact_translation(start, velocity, steps, thresholds=()):
    """Sufficient proof for a bounded binary32 exact-add/compare subdomain.

    Inputs must already be these exact values, not rounded decimal expressions.
    Does not certify collision systems, an entire actor, or timer delivery.
    """
    if steps < 0:
        raise ValueError('nonnegative bounded step count required')
    values = [F(start) + i * F(velocity) for i in range(steps + 1)]
    operands = [F(velocity), *map(F, thresholds), *values]
    return (all(exactly_representable(v) for v in operands)
            and all(v == 0 or F(1, 2**126) <= abs(v) < 2**128 for v in operands))


def translation_observation_enclosure(start, velocity, velocity_radius, steps, camera=0):
    """Conservative rational enclosure, not a float emulator.

    Assumes exact start and each normal-range position store has relative
    error <=2^-23; caller must justify the velocity radius. Returns the first
    uncertifiable pixel/boundary observation, not a fabricated counterexample.
    """
    if steps < 0 or F(velocity_radius) < 0:
        raise ValueError('nonnegative steps and radius required')
    x, radius = F(start), F(0)
    velocity, velocity_radius = F(velocity), F(velocity_radius)
    for tick in range(steps + 1):
        low, high = x - radius, x + radius
        bounds = lambda y: (y < camera - 80, y > camera + 400)
        if pixel(low) != pixel(high) or bounds(low) != bounds(high):
            return {'certified_prefix_steps': tick - 1, 'ambiguous_tick': tick,
                    'lower': str(low), 'upper': str(high), 'counterexample': False}
        x += velocity
        radius += velocity_radius
        radius += (abs(x) + radius) / 2**23
    return {'certified_prefix_steps': steps, 'ambiguous_tick': None, 'counterexample': False}


def round_binary32_normal(value):
    """Conditional IEEE binary32 normal-store oracle, using rational integers.

    Used AFTER rational analysis to retain witnesses. No host float, x87,
    double-literal evaluation, compiler contraction or original build claim.
    """
    value = F(value)
    if value == 0:
        return value
    sign = -1 if value < 0 else 1
    value = abs(value)
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    power = F(2**exponent) if exponent >= 0 else F(1, 2**-exponent)
    if value < power:
        exponent -= 1
    if not -126 <= exponent <= 126:
        raise ValueError('oracle limited to bounded normal finite values')
    quantum = F(2**(exponent - 23)) if exponent >= 23 else F(1, 2**(23 - exponent))
    units = value / quantum
    q, r = divmod(units.numerator, units.denominator)
    if 2 * r > units.denominator or (2 * r == units.denominator and q & 1):
        q += 1
    return sign * q * quantum


def conditional_drift_witness(start, speed, residue, authored_x, limit=600, camera=0):
    """Compare rational trajectory to explicit binary32-store assumption.

    randf operand division is rounded at each operation in this CONDITIONAL
    oracle. Original C excess precision is unproven; a witness blocks blanket
    certification, not proof that a historical executable takes this path.
    """
    q = round_binary32_normal
    x = stored = F(start)
    velocity = drift_velocity(speed, residue, authored_x)
    random_value = q(F(residue) / q(F(1000, 3)))
    stored_velocity = q(q(F(speed)) + random_value)
    if authored_x >= 160:
        stored_velocity = -stored_velocity
    for tick in range(limit + 1):
        rational_out = x < camera - 80 or x > camera + 400
        stored_out = stored < camera - 80 or stored > camera + 400
        if pixel(x) != pixel(stored) or rational_out != stored_out:
            return {'tick': tick, 'rational_x': str(x), 'stored_x': str(stored),
                    'rational_pixel': pixel(x), 'stored_pixel': pixel(stored),
                    'rational_outside': rational_out, 'stored_outside': stored_out,
                    'classification': VISIBLE, 'assumption': 'conditional binary32 operation/store rounding'}
        if rational_out:
            break
        x += velocity
        stored = q(stored + stored_velocity)
    return None  # no witness is NOT a certificate


def conditional_gravity_witness(velocity=1, limit=80):
    """Pressure on tossv>0/-6 predicates, not a full gravity simulation."""
    rational = stored = F(velocity)
    q = round_binary32_normal
    for tick in range(limit + 1):
        if (rational > 0, rational > -6) != (stored > 0, stored > -6):
            return {'tick': tick, 'rational_velocity': str(rational),
                    'stored_velocity': str(stored), 'classification': VISIBLE,
                    'assumption': 'conditional nearest binary32 store of exact decimal subtraction'}
        if rational > -6:
            rational -= F(1, 10)
        if stored > -6:
            stored = q(stored - F(1, 10))
    return None
