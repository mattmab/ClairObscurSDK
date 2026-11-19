"""Read an original save-list row's actual view model through the engine getter."""
import secrets,struct
from ._stable_lease import acquire_stable
from .catalog import capture_matching,capture_selected
from ._scope import SessionScope
SIZE=20984
GETTER_PATHS=('/Script/UMG.Default__UserObjectListEntryLibrary','/Script/UMG.UserObjectListEntryLibrary:GetListItemObject')


class GetterMetadata:
    """Two immutable getter leases; every query still reads the live model."""
    def __init__(self,scope,catalog):
        self.scope=scope;self.session=scope._session;self.leases=[];self.ready=False
        # Partial ownership belongs to scope before any following acquisition.
        for path in GETTER_PATHS:self.leases.append(acquire_stable(scope,catalog.find_path(path))[0])
        self.ready=True
    def held(self,scope):
        self.scope._check();scope._check()
        if scope._session is not self.session or not self.ready or any(not lease.active for lease in self.leases):
            raise RuntimeError('Save-list getter metadata is unavailable or belongs to another session')
        return tuple(self.leases)
def validate(packet):
    if type(packet) is not bytes or len(packet)!=SIZE:raise ValueError('Save list query size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',packet)
    if (version,op,error,state)!=(3,250,0,0) or not owner:raise ValueError('Save list query header')
    for at in (24,40,56):
        i,s,a=struct.unpack_from('<iiQ',packet,at)
        if i<0 or s<=0 or not a:raise ValueError('Save list query identity')
    if not all(struct.unpack_from('<3Q',packet,72)) or any(packet[96:]):raise ValueError('Save list query leases/padding')

def read(scope,row,catalog=None,*,metadata=None):
    child=SessionScope(scope)
    try:
        c=catalog or (capture_selected(scope.pid,((row.index,row.serial,row.address),)) if metadata is not None else
            capture_matching(scope.pid,names=('GetListItemObject','Default__UserObjectListEntryLibrary')))
        c=c.with_observations(capture_selected(scope.pid,((row.index,row.serial,row.address),)))
        if metadata is None:
            objects=(c.resolve(row),*(c.find_path(path) for path in GETTER_PATHS))
            held=tuple(acquire_stable(child,obj)[0] for obj in objects)
        else:
            getters=metadata.held(child)
            held=(acquire_stable(child,c.resolve(row))[0],*getters)
        packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,250,0,0,secrets.randbits(64) or 1)
        for at,lease in zip((24,40,56),held):struct.pack_into('<iiQ',packet,at,lease.object.index,lease.object.serial,lease.object.address)
        struct.pack_into('<3Q',packet,72,*(lease._token for lease in held));sent=bytes(packet);validate(sent)
        with child._lease_context():response=child._session._transport.command('mesh',sent)
        reply=bytes.fromhex(response['mesh_packet']);compare=bytearray(reply)
        if len(reply)!=SIZE:raise RuntimeError('Save list query reply size')
        compare[8:16]=sent[8:16];compare[96:112]=sent[96:112]
        error,state=struct.unpack_from('<II',reply,8)
        if bytes(compare)!=sent or error or state not in (1,2):raise RuntimeError(f'Save list query rejected ({error})')
        if state==2:return None
        ident=struct.unpack_from('<iiQ',reply,96)
        return capture_selected(scope.pid,(ident,)).by_index[ident[0]]
    finally:child.close()
