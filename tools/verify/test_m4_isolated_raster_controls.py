import unittest
from pathlib import Path
from m4_isolated_raster_obj_native import compile_rom
from raster_math_windows import compile_mask


class NativeControlAdmissionTests(unittest.TestCase):
    def fixture(self):
        descriptor=compile_mask([True]*256)
        controls=dict(scanline_math_controls_source_bound=True,source_rgb555_sha256='source',metadata={},
            selected_modes={'0':'add'},compiled_color_window_descriptors={'0':descriptor})
        schedule=dict(color_math='additive',scanline_math_controls_source_bound=True,source_rgb555_sha256='source',metadata={},
            physical_slot_layout=dict(status='PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN'))
        return schedule,controls

    def test_main_screen_requires_complete_source_bound_controls(self):
        schedule,controls=self.fixture()
        with self.assertRaisesRegex(ValueError,'MAIN_COMPLETE_SOURCE_CONTROLS'):
            compile_rom(b'',Path('unused'),{},schedule,Path('unused'),control_traffic=controls,authored_context={})
        controls['source_rgb555_sha256']='different source'
        with self.assertRaisesRegex(ValueError,'MAIN_COMPLETE_SOURCE_CONTROLS'):
            compile_rom(b'',Path('unused'),{},schedule,Path('unused'),control_traffic=controls,authored_context={})

    def test_window_owner_bits_and_clip_policy_are_explicit(self):
        for field,value in (('wobjsel_color_bits',0x21),('wobjlog_color_bits',1),('cgwsel_clip_and_prevent_bits',0)):
            schedule,controls=self.fixture();controls['compiled_color_window_descriptors']['0'][field]=value
            with self.assertRaisesRegex(ValueError,'WINDOW_ROUTING_DOMAIN'):
                compile_rom(b'',Path('unused'),{},schedule,Path('unused'),control_traffic=controls,authored_context={})


if __name__=='__main__':unittest.main()
