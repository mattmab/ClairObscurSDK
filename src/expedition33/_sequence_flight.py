"""Flight camera control within the existing owned sequence/menu lifecycle."""
import math,struct
from dataclasses import replace
from . import _invocation_wire as call

CONTROL=struct.Struct('<4I6d')
MAGIC=0x46533345
INPUT=struct.Struct('<4I3d')
INPUT_MAGIC=0x49533345

def validate(operation,payload):
    if operation in (10,12):
        if len(payload)!=2*call.SIZE:raise ValueError('Two flight call plans required')
        for at in (0,call.SIZE):
            version,size,extent,returned,_,_,fields,objects,outcome,error=call.HEADER.unpack_from(payload,at)
            if version not in (1,2) or not fields or objects or outcome or error or extent<size:
                raise ValueError('Unexecuted flight plans required')
        if operation==10:
            if call.HEADER.unpack_from(payload)[1:4]!=(49,56,48):raise ValueError('Camera teleport frame required')
            if call.HEADER.unpack_from(payload,call.SIZE)[1:4]!=(1,1,0):raise ValueError('Idle player query required')
        elif any(call.HEADER.unpack_from(payload,at)[1:4]!=(8,8,0) for at in (0,call.SIZE)):
            raise ValueError('Source camera object queries required')
    elif operation==13:
        if INPUT.unpack_from(payload)!=(INPUT_MAGIC,1,0,0,0.,0.,0.) or any(payload[INPUT.size:]):
            raise ValueError('Empty editor input poll required')
    elif operation==11:
        magic,version,action,reserved,*pose=CONTROL.unpack_from(payload)
        if (magic,version)!=(MAGIC,1) or action not in (0,1,2) or reserved or any(pose) or any(payload[CONTROL.size:]):
            raise ValueError('Flight status or stop request required')
    else:raise ValueError('Unknown flight operation')

class SequenceFlight:
    def __init__(self,sequence):
        self.sequence=sequence;self.active=False;self.pose=None
    def _send(self,operation,plans=(),*,action=None):
        from ._sequence_owner import HEADER,SIZE,validate_request
        sequence=self.sequence;sequence.scope._check();owner=sequence.owner
        capability=getattr(sequence.scope._session._transport,'sequence_flight_protocol',0)
        if type(capability) is not int or capability!=1:
            raise ValueError('Native sequence flight runtime required')
        if (operation==13 or action==2) and getattr(sequence.scope._session._transport,'sequence_placement_input_protocol',0)!=1:
            raise ValueError('Native scene placement input required')
        if owner.state!='armed' or sequence.uncertain:raise RuntimeError('Owned sequence is unavailable')
        if operation in (10,12):payload=b''.join(call.encode_plan(replace(p,wire_version=2 if operation==10 and i==0 else 1)) for i,p in enumerate(plans))
        elif operation==13:payload=INPUT.pack(INPUT_MAGIC,1,0,0,0.,0.,0.)+bytes(2*call.SIZE-INPUT.size)
        else:
            action=(1 if plans else 0) if action is None else action
            payload=CONTROL.pack(MAGIC,1,action,0,*([0.]*6))+bytes(2*call.SIZE-CONTROL.size)
        request=HEADER.pack(1,operation,owner.owner,0,0,0)+payload;validate_request(request)
        sequence.uncertain=True
        try:
            response=sequence.scope._session._transport.command('sequence-owner',request)
            data=bytes.fromhex(response['sequence_owner_packet'])
            if type(data) is not bytes or len(data)!=SIZE or data[:24]!=request[:24]:raise RuntimeError('Flight acknowledgement mismatch')
            error,state=HEADER.unpack_from(data)[4:]
            if error==1791 and state==1 and data[32:]==payload:
                sequence.uncertain=False;raise ValueError('The paused source camera is unavailable for flight')
            if error or state!=1:raise RuntimeError(f'Flight ownership failed ({error}, {state})')
            if operation==13:
                magic,version,action,toggle,*delta=INPUT.unpack_from(data,32)
                if ((magic,version,action)!=(INPUT_MAGIC,1,0) or toggle not in (0,1) or
                        any(not math.isfinite(v) or abs(v)>10000 for v in delta) or any(data[32+INPUT.size:])):
                    raise RuntimeError('Editor input acknowledgement mismatch')
                self.input=(bool(toggle),tuple(delta))
            elif operation==11:
                magic,version,action,active,*pose=CONTROL.unpack_from(data,32)
                expected=CONTROL.unpack_from(payload)[2]
                if ((magic,version,action)!=(MAGIC,1,expected) or active not in (0,1) or (expected==1 and active) or (expected==2 and not active) or
                        any(not math.isfinite(v) for v in pose) or any(data[32+CONTROL.size:])):
                    raise RuntimeError('Flight status mismatch')
                self.active=bool(active);self.pose=tuple(pose)
            elif data[32:]!=payload:raise RuntimeError('Flight preparation mismatch')
            sequence.uncertain=False
        except BaseException:
            if sequence.uncertain:
                owner.state='unknown';sequence.scope._session._abort_ownership()
            raise
    def start(self,move,status,source,component_owner):
        if self.active:raise ValueError('Stop the current flight view before starting another')
        self._send(12,(source,component_owner));self._send(10,(move,status));self.active=True
    def poll(self):
        self._send(11);return self.pose
    def stop(self):
        if self.active:self._send(11,(True,))
    def inputs(self):
        self._send(13);return self.input
    def restore_pose(self):
        self._send(11,action=2)
