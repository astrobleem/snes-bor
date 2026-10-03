import copy
import struct
import unittest
from actor_lowering import lower_model
from test_actor_lowering import fixture
from source_actor_link import link_scheduler, link_world_contexts


class LinkTests(unittest.TestCase):
    def test_frame_extension_and_no_ir_mutation(self):
        actor=lower_model(fixture());original=copy.deepcopy(actor)
        blob,manifest=link_scheduler(actor,bank_base=0x018000)
        self.assertEqual(struct.unpack_from('<hH',blob,28),(-2,0))
        self.assertEqual(len(blob),48);self.assertEqual(manifest['role_table'],0x018020)
        self.assertEqual(actor,original)

    def test_policy_fail_closed(self):
        actor=lower_model(fixture())
        with self.assertRaisesRegex(ValueError,'POLICY'):link_scheduler(actor,bank_base=0x18000,profile='ACCEPTED_COMPAT')
        actor['policy_contract']={}
        with self.assertRaisesRegex(ValueError,'COMPAT'):link_scheduler(actor,bank_base=0x18000)

    def test_unknown_role_is_blocker_not_fallback(self):
        _,m=link_scheduler(lower_model(fixture('foreign')),bank_base=0x18000)
        self.assertEqual(m['blockers'][0]['capability'],'ROLE_TRANSITION')
        self.assertIsNone(m['roles'][0]['behavior'])

    def test_order_determinism(self):
        actor=lower_model(fixture());actor['animations'].append(copy.deepcopy(actor['animations'][0]))
        actor['animations'][1]['role']='idle'
        expected=link_scheduler(actor,bank_base=0x18000)
        actor['animations'].reverse();self.assertEqual(expected,link_scheduler(actor,bank_base=0x18000))

    def test_bank_failure(self):
        with self.assertRaisesRegex(ValueError,'BANK_CAPACITY'):link_scheduler(lower_model(fixture()),bank_base=0x1fff0)

    def test_world_sparse_slots_are_not_compacted(self):
        blob,m=link_world_contexts([0x1000,None,0x1200],world_address=0x1800,table_address=0x18800)
        self.assertEqual(struct.unpack('<3H',blob),(0x1000,0,0x1200))
        self.assertEqual(m['occupied_slots'],[0,2]);self.assertEqual(m['actor_bytes'],512)
        self.assertFalse(m['full_actor_certification'])

    def test_world_contexts_fail_on_overlap_or_bad_address(self):
        for slots in ([0x1800],[0x1000,0x1000],[0x1F00],[0x1001]):
            with self.assertRaisesRegex(ValueError,'SOURCE_WORLD'):
                link_world_contexts(slots,world_address=0x1800,table_address=0x18800)
        with self.assertRaisesRegex(ValueError,'OVERLAP'):
            link_world_contexts([0x1000],world_address=0x1800,table_address=0x18800,
                                reserved_regions=[(0x1080,0x1200)])

    def test_world_scope_and_policy_fail_closed(self):
        for kwargs in (dict(profile='ACCEPTED_COMPAT'),dict(table_address=0x1FFFF)):
            options=dict(world_address=0x1800,table_address=0x18800);options.update(kwargs)
            with self.assertRaisesRegex(ValueError,'SOURCE_WORLD'):link_world_contexts([0x1000],**options)
        with self.assertRaisesRegex(ValueError,'SLOT_LIMIT'):
            link_world_contexts([None]*151,world_address=0x1800,table_address=0x18800)

    def test_world_cannot_overlap_production_or_auxiliary_storage(self):
        for reserved in ([(0x0A00,0x1600)],[(0x1500,0x1700)]):
            with self.assertRaisesRegex(ValueError,'OVERLAP'):
                link_world_contexts([0x1900],world_address=0x1500,
                                    table_address=0x18800,reserved_regions=reserved)

    def test_world_table_must_be_immutable_lorom_not_wram_alias(self):
        for address in (0x1900,0x801900,0x7E1900,0x7F9200,0x700000,0x002100):
            with self.assertRaisesRegex(ValueError,'IMMUTABLE_ROM'):
                link_world_contexts([0x1900],world_address=0x1B00,table_address=address)
        for address in (0x008000,0x018800,0x808000,0xBF8000):
            link_world_contexts([0x1900],world_address=0x1B00,table_address=address)


if __name__=='__main__':unittest.main()
