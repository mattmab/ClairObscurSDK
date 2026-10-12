import unittest
from types import SimpleNamespace
from expedition33.invocation import CallPlan
from expedition33._music_audio_owner import HEADER, SIZE, NativeMusicAudioOwner, validate_request

class MusicAudioOwnerTests(unittest.TestCase):
    def test_pause_operation_has_only_setter_payload(self):
        from expedition33 import _invocation_wire as wire
        data=HEADER.pack(1,4,5,0,0,0)+bytes(64)+bytes(wire.SIZE)+bytes(wire.SIZE)
        validate_request(data)
        with self.assertRaises(ValueError): validate_request(data[:32]+b'\1'+data[33:])
        with self.assertRaises(ValueError): validate_request(data[:-1]+b'\1')

    def test_sound_factory_uses_scalar_wire_and_retains_result(self):
        session=SimpleNamespace(_transport=SimpleNamespace(owned_sound_protocol=1))
        scope=SimpleNamespace(_session=session,_audio_owners=[],_check=lambda:None)
        owner=NativeMusicAudioOwner(scope); owner.state='armed'
        cls=SimpleNamespace(name='GameplayStatics',class_name='Class',index=1)
        default=SimpleNamespace(name='Default__GameplayStatics',class_name='GameplayStatics',class_index=1)
        function=SimpleNamespace(name='CreateSound2D',class_name='Function',outer_index=1)
        # Supply attributes used by the deliberately mixed catalog iteration.
        cls.class_index=0; cls.outer_index=0
        default.outer_index=0; function.class_index=2
        result=SimpleNamespace(return_value=SimpleNamespace(class_name='AudioComponent'))
        prepared=SimpleNamespace(_plan=CallPlan(default,function,0,0,0,0,65535,(),b'',(),2))
        def invoke(**kwargs):
            self.assertEqual(prepared._plan.wire_version,1)
            self.assertTrue(kwargs['refresh_from_result'])
            return result
        prepared.invoke=invoke
        captured={}
        def prepare(obj,fn,**kwargs):
            captured.update(kwargs)
            return prepared
        planner=SimpleNamespace(_scope=lambda:scope,_catalog=SimpleNamespace(objects=(cls,default,function)),prepare=prepare)
        panel=SimpleNamespace(state='open',uncertain=False,scope=scope,player=object())
        self.assertIs(owner.create_sound(planner,panel,object()),result.return_value)
        self.assertFalse(captured['bAutoDestroy'])
        self.assertFalse(captured['bPersistAcrossLevelTransition'])
        self.assertEqual(owner._sounds,[result])
        for volume in (-1,2,float('nan')):
            with self.assertRaises(ValueError): owner.create_sound(planner,panel,object(),volume=volume)

    def owner(self, response):
        session=SimpleNamespace(_check=lambda: None, aborted=False)
        session._abort_ownership=lambda: setattr(session,'aborted',True)
        session._transport=SimpleNamespace(command=lambda command,data: {'music_audio_packet': response(data).hex()})
        owner=NativeMusicAudioOwner(SimpleNamespace(_session=session,_audio_owners=[]))
        owner.state='armed'
        return owner,session

    def test_close_has_no_payload(self):
        data=HEADER.pack(1,2,5,0,0,0)+bytes(SIZE-32)
        validate_request(data)
        with self.assertRaises(ValueError): validate_request(data[:-1]+b'\1')

    def test_cleanup_deferral_preserves_owner(self):
        owner,session=self.owner(lambda data: data[:24]+HEADER.pack(1,1,1,0,407,3)[24:]+data[32:])
        self.assertFalse(owner.close())
        self.assertEqual(owner.state,'armed')
        self.assertFalse(session.aborted)

    def test_unknown_dispatch_aborts(self):
        owner,session=self.owner(lambda data: data[:24]+HEADER.pack(1,1,1,0,1493,2)[24:]+data[32:])
        with self.assertRaises(RuntimeError): owner.close()
        self.assertTrue(session.aborted)

    def test_changed_owner_rejected(self):
        owner,session=self.owner(lambda data: data[:8]+bytes(8)+data[16:])
        with self.assertRaises(ValueError): owner.close()
        self.assertTrue(session.aborted)
