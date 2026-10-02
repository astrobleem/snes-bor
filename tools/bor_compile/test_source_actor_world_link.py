import unittest
from copy import deepcopy
import ast
from pathlib import Path
import re

from source_actor_world_link import link_world_program


class WorldProgramTests(unittest.TestCase):
    def fixture(self):
        names=('idle','pain','rise','attack1','walk')
        actor=dict(dialect='historical-bor',source_identity=['project','independent-model'],
                   stats=dict(type='enemy',health='100'),
                   animations=[dict(role=n,properties={}) for n in names])
        scheduler=dict(role_table=0x1DC000,roles=[dict(role=n,role_id=i) for i,n in enumerate(names)])
        return actor,scheduler

    def test_source_unchanged_and_deterministic(self):
        actor,scheduler=self.fixture();before=deepcopy(actor)
        first,manifest=link_world_program(actor,scheduler,7)
        self.assertEqual(len(first),32)
        self.assertEqual((first,manifest),link_world_program(actor,scheduler,7))
        self.assertEqual(actor,before)
        self.assertFalse(manifest['source_certified'])

    def test_source_range_not_default_substitution(self):
        actor,scheduler=self.fixture()
        actor['animations'][3]['properties']['range']=[['-3','67']]
        self.assertEqual(link_world_program(actor,scheduler,7)[1]['source_range'],[-3,67])

    def test_player_requires_explicit_control_scope(self):
        actor,scheduler=self.fixture();actor['stats']['type']='player'
        with self.assertRaisesRegex(ValueError,'SOURCE_PLAYER_CONTROLLER'):
            link_world_program(actor,scheduler,0)
        self.assertEqual(link_world_program(actor,scheduler,0,controlled_player_action=True)[1]['scope'],
                         'CONTROLLED_ATTACK1_ACTION')

    def test_no_compat_fallback(self):
        actor,scheduler=self.fixture()
        with self.assertRaisesRegex(ValueError,'SOURCE_WORLD_POLICY'):
            link_world_program(actor,scheduler,0,profile='ACCEPTED_COMPAT')

    def test_foreign_dialect_is_not_bor(self):
        actor,scheduler=self.fixture();actor['dialect']='unspecified'
        with self.assertRaisesRegex(ValueError,'SOURCE_WORLD_DIALECT'):
            link_world_program(actor,scheduler,0)

    def test_additional_attack_not_silently_dropped(self):
        actor,scheduler=self.fixture();scheduler['roles'].append(dict(role='attack2',role_id=5))
        with self.assertRaisesRegex(ValueError,'SOURCE_AI_EXTRA_ROLE_SEMANTICS'):
            link_world_program(actor,scheduler,0)

    def test_health_not_truncated(self):
        actor,scheduler=self.fixture();actor['stats']['health']='400'
        with self.assertRaisesRegex(ValueError,'SOURCE_WORLD_HEALTH_WIDTH'):
            link_world_program(actor,scheduler,0)

    def test_effect_blocker_precedes_enemy_role_requirement(self):
        actor,scheduler=self.fixture();actor['stats']['type']='item'
        actor['behavior']={'default_effect':'reset_timer'}
        with self.assertRaisesRegex(ValueError,'SPECIAL_EFFECT_GAMEPLAY_TIMER_LIFECYCLE'):
            link_world_program(actor,scheduler,0)

    def test_no_source_name_behavior_selection(self):
        root=Path(__file__).resolve().parents[2]
        forbidden={'kula','time','ramon','crab','lobster'}
        for path in (root/'src/core').glob('actor_source*.pasm'):
            code='\n'.join(line.split(';',1)[0] for line in path.read_text().splitlines())
            self.assertFalse(set(re.findall(r'\b\w+\b',code.lower())) & forbidden, str(path))
        for path in (root/'tools/bor_compile').glob('source_actor*.py'):
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Constant) and isinstance(node.value,str):
                    self.assertNotIn(node.value.casefold(),forbidden,str(path))


if __name__=='__main__':unittest.main()
