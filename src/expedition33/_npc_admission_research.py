"""Exact read-only original NPC admission probe; grants no spawning authority."""
import secrets
import struct
SIZE=20984

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('NPC admission packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',data)
    if (version,op,error,state)!=(3,134,0,0) or not owner or any(data[24:88]) or any(data[136:]):raise ValueError('NPC admission packet header/padding')
    for at in (88,104,120):
        index,serial,address=struct.unpack_from('<iiQ',data,at)
        if index<0 or serial<0 or address<0x10000:raise ValueError('Exact NPC admission identity required')

def request(scope,identities):
    scope._check()
    capability=getattr(scope._session._transport,'npc_presentation_admission_research_protocol',0)
    if type(capability) is not int or capability!=1:raise RuntimeError('Original NPC admission research unavailable')
    if len(identities)!=3:raise ValueError('Expected original class, CDO and own availability function')
    packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,134,0,0,secrets.randbits(64) or 1)
    for n,obj in enumerate(identities):struct.pack_into('<iiQ',packet,88+16*n,obj.index,obj.serial,obj.address)
    validate_request(bytes(packet))
    with scope._lease_context():reply=scope._session._transport.command('mesh',bytes(packet))
    raw=bytes.fromhex(reply['mesh_packet'])
    if len(raw)!=SIZE:raise RuntimeError('NPC admission acknowledgement size')
    compare=bytearray(raw);compare[8:16]=packet[8:16];compare[4096:4100]=packet[4096:4100]
    if compare!=packet:raise RuntimeError('NPC admission acknowledgement changed immutable data')
    error,state=struct.unpack_from('<II',raw,8)
    if error:return dict(admitted=False,native_error=error,actors_spawned=0)
    if state!=1 or struct.unpack_from('<I',raw,4096)[0]!=1:raise RuntimeError('NPC admission acknowledgement incomplete')
    return dict(admitted=True,actors_spawned=0,scope='Exact class/CDO/constant-unavailable contract only; not lifecycle or spawning permission')
