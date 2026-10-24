"""Bounded process-lifetime native guard for assigned-map collision loading."""
import re
import secrets
import struct
from .map_runtime import SIZE


def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Map load guard packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',data)
    if version!=3 or op not in (99,100,101,102) or error or state or not owner or any(data[24:88]):
        raise ValueError('Map load guard header')
    count=3 if op==99 else 2 if op==100 else 0
    for at in range(88,88+16*count,16):
        index,serial,address=struct.unpack_from('<iiQ',data,at)
        if index<0 or serial<0 or not address:raise ValueError('Map load guard identity')
    if any(data[88+16*count:2000]):raise ValueError('Map load guard identity padding')
    if op==99:
        paths=struct.unpack_from('<I',data,2000)[0]
        if not 1<=paths<=32 or any(data[2004:4096]) or any(data[4096+512*paths:]):
            raise ValueError('Map load guard worlds bound')
        for at in range(4096,4096+512*paths,512):
            raw=data[at:at+512];path=raw.split(b'\0',1)[0]
            if len(path)>=512 or not re.fullmatch(rb'/Game/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+',path) or any(raw[len(path):]):
                raise ValueError('Map load guard world path')
    elif any(data[2000:]):raise ValueError('Map load guard padding')


class MapLoadGate:
    def __init__(self,session,context,worlds):
        from .catalog import capture_matching,capture_selected
        from ._reader import ReadBatch
        self.session=session;self.owner=secrets.randbits(64) or 1;self.closed=False
        with ReadBatch(session.pid):
            c=capture_matching(session.pid,names=('SetMovementMode',))
            fn=c.find_path('/Script/Engine.CharacterMovementComponent:SetMovementMode')
            from ._metadata_stabilization import process_preparation
            fn=process_preparation(session).prepare(c,(fn,)).by_index[fn.index]
            selected=capture_selected(session.pid,(context.local_player[1:],context.gi[1:]))
            player=selected.by_index[context.local_player[1]];gi=selected.by_index[context.gi[1]]
            self.ids=(player,gi,fn);self.worlds=tuple(sorted(set(worlds)))
            self._send(99,ids=self.ids,worlds=self.worlds)

    def _send(self,op,*,ids=(),worlds=()):
        packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,op,0,0,self.owner)
        for i,obj in enumerate(ids):
            value=(obj.index,obj.serial,obj.address) if hasattr(obj,'index') and not isinstance(obj,(tuple,list)) else tuple(obj)
            struct.pack_into('<iiQ',packet,88+16*i,*value)
        if op==99:
            worlds=tuple(sorted(set(worlds)))
            if not 1<=len(worlds)<=32:raise ValueError('Map load guard worlds bound')
            struct.pack_into('<I',packet,2000,len(worlds))
            for i,path in enumerate(worlds):
                raw=path.encode('ascii')
                if len(raw)>=512:raise ValueError('Map load guard world path length')
                packet[4096+512*i:4096+512*i+len(raw)]=raw
        validate_request(bytes(packet))
        reply=self.session._transport.command('mesh',bytes(packet))
        raw=bytes.fromhex(reply['mesh_packet']);compare=bytearray(raw)
        if len(raw)!=SIZE:raise RuntimeError('Map load guard acknowledgement size')
        compare[8:16]=packet[8:16]
        if op==101:compare[4096:4146]=packet[4096:4146]
        if compare!=packet:raise RuntimeError('Map load guard acknowledgement mismatch')
        error,state=struct.unpack_from('<II',raw,8)
        if error:raise RuntimeError(f'Map load guard operation {op} rejected ({error}); not replayed')
        if state not in (0,1,2,4):raise RuntimeError('Map load guard state')
        return dict(state=state,world=list(struct.unpack_from('<iiQ',raw,4096)),pawn=list(struct.unpack_from('<iiQ',raw,4112)))

    def status(self):return self._send(101)
    def update_worlds(self,worlds):
        worlds=tuple(sorted(set(worlds)))
        if not worlds:self.close();return
        if worlds!=self.worlds:
            self._send(99,ids=self.ids,worlds=worlds);self.worlds=worlds
    def release(self,ctx):return self._send(100,ids=(ctx['visit'],ctx['pawn']))
    def close(self):
        if not self.closed:self._send(102);self.closed=True


class NativePlayerHold:
    def __init__(self,gate,expected):
        self.gate=gate;self.expected=expected;self.held=True;self.closed=False
    def close(self):
        if self.closed:return
        state=self.gate.status()
        if state['state'] in (2,4) and state['world']==self.expected['visit'] and state['pawn']==self.expected['pawn']:
            self.gate.release(self.expected)
        self.discard()
    def discard(self):self.held=False;self.closed=True
