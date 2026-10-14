"""Exact-content reference for paired component residency and sparse DMA.

Purpose: remove repeated backdrop reloads WITHOUT the incorrect assumption that
all 596 backdrop tiles can stay pinned next to 225 dynamic tiles in 768 slots.
This is a tested planner/reference, not a native allocator or a non-blank proof.

A slot holds what was LAST UPLOADED, not what its original slot number meant.
A backdrop tile needed again after eviction becomes a real missing upload.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Iterable
import struct


@dataclass(frozen=True)
class Packet:
    tag: str
    vram_byte_address: int
    data: bytes


@dataclass(frozen=True)
class Plan:
    base_epoch: int
    epoch: int
    slot_writes: tuple[tuple[int,bytes], ...]
    tilemap: tuple[int, ...]
    cells: tuple[bytes, ...]
    packets: tuple[Packet, ...]
    needs_forced_blank: bool

    @property
    def dma_bytes(self):return sum(len(p.data) for p in self.packets)
    @property
    def changed_cells(self):return sum(len(p.data)//2 for p in self.packets if p.tag.startswith('mapH:'))


def runs(values: Iterable[int]):
    a=sorted(set(values))
    if not a:return []
    result=[];start=previous=a[0]
    for x in a[1:]:
        if x!=previous+1:result.append((start,previous+1));start=x
        previous=x
    result.append((start,previous+1))
    return result


class WarmCache:
    def __init__(self, backdrop: list[bytes], backdrop_map: Iterable[int], capacity=768):
        self.base_tiles=tuple(backdrop);self.base_map=tuple(map(int,backdrop_map))
        if (not 1<=capacity<=768 or len(backdrop)>capacity or len(self.base_map)!=1024
                or any(len(t)!=80 for t in backdrop)
                or any(not 0<=v<len(backdrop) for v in self.base_map)):
            raise ValueError('WARM_CACHE_LAYOUT')
        self.capacity=capacity;self.epoch=0
        self.resident=list(backdrop)+[None]*(capacity-len(backdrop))
        self.tilemap=self.base_map
        self.cells=tuple(backdrop[i] for i in self.base_map)

    def prepare(self, epoch: int, patch: Mapping[int,bytes], *, allow_blank=True) -> Plan:
        if type(epoch)is not int or epoch<=self.epoch:
            raise ValueError('CACHE_EPOCH')
        target=[self.base_tiles[i] for i in self.base_map]
        for cell,raw in patch.items():
            if type(cell)is not int or not 0<=cell<896 or not isinstance(raw,bytes) or len(raw)!=80:
                raise ValueError('CACHE_PATCH_DOMAIN')
            target[cell]=raw
        required=set(target)
        if len(required)>self.capacity:
            raise ValueError('TARGET_CAPACITY')
        # Maintain a content-addressed directory. Native hashes require full
        # identity/collision validation; a small unchecked hash is NOT enough.
        resident_index={raw:i for i,raw in enumerate(self.resident) if raw is not None}
        used_slots={resident_index[raw] for raw in required if raw in resident_index}
        old_visible=set(self.tilemap)
        free=[i for i in range(self.capacity) if i not in used_slots and (allow_blank or i not in old_visible)]
        missing=sorted(required-resident_index.keys())
        if len(missing)>len(free):
            raise ValueError('SAFE_PRELOAD_CAPACITY')
        mapping={raw:resident_index[raw] for raw in required if raw in resident_index}
        writes=[]
        for raw,slot in zip(missing,free):mapping[raw]=slot;writes.append((slot,raw))
        newmap=tuple(mapping[raw] for raw in target)
        if any(v&0x6000 for v in newmap):raise ValueError('OFFSET_MAP_ENABLE_BITS')
        packets=[];write_dict=dict(writes)
        for first,last in runs(write_dict):
            group=[write_dict[slot] for slot in range(first,last)]
            packets.append(Packet(f'chrH:{first}',first*64,b''.join(t[:64] for t in group)))
            packets.append(Packet(f'chrL:{first}',0xC000+first*16,b''.join(t[64:] for t in group)))
        changed=[i for i,(a,b) in enumerate(zip(self.tilemap,newmap)) if a!=b]
        for first,last in runs(changed):
            data=struct.pack('<'+'H'*(last-first),*newmap[first:last])
            packets.append(Packet(f'mapH:{first}',0xF000+first*2,data))
            packets.append(Packet(f'mapL:{first}',0xF800+first*2,data))
        if any(not 0<len(p.data)<=65535 or p.vram_byte_address+len(p.data)>65536 for p in packets):
            raise AssertionError('DMA_RANGE')
        return Plan(self.epoch,epoch,tuple(writes),newmap,tuple(target),tuple(packets),
                    any(slot in old_visible for slot,_ in writes))

    def commit(self, plan: Plan, completed_packet_tags: Iterable[str]) -> None:
        if plan.base_epoch!=self.epoch or plan.epoch<=self.epoch:
            raise ValueError('STALE_PLAN')
        done=list(completed_packet_tags);wanted=[p.tag for p in plan.packets]
        if len(done)!=len(wanted) or set(done)!=set(wanted):
            raise ValueError('TRANSFER_FENCE_NOT_COMPLETE')
        # Real native copies happen before this metadata commit. Under forced
        # blank, a partial physical transfer failure must remain blank, NOT
        # claim the previous display is intact. Safe preflight rejects earlier.
        updated=self.resident.copy()
        for slot,raw in plan.slot_writes:updated[slot]=raw
        if tuple(updated[i] for i in plan.tilemap)!=plan.cells:
            raise AssertionError('RESIDENT_IDENTITY_MISMATCH')
        self.resident=updated;self.tilemap=plan.tilemap
        self.cells=plan.cells;self.epoch=plan.epoch

    def initialized_vram(self) -> bytearray:
        out=bytearray(65536)
        for slot,raw in enumerate(self.resident):
            if raw is not None:
                out[slot*64:slot*64+64]=raw[:64]
                out[0xC000+slot*16:0xC000+slot*16+16]=raw[64:]
        maps=struct.pack('<1024H',*self.tilemap)
        out[0xF000:0xF800]=maps;out[0xF800:]=maps
        return out


def apply_packets(vram: bytearray, plan: Plan):
    if len(vram)!=65536:raise ValueError('VRAM_LENGTH')
    for p in plan.packets:vram[p.vram_byte_address:p.vram_byte_address+len(p.data)]=p.data


def verify_vram(vram: bytes, expected_cells: tuple[bytes,...]):
    hi=struct.unpack_from('<1024H',vram,0xF000)
    lo=struct.unpack_from('<1024H',vram,0xF800)
    for cell,raw in enumerate(expected_cells):
        h,l=hi[cell],lo[cell]
        if h>=768 or l>=768 or h&0x6000 or l&0x6000:
            raise AssertionError('INVALID_MAP')
        actual=vram[h*64:h*64+64]+vram[0xC000+l*16:0xC000+l*16+16]
        if actual!=raw:raise AssertionError(f'VRAM_PIXEL_SOURCE_MISMATCH_CELL_{cell}')
