"""Closed smartspawn stage properties after the real constructor returns.

Music/events are explicit services. This reference does not admit gameplay.
"""
def post(e, row, player_count, maps_loaded, boss_music_present):
    if not 1<=player_count<=4:raise ValueError('SMARTSPAWN_PLAYER_COUNT_DOMAIN')
    trace=[]
    if row['alias']:e['name']=row['alias'][:47]
    e['itemplayer_count']=0
    e['spawntype']=1
    health=row['health'][player_count-1]
    if health:e['health']=e['model_health']=health
    if not e['map']and row['map']:
        which=row['map']&0xffffffff
        if which>maps_loaded:which=0
        e['map']=which;e['palette']=which if which>0 else 0;trace.append('COLOURMAP')
    e['boss']=row['boss']
    if row['boss']and boss_music_present:trace.append('BOSS_MUSIC')
    trace.extend(('ONSPAWN','STAGE_SPAWN_SCRIPT'))
    return trace
