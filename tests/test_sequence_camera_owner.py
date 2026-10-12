import unittest
from dataclasses import replace
from types import SimpleNamespace as N
from unittest.mock import Mock, patch
from expedition33 import _sequence_owner as wire
from expedition33.invocation import CallPlan, Parameter


class SequenceCameraOwnerTests(unittest.TestCase):
    def owner(self, capability=1):
        transport=N(sequence_camera_protocol=capability, command=Mock())
        session=N(_transport=transport,_check=lambda:None,_abort_ownership=Mock())
        owner=wire.NativeSequenceOwner(N(_session=session)); owner.state='prepared'
        return owner,session

    def plan(self):
        fields=(('NewViewTarget','ObjectProperty',0,8),('BlendTime','FloatProperty',8,4),
            ('blendFunc','ByteProperty',12,1),('BlendExp','FloatProperty',16,4),
            ('bLockOutgoing','BoolProperty',20,1))
        return CallPlan(N(),N(name='SetViewTargetWithBlend'),0,0,21,24,65535,
            tuple(Parameter(n,k,o,w,1,128) for n,k,o,w in fields),bytes(24),())

    def test_old_runtime_never_receives_new_operation(self):
        owner,session=self.owner(0)
        with self.assertRaisesRegex(RuntimeError,'capability'): owner.arm_camera(self.plan())
        session._transport.command.assert_not_called()
        self.assertEqual(owner.state,'prepared')

    def test_capture_only_before_factory(self):
        for state in ('new','armed','closed','unknown','cleanup_pending'):
            owner,session=self.owner(); owner.state=state
            with self.assertRaises(RuntimeError): owner.arm_camera(self.plan())
            session._transport.command.assert_not_called()

    def test_nonzero_blends_target_patches_and_bad_shapes_refused(self):
        plan=self.plan()
        invalid=(replace(plan,data=bytes(8)+b'\1'+bytes(15)),
            replace(plan,objects=(object(),)),replace(plan,parameter_size=24),
            replace(plan,parameters=plan.parameters[:-1]),replace(plan,texts=(('x','y'),)))
        for candidate in invalid:
            owner,session=self.owner()
            with self.assertRaises(ValueError):owner.arm_camera(candidate)
            session._transport.command.assert_not_called()

    def test_arm_wire_slot_and_acknowledgement(self):
        owner,session=self.owner()
        def command(name,data):
            self.assertEqual(name,'sequence-owner'); wire.validate_request(data)
            self.assertEqual(wire.HEADER.unpack_from(data)[1],4)
            self.assertEqual(data[32:32+wire.call.SIZE],bytes(wire.call.SIZE))
            self.assertEqual(data[32+wire.call.SIZE:],b'\1'*wire.call.SIZE)
            reply=data[:28]+(3).to_bytes(4,'little')+data[32:]
            return {'sequence_owner_packet':reply.hex()}
        session._transport.command.side_effect=command
        with patch.object(wire.call,'encode_plan',return_value=b'\1'*wire.call.SIZE):
            self.assertTrue(owner.arm_camera(self.plan()))
        self.assertEqual(owner.state,'prepared');session._abort_ownership.assert_not_called()

    def test_arm_rejects_payload_in_capture_slot(self):
        payload=wire.HEADER.pack(1,4,1,0,0,0)+bytes(wire.call.SIZE)+b'\1'*wire.call.SIZE
        wire.validate_request(payload)
        with self.assertRaises(ValueError):wire.validate_request(payload[:32]+b'\1'+payload[33:])
        with self.assertRaises(ValueError):wire.validate_request(payload[:32]+bytes(2*wire.call.SIZE))

    def test_uncertain_reply_aborts_ownership(self):
        owner,session=self.owner()
        session._transport.command.return_value={'sequence_owner_packet':bytes(wire.SIZE).hex()}
        with patch.object(wire.call,'encode_plan',return_value=b'\1'*wire.call.SIZE):
            with self.assertRaises(ValueError):owner.arm_camera(self.plan())
        session._abort_ownership.assert_called_once()
        self.assertEqual(owner.state,'unknown')

    def test_pre_factory_cleanup_deferral_retries_without_abort(self):
        owner,session=self.owner()
        outcomes=iter(((407,3),(0,0)))
        def command(name,data):
            error,state=next(outcomes)
            reply=data[:24]+error.to_bytes(4,'little')+state.to_bytes(4,'little')+data[32:]
            return {'sequence_owner_packet':reply.hex()}
        session._transport.command.side_effect=command
        self.assertFalse(owner.close());self.assertEqual(owner.state,'cleanup_pending')
        self.assertTrue(owner.close());self.assertEqual(owner.state,'closed')
        session._abort_ownership.assert_not_called()


if __name__=='__main__':unittest.main()
