"""Scope-bound game-thread scrub binding for the owned timeline slider."""
import math,struct
from dataclasses import replace
from . import _invocation_wire as call

CONFIG=struct.Struct('<IIiiQiiQii4I')
STATUS=struct.Struct('<4Iifd8I')
VIEWPORT=struct.Struct('<4I3d6I')
MAGIC=0x44533345

def validate(operation,payload):
    if type(payload) is not bytes or len(payload)!=2*call.SIZE:raise ValueError('Scrub payload size')
    if operation in (21,22,23):
        if any(payload):raise ValueError('Empty scrub status/release required')
        return
    if operation!=20:raise ValueError('Scrub operation')
    header=call.HEADER.unpack_from(payload)
    if header[:4]!=(1,4,4,0) or header[6:10]!=(1,0,0,0):raise ValueError('Slider float getter required')
    kind,offset,width,dimension,_,_,name,*_=call.FIELD.unpack_from(payload,call.FIELDS_AT)
    if (kind,offset,width,dimension)!=(5,0,4,1) or name.rstrip(b'\0')!=b'ReturnValue':raise ValueError('Slider value field required')
    magic,version,si,ss,sa,pi,ps,pa,start,end,*reserved=CONFIG.unpack_from(payload,call.SIZE)
    if ((magic,version)!=(MAGIC,1) or min(si,pi)<0 or min(ss,ps)<=0 or not sa or not pa or
            end<=start or any(reserved) or any(payload[call.SIZE+CONFIG.size:])):raise ValueError('Scrub configuration')

class SequenceDrag:
    def __init__(self,sequence):
        self.sequence=sequence;self.bound=False;self.counter=0
    def _send(self,operation,payload=None):
        from ._sequence_owner import HEADER,SIZE,validate_request
        s=self.sequence;s.scope._check()
        if getattr(s.scope._session._transport,'sequence_drag_scrub_protocol',0)!=1:raise RuntimeError('Native drag scrub runtime required')
        if operation==23 and getattr(s.scope._session._transport,'sequence_timeline_viewport_protocol',0) not in (1,2):raise RuntimeError('Native timeline viewport required')
        if s.uncertain or s.owner.state!='armed':raise RuntimeError('Sequence is unavailable')
        payload=bytes(2*call.SIZE) if payload is None else payload
        request=HEADER.pack(1,operation,s.owner.owner,0,0,0)+payload;validate_request(request)
        s.uncertain=True
        try:
            reply=s.scope._session._transport.command('sequence-owner',request)
            data=bytes.fromhex(reply['sequence_owner_packet'])
            if len(data)!=SIZE or data[:24]!=request[:24]:raise RuntimeError('Scrub acknowledgement mismatch')
            error,state=HEADER.unpack_from(data)[4:]
            if error==1811 and state==1 and data[32:]==payload:
                s.uncertain=False;raise ValueError('Timeline scrub binding is unavailable')
            if error or state!=1:raise RuntimeError(f'Scrub ownership failed ({error}, {state})')
            if operation==23:
                magic,version,revision,pick_counter,start,end,pick_frame,lane,*reserved=VIEWPORT.unpack_from(data,32)
                if (magic!=0x56533345 or version!=getattr(s.scope._session._transport,'sequence_timeline_viewport_protocol',0) or lane>(6 if version==2 else 2) or not all(math.isfinite(v) for v in (start,end,pick_frame)) or
                        not self.start<=start<end<=self.end or revision<getattr(self,'view_revision',0) or
                        pick_counter<getattr(self,'pick_counter',0) or (pick_counter and not self.start<=pick_frame<=self.end) or
                        (any(reserved) if version==1 else reserved[1]>6 or reserved[2]>1 or reserved[4]!=0) or any(data[32+VIEWPORT.size:])):raise RuntimeError('Timeline viewport acknowledgement mismatch')
                result=dict(start=start,end=end,revision=revision,pick=pick_counter!=getattr(self,'pick_counter',0),frame=pick_frame,lane=lane)
                if version==2:
                    fraction=struct.unpack('<f',struct.pack('<I',reserved[0]))[0]
                    if not math.isfinite(fraction) or not 0<=fraction<=1:raise RuntimeError('Timeline hover position mismatch')
                    result.update(hover=bool(reserved[2]),hover_frame=start+fraction*(end-start),hover_lane=reserved[1])
                self.view_revision=revision;self.pick_counter=pick_counter
            elif operation==21:
                magic,version,counter,dragging,frame,subframe,value,*reserved=STATUS.unpack_from(data,32)
                if ((magic,version)!=(MAGIC,1) or dragging not in (0,1) or counter<self.counter or
                        not math.isfinite(subframe) or not 0<=subframe<1 or not math.isfinite(value) or not 0<=value<=1 or
                        any(reserved) or any(data[32+STATUS.size:])):raise RuntimeError('Scrub status mismatch')
                changed=counter!=self.counter;self.counter=counter
                if changed:s.state='paused'
                result=(changed,frame,subframe,value,bool(dragging))
            else:
                if data[32:]!=payload:raise RuntimeError('Scrub binding acknowledgement mismatch')
                result=None
            s.uncertain=False
            return result
        finally:
            if s.uncertain:
                s.owner.state='unknown';s.scope._session._abort_ownership()
    def bind(self,plan,start,end):
        s=self.sequence
        if self.bound:raise ValueError('Scrub slider is already bound')
        if s._seek_function is None:s._prepare_seek_function()
        from ._stable_lease import acquire_stable
        pause=getattr(self,'pause',None)
        if pause is None:
            pause,_=acquire_stable(s.scope,s._function('MovieSceneSequencePlayer','Pause'))
            self.pause=pause
        payload=call.encode_plan(replace(plan,wire_version=1))
        payload+=CONFIG.pack(MAGIC,1,s._seek_function.index,s._seek_function.serial,s._seek_function.address,
            pause.object.index,pause.object.serial,pause.object.address,start,end,0,0,0,0)+bytes(call.SIZE-CONFIG.size)
        self._send(20,payload);self.counter=0;self.view_revision=self.pick_counter=0;self.start=start;self.end=end;self.bound=True
    def poll(self):return self._send(21)
    def viewport(self):return self._send(23)
    def close(self):
        if self.bound:self._send(22);self.bound=False
