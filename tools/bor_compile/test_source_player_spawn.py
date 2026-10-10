import unittest
from source_player_spawn_4086 import spawnplayer
from source_player_spawn_authority import BASE,expected


class PlayerSpawnTests(unittest.TestCase):
    def test_negative_recovery_values_and_index_alias_survive(self):
        result=expected(dict(BASE,index=-1,spawnhealth=-9,spawnmp=-9,weapnum=-2,rush_policy=2))
        self.assertEqual(result[8:14],[3,3,24,-4,-7,-2])
        self.assertEqual(result[14:17],[1,1,0])

    def test_null_constructor_is_fatal_after_index_publication(self):
        players=[dict(name='p',colourmap=0,ent='old')for _ in range(4)]
        state=dict(players=players,level=dict(spawn=[(0,0)]*4,scrolldir=0,setweap=0),hres=256,minz=160,maxz=244,advancex=0,max_wall_height=1000)
        children=[]
        with self.assertRaisesRegex(RuntimeError,'PLAYER_SPAWN_FACTORY_NULL'):
            spawnplayer(state,7,lambda x,z:None,lambda x,z:False,lambda p:children.append(dict(p)) or None,lambda *args:self.fail('weapon called after null construction'))
        self.assertEqual(state['currentspawnplayer'],3)
        self.assertIsNone(players[3]['ent'])
        self.assertEqual(len(children),1)
        self.assertEqual(children[0]['index'],-1)
        self.assertEqual(children[0]['position'],dict(x=110.0,y=0.0,z=165.0))


if __name__=='__main__':unittest.main()
