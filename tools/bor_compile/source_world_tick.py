"""4086 entity traversal owner, with explicit resumable backend requests.

The owner determines order and tick completion. Requests are requirements, not
implemented gameplay handlers. In particular, yielding ANIMATION does not
execute update_frame, and yielding POST_UPDATE does not implement gravity.
Mutable order is the source ent_list permutation, separate from stable tokens.
"""
from dataclasses import dataclass
from enum import IntEnum


class Service(IntEnum):
    RESET_MARK = 1
    LOST = 2
    FROZEN = 3
    EXPAND_TIME = 4
    SCRIPT = 5
    AI = 6
    ANIMATION = 7
    ATTACK = 8
    HEALTH = 9
    VELOCITY = 10
    POST_UPDATE = 11
    CLEAR_MOVE = 12


@dataclass
class Entity:
    alive: bool = False
    birth: int = 0
    frozen: bool = False


@dataclass
class World:
    entities: list[Entity]
    order: list[int]
    maximum: int
    time: int
    level: bool = True
    active: bool = False
    completed: bool = False

    def validate(self):
        if (not 1 <= len(self.entities) <= 128 or
                sorted(self.order) != list(range(len(self.entities))) or
                not 0 <= self.maximum <= len(self.entities) or
                not 0 <= self.time <= 0xffffffff or
                any(self.entities[s].alive for s in self.order[self.maximum:])):
            raise ValueError('SOURCE_WORLD_ORDER_OR_LIVE_PREFIX')

    def spawn_slot(self):
        """First free ent_list entry, not first free physical slot."""
        for slot in self.order:
            e = self.entities[slot]
            if not e.alive:
                e.alive = True
                e.birth = self.time
                self.maximum = max(self.maximum, sum(e.alive for e in self.entities))
                return slot
        return None

    def tick(self):
        self.validate()
        if self.active:
            raise ValueError('SOURCE_WORLD_REENTRANT_TICK')
        self.active = True
        self.completed = False
        epoch = self.time
        # The loop bound is live: callbacks can increase ent_max by spawning.
        i = 0
        while i < self.maximum:
            if self.time != epoch:
                raise ValueError('SOURCE_WORLD_TIME_CHANGED_DURING_TICK')
            slot = self.order[i]
            e = self.entities[slot]
            if e.alive and e.birth != epoch:
                yield Service.RESET_MARK, slot
                if self.level:
                    yield Service.LOST, slot
                if e.alive:
                    yield Service.FROZEN, slot
                    if e.frozen:
                        yield Service.EXPAND_TIME, slot
                    else:
                        for service in (Service.SCRIPT, Service.AI, Service.ANIMATION,
                                        Service.ATTACK, Service.HEALTH, Service.VELOCITY):
                            yield service, slot
                            # Pinned update_ents checks exists after SCRIPT, AI,
                            # ANIMATION and ATTACK, but not after HEALTH.
                            if service in (Service.SCRIPT, Service.AI, Service.ANIMATION,
                                           Service.ATTACK) and not e.alive:
                                break
            i += 1
        count = sum(e.alive for e in self.entities)
        if count:
            if self.maximum == count:
                i = 0
                while i < self.maximum:
                    slot = self.order[i]
                    if self.entities[slot].alive:
                        yield Service.POST_UPDATE, slot
                    i += 1
            else:
                hole = -1
                i = 0
                while i < self.maximum:
                    if not self.entities[self.order[i]].alive and hole < 0:
                        hole = i
                    elif self.entities[self.order[i]].alive and hole >= 0:
                        self.order[i], self.order[hole] = self.order[hole], self.order[i]
                        hole += 1
                    # This is intentionally evaluated AFTER the swap, as in
                    # arrange_ents, rather than post-updating the moved entity.
                    slot = self.order[i]
                    if self.entities[slot].alive:
                        yield Service.POST_UPDATE, slot
                    i += 1
                self.maximum = sum(e.alive for e in self.entities)
            i = 0
            while i < self.maximum:
                yield Service.CLEAR_MOVE, self.order[i]
                i += 1
        # arrange_ents returns immediately for count zero: ent_max is retained.
        if self.time != epoch:
            raise ValueError('SOURCE_WORLD_TIME_CHANGED_DURING_TICK')
        self.completed = True
        self.active = False

    def commit(self):
        if self.active or not self.completed:
            raise ValueError('SOURCE_WORLD_INCOMPLETE_TICK')
        self.time = (self.time + 1) & 0xffffffff
        self.completed = False
