"""Copied authoritative owned-battle completion receipt; never idle inference."""
from dataclasses import dataclass
import struct

PACKET=struct.Struct('<4I2Q'+'iiQ'*4)
MAGIC=0x52423345
STATES={1:'pending',2:'ready',3:'consumed',4:'revoked',5:'unknown'}

@dataclass(frozen=True)
class CompletionReceipt:
    state:str
    result:str|None
    battle:int
    generation:int=0
    world:tuple|None=None
    controller:tuple|None=None
    source:tuple|None=None
    arena:tuple|None=None

def decode(data,*,owner):
    if type(data) is not bytes or len(data)!=PACKET.size:
        raise ValueError('Exact completion receipt size required')
    magic,version,result,state,battle,generation,*identities=PACKET.unpack(data)
    if magic!=MAGIC or version!=1 or state not in STATES or battle!=owner:
        raise ValueError('Completion receipt header/owner mismatch')
    if state==2:
        if result not in (1,2) or generation<=0:
            raise ValueError('Explicit original victory/defeat receipt required')
        rows=tuple(tuple(identities[i:i+3]) for i in range(0,12,3))
        if any(index<0 or serial<=0 or not 0x10000<=address<=0x7fffffffffff for index,serial,address in rows):
            raise ValueError('Complete stable completion context identities required')
        return CompletionReceipt(STATES[state],{1:'victory',2:'defeat'}[result],battle,generation,*rows)
    if result or generation or any(identities):
        raise ValueError('Non-receipt state must not carry completion data')
    return CompletionReceipt(STATES[state],None,battle)
