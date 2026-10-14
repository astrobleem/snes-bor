"""Independent offline oracle for the bounded nonblank queue/capacity protocol.

Tests transaction order and physical-lease assumptions. NOT a native clock or
Mesen proof. Real queued DMA addresses and timing must be measured in Mesen.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import ceil
from nonblank_batch_rescue import QUEUE_BASE, QUEUE_CAPACITY, QUEUE_END, RESTORE_BASE, RESTORE_CAPACITY

VRAM_BYTES = 65536
HIGH_BYTES = 64
LOW_BYTES = 16
HIGH_BASE = 0
LOW_BASE = 49152
MAPS_BASE = 61440
TOTAL_SLOTS = 768

@dataclass(frozen=True)
class Packet:
    source: int
    destination: int
    data: bytes
    slot: int
    plane: str
    window: int


@dataclass(frozen=True)
class Admission:
    old_slots: frozenset[int]
    restore_identities: tuple[bytes,...]
    actor_identity_cells: tuple[bytes,...]
    visible_actor_cells: tuple[bytes,...]
    exact_retry: bool
    admitted: bool
    selected_count: int
    free_slots: int
    pending_slots: tuple[int,...]
    failure: str | None


def admission(old_slots, restore_identities, conservative_actor_cells, exact_actor_cells,
              *,tail_min=596, restore_limit=RESTORE_CAPACITY) -> Admission:
    """Fail-closed source-coverage -> exact-FG fallback before any graphics IO.

    'actor cells' here stand for distinct required tiles (the current native
    simple planner does not deduplicate them). A cell identity is its screen
    tile index, not a precompiled image. Exact cells must be a subset of the
    conservatively occupied cells. Restores are dedicated reservations.
    """
    old=frozenset(old_slots)
    if any(not 0<=x<TOTAL_SLOTS for x in old):raise ValueError('DISPLAY_SLOT_DOMAIN')
    cons=tuple(conservative_actor_cells); exact=tuple(exact_actor_cells);restore=tuple(restore_identities)
    if len(set(cons))!=len(cons) or len(set(exact))!=len(exact) or not set(exact).issubset(cons):
        raise ValueError('SOURCE_EFFECTIVE_COVERAGE_SUBSET')
    if len(restore)>restore_limit:
        return Admission(old,restore,cons,exact,False,False,0,0,(),'RESTORE_RECORD_CAPACITY')
    free=tuple(s for s in range(tail_min,TOTAL_SLOTS) if s not in old)
    need_conservative=len(cons)+len(restore)
    retry=need_conservative>len(free)
    selected=exact if retry else cons
    needed=len(selected)+len(restore)
    if needed>len(free):
        return Admission(old,restore,cons,exact,retry,False,needed,len(free),(),'TWO_FRAME_SLOT_CAPACITY')
    return Admission(old,restore,cons,exact,retry,True,needed,len(free),free[:needed],None)


class Publisher:
    """Simulates immutable visible slots, queued source images and map commit.

    A queue entry is a full 80-byte component pair; mutation of the caller's
    scratch cannot change queued bytes. A failed READY keeps the old map.
    """
    def __init__(self,old_map:tuple[int,...],vram:bytes,capacity=QUEUE_CAPACITY):
        if len(vram)!=VRAM_BYTES or len(old_map)!=1024 or any(not 0<=s<TOTAL_SLOTS for s in old_map):
            raise ValueError('PUBLISHER_INIT_DOMAIN')
        self.vram=bytearray(vram);self.display=old_map;self.pending=None
        self.lease=frozenset(old_map);self.capacity=capacity
        self.queue=[];self.packets=[];self.windows=0;self.ready=False
        self.committed_epochs=0;self.byte_identity_at_old_slots={s:self.read_pair(s) for s in self.lease}
    def read_pair(self,slot):
        return bytes(self.vram[slot*HIGH_BYTES:(slot+1)*HIGH_BYTES])+bytes(self.vram[LOW_BASE+slot*LOW_BYTES:LOW_BASE+(slot+1)*LOW_BYTES])
    def begin(self,next_map):
        if self.pending is not None:raise ValueError('PENDING_ALREADY_EXISTS')
        if len(next_map)!=1024 or any(not 0<=s<TOTAL_SLOTS for s in next_map):raise ValueError('PENDING_MAP_DOMAIN')
        self.pending=next_map;self.ready=False
    def enqueue(self,slot,pair):
        if self.pending is None or self.ready:raise ValueError('BAD_ENQUEUE_STATE')
        if slot in self.lease or not 0<=slot<TOTAL_SLOTS or len(pair)!=80:raise ValueError('UNSAFE_PENDING_SLOT')
        if slot in {p[0] for p in self.queue} or any(p.slot==slot for p in self.packets):raise ValueError('DOUBLE_RESERVATION')
        self.queue.append((slot,bytes(pair)))
        if len(self.queue)==self.capacity:self.flush()
    def flush(self):
        if not self.queue:return
        window=self.windows;self.windows+=1
        for index,(slot,pair) in enumerate(self.queue):
            source=QUEUE_BASE+index*80
            self.packets.append(Packet(source,slot*64,pair[:64],slot,'HIGH',window))
            self.packets.append(Packet(source+64,LOW_BASE+slot*16,pair[64:],slot,'LOW',window))
            self.vram[slot*64:slot*64+64]=pair[:64]
            self.vram[LOW_BASE+slot*16:LOW_BASE+slot*16+16]=pair[64:]
        self.queue.clear()
        self.assert_old_untouched()
    def finish_ready(self):
        if self.pending is None:raise ValueError('NO_PENDING')
        self.flush()
        if self.queue:raise ValueError('INCOMPLETE_PRELOAD')
        self.ready=True
    def commit(self):
        if not self.ready or self.pending is None:raise ValueError('COMMIT_BEFORE_ALL_FENCES')
        self.display=self.pending
        raw=b''.join(int(x).to_bytes(2,'little') for x in self.display)
        self.vram[MAPS_BASE:MAPS_BASE+2048]=raw
        self.vram[MAPS_BASE+2048:MAPS_BASE+4096]=raw
        self.lease=frozenset(self.display)
        self.byte_identity_at_old_slots={s:self.read_pair(s) for s in self.lease}
        self.pending=None;self.ready=False;self.committed_epochs+=1
    def rollback(self):
        if self.pending is None:raise ValueError('NO_PENDING_ROLLBACK')
        self.assert_old_untouched()
        self.pending=None;self.queue.clear();self.ready=False
    def assert_old_untouched(self):
        for s,b in self.byte_identity_at_old_slots.items():
            if self.read_pair(s)!=b:raise ValueError('DISPLAYED_TILE_MUTATED')
    def describe(self):return dict(windows=self.windows,packets=len(self.packets),chr_bytes=sum(len(p.data) for p in self.packets),committed=self.committed_epochs)


def budget(batch_len,per_pair_clocks,overhead_clocks,vblank_clocks,margin=10000):
    if not 0<=batch_len<=QUEUE_CAPACITY:raise ValueError('BATCH_COUNT_DOMAIN')
    if min(per_pair_clocks,overhead_clocks,vblank_clocks,margin)<0:raise ValueError('BUDGET_DOMAIN')
    elapsed=batch_len*per_pair_clocks+overhead_clocks
    return dict(elapsed=elapsed,remaining=vblank_clocks-elapsed,admissible=elapsed+margin<=vblank_clocks)


def windows_for_pairs(n):
    if n<0:raise ValueError('PAIR_COUNT_DOMAIN')
    return ceil(n/QUEUE_CAPACITY)
