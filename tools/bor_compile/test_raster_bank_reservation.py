import copy,unittest
from raster_bank_reservation import reserve
from raster_slot_greedy import demand
import test_raster_word_bank_balance as fixtures


class ReservationTests(unittest.TestCase):
    def source(self):return fixtures.WordBankBalanceTests().fixture()[0]

    def test_reserved_bank_preserves_coordinates_words_and_geometry(self):
        source=self.source();before=copy.deepcopy(source);bank=source['pieces'][0]['bank'];result=reserve(source,[bank])
        self.assertEqual(source,before)
        self.assertEqual(result['bank_reservation']['status'],'RESERVED_BANK_ROW_CAPACITY_AND_SOURCE_IDENTITIES_PROVEN')
        self.assertTrue(all(p['bank']!=bank for p in result['pieces']))
        self.assertTrue(all(bank not in p['allowed_banks']for p in result['pieces']))
        def pixels(s):return {(p['actor'],p['x']+x,p['y']+y):int(c)for p,im in zip(s['pieces'],demand(s)[2])for y,row in enumerate(im)for x,c in enumerate(row)if c>=0}
        self.assertEqual(pixels(source),pixels(result))
        self.assertEqual([(p['x'],p['y'],p['width'],p['height'])for p in result['pieces']],
                         [(p['x'],p['y'],p['width'],p['height'])for p in source['pieces']])
        self.assertFalse(result['bank_reservation']['concurrent_actor_admitted'])

    def test_empty_domain_and_search_limit_do_not_reject_raster(self):
        source=self.source();bank=source['pieces'][0]['bank']
        for p in source['pieces']:p['allowed_banks']=[p['bank']]
        result=reserve(source,[bank])
        self.assertEqual(result['status'],'FIXED_GEOMETRY_BANK_RESERVATION_INFEASIBLE')
        self.assertFalse(result['universal_raster_rejected'])
        result=reserve(self.source(),[bank],maximum_assignments=1)
        self.assertEqual(result['status'],'ASSIGNMENT_SPACE_LIMIT')
        self.assertFalse(result['universal_raster_rejected'])

    def test_invalid_domains_rejected(self):
        for banks in ([],[8],[True],[1,1]):
            with self.assertRaisesRegex(ValueError,'DOMAIN'):reserve(self.source(),banks)


if __name__=='__main__':unittest.main()
