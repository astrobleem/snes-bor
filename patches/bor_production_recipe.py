"""Preserved production-only recipe extracted from hud1487/hud1543 workers.
Supply the 4MiB retained image, exact symbol dictionaries, donor root and MSU.
No emulator or worker launch occurs here. This extraction has not been executed.
"""
import bor_production_candidate as candidate

def compose_v1487(root,raw,main,world,msu):
    patched=raw
    # Original BOR.C character selection assigns player[i].colourmap=i.
    # Limit this private experiment to the authenticated Kula/P2 context.
    read=candidate.connected.link.read
    start=main['G13_EnableP2Session__init_slot']
    prefix=bytes.fromhex('22218207 2265e900 c220 a90000 8543 8545 e220')
    tail=bytes.fromhex('225e8307 2b c231')
    caller=read(patched,start,150)
    if start!=0x0784f5 or caller.count(prefix+tail)!=1 or main['CHAR_MAP_INDEX']!=52 or main['CHAR_ROSTER_INDEX']!=12:
        raise ValueError('P2 creation or retained map layout differs')
    addr=start+caller.index(prefix+tail)+len(prefix)
    helper=0x28c540
    # Incoming A8. Preserve A and P for the original context exit. JML
    # reuses the original long return address and stack from the caller.
    code=bytes.fromhex('08 48 a50c c916 d004 a901 8534 68 28 5c5e8307')
    if main['G13_Player2_ContextExit']!=0x07835e or code[8+code[7]]!=0x68:
        raise ValueError('P2 private helper contract mismatch')
    for catalog in (main,world):
        if any(isinstance(v,int) and helper<=v<helper+len(code) for v in catalog.values()):
            raise ValueError('test helper collides with linked label')
    patched,touched=candidate.finish_bytes(patched,patched,(),((helper,code),),((addr,tail[:4],bytes.fromhex('2240c528')),))
    import bor_split_budget_v1473 as share
    patched=share.compose(root,raw,patched)
    import bor_blue_impact_v1444 as blue
    patched=blue.fix(patched,msu,candidate,(main,world))
    import bor_piece_reuse_v1454 as piece
    patched=piece.fix(patched,candidate,(main,world))
    import bor_piece_count_v1455 as count
    patched=count.fix(patched,candidate,(main,world))
    import bor_repeat_admit_v1487 as split
    patched=split.fix(patched,candidate,(main,world))
    return patched

def compose_v1543(image,sy):
    from bor_restart_burst_v1494 import patch
    from bor_normal_atlas_v1543 import correct
    image=patch(image,sy)
    return correct(image,sy)
