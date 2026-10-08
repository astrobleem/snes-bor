import unittest
from m4_component_production_sequence import fixed_palette_edges


class RestoreEdges(unittest.TestCase):
    def test_single_frame_raster_mutation_requires_restore(self):
        initial=[0]*236
        report=dict(trace=[dict(updates=[dict(slot=51,color=7),dict(slot=51,color=0)])])
        self.assertEqual(fixed_palette_edges([report],[initial]),(50,185))

    def test_raster_and_frame_changes_bound_one_restore_range(self):
        a=[0]*236;b=a.copy();b[20]=99
        reports=[dict(trace=[dict(updates=[dict(slot=200,color=1)])]),dict(trace=[])]
        self.assertEqual(fixed_palette_edges(reports,[a,b]),(20,36))


if __name__=='__main__':unittest.main()
