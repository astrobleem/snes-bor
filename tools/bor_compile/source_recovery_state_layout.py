"""Generation-bound blink/time below all existing scoped control snapshots."""
from source_scoped_control_stack import layout as neighbor_layout
from sa1_character_conversion import reused_workspace_descriptors

def layout(entities=128):
 if not 1<=entities<=128:raise ValueError('RECOVERY_STATE_ENTITY_COUNT')
 n=neighbor_layout();end=n['controls'];size=entities*16;base=end-size;controls=base-64
 jobs=[dict(bpp=8,columns=16,tile_count=896,vram_byte_address=0),dict(bpp=2,columns=16,tile_count=512,vram_byte_address=57344)]
 return dict(schema='BYOR_SOURCE_RECOVERY_STATE_LAYOUT_V1',entities=entities,stride=16,base=base,end=end,bytes=size,controls=controls,control_bytes=64,
  fields=dict(blink=0,invinctime=4,generation=8,marker=12,physical_slot=14),chr_workspace=[0x420000,controls],chr_capacity=controls-0x420000,
  conversion_descriptors=reused_workspace_descriptors(0x420000,controls-0x420000,jobs),scoped_control_neighbor=[n['controls'],n['end']],prior_chr_capacity=n['chr_capacity'],
  additional_persistent_bytes=size+64,existing_juggle_owner='source_hit_contact_layout juggle_current',
  birth_policy='calloc blink and invinctime zero before exists publication',model_switch_policy='retain both entity fields',
  required_lease='all CHR producers use this reduced boundary; conversions and DMA retired before lifetime enable; nonzero independent generation and actual birth initialization',
  native_storage_bound=False,production_memory_lease=False,actual_constructor_bound=False,actual_recovery_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
