import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from build_rom import vm_wram_layout_ranges
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_converter'))
from openbor_script.compiler import Module,Instr
from openbor_script.module import pack_module,ModuleLimitError


class VMLayoutTests(unittest.TestCase):
    def symbols(self):return dict(VmCode_Wram=0x7e9aa0,VM_CODE_MAX=17760,VmGuardLo=0x7ee000,
        SceneVideo_FrameStaging=0x7e6200,SceneVideo_MsuDmaProbe=0x7e9a9a)

    def test_larger_script_code_does_not_lease_live_scene_video_storage(self):
        s=self.symbols();self.assertEqual(vm_wram_layout_ranges(s)['code'],[0x7e9aa0,0x7ee000])
        s.update(VmCode_Wram=0x7e6000,VM_CODE_MAX=32768)
        with self.assertRaisesRegex(ValueError,'SCENE_VIDEO_OVERLAP'):vm_wram_layout_ranges(s)

    def test_code_cannot_spill_into_guard(self):
        s=self.symbols();s['VM_CODE_MAX']+=1
        with self.assertRaisesRegex(ValueError,'CODE_RANGE_INVALID'):vm_wram_layout_ranges(s)

    def test_packed_metadata_also_counts_toward_real_code_reservation(self):
        m=Module();m.instructions=[Instr(43) for _ in range(2100)]
        m.slots=[(0,0,0,0) for _ in range(121)]
        # Instruction and slot counts are separately legal; their packed
        # sections together exceed the physical code reservation.
        with self.assertRaisesRegex(ModuleLimitError,'VM_CODE_MAX=17760'):pack_module(m)


if __name__=='__main__':unittest.main()
