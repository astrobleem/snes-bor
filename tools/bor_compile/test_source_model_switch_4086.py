from pathlib import Path
import unittest
from compiler import Source
from source_model_switch_requirements import derive
from source_model_switch_4086 import set_weapon


class ModelSwitch(unittest.TestCase):
    def test_authored_weapon_dependencies_retain_distinct_declared_type_and_frame_identity(self):
        r=derive(Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak'))
        by_name={m['identity']:m for m in r['models']}
        a,b=by_name['He_Man'],by_name['He_ManB']
        self.assertEqual(a['weapon_ids'],[b['id'],a['id']]);self.assertEqual(b['weapon_ids'],a['weapon_ids'])
        self.assertEqual(a['declared_type'],'player');self.assertEqual(b['declared_type'],'none')
        self.assertEqual(a['weaploss'],[3,0]);self.assertEqual(b['weaploss'],[3,0])
        self.assertEqual(a['weapon_frame_events'][0]['weapon_number'],1)
        self.assertEqual(b['weapon_frame_events'][0]['weapon_number'],2)
        self.assertEqual(r['maximum_animations'],168);self.assertEqual(r['cached_animation_map_bytes'],5376)
        self.assertFalse(r['native_model_switch_bound']);self.assertFalse(r['foreign_profile_admitted'])
        self.assertFalse(any(m['rejections'] for m in r['models']))

    def test_undefined_negative_weapon_index_cannot_alias_python_last_model(self):
        e=dict(modeldata=dict(type=1,weaploss=[3,0],weapon=[-1],numweapons=1),playerindex=0)
        owner=dict(player_weapons=[77],models=[object()],level_weapon=5)
        with self.assertRaisesRegex(ValueError,'SOURCE_WEAPON_CACHED_INDEX_UNDEFINED'):set_weapon(e,1,0,owner)
        self.assertEqual(owner['player_weapons'],[1])


if __name__=='__main__':unittest.main()
