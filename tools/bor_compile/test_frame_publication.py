import struct
import unittest
from frame_publication import pack_descriptor,oam_oracle,transfer_requirement,piece_word
from frame_publication_inventory import measure_frame
from PIL import Image
import io


class PublicationTests(unittest.TestCase):
    def frame(self):
        return dict(chunks=[dict(right_xy=[-3,-4],left_xy=[-12,-4],tile=256)],
                    writes=[dict(size=512)])

    def test_map_byte_and_source_not_mutated(self):
        frame=self.frame()
        for selector in (0,1,3,4,5,255):
            header,pieces=pack_descriptor(frame,role=2,index=3,map_selector=selector,piece_address=0x298000)
            self.assertEqual(len(header),12)
            self.assertEqual(struct.unpack('<HHHBBI',header),(2,3,1,selector,0,0x298000))
            self.assertEqual(len(pieces),8)
        self.assertEqual(frame,self.frame())

    def test_facing_and_tile_high_bit(self):
        _,pieces=pack_descriptor(self.frame(),role=0,index=0,map_selector=4,piece_address=0)
        right=oam_oracle(pieces,anchor_x=100,anchor_y=100,facing_left=False,palette_slot=6)[0]
        left=oam_oracle(pieces,anchor_x=100,anchor_y=100,facing_left=True,palette_slot=6)[0]
        self.assertEqual((right['x'],left['x'],right['y'],left['y']),(97,88,96,96))
        self.assertEqual(right['low'][3],0x3d)
        self.assertEqual(left['low'][3],0x7d)

    def test_partial_top_and_negative_x_are_small(self):
        _,pieces=pack_descriptor(self.frame(),role=0,index=0,map_selector=0,piece_address=0)
        row=oam_oracle(pieces,anchor_x=0,anchor_y=0,facing_left=False,palette_slot=0)[0]
        self.assertEqual(row['high'],1)
        self.assertEqual(row['low'][:2],bytes([253,252]))
        self.assertEqual(oam_oracle(pieces,anchor_x=-100,anchor_y=0,facing_left=False,palette_slot=0),[])

    def test_no_truncation(self):
        frame=self.frame();frame['chunks']*=129
        with self.assertRaisesRegex(ValueError,'RESOURCE_OAM'):
            pack_descriptor(frame,role=0,index=0,map_selector=0,piece_address=0)

    def test_exact_budget_boundary_fails(self):
        self.assertEqual(transfer_requirement(self.frame(),byte_limit=544,slot_limit=8,
                          reserved_bytes=32,reserved_slots=1)['status'],'RESOURCE_TRANSFER_BATCH')

    def test_large_size_and_x_high_owned_independently(self):
        frame=self.frame()
        frame['chunks'][0]['size']=[32,64]
        _,pieces=pack_descriptor(frame,role=0,index=0,map_selector=4,piece_address=0)
        row=oam_oracle(pieces,anchor_x=-17,anchor_y=-30,
                       facing_left=False,palette_slot=6)[0]
        self.assertEqual((row['x'],row['y'],row['high']),(-20,-34,3))
        self.assertEqual(row['low'][3],0x3d)
        self.assertEqual(oam_oracle(pieces,anchor_x=-29,anchor_y=0,
                                    facing_left=False,palette_slot=6),[])

    def test_mode6_all_tile_origins_against_rectangle_oracle(self):
        for tile in range(512):
            for width,height in ((16,32),(32,64)):
                occupied=[tile+x+16*y for y in range(height//8) for x in range(width//8)]
                valid=(tile%16+width//8<=16 and
                       all(t//256==tile//256 for t in occupied))
                if valid:
                    self.assertEqual(piece_word(tile,(width,height))&511,tile)
                else:
                    with self.assertRaisesRegex(ValueError,'FOOTPRINT'):
                        piece_word(tile,(width,height))

    def test_piece_reserved_bits_rejected(self):
        with self.assertRaisesRegex(ValueError,'RESERVED_BITS'):
            oam_oracle(struct.pack('<hhhH',0,0,0,0x200),anchor_x=0,
                       anchor_y=0,facing_left=False,palette_slot=0)

    def test_inventory_preserves_nontransparent_edges(self):
        image=Image.new('P',(17,33));image.putpixel((16,32),1)
        data=io.BytesIO();image.save(data,format='PNG')
        result=measure_frame(data.getvalue())
        self.assertEqual(result['cells'],[[16,32]])
        self.assertEqual(result['dimensions'],[17,33])


if __name__=='__main__':unittest.main()
