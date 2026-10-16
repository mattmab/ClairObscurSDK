import math,struct,unittest
from types import SimpleNamespace
from mods.CatalogModels.character import select_visuals
from mods.CatalogModels.mod import Mod
from mods.CatalogModels.skin import arc,rotate,reference_world,mapped_sides
from expedition33.procedural_mesh import validate_request,SIZE,HEADER

class SkinMathTests(unittest.TestCase):
    def test_character_retirement_keeps_follow_intent_but_explicit_destroy_clears_it(self):
        mod=Mod();mod.follow_character=True
        closed=[];mod.scope=SimpleNamespace(close=lambda:closed.append(True));mod.model=object()
        mod._retire()
        self.assertEqual(closed,[True]);self.assertTrue(mod.follow_character);self.assertIsNone(mod.model)
        mod.destroy();self.assertFalse(mod.follow_character)
    def test_dynamic_character_components_are_selected_without_body_name(self):
        def row(name,asset,animation=None):
            return dict(object=SimpleNamespace(name=name),asset=SimpleNamespace(name=asset) if asset else None,animation=SimpleNamespace(name='ALS_UE5_AnimBP') if animation else None)
        body=row('SkeletalMeshComponent_123','SK_Lune_Placeholder',object())
        face=row('SkeletalMeshComponent_456','Lune_FaceMesh',object())
        hair=row('Haircut_SkeletalMesh','Hair_Lune_2_skl')
        self.assertEqual(select_visuals([row('SkeletalMesh',None),hair,face,body]),(body,face,hair))
        with self.assertRaises(ValueError):select_visuals([body,dict(body),face,hair])
        body['asset'].name='SK_Monoco_Esquie'
        face['asset'].name='SK_Monoco_Head';face['object'].name='Face'
        self.assertEqual(select_visuals([hair,face,body]),(body,face,hair))
    def test_unbind_cannot_supply_identities(self):
        p=bytearray(SIZE);HEADER.pack_into(p,0,3,11,0,0,1)
        validate_request(bytes(p));p[88]=1
        with self.assertRaises(ValueError):validate_request(bytes(p))
    def test_rotated_source_sides_match_target_reference(self):
        self.assertEqual(mapped_sides(-20,-15),('l','r'))
        self.assertEqual(mapped_sides(20,-15),('r','l'))
        self.assertEqual(mapped_sides(20,15),('l','r'))
        self.assertEqual(mapped_sides(-20,15),('r','l'))
        with self.assertRaises(ValueError):mapped_sides(0,-15)
        with self.assertRaises(ValueError):mapped_sides(float('nan'),-15)
    def test_alignment_preserves_length(self):
        result=rotate(arc((0,0,2),(0,3,0)),(0,0,2))
        for actual,expected in zip(result,(0,2,0)):self.assertAlmostEqual(actual,expected)
    def test_parent_reference_composition(self):
        q=(0,0,math.sqrt(.5),math.sqrt(.5))
        rows=[dict(name='root',parent='None',reference=(*q,10,0,0,0,1,1,1,0)),
              dict(name='child',parent='root',reference=(0,0,0,1,1,0,0,0,1,1,1,0))]
        _,p=reference_world(rows)['child']
        self.assertAlmostEqual(p[0],10);self.assertAlmostEqual(p[1],1)
    def test_capture_rejects_output_and_extra_identities(self):
        p=bytearray(SIZE);HEADER.pack_into(p,0,3,8,0,0,1)
        validate_request(bytes(p))
        p[344]=1
        with self.assertRaises(ValueError):validate_request(bytes(p))
    def test_bind_rejects_geometry_injection(self):
        p=bytearray(SIZE);HEADER.pack_into(p,0,3,9,0,0,1)
        with self.assertRaisesRegex(ValueError,'hair setter'):validate_request(bytes(p))
        struct.pack_into('<iiQ',p,19808,1,1,0x10000)
        validate_request(bytes(p));p[352]=1
        with self.assertRaises(ValueError):validate_request(bytes(p))
    def test_hide_cannot_supply_identities(self):
        p=bytearray(SIZE);HEADER.pack_into(p,0,3,10,0,0,1);p[88]=1
        with self.assertRaises(ValueError):validate_request(bytes(p))

if __name__=='__main__':unittest.main()
