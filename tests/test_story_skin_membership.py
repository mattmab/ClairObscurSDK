import unittest
from types import SimpleNamespace as N
from unittest.mock import patch
from expedition33.story_facial import current_skin
from expedition33.values import StoredArray


class SkinMembershipTests(unittest.TestCase):
    def skin(self,**changes):
        values=dict(index=2,serial=3,address=0x20000,class_name='BP_CharacterSkinComponent_C',
            outer_index=1,outer_serial=2,object_flags=0)
        return N(**dict(values,**changes))

    def read(self,fields,**changes):
        value=N(**dict(dict(values={(1,k):v for k,v in fields.items()},errors=(),truncated=False),**changes))
        return patch('expedition33.story_facial.capture_selected_values',return_value=(None,{1:value}))

    def test_direct_and_component_array_reference_same_skin(self):
        skin=self.skin();scope=N(pid=7);actor=(1,2,0x10000)
        with self.read(dict(BP_CharacterSkinComponent=skin,BlueprintCreatedComponents=StoredArray((skin,),1),InstanceComponents=StoredArray((),0))) as read,patch('expedition33.story_facial.capture_matching',side_effect=AssertionError('global scan')):
            self.assertIs(current_skin(scope,actor),skin)
        self.assertEqual(read.call_args.args,(7,(actor,)))

    def test_cinematic_component_array_supports_missing_direct_property(self):
        skin=self.skin(class_name='BP_CinematicCharacterSkinComponent_C')
        with self.read(dict(BlueprintCreatedComponents=StoredArray((skin,),1),InstanceComponents=StoredArray((),0))):
            self.assertIs(current_skin(N(pid=7),(1,2,0x10000)),skin)

    def test_stale_foreign_duplicate_and_partial_components_reject(self):
        skin=self.skin()
        cases=[(dict(BP_CharacterSkinComponent=self.skin(outer_serial=99)),{}),
            (dict(BP_CharacterSkinComponent=self.skin(object_flags=0x20)),{}),
            (dict(BP_CharacterSkinComponent=skin,InstanceComponents=StoredArray((self.skin(index=3),),1)),{}),
            (dict(BP_CharacterSkinComponent=skin,InstanceComponents=StoredArray((),1)),{}),
            (dict(BP_CharacterSkinComponent=skin),dict(errors=('read failed',))),
            (dict(BP_CharacterSkinComponent=skin),dict(truncated=True)),({}, {})]
        for fields,changes in cases:
            with self.subTest(fields=fields,changes=changes),self.read(fields,**changes):
                with self.assertRaises(RuntimeError):current_skin(N(pid=7),(1,2,0x10000))

if __name__=='__main__':unittest.main()
