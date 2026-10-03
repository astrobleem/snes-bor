import unittest
from compiler import Source,ROOT
from model_ir import parse_model
from source_publication_set import compile_set,live_set_report,oam_resource_report,PublicationResourceBlocked
from source_publication_codegen import capture_code


class PublicationSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')

    def request(self,name,identity,frames,maps,role='attack1'):
        m=parse_model(self.source,f'data/chars/{name}/{name}.txt',name,'test','historical-bor')
        return dict(model=m,runtime_id=identity,role=role,role_id=0,frames=frames,maps=maps)

    def test_independent_model_and_palette_keys(self):
        p=compile_set(self.source,[self.request('Kula',22,[0],[0]),self.request('Mary',24,[0,1],[1])])
        self.assertEqual(p['required_bytes'],7936)
        self.assertEqual({f['model'] for f in p['frames']},{22,24})
        self.assertEqual(len(p['palettes']),2)
        self.assertEqual(len(p['tiles']),16384)
        self.assertFalse(p['hardware_ready'])

    def test_map_four_shares_tiles_not_palette(self):
        base=compile_set(self.source,[self.request('Angel',29,[0],[0],role='idle')])
        alt=compile_set(self.source,[self.request('Angel',29,[0],[0,4],role='idle')])
        self.assertEqual(base['tiles'],alt['tiles'])
        self.assertEqual(base['blocks'],alt['blocks'])
        self.assertEqual(len(alt['palettes']),2)
        self.assertEqual({f['map'] for f in alt['frames']},{0,4})

    def test_reserved_accepted_obj_lease_excludes_placement_and_bytes(self):
        reserved=(2,3,10,11)
        r=self.request('Crab',45,list(range(8)),[0],role='walk')
        p=compile_set(self.source,[r],reserved_slots=reserved)
        self.assertEqual(p['available_bytes'],15360)
        self.assertFalse(set(reserved)&{b['slot'] for b in p['blocks'].values()})
        for slot in reserved:
            tile=(slot//8)*64+(slot%8)*2
            for row in range(4):
                start=(tile+row*16)*32
                self.assertEqual(p['tiles'][start:start+64],bytes(64))
        self.assertEqual(p,compile_set(self.source,[r],reserved_slots=reversed(reserved)))

    def test_reserved_capacity_fails_with_actual_available_space(self):
        with self.assertRaises(PublicationResourceBlocked) as caught:
            compile_set(self.source,[self.request('Kula',22,[0],[0])],reserved_slots=range(56))
        self.assertEqual(caught.exception.details['available_bytes'],2048)
        self.assertEqual(caught.exception.details['fragmentation_bytes'],0)

    def test_packet_palettes_do_not_pin_or_duplicate_graphics(self):
        r=self.request('Angel',29,[0],[0,1,4],role='idle')
        with self.assertRaisesRegex(PublicationResourceBlocked,'PINNED_PALETTE_SET_BLOCKED'):
            compile_set(self.source,[r])
        packet=compile_set(self.source,[r],packet_palettes=True)
        base=compile_set(self.source,[dict(r,maps=[0])])
        self.assertEqual(packet['blocks'],base['blocks'])
        self.assertEqual(packet['tiles'],base['tiles'])
        self.assertEqual(len(packet['palettes']),3)
        self.assertEqual(packet['palette_slots'],{})
        self.assertEqual(packet['palette_ownership'],'IMMUTABLE_PUBLICATION_PACKET')
        self.assertFalse(packet['hardware_ready'])

    def test_atomic_palette_packets_do_not_require_old_and_new_cgram_at_once(self):
        packets=[dict(identity=i,ownership=owner,requests=[self.request('Angel',29,[0],[i],role='idle')])
                 for i,owner in enumerate(('displayed','queued','new_packet'))]
        pinned=live_set_report(self.source,packets)
        atomic=live_set_report(self.source,packets,atomic_palette_packets=True)
        self.assertEqual(pinned['status'],'RESOURCE_BLOCKED')
        self.assertEqual(atomic['status'],'REPRESENTABLE_EMITTED_ABI')
        self.assertEqual(atomic['referenced_palette_identities'],3)
        self.assertEqual(atomic['required_palette_slots'],1)
        self.assertEqual(pinned['required_bytes'],atomic['required_bytes'])

    def test_pinned_pool_failure_not_false_hardware_minimum(self):
        with self.assertRaisesRegex(ValueError,'not a simultaneous-live-set lower bound'):
            compile_set(self.source,[self.request('Kula',22,list(range(6)),[0])])

    def test_native_lookup_distinguishes_every_identity_field(self):
        code=capture_code(3,[22,24])
        for address in ('$20C000','$20C002','$20C004','$20C006'):
            self.assertIn(address,code)
        self.assertIn('S7Multi_Missing__admitted_model',code)
        for name in ('Kula','Mary','Angel','Crab','Lobster'):
            self.assertNotIn(name,code)

    def test_identical_instance_keys_deduplicate(self):
        r=self.request('Angel',29,[0],[4],role='idle')
        self.assertEqual(compile_set(self.source,[r]),compile_set(self.source,[r,r]))

    def test_live_set_excludes_future_only_and_sums_blocks(self):
        requests=[self.request('Kula',22,[i],[0]) for i in range(6)]
        packets=[dict(identity=i,ownership='new_packet' if i==0 else 'prefetch',requests=[r]) for i,r in enumerate(requests)]
        report=live_set_report(self.source,packets)
        self.assertEqual(report['required_bytes'],compile_set(self.source,requests[:1])['required_bytes'])
        self.assertGreater(report['optional_only_bytes'],0)
        report=live_set_report(self.source,[dict(identity='six-independent-instances',ownership='new_packet',requests=requests)])
        self.assertEqual(report['status'],'RESOURCE_BLOCKED')
        self.assertEqual(report['required_bytes'],sum(b['size'] for b in report['blocks']))
        self.assertEqual(report['fragmentation_bytes'],0)
        self.assertFalse(report['source_pixel_global_minimum_proven'])

    def test_resource_exception_is_machine_readable(self):
        with self.assertRaises(PublicationResourceBlocked) as caught:
            compile_set(self.source,[self.request('Kula',22,list(range(6)),[0])])
        d=caught.exception.details
        self.assertEqual(d['required_bytes'],sum(b['size'] for b in d['blocks']))
        self.assertFalse(d['simultaneous_requirement_proven'])

    def test_scanline_limit_is_not_total_piece_limit(self):
        pieces=[dict(x=i*8,y=100) for i in range(20)]
        self.assertEqual(oam_resource_report(pieces)['status'],'RESOURCE_BLOCKED')
        for i,p in enumerate(pieces):p['y']=100+64*(i%2)
        self.assertEqual(oam_resource_report(pieces)['status'],'PASS')

    def test_invalid_frame_and_map_do_not_wrap(self):
        for frames,maps,reason in [([-1],[0],'SOURCE_FRAME_UNAVAILABLE'),([0],[256],'SOURCE_MAP_SELECTOR_WIDTH')]:
            with self.assertRaisesRegex(ValueError,reason):
                compile_set(self.source,[self.request('Angel',29,frames,maps,role='idle')])

    def test_same_runtime_key_cannot_alias_distinct_models(self):
        with self.assertRaisesRegex(ValueError,'RUNTIME_PUBLICATION_ID_COLLISION'):
            compile_set(self.source,[self.request('Kula',22,[0],[0]),self.request('Mary',22,[0],[0])])

    def test_capture_membership_is_explicit_not_unknown_model_fallback(self):
        code=capture_code(3,[22,24],slot_mask=3)
        self.assertNotIn('lda #$1B00',code)
        self.assertIn('S7Multi_Missing__admitted_model:',code)
        self.assertIn('sta.l S7Pub_State+$F4',code)


if __name__=='__main__':unittest.main()
