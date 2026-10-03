"""Fail-closed S6 evidence classification, never an arithmetic implementation.

Historical status means ONLY the named retained NT probe family and exact
input tuples. It never certifies the released DOS game. Analytic status is a
conditional theorem over exact binary operands, not a chosen runtime policy.
No floating evaluation, rational model, or software float is used here.
"""
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path


class Status(str, Enum):
    HISTORICAL_FAMILY_PROVEN = 'HISTORICAL_FAMILY_PROVEN'
    OBSERVATIONALLY_EQUIVALENT = 'OBSERVATIONALLY_EQUIVALENT'
    NUMERIC_BLOCKED = 'NUMERIC_BLOCKED'


HISTORICAL_FAMILY_PROVEN = Status.HISTORICAL_FAMILY_PROVEN
OBSERVATIONALLY_EQUIVALENT = Status.OBSERVATIONALLY_EQUIVALENT
NUMERIC_BLOCKED = Status.NUMERIC_BLOCKED
NT_SCOPE = 'retained_open_watcom_1_9_nt_probes'
EXACT_SCOPE = 'conditional_exact_binary_operations'
FIXTURE = Path(__file__).with_name('fixtures') / 'watcom_numeric_vectors.json'
ASSUMPTIONS = frozenset({
    'binary_precision_at_least_24', 'normal_exponent_range_includes_-16_to_24',
    'exact_representable_operations_preserved', 'numeric_observables_only',
    'signed_int_at_least_32_bits',
})


@dataclass(frozen=True)
class Decision:
    status: Status
    scope: str
    reason: str


@dataclass(frozen=True)
class DyadicDomain:
    """All n / 2**fraction_bits for inclusive integer lo <= n <= hi.

    Booleans, host floats, arbitrary fractions, NaNs and infinities are not
    domain descriptors. The common lattice makes containment exact.
    """
    lo: int
    hi: int
    fraction_bits: int = 0

    def __post_init__(self):
        if any(type(x) is not int for x in (self.lo, self.hi, self.fraction_bits)):
            raise ValueError('domain requires integers, not bool/float')
        if self.lo > self.hi or not 0 <= self.fraction_bits <= 16:
            raise ValueError('empty domain or unsupported dyadic scale')


def load_vectors():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def _same(left, right):
    # Python equality otherwise conflates True, 1 and 1.0.
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    return left == right


def classify_probe(probe, requested_inputs, *, scope):
    """Request a nonempty finite domain of exact harness input dictionaries.

    Every tuple must be retained; intervals, partial dictionaries, changed
    iteration counts and wildcard requests cannot inherit a spot result.
    Literal strings specify the C harness literals, not decimal runtime values.
    """
    blocked = Decision(NUMERIC_BLOCKED, scope, 'request not contained in retained NT harness inputs')
    if scope != NT_SCOPE or type(requested_inputs) not in (tuple, list) or not requested_inputs:
        return blocked
    vectors = [v for v in load_vectors()['vectors'] if v['id'] == probe]
    if not all(any(_same(item, v['input']) for v in vectors) for item in requested_inputs):
        return blocked
    return Decision(HISTORICAL_FAMILY_PROVEN, scope,
                    'exact retained harness tuples only; constant casts are not runtime conversion proof')


def classify_exact(operation, domains, *, scope, assumptions=frozenset()):
    """Prove one operation over the entire Cartesian input domain.

    Proof: with common scale q <= 16 and |n| <= 2**24, every operand
    n*2**-q is exactly representable with >=24 binary significant bits
    (the endpoints +/-2**24 are powers of two). Addition/subtraction have
    exact numerator endpoint bounds; require those also within +/-2**24.
    All nonzero values are >=2**-16 and <=2**24, excluding under/overflow.
    Thus stores and wider temporaries cannot change numeric results. Compare
    needs only exact operands. Integer identity casts need q=0 and fit int32.
    Signed-zero bits, exceptions, compositions and lifecycle are not covered.
    No inference from observed vectors is involved.
    """
    def blocked(reason):
        return Decision(NUMERIC_BLOCKED, scope, reason)

    if scope != EXACT_SCOPE or not ASSUMPTIONS.issubset(assumptions):
        return blocked('conditional arithmetic/observable assumptions not established')
    arity = {'add': 2, 'subtract': 2, 'compare': 2, 'integer_identity_cast': 1}.get(operation)
    if type(domains) not in (list, tuple) or arity is None or len(domains) != arity:
        return blocked('unsupported operation or arity')
    if any(type(d) is not DyadicDomain for d in domains):
        return blocked('explicit bounded dyadic domains required')
    q = domains[0].fraction_bits
    if any(d.fraction_bits != q for d in domains):
        return blocked('common dyadic lattice required')
    limit = 1 << 24
    if any(d.lo < -limit or d.hi > limit for d in domains):
        return blocked('operand domain exceeds exact representability bound')
    if operation == 'integer_identity_cast' and q != 0:
        return blocked('fractional runtime conversions are not proven')
    if operation in ('add', 'subtract'):
        a, b = domains
        lo, hi = ((a.lo + b.lo, a.hi + b.hi) if operation == 'add'
                  else (a.lo - b.hi, a.hi - b.lo))
        if lo < -limit or hi > limit:
            return blocked('intermediate/result domain exceeds exact representability bound')
    return Decision(OBSERVATIONALLY_EQUIVALENT, scope,
                    'entire requested Cartesian domain satisfies the documented exact-operation theorem')
