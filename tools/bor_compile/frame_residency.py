"""Finite-domain readiness model, not a live DMA or source timing certificate.

Never advances logical deadlines to accommodate transfers. Tile tokens denote
hardware-addressable blocks supplied by a linker, not arbitrary 8x8 aliases.
The planner's byte-only feasibility is separate from physical DMA placement.
"""
from dataclasses import dataclass,field


class DeadlineBlocked(ValueError):
    pass


@dataclass
class Residency:
    capacity: int
    resident: dict = field(default_factory=dict)  # slot -> committed content
    visible: set = field(default_factory=set)
    palettes: dict = field(default_factory=dict)  # CGRAM slot -> committed map identity
    pending: dict = field(default_factory=dict)
    pending_palettes: dict = field(default_factory=dict)

    def stage(self,slot,token):
        if not 0<=slot<self.capacity:raise DeadlineBlocked('VRAM_WORKING_SET')
        if slot in self.visible and self.resident.get(slot)!=token:
            raise DeadlineBlocked('VISIBLE_TILE_OVERWRITE')
        self.pending[slot]=token

    def stage_palette(self,slot,identity,visible_palette_slots=()):
        if not 0<=slot<8:raise DeadlineBlocked('OBJ_PALETTE_SLOT')
        if slot in visible_palette_slots and self.palettes.get(slot)!=identity:
            raise DeadlineBlocked('VISIBLE_PALETTE_OVERWRITE')
        self.pending_palettes[slot]=identity

    def complete_transfer(self):
        # Called only by a consumer with a completed hardware fence.
        self.resident.update(self.pending);self.pending.clear()
        self.palettes.update(self.pending_palettes);self.pending_palettes.clear()

    def publish(self,required,palette,descriptor_linked):
        # New OAM ownership is all-or-nothing. Pending is never ready.
        if (not descriptor_linked or any(self.resident.get(slot)!=token
            for slot,token in required.items()) or
            self.palettes.get(palette[0])!=palette[1]):
            raise DeadlineBlocked('FRAME_PUBLICATION_DEADLINE_BLOCKED')
        self.visible=set(required)


def plan_deadlines(frames,deadlines,*,capacity,blocks_per_field,initial=(),pinned=()):
    """Deterministic farthest-next-use cache + earliest-deadline prefetch.

    Returns a conservative byte/block schedule. False BLOCK is possible;
    success still requires a physical placement/queue-slot/live timing proof.
    Frame0 has zero notice: callers must declare its initial residency.
    """
    if not frames or len(frames)!=len(deadlines) or deadlines[0]!=0:
        raise ValueError('DEADLINE_DOMAIN')
    if any(b<=a for a,b in zip(deadlines,deadlines[1:])):
        raise ValueError('DEADLINE_ORDER')
    if capacity<1 or blocks_per_field<1:raise ValueError('RESOURCE_DOMAIN')
    requirements=[set(f)|set(pinned) for f in frames]
    cache=set(initial)|set(pinned);active=set();events=[];index=0
    if len(cache)>capacity:raise DeadlineBlocked('VRAM_INITIAL_WORKING_SET')
    for field_number in range(deadlines[-1]+1):
        if field_number==deadlines[index]:
            missing=requirements[index]-cache
            if missing:
                raise DeadlineBlocked(f'FRAME_PUBLICATION_DEADLINE_BLOCKED: frame={index}, '
                                      f'field={field_number}, missing_blocks={len(missing)}')
            active=requirements[index]
            events.append(dict(field=field_number,publication=index,ready=True))
            index+=1
            if index==len(frames):break
        future={token:min(deadlines[i] for i in range(index,len(frames)) if token in requirements[i])
                for token in set().union(*requirements[index:])}
        transferred=[];evicted=[]
        for token in sorted(set(future)-cache,key=lambda t:(future[t],t)):
            if len(transferred)==blocks_per_field:break
            if len(cache)==capacity:
                choices=cache-active-set(transferred)-set(pinned)
                if not choices:break
                victim=max(choices,key=lambda t:(future.get(t,float('inf')),t))
                if future.get(victim,float('inf'))<=future[token]:break
                cache.remove(victim);evicted.append(victim)
            cache.add(token);transferred.append(token)
        events.append(dict(field=field_number,transfers=transferred,evicted=evicted,
                           resident_blocks=len(cache)))
    return dict(status='BLOCK_SCHEDULE_CANDIDATE',events=events,capacity=capacity,
                blocks_per_field=blocks_per_field,physical_placement_proven=False,
                palette_deadlines_proven=False,live_deadlines_proven=False)
