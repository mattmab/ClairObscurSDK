import io,struct,unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import map_runtime as source


class VisibilityBatchTests(unittest.TestCase):
    def owner(self,count=50):
        owner=source.MapRuntime.__new__(source.MapRuntime)
        function=N(index=1,serial=2,address=0x10000)
        construction=N(catalog=Mock(return_value=N(find_path=lambda _:function)),resources=N(hold=Mock(return_value=N(object=function))))
        owner.scope=N(pid=123,_check=Mock(),_lease_context=lambda:nullcontext(),
            _session=N(_story_construction_resources=construction,_transport=N(map_visibility_batch_protocol=1)))
        owner.objects={str(i):{'actor':(i+10,i+100,0x20000+i*8)} for i in range(count)}
        owner.started=True;owner._closed=False;owner.uncertain=False;owner.owner=27;owner.profile={}
        return owner,function
    def packet(self):
        owner,function=self.owner(2);packets=[]
        def command(_,sent):
            packets.append(sent);reply=bytearray(sent)
            struct.pack_into('<I',reply,12,1);struct.pack_into('<2I',reply,3560,2,2)
            return dict(mesh_packet=reply.hex())
        owner.scope._session._transport.command=command
        owner._send(source.VISIBILITY_BATCH,ids=(function,),actors=tuple(r['actor'] for r in owner.objects.values()))
        return packets[0]
    def test_wire_only_accepts_bounded_unique_exact_actors_and_function(self):
        sent=self.packet();source.validate_request(sent)
        for at,data in ((8,b'\x01'),(24,b'\x01'),(104,b'\x01'),(2000,struct.pack('<I',33)),
                        (2004,b'\x01'),(4128,b'\x01'),(92,b'\0'*4),(4112,sent[4096:4112])):
            raw=bytearray(sent);raw[at:at+len(data)]=data
            with self.subTest(at=at),self.assertRaises(ValueError):source.validate_request(bytes(raw))
    def test_budgeted_prefix_advances_without_repeating_acknowledged_actors(self):
        owner,function=self.owner();requests=[];sizes=iter((17,32,1))
        def send(op,**kw):
            self.assertEqual(op,262);self.assertEqual(kw['ids'],(function,));requests.append(kw['actors'])
            raw=bytearray(source.SIZE);struct.pack_into('<I',raw,12,1);struct.pack_into('<2I',raw,3560,next(sizes),50);return raw
        owner._send=Mock(side_effect=send);temporary=Mock()
        with patch.object(source,'SessionScope',return_value=temporary):
            self.assertEqual(owner.hide_collision_objects(tuple(owner.objects)),50)
        self.assertEqual([len(r) for r in requests],[32,32,1])
        self.assertEqual([r[0][0] for r in requests],[10,27,59]);temporary.close.assert_called_once()
    def test_foreign_keys_reject_before_metadata_or_native_work(self):
        owner,_=self.owner();owner._send=Mock()
        with self.assertRaises(ValueError):owner.hide_collision_objects(('foreign',))
        owner.scope._session._story_construction_resources.catalog.assert_not_called();owner._send.assert_not_called()
    def test_partial_failure_remains_owned_and_cannot_retry(self):
        owner,_=self.owner();first=bytearray(source.SIZE);struct.pack_into('<I',first,12,1);struct.pack_into('<2I',first,3560,1,50)
        owner._send=Mock(side_effect=(first,RuntimeError('native partial failure')))
        with patch.object(source,'SessionScope',return_value=Mock()):
            with self.assertRaisesRegex(RuntimeError,'partial'):owner.hide_collision_objects(tuple(owner.objects))
            with self.assertRaisesRegex(RuntimeError,'not replayed'):owner.hide_collision_objects(tuple(owner.objects))
        self.assertTrue(owner.uncertain);self.assertEqual(owner._send.call_count,2)
    def test_zero_or_oversized_acknowledgement_is_uncertain(self):
        for done in (0,33):
            owner,_=self.owner();raw=bytearray(source.SIZE);struct.pack_into('<I',raw,12,1);struct.pack_into('<2I',raw,3560,done,50)
            owner._send=Mock(return_value=raw)
            with patch.object(source,'SessionScope',return_value=Mock()),self.assertRaisesRegex(RuntimeError,'progress mismatch'):
                owner.hide_collision_objects(tuple(owner.objects))
            self.assertTrue(owner.uncertain);owner._send.assert_called_once()
    def test_wrong_reply_identity_or_native_partial_error_quarantines_client(self):
        for kind in ('identity','native'):
            owner,function=self.owner(2)
            def command(_,sent):
                raw=bytearray(sent);struct.pack_into('<I',raw,12,1)
                if kind=='identity':raw[4096]^=1
                else:struct.pack_into('<I',raw,8,2117)
                return dict(mesh_packet=raw.hex())
            owner.scope._session._transport.command=command
            with self.assertRaises(RuntimeError):owner._send(262,ids=(function,),actors=tuple(r['actor'] for r in owner.objects.values()))
            self.assertTrue(owner.uncertain)
    def test_missing_or_boolean_capability_rejects_without_sending(self):
        owner,_=self.owner();owner._send=Mock()
        for cap in (0,True,2):
            owner.scope._session._transport.map_visibility_batch_protocol=cap
            with self.assertRaisesRegex(RuntimeError,'unavailable'):owner.hide_collision_objects(tuple(owner.objects))
        owner._send.assert_not_called()
    def test_transport_requires_exact_capability_before_admitting_packet(self):
        from expedition33._session import SessionTransport
        for cap in (0,True,2):
            transport=SessionTransport.__new__(SessionTransport);transport._check_thread=lambda:None
            transport._closed=False;transport.mesh_protocol=3;transport.map_visibility_batch_protocol=cap
            transport._process=N(stdin=io.StringIO());transport._read=Mock()
            with self.assertRaisesRegex(ValueError,'visibility batches'):transport._command('mesh',self.packet())
            self.assertEqual(transport._process.stdin.getvalue(),'');transport._read.assert_not_called()
