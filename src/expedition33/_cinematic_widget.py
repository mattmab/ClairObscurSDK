"""Exact-profile widget routing for a retained SDK cinematic sequence."""
import secrets
import struct
from dataclasses import replace
from . import _invocation_wire as call
from ._menu_latency import measure_method

HEADER=struct.Struct('<IIQQIIII')
RESOURCE_NAMES=('getter','native_getter','library','component','graph','track_class',
                'widget_class','register','unregister','controls','remove')
SIZE=40+16*12+8*11+call.SIZE

class WidgetAdmissionRejected(RuntimeError):
    """Verified profile rejection before native hook installation."""
    def __init__(self,error,diagnostic):
        self.native_error=error;self.diagnostic=diagnostic
        super().__init__(f'Cinematic widget admission rejected ({error}, diagnostic={diagnostic})')

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE: raise ValueError('Cinematic widget packet size')
    version,op,owner,reserved,error,state,observed,failed=HEADER.unpack_from(data)
    if version!=1 or op not in (1,2,3,4) or not owner or reserved or error or state or observed or failed:
        raise ValueError('Cinematic widget header')
    if op!=1 and any(data[40:]): raise ValueError('Unexpected cinematic widget payload')

class NativeCinematicWidgets:
    def __init__(self,scope):
        self.scope=scope;self.owner=secrets.randbits(64) or 1
        self.state='new';self.observed=self.failed=0
        # SessionScope stops owned sequences before this cleanup list.
        scope._audio_owners.append(self)

    def _send(self,op,payload=None):
        session=self.scope._session;session._check()
        if self.state=='unknown': raise RuntimeError('Cinematic widget ownership is unknown')
        request=HEADER.pack(1,op,self.owner,0,0,0,0,0)+(payload or bytes(SIZE-40))
        validate_request(request);previous=self.state;self.state='unknown'
        try:
            reply=session._transport.command('cinematic-widget',request)
            data=bytes.fromhex(reply['cinematic_widget_packet'])
            if len(data)!=SIZE or data[:24]!=request[:24] or data[40:]!=request[40:]:
                raise ValueError('Cinematic widget acknowledgement mismatch')
            error,state,self.observed,self.failed=HEADER.unpack_from(data)[4:]
            if op==1 and previous=='new' and state==0 and self.observed==0 and error in (1512,1514,1515):
                # These exact native branches return before any owner, journal,
                # hook or engine mutation. Owned input leases still close normally.
                self.state='closed'
                raise WidgetAdmissionRejected(error,self.failed)
            if error==407 and state==1: self.state='armed';return False
            if error or state not in (0,1) or self.failed:
                raise RuntimeError(f'Cinematic widget rejected ({error}, {state}, failed={self.failed})')
            self.state='armed' if state else 'closed';return True
        except WidgetAdmissionRejected:
            raise
        except BaseException:
            session._abort_ownership();raise

    @measure_method('widgets.prepare')
    def prepare(self,resources,player,remove):
        self.scope._check()
        if self.state!='new': raise RuntimeError('Cinematic widget owner already used')
        if getattr(self.scope._session._transport,'cinematic_widget_protocol',0)!=1:
            raise RuntimeError('Runtime has no verified cinematic widget adapter')
        if set(resources)!=set(RESOURCE_NAMES): raise ValueError('Exact cinematic resources required')
        ordered=[resources[name] for name in RESOURCE_NAMES]
        if any(obj.pid!=self.scope.pid for obj in ordered+[player]):
            raise ValueError('Cinematic widget identity session mismatch')
        with self.latency.measure('widgets.retain_inputs'):
            leases=[self.scope.retain(obj) for obj in ordered]
        # Serialize the identity associated with each acknowledged scoped lease.
        ordered=[lease.object for lease in leases]
        payload=b''.join(struct.pack('<iiQ',obj.index,obj.serial,obj.address) for obj in ordered+[player])
        payload+=struct.pack('<11Q',*(lease._token for lease in leases))
        payload+=call.encode_plan(replace(remove,wire_version=1))
        with self.latency.measure('widgets.native_arm'):
            return self._send(1,payload)

    def status(self):
        self._send(3)
        return dict(state=self.state,observed=self.observed,failed=self.failed)

    def diagnostics(self):
        """Read bounded route counters; mismatches are not ownership evidence."""
        session=self.scope._session;session._check()
        if getattr(session._transport,'cinematic_widget_diagnostics_protocol',0)!=1:
            raise RuntimeError('Widget route diagnostics unavailable')
        packet=HEADER.pack(1,4,self.owner,0,0,0,0,0)+bytes(SIZE-40)
        try:
            response=session._transport.command('cinematic-widget',packet)
            data=bytes.fromhex(response['cinematic_widget_packet'])
            if len(data)!=SIZE or data[:24]!=packet[:24] or any(data[60:]):
                raise ValueError('Widget diagnostic acknowledgement mismatch')
            error,state,observed,failed=HEADER.unpack_from(data)[4:]
            counts=struct.unpack_from('<5I',data,40)
            calls,frames,misses,matches,route_failures=counts
            if (error or state not in (1,2) or frames>calls or min(0xffffffff,misses+matches)>frames
                    or observed!=matches or failed!=route_failures):
                raise ValueError('Invalid widget diagnostic counters')
            self.observed,self.failed=observed,failed
            self.state='armed' if state==1 else 'quarantined'
            return dict(zip(('eligible_game_thread_calls','exact_frames','root_misses',
                            'owned_matches','route_failures'),counts))
        except BaseException:
            session._abort_ownership();raise

    def close(self):
        if self.state in ('new','closed'):return True
        return self._send(2)
