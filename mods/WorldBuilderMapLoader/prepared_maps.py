"""Bounded process-only scene preparation; no engine objects or persistent cache."""
from collections import OrderedDict
import hashlib,json,os
from types import MappingProxyType
from expedition33.worldbuilder_maps import MapStore,validate,unique_object

def freeze(value):
    if type(value) is dict:return MappingProxyType({k:freeze(v) for k,v in value.items()})
    if type(value) is list:return tuple(freeze(v) for v in value)
    return value

def thaw(value):
    if isinstance(value,MappingProxyType):return {k:thaw(v) for k,v in value.items()}
    if type(value) is tuple:return [thaw(v) for v in value]
    return value

class PreparedMapStore(MapStore):
    MAX_FILE_BYTES=32*1024*1024
    MAX_CACHE_BYTES=32*1024*1024
    MAX_CACHE_ENTRIES=4
    MAX_PREPARE_ENTRIES=4
    def __init__(self,root):
        super().__init__(root)
        self._prepared=OrderedDict();self._prepared_bytes=0
        self.stats=dict(hits=0,parses=0,invalidated=0,prepared=0,failed=0,skipped=0)
    @staticmethod
    def signature(st):return st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns
    def _read_bytes(self,key):
        path=self.file(key)
        with path.open('rb') as stream:
            before=os.fstat(stream.fileno())
            if before.st_size>self.MAX_FILE_BYTES:raise ValueError('Scene file is too large')
            raw=stream.read(self.MAX_FILE_BYTES+1)
            after=os.fstat(stream.fileno())
        if len(raw)>self.MAX_FILE_BYTES:raise ValueError('Scene file is too large')
        if self.signature(before)!=self.signature(after) or self.signature(after)!=self.signature(path.stat()):
            raise ValueError('Scene changed during preparation; choose Load Now after saving finishes')
        return raw
    def _forget(self,key):
        previous=self._prepared.pop(key,None)
        if previous:self._prepared_bytes-=previous[2]
    def read(self,key):
        # Rehash current bytes before every use: even same-size/same-mtime edits
        # invalidate. Unchanged bytes avoid duplicate JSON parse and validation;
        # MapRuntime still validates its defensive copy at the mutation boundary.
        try:raw=self._read_bytes(key)
        except BaseException:
            self._forget(key);raise
        digest=hashlib.sha256(raw).digest();cached=self._prepared.get(key)
        if cached and cached[0]==digest:
            self.stats['hits']+=1;self._prepared.move_to_end(key);return thaw(cached[1])
        if cached:self.stats['invalidated']+=1;self._forget(key)
        data=validate(json.loads(raw.decode('utf8'),object_pairs_hook=unique_object))
        self.stats['parses']+=1
        if len(raw)<=self.MAX_CACHE_BYTES:
            while self._prepared and (len(self._prepared)>=self.MAX_CACHE_ENTRIES or self._prepared_bytes+len(raw)>self.MAX_CACHE_BYTES):
                self._forget(next(iter(self._prepared)))
            self._prepared[key]=(digest,freeze(data),len(raw));self._prepared_bytes+=len(raw)
        return data
    def prepare(self,keys):
        budget=self.MAX_CACHE_BYTES
        for i,key in enumerate(dict.fromkeys(keys)):
            if i>=self.MAX_PREPARE_ENTRIES:
                self.stats['skipped']+=1;continue
            try:
                size=self.file(key).stat().st_size
                if size>budget:self.stats['skipped']+=1;continue
                self.read(key);budget-=size;self.stats['prepared']+=1
            except (OSError,ValueError,KeyError,TypeError,RecursionError):self.stats['failed']+=1
        return dict(self.stats)
