"""Pinned BOR timer arithmetic; not gameplay floating-point arithmetic.

Reference only. No runtime clock policy is silently changed by this module.
PIT samples supplied by callers must respect timer_gettime's short-interval
domain. Target mapping uses declared oscillator frequencies, not completion
timestamps. Source render-loop timing remains a separate contract.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

PIT_HZ = 1193181
GAME_SPEED = 200
MASTER_HZ = 21477270
TIMER_SHA256 = '15e32988720548a53cf4c9afd565e8fa7eddbfbd6629d58a0f7e380897a94b3f'
SOURCE_COMMIT = 'eba02fe6c9e97e388126c51560a92024f406d8c0'


def verify_timer(path):
    digest = sha256(Path(path).read_bytes()).hexdigest()
    if digest != TIMER_SHA256:raise ValueError('UNPINNED_TIMER_SOURCE')
    return digest


def timer_interval(now, lastinterval, frequency=GAME_SPEED):
    """Unsigned register operations from timer_getinterval_, including carry wrap."""
    if not 1<=frequency<=PIT_HZ:raise ValueError('FREQUENCY_DOMAIN')
    if not 0<=now<=0xffffffff or not 0<=lastinterval<=0xffffffff:
        raise ValueError('PIT_WORD_DOMAIN')
    block, correction = divmod(PIT_HZ, frequency)
    elapsed = ((now-lastinterval)+correction)&0xffffffff
    count, residual = divmod(elapsed, block)
    return count, (lastinterval+elapsed-residual)&0xffffffff


def ceil_div(n, d):return -(-n//d)


@dataclass(frozen=True)
class AbsoluteSourceClock:
    epoch: int
    master_hz: int = MASTER_HZ
    frequency: int = GAME_SPEED

    def __post_init__(self):
        if self.master_hz<=0 or not 1<=self.frequency<=PIT_HZ:
            raise ValueError('CLOCK_DOMAIN')

    def due(self, now):
        if now<self.epoch:raise ValueError('BEFORE_EPOCH')
        pit = (now-self.epoch)*PIT_HZ//self.master_hz
        block, correction = divmod(PIT_HZ, self.frequency)
        return (pit+correction)//block

    def deadline(self, tick):
        if tick<0:raise ValueError('NEGATIVE_TICK')
        block, correction = divmod(PIT_HZ, self.frequency)
        return self.epoch+ceil_div(max(0,tick*block-correction)*self.master_hz,PIT_HZ)


def visible_boundary(deadline, boundaries):
    """Earliest supplied hardware boundary not before a deadline; no extra slack.

    This arithmetic is not a claim that BOR requires that presentation boundary.
    Source draws before catch-up and does not guarantee every logical frame is
    displayed. A target display-loop policy must be declared independently.
    """
    return next((b for b in boundaries if b>=deadline), None)
