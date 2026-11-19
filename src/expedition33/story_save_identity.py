"""Read or insert a save-carried story identity in the current admitted world.

Uses the game's GUID history map through the dedicated native owner. Does not
request autosaves, alter campaign flags, or keep a slot-number association.
"""
import secrets
import struct
from . import RuntimeQueryError
from . import _story_identity_wire as wire


class IdentityError(RuntimeQueryError):
    def __init__(self, code):
        self.code=code
        super().__init__('Story save identity request failed ('+str(code)+')')


def decode(sent, reply):
    if type(reply) is not bytes or len(reply)!=wire.SIZE:
        raise RuntimeQueryError('Story identity acknowledgement size')
    error,state=struct.unpack_from('<II',reply,8)
    mode=struct.unpack_from('<I',sent,144)[0]
    compare=bytearray(reply);compare[8:16]=sent[8:16]
    if not error and state==1 and mode==0:
        if struct.unpack_from('<I',reply,128)[0]!=wire.PREFIX:
            raise RuntimeQueryError('Story identity acknowledgement namespace')
        compare[128:144]=sent[128:144]
    if bytes(compare)!=sent:raise RuntimeQueryError('Story identity acknowledgement changed its context')
    if error:
        if state or error not in (3880,3881):raise RuntimeQueryError('Invalid story identity rejection')
        raise IdentityError(error)
    if state==2 and mode==0:return None
    if state!=1:raise RuntimeQueryError('Story identity request was not acknowledged')
    return ''.join('%08x'%word for word in struct.unpack_from('<4I',reply,128))


class StoryIdentityNotReady(RuntimeQueryError):
    """Read-only discovery raced loading; no identity command was dispatched."""

def observe(scope):
    from ._reader import shared_operation
    try:
        with shared_operation(scope.pid):return _observe(scope)
    except RuntimeQueryError as error:
        if any(message in str(error) for message in ('Catalog outer missing or changed','DESCRIPTOR_IDENTITY_CHANGED','SELECTED_DEPENDENCY_NOT_REGISTERED','Object identity changed or belongs to another process','Object property reference changed during observation')):
            raise StoryIdentityNotReady('Story identity discovery is waiting for stable loading objects') from error
        raise

def _observe(scope):
    from .catalog import capture_matching,capture_selected
    from .values import capture_selected_values
    from .cinematics.controller_anchor import for_scope
    scope._check()
    construction=getattr(getattr(scope,'_session',None),'_story_construction_resources',None)
    if construction is not None and hasattr(construction,'viewport'):
        context=construction.anchor.context()
        current=capture_selected(scope.pid,(context['world'][1:],context['controller'][1:]))
        # Process-owned selectors carry no cached save/world authority. The
        # native identity owner checks Engine -> Viewport -> current World,
        # World -> GI, local controller membership and the save on every read.
        function=next(o for o in construction.metadata if o.name=='Map_Add')
        return (construction.engine,construction.viewport,current.by_index[context['world'][1]],
                current.by_index[context['controller'][1]],construction.resources.gi,function)
    if construction is not None and hasattr(construction,'engine'):
        context=construction.anchor.context()
        engine=construction.engine
        catalog=construction.catalog(scope,('Map_Add',)).with_observations(
            capture_selected(scope.pid,((engine.index,engine.serial,engine.address),)))
    else:
        context=for_scope(scope).context()
        catalog=capture_matching(scope.pid,classes=('GameEngine',),names=('Map_Add',))
    catalog=catalog.with_observations(capture_selected(scope.pid,(context['world'][1:],context['controller'][1:])))
    if catalog.pid!=scope.pid:raise RuntimeQueryError('Story identity process changed')
    world=catalog.by_index[context['world'][1]];controller=catalog.by_index[context['controller'][1]]
    engines=[o for o in catalog.objects if o.class_name=='GameEngine' and not o.object_flags&0x30]
    if len(engines)!=1:raise RuntimeQueryError('One current game engine required')
    engine=engines[0]
    _,values=capture_selected_values(scope.pid,tuple((o.index,o.serial,o.address) for o in (engine,world)),
        fields=('GameViewport','OwningGameInstance'),references=True)
    def field(value,name):
        keys=[key for key in value.types if key[1]==name]
        if len(keys)!=1 or keys[0] in value.errors or keys[0] not in value.values:
            raise RuntimeQueryError('Story identity context is incomplete: '+name)
        result=value.values[keys[0]]
        if result is None:raise RuntimeQueryError('Story identity context is not ready: '+name)
        return result
    viewport=field(values[engine.index],'GameViewport');gi=field(values[world.index],'OwningGameInstance')
    function=catalog.find_path('/Script/Engine.BlueprintMapLibrary:Map_Add')
    return engine,viewport,world,controller,gi,function


class StorySaveIdentity:
    def __init__(self,parent,*,observer=observe):
        parent._check();cap=getattr(parent._session._transport,'story_save_identity_protocol',0)
        if type(cap) is not int or cap!=2:raise RuntimeQueryError('Story save identity reader runtime required')
        from ._scope import SessionScope
        self.scope=SessionScope(parent);self.observer=observer;self.unknown=False;self.closed=False

    def _send(self,key,insert,*,_objects=None):
        if self.closed or self.unknown:raise RuntimeQueryError('Story identity owner is unavailable')
        from ._stable_lease import acquire_stable
        objects=list(self.observer(self.scope) if _objects is None else _objects)
        prepared=getattr(self.scope._session,'_story_construction_resources',None)
        gi=getattr(getattr(prepared,'resources',None),'gi',None)
        borrowed=gi is not None and (gi.index,gi.serial,gi.address)==(objects[4].index,objects[4].serial,objects[4].address)
        if borrowed:held=prepared.resources.hold(gi)
        else:held,_=acquire_stable(self.scope,objects[4])
        objects[4]=held.object
        try:
            packet=wire.encode(secrets.randbits(64) or 1,held._token,objects,key,insert=insert)
            with self.scope._lease_context():response=self.scope._session._transport.command('mesh',packet)
            return decode(packet,bytes.fromhex(response['mesh_packet']))
        except IdentityError as error:
            if error.code==3881:self.unknown=True
            raise
        except BaseException:
            self.unknown=True;raise
        finally:
            if not self.unknown and not borrowed:held.release()

    def read(self):return self._send('e33c5701'+'0'*24,False)
    def read_context(self,ctx):
        """Read through an already observed bound context; native revalidates it."""
        prepared=getattr(self.scope._session,'_story_construction_resources',None)
        if prepared is None or not hasattr(prepared,'viewport') or 'controller' not in ctx:return self.read()
        token=getattr(self.scope,'_world_binding_token',None)
        if not ctx.get('ready') or token is None or tuple(token[0][1:])!=tuple(ctx['visit']):
            raise StoryIdentityNotReady('Identity context differs from scope admission')
        from types import SimpleNamespace
        def obj(identity):
            if len(identity)!=3 or any(type(v) is not int for v in identity):raise ValueError('Observed context identity required')
            return SimpleNamespace(index=identity[0],serial=identity[1],address=identity[2])
        function=next(o for o in prepared.metadata if o.name=='Map_Add')
        objects=(prepared.engine,prepared.viewport,obj(ctx['visit']),obj(ctx['controller']),prepared.resources.gi,function)
        try:return self._send('e33c5701'+'0'*24,False,_objects=objects)
        except IdentityError as error:
            if error.code==3880:raise StoryIdentityNotReady('Native identity context changed before read') from error
            raise
    def bind(self,key):return self._send(key,True)
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        self.scope.close();self.closed=True;return True
