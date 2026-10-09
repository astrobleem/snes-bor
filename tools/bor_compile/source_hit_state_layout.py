"""Persistent source hit identities carved from serialized CHR staging.

Generation-bound birth owns these identities. Model switching retains them.
This plan grants no live CHR producer or gameplay memory lease.
"""
from source_pending_jump_layout import layout as jump_layout
from sa1_character_conversion import reused_workspace_descriptors


def layout(entities=128):
    jump=jump_layout(entities)
    stride=16;control_bytes=64;row_bytes=entities*stride
    end=jump['base'];base=end-row_bytes;controls=base-control_bytes
    jobs=[dict(bpp=8,columns=16,tile_count=896,vram_byte_address=0),dict(bpp=2,columns=16,tile_count=512,vram_byte_address=57344)]
    descriptors=reused_workspace_descriptors(0x420000,controls-0x420000,jobs)
    return dict(schema='BYOR_SOURCE_HIT_STATE_LAYOUT_V1',entities=entities,stride=stride,base=base,end=end,bytes=row_bytes,controls=controls,control_bytes=control_bytes,
        fields=dict(attack_id=0,hit_by_attack_id=4,generation=8,marker=12,physical_slot=14),
        birth_policy='source calloc clears both unsigned identities; independent lease generation and physical-slot marker',
        model_switch_policy='retain entity attack_id and hit_by_attack_id',
        chr_workspace=[0x420000,controls],chr_capacity=controls-0x420000,conversion_descriptors=descriptors,
        pending_jump_neighbor=[jump['base'],jump['end']],physics_neighbor=jump['physics_neighbor'],
        prior_chr_capacity=jump['chr_capacity'],persistent_bytes=row_bytes+control_bytes,
        requires_serialized_source_chr_owner=True,
        required_lease='all CHR producers use the reduced capacity; retire previous conversions/DMA before enabling persistent rows; bind nonzero independent generation; clear actual birth before exists publication',
        native_storage_bound=False,production_memory_lease=False,native_combat_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
