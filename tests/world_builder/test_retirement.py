import sys,types,unittest,struct
from pathlib import Path
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
package=types.ModuleType('retirement_test_builder')
package.__path__=[str(Path(__file__).resolve().parents[2]/'mods/E33WorldBuilder')]
sys.modules[package.__name__]=package
from retirement_test_builder import retirement as r

class RetirementTests(unittest.TestCase):
    def native(self,reply=None):
        transport=N(builder_world_retirement_protocol=1,command=Mock())
        def send(command,packet):
            raw=bytearray(packet)
            if reply is not None:reply(raw)
            return {'mesh_packet':raw.hex()}
        transport.command.side_effect=send
        mod=N(_native_retirement=None,started=True,owner=42,
            session=N(_session=N(_transport=transport),_lease_context=lambda:nullcontext()))
        return mod,transport
    def test_ack_is_not_replayed(self):
        mod,t=self.native();self.assertEqual(r.native_retire(mod),'ack')
        self.assertEqual(r.native_retire(mod),'ack');t.command.assert_called_once()
    def test_pending_retains_owner_and_accepts_later_ack(self):
        mod,t=self.native(lambda raw:struct.pack_into('<II',raw,8,407,1))
        self.assertEqual(r.native_retire(mod),'pending')
        t.command.side_effect=lambda _,p:{'mesh_packet':p.hex()}
        self.assertEqual(r.native_retire(mod),'ack')
    def test_changed_request_or_unknown_native_outcome_never_retries(self):
        for change in (lambda raw:raw.__setitem__(16,99),lambda raw:struct.pack_into('<I',raw,8,1968)):
            mod,t=self.native(change)
            self.assertEqual(r.native_retire(mod),'unknown')
            self.assertEqual(r.native_retire(mod),'unknown');t.command.assert_called_once()
    def test_no_native_resources_requires_no_protocol_or_dispatch(self):
        mod,t=self.native();mod.started=False;t.builder_world_retirement_protocol=0
        self.assertEqual(r.native_retire(mod),'ack');t.command.assert_not_called()
    def test_worker_pending_cannot_release_panels(self):
        panel=N(retire_world=Mock())
        mod=N(_retirement_token=('old',),_retirement_result=None,catalog_menu=panel,hud=None)
        with patch.object(r,'drain_workers',return_value=False),patch.object(r,'native_retire') as native:
            self.assertEqual(r.poll(mod,N(previous_token=('old',))),'pending')
        native.assert_not_called();panel.retire_world.assert_not_called()
    def test_full_ack_retires_owned_ui_without_graceful_world_compensation(self):
        panel=N(retire_world=Mock(return_value='ack'),close=Mock())
        mod=N(_retirement_token=('old',),_retirement_result=None,catalog_menu=panel,hud=None,
            _menu_reader=None,library=N(_catalog=object(),owned={'actor':1},preview_key=1,selected=1,world=1),session=object())
        with patch.object(r,'drain_workers',return_value=True),patch.object(r,'native_retire',return_value='ack'):
            self.assertEqual(r.poll(mod,N(previous_token=('old',))),'ack')
        panel.retire_world.assert_called_once_with(native_retirement_ack=True);panel.close.assert_not_called()
        self.assertIsNone(mod.session);self.assertFalse(mod.library.owned)

if __name__=='__main__':unittest.main()
