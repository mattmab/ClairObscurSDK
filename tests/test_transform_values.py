import math
import struct
import unittest
from expedition33._pod_values import encode,decode,QUAT,TRANSFORM


class TransformValuesTests(unittest.TestCase):
    def value(self):
        return dict(Rotation=dict(X=0.,Y=0.,Z=math.sqrt(.5),W=math.sqrt(.5)),
                    Translation=dict(X=12.,Y=-34.,Z=56.),Scale3D=dict(X=1.,Y=1.,Z=1.))

    def test_transform_preserves_rotation_translation_scale_and_zeroes_padding(self):
        value=self.value();data=encode(TRANSFORM,value)
        self.assertEqual(len(data),96)
        self.assertEqual(struct.unpack_from('<3d',data,32),(12.,-34.,56.))
        self.assertEqual(data[56:64]+data[88:96],bytes(16))
        self.assertEqual(encode(TRANSFORM,decode(TRANSFORM,data)),data)
        native=bytearray(data);native[56:64]=b'padding!'
        self.assertEqual(encode(TRANSFORM,decode(TRANSFORM,bytes(native))),data)

    def test_rejects_invalid_rotation_and_nonfinite_fields(self):
        for q in (dict(X=0.,Y=0.,Z=0.,W=0.),dict(X=0.,Y=0.,Z=0.,W=2.),dict(X=math.nan,Y=0.,Z=0.,W=1.)):
            with self.assertRaises(ValueError):encode(QUAT,q)
        value=self.value();value['Translation']['Z']=math.inf
        with self.assertRaises(ValueError):encode(TRANSFORM,value)

if __name__=='__main__':unittest.main()
