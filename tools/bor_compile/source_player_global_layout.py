"""Player death globals below the VM tail limit, following existing actor state."""
GLOBAL_FIELDS=('firstplayer','livescheat','nomaxrushreset_policy','noshare','credits','nodropen')
PLAYER_FIELDS=('credits','joining','spawnhealth','spawnmp','nomaxrushreset')

def layout(tail):
 base=tail['base']+tail['entity_state_bytes'];end=base+144
 if end>tail['end']:raise ValueError('FOREIGN_VM_TAIL_PLAYER_GLOBAL_CAPACITY')
 return dict(schema='BYOR_PLAYER_GLOBAL_LAYOUT_V1',base=base,bytes=144,end=end,controls=base,control_bytes=32,global_base=base+32,global_bytes=32,player_base=base+64,player_stride=20,players=4,global_fields=list(GLOBAL_FIELDS),player_fields=list(PLAYER_FIELDS),live_slot_count=tail['live_slot_count'],remaining_bytes=tail['end']-end,existing_lives_scores_weapon_timer_reused=True,runtime_owner_bound=False,production_memory_lease=False)
