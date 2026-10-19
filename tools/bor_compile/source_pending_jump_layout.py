"""Explicit pending-jump rows carved from the serialized source CHR workspace.

The 16-byte source descriptor preserves binary32 arguments and full int id.
The immutable model snapshot handle, marker and generation add eight bytes.
This layout grants no producer, DMA or constructor lease by itself.
"""
from sa1_character_conversion import reused_workspace_descriptors


def layout(entities=128):
    if not 1<=entities<=128:raise ValueError('PENDING_JUMP_ENTITY_COUNT')
    extent=entities*24;limit=0x42d800;base=limit-extent
    jobs=[dict(bpp=8,columns=16,tile_count=896,vram_byte_address=0),dict(bpp=2,columns=16,tile_count=512,vram_byte_address=57344)]
    descriptors=reused_workspace_descriptors(0x420000,base-0x420000,jobs)
    return dict(schema='BYOR_SOURCE_PENDING_JUMP_LAYOUT_V1',entities=entities,stride=24,base=base,end=limit,bytes=extent,
        fields=dict(y=0,x=4,z=8,id=12,model_snapshot=16,marker=18,generation=20),
        descriptor_float_policy='SOURCE_BINARY32_ARGUMENT_BITS',jump_id_policy='SOURCE_INT32',
        chr_workspace=[0x420000,base],chr_capacity=base-0x420000,conversion_descriptors=descriptors,
        physics_neighbor=[0x42d800,0x42e000],requires_serialized_source_chr_owner=True,
        required_lease='all CHR producers use the reduced capacity, previous conversion and DMA disabled before enabling persistent rows, nonzero matching generation and birth/model-copy hooks before exists publication',
        native_storage_bound=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True)


def rehost(entities=128, base=0x7e6200):
    """Plan rows in the explicitly retired original scene-video staging area.

    This is not a lease. The caller must retire its foreground video producer,
    drain its DMA, and suppress legacy visual NMI commits before installation.
    The accepted BG renderer retains its complete BW-RAM maps/ref/queue arena.
    """
    if not 1 <= entities <= 128 or base & 1:
        raise ValueError('PENDING_JUMP_REHOST_GEOMETRY')
    end = base + 24 * entities
    if not 0x7e6200 <= base < end <= 0x7e9a60:
        raise ValueError('PENDING_JUMP_REHOST_EXTENT')
    result = layout(entities)
    result.update(base=base, end=end, storage_profile='RETIRED_SCENE_VIDEO_STAGING',
                  chr_workspace=None, chr_capacity=0xd800, conversion_descriptors=[],
                  requires_serialized_source_chr_owner=False,
                  required_lease='retired original scene-video foreground; drained legacy DMA; legacy visual NMI commits suppressed; exclusive generation-bound WRAM rows; existing source CHR producer remains retired')
    return result
