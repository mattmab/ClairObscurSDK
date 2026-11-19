import copy,struct,unittest
from expedition33.scene_bones import validate_motion,validate_wire
class SceneBonesTests(unittest.TestCase):
    def document(self):
        pose=[0.,0.,0.,1.,0.,0.,95.,1.,1.,1.]
        motion=dict(format='e33.bone-motion',version=1,source='/Game/Reviewed.ChairRise',duration=1/30,fps=30,
                    bones=[dict(name='Pelvis',index=1)],frames=[dict(at=0.,poses=[pose]),dict(at=1/30,poses=[pose])])
        return dict(duration=6.,actors=[dict(id='sophie',assembly='mesh-4139998eb15a')],bone_motion=dict(actor='sophie',hold=1.,end=6.,motion=motion))
    def test_qualified_motion_and_rejection_of_bad_transforms_and_handoffs(self):
        d=self.document();self.assertEqual(validate_motion(d)[0],0)
        for mutation in (lambda d:d['bone_motion'].update(end=7.),lambda d:d['actors'][0].update(assembly='another'),
                         lambda d:d['bone_motion']['motion']['frames'][1]['poses'][0].__setitem__(3,0.),
                         lambda d:d['bone_motion']['motion']['frames'][1].update(at=.5)):
            bad=copy.deepcopy(d);mutation(bad)
            with self.assertRaises(ValueError):validate_motion(bad)
    def test_wire_does_not_admit_unbounded_frames_or_nonfinite_pose(self):
        data=bytearray(20984);struct.pack_into('<I',data,4,202);struct.pack_into('<4I',data,88,0,0,1,0)
        struct.pack_into('<10f',data,104,0,0,0,1,0,0,0,1,1,1);validate_wire(bytes(data))
        for offset,value in ((92,96),(96,385),(100,1)):
            bad=bytearray(data);struct.pack_into('<I',bad,offset,value)
            with self.assertRaises(ValueError):validate_wire(bytes(bad))
        bad=bytearray(data);struct.pack_into('<f',bad,104,float('nan'))
        with self.assertRaises(ValueError):validate_wire(bytes(bad))
    def test_import_requires_owned_identities_and_bounded_slot(self):
        data=bytearray(20984);struct.pack_into('<I',data,4,203)
        for at in (88,104,120,136,152,168):struct.pack_into('<iiQ',data,at,1,1,0x1234)
        validate_wire(bytes(data))
        for at,fmt,value in ((88,'<i',-1),(96,'<Q',0),(184,'<I',6),(188,'<I',1)):
            bad=bytearray(data);struct.pack_into(fmt,bad,at,value)
            with self.assertRaises(ValueError):validate_wire(bytes(bad))
if __name__=='__main__':unittest.main()
