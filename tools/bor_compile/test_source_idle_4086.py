import copy
import json
from pathlib import Path
import unittest
from source_idle_4086 import default_idle_capability, common_anim_series, common_idle_anim


class IdlePolicy(unittest.TestCase):
    def test_complete_authored_registry_admits_only_derived_default_idle(self):
        root=Path(__file__).resolve().parents[2]
        identities=json.loads((root/'out/byor-motu-animation-identities.json').read_text())
        core=json.loads((root/'out/byor-motu-model-core-inputs.json').read_text())
        result=default_idle_capability(identities,core)
        self.assertEqual(len(result['models']),16)
        for kind in ('maximum','special','subtype'):
            i=copy.deepcopy(identities);c=copy.deepcopy(core)
            if kind=='maximum':i['limits']['max_idles']=2
            elif kind=='special':i['models'][0]['animations'].append(dict(engine_animation_id=61))
            else:c['models'][0]['fields']['subtype']=1
            with self.assertRaisesRegex(ValueError,'SERVICE_REQUIRED'):default_idle_capability(i,c)

    def test_nested_service_failure_restores_source_self(self):
        previous=object();entity=dict(idling=1,model=dict(type=0,subtype=0),modeldata=dict(health=100),health=10)
        def fail(*args):raise RuntimeError('service')
        owner=dict(self=previous,biker=1,faint=61,sleep=80,valid_animation=lambda e,n:True,set_animation=fail)
        with self.assertRaises(RuntimeError):common_idle_anim(entity,owner)
        self.assertIs(owner['self'],previous)

    def test_series_outside_source_array_is_explicitly_rejected(self):
        for mode in (-1,4):
            with self.assertRaisesRegex(ValueError,'INDEX_UNDEFINED'):common_anim_series({},[0,105,106],mode,0,{})


if __name__=='__main__':unittest.main()
