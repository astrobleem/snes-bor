import unittest
from source_raster_irq import emit


class RasterHook(unittest.TestCase):
    def test_frame_target_cursor_is_initialized_after_the_hook(self):
        contract={k:0x108000+i for i,k in enumerate(['timer_hook','audio_fence','frame_counter','hdma_enable','hdma_current'])}
        code=emit(contract,targets_rom=0xb48000,frame_hook=0xa7d000)
        cursor='    lda.l SourceRaster_TargetBase\n    sta.l SourceRaster_Row\n'
        self.assertEqual(code.count(cursor),1)
        hook=code.index('    jsl $A7D000')
        self.assertGreater(code.index(cursor),hook)
        self.assertLess(code.index(cursor),code.index('    lda.l SourceRaster_InitialBase',hook))
        plain=emit(contract,targets_rom=0xb48000)
        self.assertEqual(plain.count(cursor),1)


if __name__=='__main__':unittest.main()
