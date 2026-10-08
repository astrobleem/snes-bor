import unittest
from source_check_move_4086 import check_move


def entity():
    return dict(update_mark=0, landed_on_platform=None, position=dict(x=80.0,z=220.0),
                nextmove=48, movex=1.5, movez=-.25, trymove=None)


class CheckMoveTests(unittest.TestCase):
    def test_due_direct_movement(self):
        e=entity();check_move(e,48,lambda e:False)
        self.assertEqual(e['position'],dict(x=81.5,z=219.75))
        self.assertEqual((e['movex'],e['movez'],e['nextmove'],e['update_mark']),(1.5,-.25,49,4))

    def test_mark_idempotence_precedes_all_services(self):
        e=entity();e['update_mark']=4;e['landed_on_platform']=object();before=dict(e)
        def query(e): self.fail('duplicate move queried freeze')
        check_move(e,48,query);self.assertEqual(e,before)

    def test_future_and_frozen_displacement_zero(self):
        for future,frozen in ((49,False),(48,True)):
            e=entity();e['nextmove']=future;check_move(e,48,lambda e:frozen)
            self.assertEqual((e['movex'],e['movez'],e['nextmove']),(0.0,0.0,future))
            self.assertEqual(e['position'],dict(x=80.0,z=220.0))

    def test_due_zero_motion_still_advances_timer_and_wraps(self):
        e=entity();e.update(movex=0.0,movez=0.0,nextmove=0xffffffff)
        check_move(e,0xffffffff,lambda e:False);self.assertEqual(e['nextmove'],0)

    def test_explicit_missing_services_only_when_needed(self):
        e=entity();e['landed_on_platform']=object()
        with self.assertRaisesRegex(ValueError,'PLATFORM_BACKEND_REQUIRED'):check_move(e,48,lambda e:False)
        e=entity();e['trymove']=object()
        check_move(e,47,lambda e:False)
        e=entity();e['trymove']=object()
        with self.assertRaisesRegex(ValueError,'TRYMOVE_BACKEND_REQUIRED'):check_move(e,48,lambda e:False)

if __name__=='__main__':unittest.main()
