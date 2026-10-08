"""Pinned perform_atchain policy with mandatory animation continuation.

Model chain entries are one-based indices into the configured attack directory.
The source indexes before checking chainlength; undefined source accesses fail
explicitly instead of wrapping or treating an invalid entry as attack one.
"""
from enum import IntEnum


class Service(IntEnum):
    SET_ANIMATION = 1


def execute(entity, context, valid, target):
    data = entity['modeldata']
    if data['chainlength'] <= 0:
        return 0
    if entity['combotime'] > context['time']:
        if entity['combostep'][0] == 0x7fffffff:
            raise ValueError('SOURCE_ATTACK_CHAIN_SIGNED_OVERFLOW')
        entity['combostep'][0] += 1
    else:
        entity['combostep'][0] = 1

    def entry():
        step = entity['combostep'][0]
        if not 1 <= step <= len(data['atchain']):
            raise ValueError('SOURCE_ATTACK_CHAIN_INDEX_UNDEFINED')
        return data['atchain'][step - 1]

    def animation(code):
        if not 1 <= code <= len(context['attacks']):
            raise ValueError('SOURCE_ATTACK_CHAIN_ROLE_UNDEFINED')
        return context['attacks'][code - 1]

    if entry() == 0:
        entity['combostep'][0] = 1
    picked = 0
    if valid(animation(entry())):
        ranged = data['combostyle'] & 1
        if (((entity['combostep'][0] == 1 or not ranged) and data['type'] & 1)
                or (not ranged and target(animation(data['atchain'][0]), 0))
                or (ranged and target(animation(entry()), 0))):
            picked = 1
        elif ranged and entity['combostep'][0] != 1:
            while True:
                entity['combostep'][0] += 1
                if entity['combostep'][0] > data['chainlength']:
                    break
                code = entry()
                if (code and valid(animation(code)) and
                        (entity['combostep'][0] == data['chainlength'] or
                         target(animation(code), 0))):
                    picked = 1
                    break
    else:
        entity['combostep'][0] = 0
    if picked:
        entity['takeaction'] = 17
        # Literal set_attacking macro from the pinned header.
        entity['attacking'] = 1
        entity['idling'] = 0
        yield Service.SET_ANIMATION, entity, animation(entry()), 1
    # These reads deliberately occur after the real animation callback.
    if not picked or entity['combostep'][0] > entity['modeldata']['chainlength']:
        entity['combostep'][0] = 0
    if entity['modeldata']['combostyle'] & 2:
        entity['combotime'] = (context['time'] + context['combodelay']) & 0xffffffff
    return picked
