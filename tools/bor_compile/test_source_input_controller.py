import unittest
from source_input_controller import convert,refresh,BINDING
from source_script_input import authority


class ControllerBinding(unittest.TestCase):
    def test_every_physical_combination_is_an_exact_disjoint_source_mask(self):
        masks={r['name']:r['mask'] for r in authority()['keys']}
        for selection in range(1<<len(BINDING)):
            chosen=[r for i,r in enumerate(BINDING) if selection&(1<<i)]
            raw=sum(bit for bit,_ in chosen)
            expected=sum(masks[name] for _,name in chosen)
            self.assertEqual(convert(raw),expected)
            self.assertEqual(convert(raw|1),0)

    def test_edges_are_outer_refresh_values_retained_until_refresh(self):
        first=refresh([0,0],[0x4000,0x0200])
        self.assertEqual(first,[(64,64,0),(4,4,0)])
        self.assertEqual(refresh([r[0] for r in first],[0x4000,0x0100]),[(64,0,0),(8,8,4)])
        self.assertEqual(refresh([64,8],[0,0]),[(0,0,64),(0,0,8)])
        with self.assertRaisesRegex(ValueError,'PORT_DOMAIN'):refresh([0]*3,[0]*3)


if __name__=='__main__':unittest.main()
