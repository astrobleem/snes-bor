"""Pinned is_frozen and expand_time macros; no executable gameplay claim."""
TIMERS = ('stalltime', 'releasetime', 'nextanim', 'nextthink', 'nextmove',
          'magictime', 'guardtime', 'toss_time', 'freezetime', 'mpchargetime',
          'invinctime', 'turntime', 'sealtime')


def frozen(entity, self_entity, *, textbox, smartbomber, time):
    # Source compares the entire type, not a TYPE_TEXTBOX bit mask, and its
    # final clause uses global self rather than the macro's e argument.
    return bool((textbox and entity['type'] != 128) or
                (smartbomber and entity['token'] != smartbomber and entity['type'] != 128) or
                (self_entity['frozen'] and self_entity['freezetime'] > time))


def expand(entity, *, textbox, smartbomber):
    values = {name: entity[name] for name in TIMERS}
    if any(type(v) is not int or not 0 <= v <= 0xffffffff for v in values.values()):
        raise ValueError('SOURCE_FREEZE_TIMER_U32_DOMAIN')
    for name, value in values.items():
        if value and (name != 'freezetime' or textbox or smartbomber):
            entity[name] = (value + 1) & 0xffffffff
