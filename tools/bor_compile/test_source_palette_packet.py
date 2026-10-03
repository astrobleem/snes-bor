import unittest
from source_palette_packet import link_packet_palettes


class PalettePacketTests(unittest.TestCase):
    def test_transaction_admission_and_calling_convention(self):
        template='    sta.l S7Pub_State+$F2\n    ldx #0\nS7Packet_Submit__free:\nS7Packet2_Submit__free:\n    adc #544\n    lda #544\n    sta.l DmaRequest_Length\n'
        code,overlays=link_packet_palettes(template,
            dict(StreamCacheFp_Slot2Tile=0x7FB000,Core_Dma_TransferOam=0x9876),'S7Palette_Transfer:\n    rtl\n',staging_cache=True)
        self.assertIn('adc #608',code)
        self.assertIn('lda #608\n    sta.l DmaRequest_Length',code)
        self.assertNotIn('sta.l $7FA840,y',code)
        self.assertIn('sta.w $A840,y',code)
        self.assertIn('sta.w $A880,y',code)
        self.assertIn('    phx\n    phy\n    phb',code)
        self.assertIn('    plb\n    ply\n    plx',code)
        self.assertIn('PreparePalette_0_empty',code)
        self.assertIn('PreparePalette_1_empty',code)
        self.assertIn('cmp.l $7FA8D0',code)
        self.assertIn('sta.l $7FA8D6',code)
        self.assertEqual(overlays,[(0x9876,bytes.fromhex('c231bf8504'))])
        for name in ('Kula','Crab','Angel','Lobster','Gold','Mary'):
            self.assertNotIn(name,code)

    def test_fail_closed_memory_and_template(self):
        with self.assertRaisesRegex(ValueError,'WRAM_OWNERSHIP'):
            link_packet_palettes('',dict(StreamCacheFp_Slot2Tile=0x7FA880),'')
        with self.assertRaisesRegex(ValueError,'RESET_BOUNDARY'):
            link_packet_palettes('',dict(StreamCacheFp_Slot2Tile=0x7FB000),'',staging_cache=True)


if __name__=='__main__':unittest.main()
