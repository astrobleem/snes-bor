"""S8 historical BOR timer/effect ABI, opt-in Normal campaign 3 only.

This emits metadata, not a production certificate. stage_timer_host.pasm
implements compatibility callbacks; missing audio/assets must not use stubs.
Source clock reference: source_world_clock.timer_interval. The selected Normal
ACCEPTED_COMPAT host explicitly uses nominal 60Hz target fields, 10/3 timer
ticks and 5/3 gravity ticks per field. It accounts for skipped main services;
it does not replay the source world or claim exact PC PIT/NTSC wall time.
"""
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

SOURCE_SHA256 = '68c54a190c5713b1a42b75898ae9ff5246896de0ded3f8c1247c507681735f41'
CAMPAIGN_ID = 3
GAME_SPEED = 200
COUNTER_SPEED = 400
RESET_TICKS = 40000
CONTINUE_TICKS = 4000
NO_CREDIT_TICKS = 200
PICKUP_TICKS = 600
EFFECT_NONE = 0
EFFECT_RESET_TIMER = 6  # new selected-Normal pickup kind; existing kinds unchanged
WRAM_START = 0x7E5900
WRAM_END = 0x7E591F  # inclusive, 32 bytes; opponent HUD owns 5A00..5ACF

HOST_CONTRACT = {
    'StageTimerHost_PlayerState': 'A=presence bits P1/P2, Y=damage-callback bits; preserve X/D/DBR',
    'StageTimerHost_DamagePlayer': 'X=player 0/1; A=1000, Y=1 drop, type=0, attacker=self; invoke real callback (self-player force halves to 500)',
    'StageTimerHost_EndGame': 'set source endgame; pinned P1/P1 absence typo is intentional',
    'StageTimerHost_Sound': 'A=1 get2 or 2 timeover; source effect volume and pitch 100',
    'StageTimerHost_Collect': 'X=item slot, Y=collector; opponent=item, off-world/pending exclusion and available GET; host requires and consumes collector attack edge; retain slot until retirement',
    'StageTimerHost_Retire': 'X=item slot; execute source suicide/kill cleanup including opponent references, then free slot',
}


