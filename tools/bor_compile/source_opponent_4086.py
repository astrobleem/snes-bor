"""Exact set_opponent assignments over a checked physical owner graph."""
from source_hit_prelude_4086 import top_owner


def set_opponent(pool, ent, other):
    if ent is None:
        return
    realself = top_owner(pool, ent)
    realother = top_owner(pool, other) if other is not None else None
    pool[ent]['opponent'] = realother
    pool[realself]['opponent'] = realother
    if realother is not None:
        pool[other]['opponent'] = realself
        pool[realother]['opponent'] = realself
