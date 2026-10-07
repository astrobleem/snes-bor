"""Stable source engine function identities; executable domains are separate."""
CALLBACKS=['player_takedamage','player_think','player_trymove','common_spawn',
 'common_drop','common_think','biker_takedamage','arrow_takedamage',
 'common_trymove','common_takedamage','trap_think','obstacle_takedamage',
 'steamer_think','text_think','anything_walk','normal_prepare','common_attack_proc']

def function_id(name):
 if name not in CALLBACKS:raise ValueError('ENGINE_FUNCTION_ID_UNREGISTERED:'+name)
 return CALLBACKS.index(name)+1
