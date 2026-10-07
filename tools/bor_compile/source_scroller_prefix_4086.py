"""Exact uint32 time/freeze/completed prefix before the source queue branch."""


def begin(state):
    state['scrolldx']=state['scrolldy']=0
    if state['time'] & 0xffffffff < state['advancetime'] & 0xffffffff or state['freezeall']:
        return False
    state['advancetime']=state['time'] & 0xffffffff
    return not bool(state['completed'])
