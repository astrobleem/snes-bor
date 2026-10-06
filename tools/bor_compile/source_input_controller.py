"""Explicit SNES control binding for the generic BOR source input snapshot.

Y attack, B attack2, A jump and X special match the existing target controls.
L/R bind attack3/4; Select binds escape. Screenshot has no physical binding.
These are target controls, not inferred BOR keyboard configuration. Refresh
publishes edge masks once per outer input refresh, never per catch-up tick.
"""
from source_script_input import authority

BINDING=[(0x4000,'attack'),(0x8000,'attack2'),(0x0080,'jump'),
         (0x0040,'special'),(0x0020,'attack3'),(0x0010,'attack4'),
         (0x2000,'esc'),(0x1000,'start'),(0x0800,'moveup'),
         (0x0400,'movedown'),(0x0200,'moveleft'),(0x0100,'moveright')]


def convert(raw):
    if not isinstance(raw,int) or not 0<=raw<=65535:raise ValueError('CONTROLLER_WORD_DOMAIN')
    if raw&15:return 0 # Existing native controller signature policy.
    masks={r['name']:r['mask'] for r in authority()['keys']}
    return sum(masks[name] for bit,name in BINDING if raw&bit)


def refresh(previous,raw):
    if len(raw) not in (1,2) or len(previous)!=len(raw):raise ValueError('CONTROLLER_PORT_DOMAIN')
    result=[]
    for old,pad in zip(previous,raw):
        if not isinstance(old,int) or not 0<=old<=0xffffffff:raise ValueError('CONTROLLER_PREVIOUS_DOMAIN')
        held=convert(pad)
        result.append((held,held&~old,old&~held))
    return result


def emit():
    masks={r['name']:r['mask'] for r in authority()['keys']}
    lines=['SourceInputController_Map:', '.a16', '.i16',
           '    sta.l SourceInputController_Raw','    lda #0','    sta.l SourceInputController_Mapped']
    for n,(bit,name) in enumerate(BINDING):
        label='SourceInputController_Map__next_'+str(n)
        lines += ['    lda.l SourceInputController_Raw','    and #$%04X'%bit,'    beq '+label,
                  '    lda.l SourceInputController_Mapped','    ora #$%04X'%masks[name],
                  '    sta.l SourceInputController_Mapped',label+':','.a16','.i16']
    return '\n'.join(lines+['    lda.l SourceInputController_Mapped','    rts'])+'\n'
