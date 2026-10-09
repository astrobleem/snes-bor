"""Persistent check_move fields below the fixed pain and hit identity rows."""
from source_hit_contact_layout import layout as contact
from sa1_character_conversion import reused_workspace_descriptors


def layout(entities=128):
    neighbor=contact(entities);end=neighbor['controls'];size=entities*8;controls=end-size-64
    jobs=[dict(bpp=8,columns=16,tile_count=896,vram_byte_address=0),dict(bpp=2,columns=16,tile_count=512,vram_byte_address=57344)]
    return dict(schema='BYOR_SOURCE_MOVE_CONTACT_LAYOUT_V1',entities=entities,stride=8,controls=controls,control_bytes=64,
        base=controls+64,end=end,bytes=size,fields=dict(pathblocked=0,grabwalking=4),field_types=dict(pathblocked='uint32',grabwalking='int32'),chr_workspace=[0x420000,controls],
        chr_capacity=controls-0x420000,conversion_descriptors=reused_workspace_descriptors(0x420000,controls-0x420000,jobs),
        pain_neighbor=[neighbor['controls'],neighbor['end']],prior_chr_capacity=neighbor['chr_capacity'],additional_persistent_bytes=size+64,
        birth_policy='source calloc clears unsigned pathblocked and signed grabwalking',model_switch_policy='retain both entity fields',
        required_lease='all CHR, pending jump and contact descriptors use the same smaller capacity; matching independent generation and actual hit birth; retire old conversions before enabling rows',
        native_storage_bound=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True)
