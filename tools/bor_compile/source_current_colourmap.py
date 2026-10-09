"""Source frozen-map identity requirements and independent active palette layout."""
from source_profile import document
from source_model_core_4086 import integer
from source_model_palette_service_native import derive as palette_models
from source_move_contact_layout import layout as movement
from sa1_character_conversion import reused_workspace_descriptors


def derive(source):
    r=palette_models(source);models=[]
    documents={d['sha256']:d for k,(n,_)in source.index.items()if k.endswith('.txt')for d in (document(source,n),)}
    for m in r['models']:
        doc=documents[m['source_sha256']]
        frozen=0
        for row in doc['directives']:
            if row['directive']=='subclass':raise ValueError('CURRENT_COLOURMAP_SUBCLASS_REQUIRED')
            if row['directive']=='fmap':frozen=integer(row['values'])
        models.append(dict(id=m['id'],identity=m['identity'],source_sha256=m['source_sha256'],frozen_map=frozen,maps_loaded=m['maps_loaded'],palette_policy=m['palettes']['policy'],palette_hashes=[p['colors_sha256']for p in [m['palettes']['base'],*m['palettes']['alternates']]if p]))
    return dict(schema='BYOR_CURRENT_COLOURMAP_REQUIREMENTS_V1',engine_commit=r['engine_commit'],models=models,palette_pointers='active palette owner/index is independent from entity.map restore index',colourmap_model_mutators_admitted=False,production_binding=False,no_color_reduction=True)


def layout(entities=128):
    neighbor=movement(entities);size=entities*12;end=neighbor['controls'];base=end-size;controls=base-64;capacity=controls-0x420000
    jobs=[dict(bpp=8,columns=16,tile_count=896,vram_byte_address=0),dict(bpp=2,columns=16,tile_count=512,vram_byte_address=57344)]
    return dict(schema='BYOR_CURRENT_COLOURMAP_LAYOUT_V1',entities=entities,stride=12,controls=controls,control_bytes=64,base=base,end=end,bytes=size,fields=dict(owner_model=0,active_map=2,generation=4,marker=8,physical_slot=10),chr_workspace=[0x420000,controls],chr_capacity=capacity,conversion_descriptors=reused_workspace_descriptors(0x420000,capacity,jobs),prior_chr_capacity=neighbor['chr_capacity'],additional_persistent_bytes=size+64,movement_neighbor=[neighbor['controls'],neighbor['end']],base_restore_map='existing entity BODY map+48; frozen selection must not overwrite it',birth_and_model_reset_required=True,all_source_chr_producers_must_use_reduced_capacity=True,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True)