def verify_source(path):
    digest = sha256(Path(path).read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError('UNPINNED_BOR_TIMER_SOURCE')
    return digest


def emit_effect_metadata(actors, *, campaign_id):
    """Return a 256-byte runtime-ID table and provenance, without writing files.

actors are source actor_lowering dictionaries with explicitly linked runtime_id.
Never guess an ID, use a display alias, or inherit an accepted actor's effect.
Only reset_timer belongs to this ABI; existing effects remain on their caller's
existing dispatch. The caller must resolve the whole strict queue independently.
"""
    if campaign_id != CAMPAIGN_ID:
        raise ValueError('TIMER_REQUIRES_NORMAL_OPT_IN_CAMPAIGN_3')
    table = bytearray(256)
    seen = set()
    records = []
    for actor in actors:
        runtime_id = actor.get('runtime_id')
        if type(runtime_id) is not int or not 0 <= runtime_id < 256:
            raise ValueError('TIMER_UNBOUND_RUNTIME_ID')
        if runtime_id in seen:
            raise ValueError('TIMER_DUPLICATE_RUNTIME_ID')
        seen.add(runtime_id)
        if actor.get('dialect') != 'historical-bor':
            raise ValueError('TIMER_UNKNOWN_DIALECT')
        behavior = actor.get('behavior', {})
        if behavior.get('default_effect') != 'reset_timer':
            continue
        stats = actor.get('stats', {})
        from model_ir import pickup_effect
        if (stats.get('type') != 'item' or behavior.get('driver') != 'pickup'
                or pickup_effect('historical-bor', str(stats.get('name', '')),
                                 stats.get('health', 0), stats.get('score', 0)) != 'reset_timer'):
            raise ValueError('TIMER_EFFECT_PRECEDENCE_CONFLICT')
        if not actor.get('source_identity') or not actor.get('source_sha256'):
            raise ValueError('TIMER_EFFECT_PROVENANCE_REQUIRED')
        table[runtime_id] = EFFECT_RESET_TIMER
        records.append(dict(runtime_id=runtime_id, effect_id=EFFECT_RESET_TIMER,
                            source_identity=actor['source_identity'],
                            source_sha256=actor['source_sha256'],
                            source_path=actor.get('source_path'),
                            pickup_retire_ticks=PICKUP_TICKS))
    return dict(schema='bor-stage-timer-v1', campaign_id=campaign_id,
                table=bytes(table), records=records, source_sha256=SOURCE_SHA256,
                game_speed=GAME_SPEED, counter_speed=COUNTER_SPEED,
                reset_ticks=RESET_TICKS, required_hosts=dict(HOST_CONTRACT),
                clock_adapter=dict(kind='ACCEPTED_COMPAT_NOMINAL_60HZ_FIELDS',
                                   timer_ratio=[10, 3], gravity_ratio=[5, 3],
                                   max_field_gap=32767, paused_fields_consumed=True),
                required_audio={'get2': 'DATA/SOUNDS/MONEY.WAV',
                                'timeover': 'DATA/SOUNDS/TIMEOVER.WAV'},
                target_bound=False, status='IMPLEMENTED_REQUIRES_PRODUCTION_VALIDATION')


def emit_effect_include(metadata):
    if metadata['campaign_id'] != CAMPAIGN_ID or len(metadata['table']) != 256:
        raise ValueError('TIMER_TABLE_ABI')
    lines = ['; Source-derived S8 effect IDs; only campaign 3 may consume.',
             'StageTimer_ModelEffects:']
    for offset in range(0, 256, 16):
        lines.append('    .db ' + ', '.join(str(v) for v in metadata['table'][offset:offset+16]))
    return '\n'.join(lines) + '\n'


@dataclass
class TimerReference:
    """Executable source-event oracle; not an emulator or runtime proof.

begin_tick is before update_ents; end_tick is after update_scroller. Collection
occurs inside that tick. Paused/render-only calls must invoke neither method.
"""
    campaign_id: int = CAMPAIGN_ID
    left: int = RESET_TICKS
    show_timeover: bool = False
    pending: list[int] = field(default_factory=lambda: [0] * 6)
    in_tick: bool = False

    def reset(self):
        if self.campaign_id == CAMPAIGN_ID:
            self.left = RESET_TICKS

    def absent(self, credits):
        if self.campaign_id == CAMPAIGN_ID:
            self.left = CONTINUE_TICKS if credits > 0 else NO_CREDIT_TICKS

    def collect(self, effect, slot):
        if self.campaign_id != CAMPAIGN_ID or effect != EFFECT_RESET_TIMER:
            return False
        if not 0 <= slot < 6:
            raise ValueError('TIMER_SLOT')
        if self.pending[slot]:
            return False
        self.reset()
        self.pending[slot] = PICKUP_TICKS
        return True

    def begin_tick(self):
        if self.campaign_id != CAMPAIGN_ID:
            return []
        if self.in_tick:
            raise ValueError('TIMER_TICK_PAIR')
        self.in_tick = True
        retired = []
        for slot, left in enumerate(self.pending):
            if left:
                self.pending[slot] -= 1
                if left == 1:
                    retired.append(slot)
        return retired

    def end_tick(self, *, ingame=True, present=3, damage_callbacks=3):
        if self.campaign_id != CAMPAIGN_ID:
            return []
        if not self.in_tick:
            raise ValueError('TIMER_TICK_PAIR')
        self.in_tick = False
        if not ingame:
            return []
        if self.left:
            self.left -= 1
            return []
        events = []
        # Intentional source bug: BOR.C tests P1 twice, not P1 and P2.
        if not present & 1:
            events.append(('endgame',))
        for player in range(2):
            if present & damage_callbacks & (1 << player):
                events.append(('damage', player, 1000, 1, 0, 'self'))
        events.append(('sound', 'timeover'))
        self.reset()
        self.show_timeover = True
        return events

    def display(self):
        value = min(99, max(0, self.left // COUNTER_SPEED))
        show = self.show_timeover  # source draws before clearing the flag
        if value < 99:
            self.show_timeover = False
        return value, show


@dataclass
class FieldClockReference:
    """Integer oracle for ClockService; caller samples at pause transitions."""
    last: int = 0
    phase: int = 0
    gravity_phase: int = 0
    gravity_due: int = 0

    def sample(self, field, *, running=True):
        delta = (field - self.last) & 0xffff
        self.last = field & 0xffff
        if not running:
            return 0
        if delta >= 32768:
            raise ValueError('TIMER_AMBIGUOUS_FIELD_GAP')
        ticks, self.phase = divmod(self.phase + delta * 10, 3)
        gravity, self.gravity_phase = divmod(self.gravity_phase + ticks, 2)
        if self.gravity_due + gravity > 65535:
            raise ValueError('TIMER_GRAVITY_OVERFLOW')
        self.gravity_due += gravity
        return ticks

    def take_gravity(self):
        result, self.gravity_due = self.gravity_due, 0
        return result
