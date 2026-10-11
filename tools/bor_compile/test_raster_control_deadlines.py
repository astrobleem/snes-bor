import copy,unittest
import test_raster_slot_layout as fixtures
from raster_control_deadlines import verify


class ControlDeadlineTests(unittest.TestCase):
    def case(self):
        source=fixtures.SlotLayoutTests().schedule()
        source.update(scanline_math_controls_source_bound=True,source_rgb555_sha256='fixture')
        source['pieces'][0]['bank']=4
        for row in source['trace']:
            before=row['resident_before'];before[0],before[4]=before[4],before[0]
            for event in row['updates']:
                if event['bank']==0:event['bank']=4
        proof=dict(status='PASS',control_traffic_fields=[12,13],resources=dict(
            controls_before_palette=True,control_traffic_rows={'1':[[0x2126,255]]}))
        observer=dict(register_writes=[[f,1,1,104,0x2126,255]for f in (12,13)])
        return source,proof,observer

    def test_conservative_pixel_guard_and_explicit_nonclaims(self):
        result=verify(*self.case())
        self.assertEqual(result['minimum_guarded_margin'],4)
        self.assertFalse(result['native_authored_alpha_rendering_proven'])
        self.assertFalse(result['native_authored_palette_transfer_proven'])

    def test_early_write_wrong_line_and_missing_field_rejected(self):
        source,proof,observer=self.case()
        for index,value,error in ((3,99,'VISIBLE_PIXEL_CONFLICT'),(2,2,'PHYSICAL_ROW_ALIGNMENT')):
            broken=copy.deepcopy(observer);broken['register_writes'][0][index]=value
            with self.assertRaisesRegex(ValueError,error):verify(source,proof,broken)
        observer['register_writes'].pop()
        with self.assertRaisesRegex(ValueError,'REGISTER_IDENTITY'):verify(source,proof,observer)


if __name__=='__main__':unittest.main()
