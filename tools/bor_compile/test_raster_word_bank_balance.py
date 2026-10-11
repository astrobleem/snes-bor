import copy,unittest
from raster_global_bank_classes import assign_masks
from raster_slot_greedy import demand
from raster_word_bank_balance import balance
from test_raster_slot_greedy import source_schedule


class WordBankBalanceTests(unittest.TestCase):
    def fixture(self):
        source=source_schedule()
        for p in source['pieces']:p.update(actor=0,local_x=p['x'],local_y=p['y'])
        pieces=[dict(p,allowed_banks=list(range(4)),rows={p['y']+y:sorted({int(c)for c in row if c>=0})for y,row in enumerate(image)if any(c>=0 for c in row)})for p,image in zip(source['pieces'],demand(source)[2])]
        return source,assign_masks(pieces,time_limit=5,maximum_oam_entries=128)

    def test_balancing_preserves_every_operand_and_fixed_bank(self):
        source,initial=self.fixture();frame,search=balance(source,initial,steps=200,seed=3)
        def pixels(s):return{(p['actor'],p['y']+y,p['x']+x):int(c)for p,image in zip(s['pieces'],demand(s)[2])for y,row in enumerate(image)for x,c in enumerate(row)if c>=0}
        self.assertEqual(pixels(source),pixels(frame))
        self.assertLessEqual(search['word_bank_balance']['final_objective'],search['word_bank_balance']['initial_objective'])
        self.assertTrue(all(p['bank']in range(4)for p in frame['pieces']))
        self.assertFalse(search['physical_transfer_admitted'])
        self.assertFalse(search['native_timing_admitted'])
        self.assertFalse(search['universal_raster_rejected'])
        again,other=balance(source,initial,steps=200,seed=3)
        self.assertEqual(search['assignment'],other['assignment'])
        self.assertEqual(frame['compiled_indices_sha256'],again['compiled_indices_sha256'])

    def test_invalid_limits_and_unvalidated_masks_reject(self):
        source,initial=self.fixture()
        with self.assertRaisesRegex(ValueError,'DOMAIN'):balance(source,initial,maximum_oam=129)
        with self.assertRaisesRegex(ValueError,'INITIAL_HARDWARE_LIMIT'):balance(source,initial,maximum_oam=1)
        bad=copy.deepcopy(initial);bad['pieces'][0]['x']+=1
        with self.assertRaisesRegex(ValueError,'GEOMETRY'):balance(source,bad)


if __name__=='__main__':unittest.main()
