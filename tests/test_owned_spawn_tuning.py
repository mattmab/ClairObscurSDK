import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33.encounter_tuning import EncounterTuningOwner,EncounterTuning,validate_request,SIZE

class Tests(unittest.TestCase):
    def owner(self,errors=()):
        pending=list(errors);calls=[]
        def command(_,request):
            validate_request(request);calls.append(struct.unpack_from('<I',request,4)[0])
            reply=bytearray(request);error=pending.pop(0) if pending else 0
            struct.pack_into('<2I',reply,8,error,0 if error else 1)
            return {'mesh_packet':bytes(reply).hex()}
        transport=N(encounter_tuning_protocol=1,owned_sdk_spawn_tuning_protocol=1,command=command)
        scope=N(_check=Mock(),_session=N(_transport=transport))
        owner=EncounterTuningOwner(scope,71,EncounterTuning(level_mode='override',level=1));owner.attempted=True
        return owner,scope,calls
    def test_direct_spawn_policy_applied_once(self):
        owner,_,calls=self.owner();owner.prepare_owned_spawn();owner.prepare_owned_spawn()
        self.assertEqual(calls,[161])
    def test_unknown_preparation_never_replays(self):
        owner,_,calls=self.owner((3632,))
        with self.assertRaises(RuntimeError):owner.prepare_owned_spawn()
        with self.assertRaisesRegex(RuntimeError,'no replay'):owner.prepare_owned_spawn()
        self.assertEqual(calls,[161])
    def test_revoked_world_cleanup_uses_retained_transport_and_defers_in_battle(self):
        owner,scope,calls=self.owner((407,0));scope._check.side_effect=RuntimeError('world revoked');scope._session=None
        self.assertFalse(owner.close());self.assertTrue(owner.close());self.assertEqual(calls,[159,159])
        self.assertEqual(owner.state,'closed')
        scope._check.assert_not_called()
    def test_preparation_packet_has_no_caller_scalar_or_target(self):
        data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,161,0,0,71);validate_request(bytes(data))
        for at in (24,88,4096):
            bad=bytearray(data);bad[at]=1
            with self.assertRaises(ValueError):validate_request(bytes(bad))
if __name__=='__main__':unittest.main()
