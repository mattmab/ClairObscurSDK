import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.story_save_identity import StorySaveIdentity,_observe

class IdentityBorrowTests(unittest.TestCase):
    def test_bound_context_read_uses_native_dispatch_without_observer_replay(self):
        prepared=N(viewport=object(),engine=object(),resources=N(gi=object()),metadata=(N(name='Map_Add'),))
        identity=StorySaveIdentity.__new__(StorySaveIdentity)
        identity.scope=N(_session=N(_story_construction_resources=prepared),_world_binding_token=((7,10,11,12),))
        identity._send=Mock(return_value='save')
        ctx=dict(ready=True,visit=[10,11,12],controller=[20,21,22])
        self.assertEqual(identity.read_context(ctx),'save')
        args=identity._send.call_args.kwargs['_objects']
        self.assertEqual((args[2].index,args[3].index),(10,20))
        identity._send.assert_called_once()
    def test_process_selectors_do_not_cache_current_controller_or_world(self):
        fn=N(name='Map_Add');world=object();pc=object()
        context={'world':(7,10,11,12),'controller':(7,20,21,22)}
        anchor=N(context=Mock(return_value=context))
        prepared=N(viewport=object(),engine=object(),resources=N(gi=object()),metadata=(fn,),anchor=anchor)
        scope=N(pid=7,_check=Mock(),_session=N(_story_construction_resources=prepared))
        with patch('expedition33.catalog.capture_selected',return_value=N(by_index={10:world,20:pc})) as capture:
            result=_observe(scope)
        anchor.context.assert_called_once()
        capture.assert_called_once_with(7,((10,11,12),(20,21,22)))
        self.assertEqual(result,(prepared.engine,prepared.viewport,world,pc,prepared.resources.gi,fn))
    def test_fresh_matching_gi_uses_process_lease_without_releasing_its_owner(self):
        gi=N(index=1,serial=2,address=4096)
        held=N(object=gi,_token=99,release=Mock())
        resources=N(gi=gi,hold=Mock(return_value=held))
        transport=N(command=Mock(return_value={'mesh_packet':'00'}))
        session=N(_story_construction_resources=N(resources=resources),_transport=transport)
        scope=N(_session=session,_lease_context=nullcontext)
        identity=StorySaveIdentity.__new__(StorySaveIdentity)
        identity.closed=False;identity.unknown=False;identity.scope=scope
        identity.observer=Mock(return_value=[object(),object(),object(),object(),gi,object()])
        with patch('expedition33._stable_lease.acquire_stable') as acquire,patch('expedition33.story_save_identity.wire.encode',return_value=b'packet') as encode,patch('expedition33.story_save_identity.decode',return_value='save'):
            self.assertEqual(identity.read(),'save')
        acquire.assert_not_called();held.release.assert_not_called()
        self.assertEqual(encode.call_args.args[1],99)
        identity.observer.assert_called_once_with(scope)
