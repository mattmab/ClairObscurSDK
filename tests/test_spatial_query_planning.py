"""Real catalog/planner/wire fixtures; no game dispatch is performed."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from expedition33 import _invocation_wire as wire
from expedition33._scope import SessionScope
from expedition33.catalog import Catalog, CatalogObject, ClassRelation
from expedition33.invocation import UnsupportedInvocation
from expedition33.sdk import Session
from expedition33.spatial_queries import SpatialQueries
from test_ownership import Transport
import test_pod_invocation


class SpatialTransport(Transport):
    def __init__(self):
        super().__init__()
        self.start['pid'] = 123
        self.retained_protocol = self.pod_value_protocol = 1
        self.stable_identity_protocol = self.object_assignment_protocol = 1
        self.packets = []
        self.output = b''

    def command(self, command, packet=None):
        if command != 'retained-invoke':
            return super().command(command, packet)
        self._check_thread()
        self.calls.append(command)
        self.packets.append(packet)
        response = bytearray(packet)
        struct.pack_into('<II', response, 32, 1, 0)
        response[wire.DATA_AT:wire.DATA_AT + len(self.output)] = self.output
        return {'retained_packet': response.hex()}


class SpatialPlanningTests(unittest.TestCase):
    def setUp(self):
        p = test_pod_invocation.PodInvocationTests(); p.setUp()
        objects = list(p.catalog.objects)
        classes = list(p.catalog.classes.values()) + [ClassRelation(19, 1, 'PlayerController', 2, 256)]
        objects = [replace(o, outer_index=18, outer_serial=1) if o.index == 2 else o for o in objects]
        objects = [replace(o, name='GetActorBounds') if o.index == 7 else o for o in objects]
        objects += [CatalogObject(123, 18, 1, 0x22000, '/Script/Engine', 'Package', 'Class', 8, -1, 0, 0, 0),
                    CatalogObject(123, 19, 1, 0x23000, 'PlayerController', 'Class', 'Class', 1, 18, 1, 0, 0),
                    CatalogObject(123, 20, 1, 0x24000, 'Controller', 'PlayerController', 'Class', 19, -1, 0, 0, 0)]
        # Layouts copied from engine_profiles.h entries 24,25,32,40.
        specs = [
            (7, 'Actor', 'GetActorBounds', 57, 64, 65535, 0x54c20402, 0x33398d0,
             [('bOnlyCollidingComponents','BoolProperty',0,1,0x18001040000280,None),
              ('Origin','StructProperty',8,24,0x18001040000380,17),
              ('BoxExtent','StructProperty',32,24,0x18001040000380,17),
              ('bIncludeFromChildActors','BoolProperty',56,1,0x18001040000280,None)]),
            (21, 'PlayerController', 'ProjectWorldLocationToScreen', 42,48,41,0x54c20403,0x3b27f10,
             [('WorldLocation','StructProperty',0,24,0x18001040000280,17),
              ('ScreenLocation','StructProperty',24,16,0x18001040000380,13),
              ('bPlayerViewportRelative','BoolProperty',40,1,0x18001040000280,None),
              ('ReturnValue','BoolProperty',41,1,0x18001040000780,None)]),
            (22,'PlayerController','GetViewportSize',8,8,65535,0x54420403,0x3b26b70,
             [('SizeX','IntProperty',0,4,0x18001040000380,None),('SizeY','IntProperty',4,4,0x18001040000380,None)]),
            (23,'PlayerController','DeprojectScreenPositionToWorld',57,64,56,0x54c20403,0x3b23d30,
             [('ScreenX','FloatProperty',0,4,0x18001040000280,None),('ScreenY','FloatProperty',4,4,0x18001040000280,None),
              ('WorldLocation','StructProperty',8,24,0x18001040000380,17),
              ('WorldDirection','StructProperty',32,24,0x18001040000380,17),
              ('ReturnValue','BoolProperty',56,1,0x18001040000780,None)])]
        for index, owner, name, *_ in specs[1:]:
            objects.append(CatalogObject(123,index,1,0x30000+index*256,name,'Function','Class',6,19,1,0,0))
        self.catalog = Catalog(123, objects, classes)
        self.descriptors = p.descriptors
        for index,owner,name,size,extent,ret,flags,rva,fields in specs:
            rows = []
            for field,kind,offset,width,fflags,st in fields:
                row = dict(owner_index=index,name=field,type=kind,offset=offset,element_size=width,dimension=1,flags=fflags)
                if st:
                    row.update(struct_index=st,struct_serial=1,struct_name=self.catalog.by_index[st].name)
                if kind == 'BoolProperty': row['bool_encoding'] = '0xff010001'
                rows.append(row)
            self.descriptors[index] = SimpleNamespace(object=self.catalog.by_index[index],
                owners=[dict(index=index,size=extent)],properties=rows,
                function=dict(params_size=size,return_offset=ret,flags=flags,entry_rva=hex(rva)))
        self.transport = SpatialTransport()
        self.patch = patch('expedition33.sdk.SessionTransport',return_value=self.transport)
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.session = Session(pod_values=True)
        self.addCleanup(self.session.close)
        self.scope = SessionScope(self.session)
        self.addCleanup(self.scope.close)
        self.query = SpatialQueries(self.scope, catalog=self.catalog)
        self.addCleanup(self.query.close)
        describe = patch('expedition33.invocation.describe',side_effect=lambda c, targets:{o.index:self.descriptors[o.index] for o in targets})
        describe.start(); self.addCleanup(describe.stop)
        scan = patch('expedition33.catalog.capture',side_effect=AssertionError('Unexpected full registry scan'))
        scan.start(); self.addCleanup(scan.stop)

    def test_real_planner_encodes_exact_layouts_and_decodes_copies(self):
        out = bytearray(57); struct.pack_into('<ddd',out,8,1,2,3); struct.pack_into('<ddd',out,32,4,5,6)
        self.transport.output = out
        self.assertEqual(self.query.actor_bounds(self.catalog.by_index[5]).extent,(4.,5.,6.))
        out = bytearray(42); struct.pack_into('<dd',out,24,120,240); out[41]=1
        self.transport.output = out
        self.assertEqual(self.query.project(self.catalog.by_index[20],(1,2,3)),(120.,240.))
        out = bytearray(57); struct.pack_into('<ddd',out,8,1,2,3); struct.pack_into('<ddd',out,32,0,1,0); out[56]=1
        self.transport.output = out
        self.assertEqual(self.query.deproject(self.catalog.by_index[20],(120,240)).direction,(0.,1.,0.))
        self.transport.output=struct.pack('<ii',1920,1080)
        self.assertEqual(self.query.viewport_size(self.catalog.by_index[20]),(1920,1080))
        self.assertEqual(len(self.transport.packets),4)
        # Retained envelope starts with the ordinary exact-schema wire packet.
        self.assertEqual(struct.unpack_from('<ddd',self.transport.packets[1],wire.DATA_AT),(1.,2.,3.))
        self.assertEqual(struct.unpack_from('<ff',self.transport.packets[2],wire.DATA_AT),(120.,240.))
        self.assertFalse(self.transport.tokens)

    def test_closed_query_and_retired_scope_prevent_transport(self):
        self.query.close()
        with self.assertRaisesRegex(RuntimeError,'closed'):
            self.query.viewport_size(self.catalog.by_index[20])
        other=SpatialQueries(self.scope,catalog=self.catalog)
        self.addCleanup(other.close)
        self.scope.close()
        with self.assertRaisesRegex(RuntimeError,'scope is closed'):
            other.viewport_size(self.catalog.by_index[20])
        self.assertFalse(self.transport.packets)

    def test_missing_pod_support_rejects_vector_query_before_transport(self):
        self.transport.pod_value_protocol=0
        with self.assertRaises(UnsupportedInvocation):
            self.query.actor_bounds(self.catalog.by_index[5])
        self.assertFalse(self.transport.packets)

    def test_native_packet_fixture_accepts_profile_shapes(self):
        executable=Path(__file__).resolve().parents[1]/'build/invocation-fixture/invocation_fixture.exe'
        if not executable.exists(): self.skipTest('Native invocation fixture not built')
        self.test_real_planner_encodes_exact_layouts_and_decodes_copies()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'spatial.bin'
            for packet in self.transport.packets:
                path.write_bytes(packet[:wire.SIZE])
                result=subprocess.run([str(executable),str(path),'--pod'],capture_output=True,text=True)
                self.assertEqual((result.returncode,result.stdout.strip()),(0,'0'))
