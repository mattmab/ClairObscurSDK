"""Process-owned asset preflight, independent of any destination world."""
import re,secrets,struct,time
from types import SimpleNamespace
from ._scope import SessionScope

SIZE=20984


def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Map asset packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',data)
    if version!=3 or op not in (104,105,106) or error or state or not owner or any(data[24:88]):
        raise ValueError('Map asset header')
    if op==104:
        for at in range(88,136,16):
            index,serial,address=struct.unpack_from('<iiQ',data,at)
            if index<0 or serial<=0 or not address:raise ValueError('Map asset metadata identity')
        if any(data[136:]):raise ValueError('Map asset metadata padding')
    elif op==105:
        path=data[2000:2512].split(b'\0',1)[0]
        if len(path)>=512 or not re.fullmatch(rb'/Game/[A-Za-z0-9_/-]+\.[A-Za-z0-9_]+',path) or any(data[88:2000]) or any(data[2000+len(path):]):
            raise ValueError('Map asset path or padding')
    elif any(data[88:]):raise ValueError('Map asset close padding')


class AssetPreparation:
    """Owns static asset leases until process shutdown, never a World lease.

    Construct/prepare on the Session owner thread during existing loading
    preparation. Metadata scope cleanup closes this owner before Script leases.
    """
    def __init__(self,session):
        from .catalog import capture_matching
        from ._reader import ReadBatch
        from ._metadata_stabilization import process_preparation
        session._check()
        if getattr(session._transport,'map_asset_preparation_protocol',0)!=1:
            raise RuntimeError('Map asset preparation backend unavailable')
        self.session=session;self.scope=SessionScope(session,lease_owner='SDKMapAssets')
        self.owner=secrets.randbits(64) or 1;self.closed=False;self.uncertain=False
        self.assets={};self.profile=dict(assets=0,preparation_ms=0.,load_ms=0.)
        metadata=process_preparation(session)
        metadata.scope._reference_owners.append(self)
        started=time.perf_counter()
        with ReadBatch(session.pid):
            catalog=capture_matching(session.pid,names=('Default__KismetSystemLibrary','LoadAsset_Blocking','StaticMesh'))
            ids=(catalog.find_path('/Script/Engine.Default__KismetSystemLibrary'),
                 catalog.find_path('/Script/Engine.KismetSystemLibrary:LoadAsset_Blocking'),
                 catalog.find_path('/Script/Engine.StaticMesh'))
            stable=metadata.prepare(catalog,ids)
            ids=tuple(stable.by_index[obj.index] for obj in ids)
        self._send(104,ids=ids)
        self.profile['preparation_ms']=(time.perf_counter()-started)*1000

    def _send(self,op,*,ids=(),path=None):
        if self.closed or self.uncertain:raise RuntimeError('Map asset owner unavailable')
        packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,op,0,0,self.owner)
        for i,obj in enumerate(ids):struct.pack_into('<iiQ',packet,88+16*i,obj.index,obj.serial,obj.address)
        if path is not None:
            encoded=path.encode('ascii')
            if len(encoded)>=512:raise ValueError('Map asset path length')
            packet[2000:2000+len(encoded)]=encoded
        validate_request(bytes(packet))
        try:
            with self.scope._lease_context():reply=self.session._transport.command('mesh',bytes(packet))
            raw=bytes.fromhex(reply['mesh_packet']);compare=bytearray(raw)
            if len(raw)!=SIZE:raise RuntimeError('Map asset acknowledgement size')
            compare[8:16]=packet[8:16]
            if op==105:compare[4096:4112]=packet[4096:4112]
            if compare!=packet:raise RuntimeError('Map asset acknowledgement mismatch')
        except BaseException:
            self.uncertain=True;raise
        error,state=struct.unpack_from('<II',raw,8)
        if error:
            if error==2169:self.uncertain=True
            raise RuntimeError(f'Map asset operation {op} rejected ({error}); not replayed')
        if state:
            self.uncertain=True;raise RuntimeError('Map asset acknowledgement state')
        return raw

    def prepare(self,paths):
        from .loading_preparation import service_loading_io
        self.session._check()
        if self.closed or self.uncertain:raise RuntimeError('Map asset owner unavailable')
        paths=tuple(dict.fromkeys(paths))
        if len(paths)>6000 or len(set(paths)|set(self.assets))>6000:raise ValueError('Map asset preparation limit')
        for path in paths:
            if not isinstance(path,str):raise ValueError('Map asset path type')
            if path in self.assets:continue
            started=time.perf_counter()
            if path.startswith('/Engine/'):
                mesh=self._prepare_engine_asset(path)
                index,serial,address=mesh.index,mesh.serial,mesh.address
            else:
                raw=self._send(105,path=path)
                index,serial,address=struct.unpack_from('<iiQ',raw,4096)
            if index<0 or serial<=0 or not address:
                self.uncertain=True;raise RuntimeError('Map asset retained identity missing')
            self.assets[path]=SimpleNamespace(index=index,serial=serial,address=address)
            self.profile['assets']=len(self.assets)
            self.profile['load_ms']+=(time.perf_counter()-started)*1000
            service_loading_io(self.session)
        return len(self.assets)

    def _prepare_engine_asset(self,path):
        from .catalog import capture_matching
        from ._reader import ReadBatch
        if not re.fullmatch(r'/Engine/[A-Za-z0-9_/-]+\.[A-Za-z0-9_]+',path) or len(path)>=512:
            raise ValueError('Engine static-mesh path')
        with ReadBatch(self.session.pid):
            catalog=capture_matching(self.session.pid,names=(path.rsplit('.',1)[-1],))
            mesh=catalog.find_path(path)
        if mesh.class_name!='StaticMesh':raise ValueError('Unsupported engine asset: '+path)
        if mesh.serial>0:
            lease=self.scope.retain(mesh)
        else:
            # Retain and assign the serial atomically on the game thread. An
            # ordinary lease deliberately preserves its original observation.
            from ._stable_lease import acquire_stable
            lease,_=acquire_stable(self.scope,mesh)
        current=lease.object
        if current.class_name!='StaticMesh' or current.index!=mesh.index or current.address!=mesh.address or current.serial<=0:
            raise RuntimeError('Retained engine asset identity changed')
        return current

    def get(self,path):
        self.session._check()
        if self.closed or self.uncertain:return None
        return self.assets.get(path)

    def close(self):
        if not self.closed:
            self._send(106);self.closed=True;self.assets.clear();self.scope.close()
        return True
