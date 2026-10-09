"""Additional persistent source pain timing and current juggle state.

Placed below existing hit controls; prior identities/pending-jump addresses stay
fixed. A plan does not enable any CHR, constructor or model-copy producer.
"""
from source_hit_state_layout import layout as identities
from sa1_character_conversion import reused_workspace_descriptors


def layout(entities=128):
    hit=identities(entities)
    end=hit['controls'];row_bytes=entities*8;controls=end-row_bytes-64;base=controls+64
    jobs=[dict(bpp=8,columns=16,tile_count=896,vram_byte_address=0),dict(bpp=2,columns=16,tile_count=512,vram_byte_address=57344)]
    return dict(schema='BYOR_SOURCE_HIT_CONTACT_LAYOUT_V1',entities=entities,stride=8,base=base,end=end,controls=controls,control_bytes=64,bytes=row_bytes,fields=dict(pain_time=0,juggle_current=4),chr_workspace=[0x420000,controls],chr_capacity=controls-0x420000,conversion_descriptors=reused_workspace_descriptors(0x420000,controls-0x420000,jobs),hit_identity_neighbor=[hit['controls'],hit['end']],prior_chr_capacity=hit['chr_capacity'],additional_persistent_bytes=row_bytes+64,required_lease='all CHR/pending-jump/hit producers agree on this smaller boundary; immutable module and matching canvas generation; actual birth clears pain and installs source model juggle current; model switching retains pain but replaces modeldata juggle metric',native_storage_bound=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True)
