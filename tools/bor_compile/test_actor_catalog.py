import copy
import struct
import unittest

from compiler import ROOT, Source
from model_ir import parse_model
from actor_lowering import lower_model
from actor_frame_abi import pack_animation
from actor_catalog import generate_catalog


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
        cls.models=[lower_model(parse_model(source,f'data/chars/{n}/{n}.txt',n,
                    'catalog-test','historical-bor')) for n in ('Kula','Lobster','Ramon','Joe')]

    def build(self,models=None,**kwargs):
        return generate_catalog(self.models if models is None else models,base_address=0x1FC000,**kwargs)

    def test_deterministic_and_immutable(self):
        before=copy.deepcopy(self.models)
        a,ma=self.build();b,mb=self.build(list(reversed(self.models)))
        self.assertEqual((a,ma),(b,mb));self.assertEqual(before,self.models)

    def test_every_role_and_frame_uses_compiler_bytes(self):
        blob,manifest=self.build()
        self.assertEqual(struct.unpack_from('<HH',blob),(0x3543,1))
        self.assertEqual(len(manifest['entries']),sum(len(m['animations']) for m in self.models))
        for row in manifest['entries']:
            model=next(m for m in self.models if tuple(m['source_identity'])==row['identity'])
            expected=pack_animation(model,row['role'])
            offset=row['address']-manifest['base_address']
            self.assertEqual(blob[offset:offset+32*row['frame_count']],expected)

    def test_pinned_runtime_ids(self):
        identity=tuple(self.models[0]['source_identity'])
        _,manifest=self.build(pinned={identity:22})
        self.assertTrue(all(r['actor_id']==22 for r in manifest['entries'] if r['identity']==identity))

    def test_project_and_duplicate_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_MODEL'): self.build(self.models*2)
        models=copy.deepcopy(self.models);models[0]['source_identity']=('foreign','kula')
        with self.assertRaisesRegex(ValueError,'PROJECT_SCOPE'): self.build(models)

    def test_duplicate_roles_fail_closed(self):
        models=copy.deepcopy(self.models);models[0]['animations'].append(models[0]['animations'][0])
        with self.assertRaisesRegex(ValueError,'DUPLICATE_ROLE'): self.build(models)

    def test_bank_extent(self):
        with self.assertRaisesRegex(ValueError,'CATALOG_BANK_EXTENT: project=catalog-test, required_bytes=.*bank_available_bytes=16'):
            generate_catalog(self.models,base_address=0x1FFFF0)
        with self.assertRaisesRegex(ValueError,'LOROM_ADDRESS'):
            generate_catalog(self.models,base_address=0x1F0000)

    def test_explicit_compatibility_is_not_certification(self):
        control=dict(source_identity=self.models[0]['source_identity'],role='attack1',
            frame_bytes=pack_animation(self.models[0],'attack1'),scope='ISOLATED_GOLDEN_CONTROL',
            policy={'test':'explicit data-only control'})
        _,manifest=self.build(compatibility_controls=[control])
        rows=[r for r in manifest['entries'] if r['identity']==tuple(control['source_identity']) and r['role']=='attack1']
        self.assertEqual([r['profile'] for r in rows],[1,2])
        self.assertEqual(rows[0]['source_fingerprint'],rows[1]['source_fingerprint'])
        self.assertFalse(manifest['runtime_certified'])
        del control['policy']
        with self.assertRaisesRegex(ValueError,'EXPLICIT_COMPAT'):
            self.build(compatibility_controls=[control])

    def test_duplicate_control_key(self):
        c=dict(source_identity=self.models[0]['source_identity'],role='attack1',
               frame_bytes=pack_animation(self.models[0],'attack1'),
               scope='ISOLATED_GOLDEN_CONTROL',policy={'test':True})
        with self.assertRaisesRegex(ValueError,'DUPLICATE_KEY'):
            self.build(compatibility_controls=[c,c])


if __name__=='__main__': unittest.main()
