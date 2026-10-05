"""Derive a bounded fixture view after the complete frontpanel stamp arena."""
from pathlib import Path
from _harness import pasm_constant_in


def fixture_base(root,record_bytes):
    def c(file,name):return pasm_constant_in(str(Path(root)/file),name)
    cache='src/core/stream_cache_fp.pasm'
    end=c(cache,'StreamCacheFp_SlotStamp')+c(cache,'STREAM_FP_CACHE_SLOTS')
    base=(end+31)&~31
    if record_bytes<=0 or base+record_bytes>c('src/core/vm/vm_consts.pasm','VmSlots_Wram'):
        raise ValueError('SOURCE_ENTITY_FIXTURE_WRAM_CAPACITY')
    return base
