"""Private cold publisher copy whose ready marker follows actual unblank."""
from __future__ import annotations

COLD_BANK=42


def emit(publisher):
    """Preserve accepted source, changing only bank and cold-ready ordering."""
    if '.bank 57\n'not in publisher:raise ValueError('COLD_READY_SOURCE_BANK')
    begin=publisher.index('OnlineComplete:');end=publisher.index('OnlineNoop:',begin)
    body=publisher[begin:end]
    ready=' lda #46264\n sta.l 8387478\n'
    unblank=' lda #15\n sta.l $002100\n rep #$20\n.a16\n'
    if body.count(ready)!=1 or body.count(unblank)!=1:
        raise ValueError('COLD_READY_SOURCE_SHAPE')
    # No hardware write, source work or clock/input change is added. A16 is
    # re-established by the existing unblank tail before the moved word store.
    body=body.replace(ready,'',1).replace(unblank,unblank+ready+'ColdReadyPublished:\n.a16\n.i16\n',1)
    result=publisher[:begin]+body+publisher[end:]
    return result.replace('.bank 57\n',f'.bank {COLD_BANK}\n')
