import unittest
from unittest.mock import patch
import numpy as np
from source_obj_subscreen_demand import measure


class SubscreenDemandTests(unittest.TestCase):
    def test_actor_identity_follows_composed_layer_order_and_dark_output_rejects(self):
        actor=dict(metadata=dict(kind='actor:Front',path='front.png'),pixels=np.array([[5]],dtype=np.int32),left=0,top=0)
        bg=np.array([[[80,0,0]]],dtype=np.uint8);expected=np.array([[[40,0,0]]],dtype=np.uint8)
        with patch('source_obj_subscreen_demand.prepare',return_value=([actor],{},expected)),patch('source_obj_subscreen_demand.compose_rgb8',return_value=(bg,{})):
            result=measure(None,'stage',dict(actors=[dict(model='Back')]))
        self.assertEqual(result['status'],'CONSTANT_SUBSCREEN_ADDITION_ROUTE_REJECTED_FOR_CONTEXT')
        self.assertEqual(result['actors'][0]['source_model'],'Front')
        self.assertEqual(result['unrepresentable_additive_pixels'],1)
        self.assertEqual(result['actors'][0]['first_unrepresentable_pixel']['darker_channels'],[0])
        self.assertFalse(result['universal_raster_rejected'])
        self.assertFalse(result['palette_transfer_proven'])

    def test_brighter_channels_admit_only_operand_existence(self):
        actor=dict(metadata=dict(kind='actor:Effect'),pixels=np.array([[15]],dtype=np.int32),left=0,top=0)
        bg=np.array([[[80,0,0]]],dtype=np.uint8);expected=np.array([[[120,0,0]]],dtype=np.uint8)
        with patch('source_obj_subscreen_demand.prepare',return_value=([actor],{},expected)),patch('source_obj_subscreen_demand.compose_rgb8',return_value=(bg,{})):
            result=measure(None,'stage',dict(actors=[dict(model='Effect')]))
        self.assertEqual(result['status'],'CONSTANT_SUBSCREEN_ADDITION_OPERANDS_EXIST_FOR_CONTEXT')
        self.assertEqual(result['unrepresentable_additive_pixels'],0)
        self.assertFalse(result['palette_bank_assignment_proven'])
        self.assertFalse(result['native_routing_proven'])


if __name__=='__main__':unittest.main()
