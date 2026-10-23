import importlib.util
from pathlib import Path
import struct
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,patch
import expedition33
from expedition33 import _multi_button_wire as wire
from expedition33.menu import NativeMenu,MenuError

ROOT=Path(__file__).resolve().parents[1]/'src/expedition33'
def load(name):
    spec=importlib.util.spec_from_file_location('expedition33._partial_'+name,ROOT/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
batch=load('_ui_batch');controls=load('multi_controls')
with patch.dict(sys.modules,{'expedition33.multi_controls':controls}):driver=load('process_title_ui')

class S:pass
class Lease:
    def __init__(self,token):
        self.active=True;self._token=token
        self.object=N(pid=7,index=token,serial=3,address=0x10000+token*8)

class PartialControlTests(unittest.TestCase):
    def test_alias_identity_still_rejected_before_native_acquisition(self):
        alias=Lease(99)
        alias.object=self.leases[2].object
        self.session._leases.add(alias)
        with self.assertRaises(ValueError):self.owner.bind_many(self.bindings)
        self.assertEqual(self.calls,0)
        self.assertEqual(self.owner.controls,[])

    def setUp(self):
        self.leases=[Lease(i) for i in range(1,7)]
        self.session=S();self.session._check=Mock();self.session._abort_ownership=Mock()
        self.session.supports_multi_controls=True;self.session._leases=set(self.leases);self.session._menus=set()
        self.session._transport=N(ui_batch_protocol=1,button_action_session=7,_check_thread=lambda:None,command=self.command)
        self.menu=NativeMenu(self.session,self.leases[:2]);self.menu._state='attached'
        self.owner=controls.MenuControls(self.menu);self.menu._controls=self.owner
        self.fail_at=1;self.error=1012;self.outcome=2;self.calls=0
        self.duplicate=False;self.malformed=False;self.defer_close=False
        self.bindings=[(lease.object,Mock()) for lease in self.leases[2:]]
        self.patch=patch.object(expedition33,'_ui_batch',batch,create=True);self.patch.start();self.addCleanup(self.patch.stop)

    def command(self,name,sent):
        if name=='menu':
            reply=bytearray(sent)
            struct.pack_into('<3I',reply,8,813 if self.defer_close else 0,2,1 if self.defer_close else 0)
            return dict(menu_packet=reply.hex())
        self.calls+=1
        count=batch.HEADER.unpack_from(sent)[1];at=batch.HEADER.size;parts=[];done=0
        for i in range(count):
            action,size=batch.ITEM.unpack_from(sent,at);at+=batch.ITEM.size
            request=batch.unpack_sparse(sent[at:at+size],wire.SIZE);at+=size
            reply=bytearray(request);failed=i==self.fail_at
            struct.pack_into('<4I',reply,8,self.error if failed else 0,self.outcome if failed else 2,0,0 if failed else 2)
            if not failed:struct.pack_into('<Q',reply,64,1 if self.duplicate else i+1)
            if failed and self.malformed:reply[-1]^=1
            packed=batch.pack_sparse(reply);parts.append(batch.ITEM.pack(action,len(packed))+packed);done+=1
            if failed:break
        body=b''.join(parts)
        raw=batch.HEADER.pack(1,count,batch.HEADER.size+len(body),done,1203 if self.fail_at is not None else 0)+body
        return dict(ui_batch_packet=raw.hex())

    def test_known_prefix_adopted_failing_owner_retained_suffix_proven_unbound(self):
        with self.assertRaises(controls.ControlBindBatchRejected) as caught:self.owner.bind_many(self.bindings)
        self.assertEqual(caught.exception.completed,2);self.assertEqual(caught.exception.native_error,1012)
        self.session._abort_ownership.assert_not_called();self.assertEqual(self.calls,1)
        self.assertEqual([c._state for c in self.owner.controls],['active','menu_closing'])
        self.assertIsNone(self.owner.controls[1]._callback)
        self.assertTrue(self.menu.protects(self.leases[2]));self.assertTrue(self.menu.protects(self.leases[3]))
        self.assertFalse(self.menu.protects(self.leases[4]));self.assertFalse(self.menu.protects(self.leases[5]))
        self.defer_close=True;self.assertFalse(self.menu.close())
        self.assertTrue(self.menu.protects(self.leases[2]));self.assertTrue(self.menu.protects(self.leases[3]))
        self.defer_close=False;self.assertTrue(self.menu.close())
        self.assertFalse(self.menu.protects(self.leases[2]));self.assertFalse(self.menu.protects(self.leases[3]))

    def test_full_success_unchanged(self):
        self.fail_at=None
        result=self.owner.bind_many(self.bindings)
        self.assertEqual(len(result),4);self.assertTrue(all(c.active for c in result))
        self.session._abort_ownership.assert_not_called()

    def test_first_failure_has_durable_owner_and_no_success_prefix(self):
        self.fail_at=0;self.error=1010;self.outcome=0
        with self.assertRaises(controls.ControlBindBatchRejected):self.owner.bind_many(self.bindings)
        self.assertEqual(len(self.owner.controls),1)
        self.assertTrue(self.menu.protects(self.leases[2]));self.assertFalse(self.menu.protects(self.leases[3]))
        self.session._abort_ownership.assert_not_called()

    def test_unknown_or_malformed_replies_quarantine_all_without_retry(self):
        for kind in ('unknown','malformed','quarantined'):
            with self.subTest(kind=kind):
                self.setUp()
                if kind=='unknown':self.error=1016;self.outcome=1
                elif kind=='malformed':self.malformed=True
                else:self.error=1014
                with self.assertRaises((ValueError,MenuError)):self.owner.bind_many(self.bindings)
                self.assertTrue(self.session._abort_ownership.called);self.assertEqual(self.calls,1)
                self.assertTrue(all(self.menu.protects(lease) for lease in self.leases[2:]))

    def test_duplicate_success_registration_quarantines_before_adoption(self):
        self.fail_at=2;self.duplicate=True
        with self.assertRaises(ValueError):self.owner.bind_many(self.bindings)
        self.assertTrue(self.session._abort_ownership.called)
        self.assertFalse(any(c.active for c in self.owner.controls));self.assertEqual(self.calls,1)

    def test_generic_execute_remains_strict_and_quarantines_known_partial(self):
        requests=[('multi-button',wire.request('bind',9,lease._token,action=10,child=lease.object)) for lease in self.leases[2:]]
        with self.assertRaises(batch.UIBatchError):batch.execute(self.session,requests)
        self.session._abort_ownership.assert_called_once_with();self.assertEqual(self.calls,1)

    def test_title_driver_recovers_only_typed_known_rejection_after_dispose_ack(self):
        events=[];scope=N(close=Mock());entry=N(close=Mock(),poll=Mock(),restore_title_input_after_menu_close=Mock(side_effect=lambda:events.append('input.restore') or True))
        service=N(menu=N(panel=N(state='built')),poll=Mock())
        def dispose():events.append('dispose.ack');service.menu=None
        service.dispose_menu=Mock(side_effect=dispose)
        ui=driver.ProcessTitleUI(N(poll=Mock()),object(),scope_factory=lambda:scope,service_factory=lambda *a:service,
            entry_factory=lambda *a,**kw:entry,view_factory=object(),menu_factory=object())
        ui.scope=scope;ui.service=service;ui.entry=entry;ui._ready=True
        entry.open=Mock(side_effect=controls.ControlBindBatchRejected(2,1012))
        ui.open();self.assertEqual(events,['dispose.ack','input.restore'])
        self.assertEqual(ui.frontend_failed['native_error'],1012)
        self.assertFalse(ui.frontend_cleanup_pending)
        with self.assertRaises(RuntimeError):ui.open()
        entry.open.assert_called_once_with()

    def test_invalid_batch_header_never_grants_suffix_proof(self):
        original=self.command
        def command(name,sent):
            response=original(name,sent)
            raw=bytearray.fromhex(response['ui_batch_packet'])
            struct.pack_into('<I',raw,12,5)
            return dict(ui_batch_packet=raw.hex())
        self.session._transport.command=command
        with self.assertRaises(ValueError):self.owner.bind_many(self.bindings)
        self.assertTrue(self.session._abort_ownership.called)
        self.assertTrue(all(self.menu.protects(lease) for lease in self.leases[2:]))

    def test_partial_bind_does_not_contain_generic_returned_menu_error(self):
        self.assertFalse(driver._recoverable_frontend(MenuError('generic',outcome='returned',native_error=1012)))
        self.assertFalse(driver._recoverable_frontend(MenuError('uncertain',outcome='unknown',native_error=1016)))

if __name__=='__main__':unittest.main()
