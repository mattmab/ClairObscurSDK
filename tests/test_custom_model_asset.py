import importlib.util
from pathlib import Path
import tempfile
import unittest
import struct
from expedition33.procedural_mesh import SIZE, HEADER, GEOMETRY, validate_request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('custom_asset', ROOT/'mods/CustomModel/asset.py')
asset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(asset)

class CustomModelTests(unittest.TestCase):
    def test_original_asset_and_wire(self):
        vertices, indices = asset.load_obj(ROOT/'mods/CustomModel/assets/supply-crate.obj')
        self.assertEqual((len(vertices), len(indices)), (192, 288))
        packet = bytearray(SIZE)
        HEADER.pack_into(packet, 0, 3, 4, 0, 0, 7)
        struct.pack_into('<II', packet, GEOMETRY, len(vertices), len(indices))
        for i, vertex in enumerate(vertices):
            struct.pack_into('<8d', packet, GEOMETRY+8+i*64, *vertex)
        struct.pack_into('<288i', packet, GEOMETRY+8+256*64, *indices)
        validate_request(bytes(packet))
        for offset, fmt, value in ((GEOMETRY,'I',257), (GEOMETRY+8,'d',float('nan')),
                                  (GEOMETRY+8+256*64,'i',192),
                                  (GEOMETRY+8+192*64,'d',1.0)):
            bad = packet.copy()
            struct.pack_into('<'+fmt, bad, offset, value)
            with self.assertRaises(ValueError): validate_request(bytes(bad))

    def test_rejects_malformed_obj(self):
        prefix = 'v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvn 0 0 1\n'
        for suffix in ('f -1/1/1 2/1/1 3/1/1', 'f 4/1/1 2/1/1 3/1/1',
                       'f 1 2 3', 'v nan 0 0', 'call executable'):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'model.obj'
                path.write_text(prefix+suffix)
                with self.assertRaises(ValueError): asset.load_obj(path)

    def test_material_reference_is_not_opened(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'model.obj'
            path.write_text('mtllib ../../missing.mtl\nv 0 0 0\nv 1 0 0\nv 0 1 0\n'
                            'vt 0 0\nvn 0 0 1\nf 1/1/1 2/1/1 3/1/1\n')
            self.assertEqual(len(asset.load_obj(path)[1]), 3)
