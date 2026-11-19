"""Process-owned additive cosmetic definitions. Registration grants no items."""
import secrets
from . import _story_item_wire as wire
from ._reader import shared_operation

def load_resource_asset(scope,path):
    """Load a canonical /Game/SDK asset from previously installed resources."""
    from ._scope import SessionScope
    from ._stable_lease import acquire_stable
    from .catalog import capture_matching
    from .assets import load_asset
    if getattr(scope._session._transport,'story_original_narrative_protocol',0)!=1:raise RuntimeError('SDK resource-name runtime 291 required')
    child=SessionScope(scope)
    try:
        with shared_operation(scope.pid):
            c=capture_matching(scope.pid,names=('Conv_StringToName','Default__KismetStringLibrary'))
            cdo,_=acquire_stable(child,c.find_path('/Script/Engine.Default__KismetStringLibrary'))
            function,_=acquire_stable(child,c.find_path('/Script/Engine.KismetStringLibrary:Conv_StringToName'))
            packet=wire.names(secrets.randbits(64) or 1,cdo,function,path)
            reply=child._session._transport.command('mesh',packet)
            wire.decode(packet,bytes.fromhex(reply['mesh_packet']))
        return load_asset(scope,path)
    finally:child.close()

class CosmeticDefinitions:
    def __init__(self,parent):
        parent._check()
        if getattr(parent._session._transport,'story_original_narrative_protocol',0)!=1:raise RuntimeError('Additive cosmetic definitions require SDK runtime 291')
        from ._scope import SessionScope
        self._scope=parent;self.scope=SessionScope(parent);self.owner=secrets.randbits(64) or 1
        self.held=[];self.started=False;self.closed=False;self.unknown=False;self.receipt=None
        parent._register_native_owner(self);parent._close_before_descendants(self)
    def hold(self,obj):
        from ._stable_lease import acquire_stable
        if obj is None:raise RuntimeError('Story cosmetic resource unavailable')
        held,_=acquire_stable(self.scope,obj);self.held.append(held);return held
    def prepare(self,path,rows):
        from .assets import load_asset
        from .catalog import capture_matching
        from .picto_class_load import load_class
        if self.started or self.held:raise RuntimeError('Cosmetic registration preparation is one-shot')
        with shared_operation(self.scope.pid):
            self.rows=tuple(rows);self.package,self.asset=path.split('.')
            self.source=self.hold(load_resource_asset(self.scope,path).return_value)
            target='/Game/jRPGTemplate/Datatables/DT_jRPG_Items_Composite.DT_jRPG_Items_Composite'
            self.target=self.hold(load_asset(self.scope,target).return_value)
            cls='/Game/Gameplay/Pictos/BP_ItemUpgradeSystem.BP_ItemUpgradeSystem_C'
            self.map_class=self.hold(load_class(self.scope,cls).return_value)
            c=capture_matching(self.scope.pid,names=('Map_Add',))
            self.map_add=self.hold(c.find_path('/Script/Engine.BlueprintMapLibrary:Map_Add'))
            self.receipt=self.send(0);self.started=True
        return self
    def send(self,mode):
        packet=wire.definitions(self.owner,self.target,self.source,self.map_class,self.map_add,self.package,self.asset,self.rows,mode=mode)
        try:
            response=self.scope._session._transport.command('mesh',packet)
            return wire.decode(packet,bytes.fromhex(response['mesh_packet']))
        except wire.OriginalNarrativeError as error:
            if error.code==3991:self.unknown=True
            raise
        except BaseException:
            self.unknown=True;raise
    def inspect(self):return self.send(1)
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:self.send(2);self.started=False
        self.scope.close();self.closed=True;return True

def install_definitions(session,path,rows):
    """Reuse the process registration across world scopes and editor reloads."""
    from ._metadata_stabilization import process_preparation
    cache=getattr(session,'_story_cosmetic_definitions',None)
    signature=(path,tuple(rows))
    if cache is not None:
        if cache[0]!=signature or cache[1].closed or cache[1].unknown:raise RuntimeError('A different or uncertain story definition registry remains owned')
        cache[1].inspect();return cache[1]
    owner=CosmeticDefinitions(process_preparation(session).scope)
    # Retain even a partial/uncertain preparation; never reconstruct it on poll.
    session._story_cosmetic_definitions=(signature,owner)
    owner.prepare(path,rows);return owner
