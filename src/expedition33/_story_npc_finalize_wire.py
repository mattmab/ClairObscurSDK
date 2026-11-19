"""One owned NPC reveal/activation transaction; never a generic command batch."""
import struct
from . import _story_npc_wire

SIZE,OP=20984,265
ID=struct.Struct('<iiQ')

def available(scope):
    value=getattr(scope._session._transport,'story_npc_finalize_protocol',0)
    return type(value) is int and value==1

def encode(owner,npc,dialogue_class,speaker,cdo,definitions,*,interaction,visual_owner=0,visual=None):
    if type(interaction) is not bool:raise TypeError('Boolean interaction gate required')
    out=bytearray(_story_npc_wire.encode(owner,npc,dialogue_class,speaker,cdo,definitions,activate=interaction))
    struct.pack_into('<I',out,4,OP)
    if visual is not None:
        struct.pack_into('<IQ',out,156,1,visual_owner);ID.pack_into(out,168,*visual)
    elif visual_owner:raise ValueError('Visual owner requires an exact visual identity')
    result=bytes(out);validate_request(result);return result

def validate_request(packet):
    if type(packet) is not bytes or len(packet)!=SIZE:raise ValueError('Owned NPC finalization packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',packet)
    interaction,show,visual_owner=struct.unpack_from('<IIQ',packet,152)
    if (version,op,error,state)!=(3,OP,0,0) or not owner or interaction>1 or show>1 or any(packet[184:]):
        raise ValueError('Owned NPC finalization header')
    plain=bytearray(packet);struct.pack_into('<I',plain,4,230);plain[156:]=bytes(SIZE-156)
    _story_npc_wire.validate_request(bytes(plain))
    if show:
        index,serial,address=ID.unpack_from(packet,168)
        if not visual_owner or visual_owner==owner or index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff or address&7:
            raise ValueError('Owned NPC visual identity')
    elif visual_owner or any(packet[168:184]):raise ValueError('Unexpected NPC visual')

class FinalizationError(RuntimeError):
    def __init__(self,error,completed,attempted):
        self.native_error=error;self.completed=completed;self.attempted=attempted
        self.outcome='unknown' if error==4341 else 'not_dispatched'
        super().__init__(f'Owned NPC finalization failed ({error}, completed={completed}, attempted={attempted}); no retry')

def decode(sent,encoded):
    data=bytes.fromhex(encoded)
    if len(data)!=SIZE or data[:8]!=sent[:8] or data[16:184]!=sent[16:184] or data[192:]!=sent[192:]:
        raise ValueError('Owned NPC finalization acknowledgement identity changed')
    error,state=struct.unpack_from('<II',data,8);completed,attempted=struct.unpack_from('<II',data,184)
    visual=struct.unpack_from('<I',sent,156)[0];prefix=(0,1,3,7) if visual else (0,1,5);full=prefix[-1]
    if (completed not in prefix or attempted not in prefix or completed&~attempted or
        prefix.index(attempted)>prefix.index(completed)+1 or error not in (0,4340,4341) or
        (not error and (state!=1 or completed!=full or attempted!=full)) or
        (error and state) or (error==4340 and (completed or attempted))):
        raise ValueError('Owned NPC finalization receipt changed')
    if error:raise FinalizationError(error,completed,attempted)
    return completed,attempted
