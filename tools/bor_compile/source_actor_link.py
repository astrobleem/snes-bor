"""Opt-in source scheduler descriptors; successful linking is NOT actor certification.

Only owns discrete animation/frame layout. World drivers, raster admission and
floating-point equivalence require independent runtime evidence. Source IR is
never edited to fit this ABI. Unknown role behavior is retained as a blocker.
"""
import struct
from actor_frame_abi import pack_source_frame, FRAME_BYTES
from lowering_policy import Profile

ROLE_BYTES=16
ACTOR_CONTEXT_BYTES=256
SOURCE_SLOT_LIMIT=150
ROLE_BEHAVIOR={
    'idle':'hold_or_loop', 'walk':'signed_loop',
    'attack1':'enemy_attack', 'attack2':'enemy_attack', 'attack3':'enemy_attack',
    'pain':'pain_wait', 'fall':'airborne_lifecycle', 'rise':'rise_wait',
    'jump':'player_jump', 'jumpattack':'jump_attack', 'jumpattack2':'jump_attack',
    'upper':'counterattack', 'grab':'linked_grab', 'throw':'linked_throw',
    'special':'special_attack', 'get':'pickup_lifecycle', 'land':'player_land',
}


def link_scheduler(actor, *, bank_base, profile=Profile.SOURCE_EXACT):
    if Profile(profile)!=Profile.SOURCE_EXACT:
        raise ValueError('SOURCE_SCHEDULER_POLICY: explicit SOURCE_EXACT required')
    if actor.get('dialect')!='historical-bor':raise ValueError('SOURCE_SCHEDULER_DIALECT')
    if 'policy_contract' in actor or any('runtime_binding' in a for a in actor['animations']):
        raise ValueError('SOURCE_SCHEDULER_COMPAT_TARGET_REJECTED')
    if not isinstance(bank_base,int) or not 0<=bank_base<=0xffffff:
        raise ValueError('SOURCE_SCHEDULER_ADDRESS')
    animations=sorted(actor['animations'],key=lambda a:a['role'])
    if len({a['role'] for a in animations})!=len(animations):raise ValueError('DUPLICATE_ROLE')
    data=bytearray();entries=[];blockers=[];raster_index=0
    for role_id,animation in enumerate(animations):
        role=animation['role'];frames=animation['frames']
        if not 0<len(frames)<=2048:raise ValueError('SOURCE_FRAME_COUNT')
        pointer=bank_base+len(data)
        for f in frames:
            blob=bytearray(pack_source_frame(f));move=f.get('move',0)
            if not isinstance(move,int) or not -32768<=move<=32767:raise ValueError('FRAME_MOVE_RANGE')
            if raster_index>65535:raise ValueError('RASTER_ID_RANGE')
            struct.pack_into('<hH',blob,28,move,raster_index);data.extend(blob);raster_index+=1
        loop=int(animation['properties'].get('loop',[['0']])[-1][0])
        if loop not in (0,1):raise ValueError('ANIMATION_LOOP_BOOLEAN_LOWERING_UNBOUND')
        behavior=ROLE_BEHAVIOR.get(role)
        if behavior is None:blockers.append(dict(capability='ROLE_TRANSITION',role=role,reason='unknown source role semantics'))
        entries.append(dict(role=role,role_id=role_id,frame_count=len(frames),frame_pointer=pointer,
                            loop=loop,behavior=behavior))
    table=bank_base+len(data)
    for e in entries:
        p=e['frame_pointer'];data.extend(struct.pack('<HHHBB8x',e['role_id'],e['frame_count'],p&65535,p>>16,e['loop']))
    if (bank_base&65535)+len(data)>65536:raise ValueError('SOURCE_SCHEDULER_BANK_CAPACITY')
    return bytes(data),dict(format='SOURCE_SCHEDULER_V1',profile=Profile.SOURCE_EXACT.value,
        frame_bytes=FRAME_BYTES,role_bytes=ROLE_BYTES,role_table=table,roles=entries,
        blockers=blockers,full_actor_certification=False)


def link_world_contexts(slots, *, world_address, table_address, reserved_regions=(),
                        profile=Profile.SOURCE_EXACT):
    """Link the current opt-in mirror-WRAM ABI, preserving sparse source slots.

    This is deliberately not the eventual150-actor layout. Resource pressure
    must be visible before a fixture/library gets mistaken for a full engine.
    Zero pointers represent empty source slots and do not renumber parity.
    Extra numeric/media allocations are supplied as reserved half-open ranges.
    """
    if Profile(profile)!=Profile.SOURCE_EXACT:raise ValueError('SOURCE_WORLD_POLICY')
    slots=tuple(slots)
    if len(slots)>SOURCE_SLOT_LIMIT:raise ValueError('SOURCE_WORLD_SLOT_LIMIT: maximum150')
    def address(value):
        if type(value) is not int or value&255 or not 0x100<=value<0x1F00:
            raise ValueError('SOURCE_WORLD_CONTEXT_ADDRESS: aligned bank0 mirror $0100..$1E00 required')
    address(world_address)
    reserved_regions=tuple(reserved_regions)
    regions=[(0,0x100),(0x1F00,0x2000),(world_address,world_address+ACTOR_CONTEXT_BYTES)]
    for start,end in reserved_regions:
        if not (type(start) is int and type(end) is int and 0<=start<end<=0x2000):
            raise ValueError('SOURCE_WORLD_RESERVED_RANGE')
        if world_address<end and start<world_address+ACTOR_CONTEXT_BYTES:
            raise ValueError('SOURCE_WORLD_RESOURCE_OVERLAP: world context intersects reserved storage')
        regions.append((start,end))
    occupied=[]
    for slot,base in enumerate(slots):
        if base is None or base==0:continue
        address(base)
        if any(base<end and start<base+ACTOR_CONTEXT_BYTES for start,end in regions):
            raise ValueError(f'SOURCE_WORLD_RESOURCE_OVERLAP: slot{slot} ${base:04X}')
        regions.append((base,base+ACTOR_CONTEXT_BYTES));occupied.append(slot)
    if type(table_address) is not int or not 0<=table_address<=0xFFFFFF:
        raise ValueError('SOURCE_WORLD_TABLE_ADDRESS')
    # This ABI requires immutable slots. Restrict the table to the unambiguous
    # LoROM windows used by the linker; WRAM mirrors, SRAM and I/O are not ROM.
    bank=table_address>>16
    if not (bank<=0x3F or 0x80<=bank<=0xBF) or table_address&65535<0x8000:
        raise ValueError('SOURCE_WORLD_TABLE_NOT_IMMUTABLE_ROM')
    if (table_address&65535)+len(slots)*2>65536:
        raise ValueError('SOURCE_WORLD_TABLE_BANK_CAPACITY')
    blob=struct.pack('<'+str(len(slots))+'H',*[v or 0 for v in slots])
    return blob,dict(format='SOURCE_WORLD_V1',profile=Profile.SOURCE_EXACT.value,
        world_address=world_address,table_address=table_address,source_slot_count=len(slots),
        occupied_slots=occupied,actor_context_bytes=ACTOR_CONTEXT_BYTES,
        actor_bytes=len(occupied)*ACTOR_CONTEXT_BYTES,world_context_bytes=ACTOR_CONTEXT_BYTES,
        mirror_address_limit=0x1F00,source_slot_limit=SOURCE_SLOT_LIMIT,
        reserved_regions=[list(r) for r in reserved_regions],full_actor_certification=False,
        required_hooks=['lost_entities','gravity_and_holes','think_driver','frame_events',
                        'attack_target_scan_and_effects','displayed_health'])
