import hashlib,struct,tempfile,unittest
from pathlib import Path
from compiler import Source
from source_player_death_requirements import derive,pack_models


class PlayerDeathRequirementTests(unittest.TestCase):
    def source(self,path):
        (path/'data').mkdir()
        (path/'data/models.txt').write_text('nomaxrushreset 1\nnomaxrushreset 2\nload ForeignPlayer data/player.txt\n')
        (path/'data/player.txt').write_text('type player\nnodieblink 1\nnodieblink 3\nweaploss 3\n')
        return Source(path)

    def test_absent_hooks_and_repeated_model_policy_follow_source(self):
        with tempfile.TemporaryDirectory()as folder:
            r=derive(self.source(Path(folder)))
        self.assertEqual(r['rush_reset_policy'],2)
        self.assertEqual(r['models'][0]['nodieblink'],3)
        self.assertEqual(r['models'][0]['weaploss_type'],3)
        self.assertEqual(len(r['hooks']),8)
        self.assertTrue(all(h['disposition']=='UNINITIALIZED_HOOK_NO_EXECUTION'for h in r['hooks']))
        self.assertFalse(r['native_player_die_bound'])

    def test_case_insensitive_present_hook_requires_child_and_keeps_hash(self):
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder);self.source(path);scripts=path/'data/SCRIPTS';scripts.mkdir()
            body=b'void main(){ /* a real global dependency */ }'
            (scripts/'DIE2.C').write_bytes(body)
            # Even an empty present file must go through compiler/loader authority.
            (scripts/'RESPAWN4.C').write_bytes(b'')
            r=derive(Source(path))
        present=[h for h in r['hooks']if h['source_sha256']is not None]
        self.assertEqual([(h['family'],h['player_index'])for h in present],[('die',1),('respawn',3)])
        self.assertEqual(present[0]['source_sha256'],hashlib.sha256(body).hexdigest())
        self.assertTrue(all(h['disposition']=='SCRIPT_CHILD_BINDING_REQUIRED'for h in present))

    def test_packed_model_keeps_full_signed_policy_and_registry_identity(self):
        r=dict(models=[dict(id=0,nodieblink=-2147483648),dict(id=1,nodieblink=65536)])
        data=pack_models(r)
        self.assertEqual(struct.unpack_from('<HHi',data,16),(0,0,-2147483648))
        self.assertEqual(struct.unpack_from('<HHi',data,24),(1,0,65536))
        r['models'][1]['id']=2
        with self.assertRaisesRegex(ValueError,'PLAYER_DEATH_MODEL_RECORD'):pack_models(r)


if __name__=='__main__':unittest.main()
