"""Pinned scroller WAIT release; camera/player presence is deliberately independent."""
def release(state, enemies):
    if not state['waiting'] or enemies:
        return False
    if state['noreset'] <= 1:
        product = state['settime'] * 400
        if not -2147483648 <= product <= 2147483647:
            raise ValueError('SOURCE_WAIT_SIGNED_TIMER_OVERFLOW')
        state['timeleft'] = product
    state['waiting'] = 0
    state['go_time'] = (state['time'] + 600) & 0xffffffff
    return True
