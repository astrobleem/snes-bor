"""Bounded lossless-cover and retained hardware-resource regression."""
import unittest
from test_source_instance_transport import InstanceTransportTests
from source_frame_transport import compile_frames, retained_working_set


class CompactTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        InstanceTransportTests.setUpClass()
        cls.source=InstanceTransportTests.source
        cls.manifest=InstanceTransportTests.manifest
        cls.plan=compile_frames(cls.source,cls.manifest,group_future=True,compact=True)

    def test_source_pixels(self):
        InstanceTransportTests.test_every_source_pixel_survives_static_placement(self)

    def test_retained_leases(self):
        InstanceTransportTests.test_lease_never_overwrites_a_retained_older_frame(self)

    def test_blocked_transition_now_fits_without_relocation(self):
        live=retained_working_set(self.plan,[4,3],[5,5])
        self.assertEqual(live['bytes'],7680)
        self.assertEqual(live['layout_conflicts'],[])
        self.assertEqual(live['status'],'FITS_STATIC_LAYOUT')
        self.assertFalse(live['hardware_ready'])

    def test_repeat_is_deterministic(self):
        self.assertEqual(self.plan,compile_frames(self.source,self.manifest,group_future=True,compact=True))


if __name__=='__main__':unittest.main()
