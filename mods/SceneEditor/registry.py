"""Scene-local typed registry/load adapter; never spawns gameplay Blueprints."""
import struct
from expedition33.catalog import capture_matching,capture_selected
from expedition33._runtime_scene_wire import validate_request

class Registry:
    TYPES=('SkeletalMesh','AnimSequence','SoundWave','SoundCue','MetaSoundSource')
    def __init__(self,runtime):self.runtime=runtime;self.rows={};self.classes=None
    def command(self,op,payload):
        if self.runtime.uncertain:raise RuntimeError('Unknown native outcome; session teardown owns cleanup')
        p=bytearray(20984);struct.pack_into('<4IQ',p,0,self.runtime.session._session._transport.runtime_scene_protocol,op,0,0,self.runtime.owner)
        for at,data in payload:p[at:at+len(data)]=data
        validate_request(bytes(p))
        self.runtime.uncertain=True
        raw=bytes.fromhex(self.runtime.session._session._transport.command('mesh',bytes(p))['mesh_packet'])
        if len(raw)!=len(p) or raw[:8]!=p[:8] or raw[16:24]!=p[16:24]:raise RuntimeError('Catalog acknowledgement mismatch; no retry')
        self.runtime.uncertain=False
        error=struct.unpack_from('<I',raw,8)[0]
        if error:raise RuntimeError('Scene asset adapter rejected request: '+str(error))
        return raw
    @staticmethod
    def identity(o):return struct.pack('<iiQ',o.index,o.serial,o.address)
    def discover(self):
        c=capture_matching(self.runtime.session.pid,names=(*self.TYPES,'LoadAsset_Blocking','Default__KismetSystemLibrary'))
        self.classes=[c.by_index[c.find_class(name).index] for name in self.TYPES]
        self.function=next(o for o in c.objects if o.class_name=='Function' and o.name=='LoadAsset_Blocking')
        self.default=next(o for o in c.objects if o.name=='Default__KismetSystemLibrary')
    def catalog(self,kind=0):
        if kind in self.rows:return self.rows[kind]
        if self.classes is None:self.discover()
        rows=[];offset=0
        while True:
            raw=self.command(80,((88,self.identity(self.classes[kind])),(104,struct.pack('<I',kind)),(2000,struct.pack('<I',offset))))
            total,count=struct.unpack_from('<II',raw,3560)
            if count>32 or total>250000 or offset+count>total or not count and offset<total:raise RuntimeError('Invalid scene registry page')
            rows.extend(raw[4000+i*512:4000+(i+1)*512].split(b'\0')[0].decode('ascii') for i in range(count))
            offset+=count
            if offset==total:break
        self.rows[kind]=rows;return rows
    def audio_catalog(self):
        paths={path:kind for kind in (2,3,4) for path in self.catalog(kind)}
        self.audio_kinds=paths
        return tuple(sorted(paths))
    def audio_kind(self,path):
        if not hasattr(self,'audio_kinds'):self.audio_catalog()
        try:return self.audio_kinds[path]
        except KeyError:raise ValueError('Choose an asset from the game audio library') from None
    def load(self,scope,path,kind):
        rows=self.catalog(kind)
        try:index=rows.index(path)
        except ValueError:raise ValueError('Asset is not in the typed game registry: '+path) from None
        raw=self.command(81,((88,self.identity(self.default)),(104,self.identity(self.function)),(120,struct.pack('<II',index,kind))))
        index,serial,address=struct.unpack_from('<iiQ',raw,24)
        c=capture_selected(scope.pid,((index,serial,address),))
        return scope.retain(c.by_index[index]).object
    def release_loading(self):self.command(82,())
