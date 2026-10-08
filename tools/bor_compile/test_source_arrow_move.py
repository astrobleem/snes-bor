import unittest
from source_arrow_move_4086 import arrow_move


def entity():
    return dict(modeldata=dict(subtype=0, speed=2.0, subject_to_wall=1),
                direction=1, velocity=dict(x=3.0, z=4.0),
                position=dict(x=12.0, z=220.0, y=34.0), autokill=2, ptype=4)


class ArrowMoveTests(unittest.TestCase):
    def test_no_level_moves_and_preserves_z(self):
        e = entity()
        self.assertEqual(arrow_move(e), 1)
        self.assertEqual(e['velocity'], dict(x=2.0, z=4.0))
        self.assertEqual(e['autokill'], 6)

    def test_wall_query_is_short_circuited(self):
        e = entity(); e['modeldata']['subject_to_wall'] = 0
        def query(*args): self.fail('unexpected wall service')
        arrow_move(e, level_present=True, checkwall=query, valid_fall=True)

    def test_contact_without_fall_does_not_kill(self):
        e = entity()
        arrow_move(e, level_present=True, checkwall=lambda x, z: 100.0)
        self.assertNotIn('health', e)
        self.assertEqual(e['autokill'], 6)

    def test_explicit_missing_backends(self):
        e = entity(); e['modeldata']['subtype'] = 11
        with self.assertRaisesRegex(ValueError, 'HOMING_BACKEND_REQUIRED'): arrow_move(e)
        with self.assertRaisesRegex(ValueError, 'WALL_QUERY_REQUIRED'):
            arrow_move(entity(), level_present=True)
        with self.assertRaisesRegex(ValueError, 'WALL_FALL_BACKEND_REQUIRED'):
            arrow_move(entity(), level_present=True, checkwall=lambda x, z: 100.0, valid_fall=True)

if __name__ == '__main__': unittest.main()
