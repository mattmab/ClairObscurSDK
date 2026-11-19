"""Explicit process assets shared by save-scoped narrative adapters.

This owns assets and metadata, never a World/controller/dialogue component.
Scene identities are read once for one synchronous installation; every native
adapter independently checks the current World and selected save GUID.
"""
from ._scope import SessionScope
from ._reader import shared_operation
from .catalog import capture_matching,capture_selected
from ._stable_lease import acquire_stable

class NarrativeResources:
    def __init__(self,parent):
        self.scope=SessionScope(parent);self.assets={};self.held={};self.loader=None;self.class_loader=None;self.ready=False
    def hold(self,obj):
        self.scope._check()
        if obj is None:raise RuntimeError('Missing narrative dependency')
        key=(obj.pid,obj.index,obj.serial,obj.address)
        held=self.held.get(key)
        if held is None and obj.serial==0:
            held=next((h for k,h in self.held.items() if (k[0],k[1],k[3])==(obj.pid,obj.index,obj.address) and h.active),None)
        if held is not None:
            if not held.active:raise RuntimeError('Narrative dependency lease expired')
            return held
        # Transient World actors/components must stay weak and scene scoped.
        if obj.class_name in ('World','BP_DialogueSystemComponent_C') or 'Controller' in obj.class_name:
            raise ValueError('Narrative resources cannot retain world objects')
        held,_=acquire_stable(self.scope,obj)
        stable=held.object;self.held[(stable.pid,stable.index,stable.serial,stable.address)]=held
        return held
    def load(self,path,*,cls=False):
        self.scope._check();key=(path,cls)
        if key in self.assets:
            held=self.assets[key]
            if not held.active:raise RuntimeError('Narrative asset lease expired')
            return held.object
        if cls:
            from .picto_class_load import load_class
            from .assets import PreparedAssetLoader
            if self.class_loader is None:self.class_loader=PreparedAssetLoader(self.scope,_class=True)
            self.class_loader.prepare_path(path)
            result=load_class(self.scope,path,prepared=self.class_loader)
        else:
            from .assets import PreparedAssetLoader,load_asset
            if self.loader is None:self.loader=PreparedAssetLoader(self.scope)
            self.loader.prepare_path(path)
            result=load_asset(self.scope,path,prepared=self.loader)
        obj=result.return_value
        if obj is None:raise RuntimeError('Narrative resource unavailable: '+path)
        matches=[held for held in result._leases if held.active and held.object.index==obj.index]
        if len(matches)!=1:raise RuntimeError('Narrative loader must return one owned asset')
        held=matches[0];self.assets[key]=held
        self.held[(obj.pid,obj.index,obj.serial,obj.address)]=held
        return obj

class NarrativeScene:
    def __init__(self,scope,resources):
        from .cinematics.controller_anchor import for_scope
        self.scope=SessionScope(scope)
        prepared=getattr(scope._session,'_story_construction_resources',None)
        self.context=prepared.anchor.context() if prepared is not None else for_scope(scope).context()
        names=(
            'StartRichDialogueLines','EndDialogue','IsPlayingSpecificInWorldDialogue',
            'AddItemToInventory','Default__KismetTextLibrary','StringTableIdAndKeyFromText')
        if prepared is not None:
            from .values import capture_selected_values
            c,values=capture_selected_values(scope.pid,(tuple(self.context['controller'][1:]),),fields=('BP_DialogueSystemComponent',),references=True)
            value=values[self.context['controller'][1]]
            if value.errors or value.truncated:raise RuntimeError('Current narrative component observation is incomplete')
            c=c.with_observations(prepared.catalog(scope,names))
        else:c=capture_matching(scope.pid,classes=('BP_DialogueSystemComponent_C',),names=names)
        systems=[o for o in c.objects if o.class_name=='BP_DialogueSystemComponent_C' and o.outer_index==self.context['controller'][1]]
        if len(systems)!=1:raise RuntimeError('One local narrative system required')
        transient,fresh=acquire_stable(self.scope,systems[0])
        self.system=transient.object;self.catalog=c.with_observations(fresh)
        # Derive GI from the admitted process identity, never by retaining World.
        from .story_save_identity import observe
        if hasattr(resources,'gi'):self.gi=resources.gi
        else:
            _,_,_,_,gi,_=observe(scope)
            self.gi=resources.hold(gi).object
        wid=tuple(self.context['world'][1:]);wc=capture_selected(scope.pid,(wid,))
        self.world=wc.by_index[wid[0]]
    def close(self):self.scope.close()


def prepare_resources(session,content):
    """Preload only process-owned narrative dependencies, without save hooks."""
    import logging,time
    from ._metadata_stabilization import process_preparation
    signature=repr(content)
    previous=getattr(session,'_original_narrative_resources',None)
    if previous is not None:
        if previous[0]!=signature:raise RuntimeError('Different narrative resources remain owned')
        if not previous[1].ready:raise RuntimeError('Incomplete narrative resource preparation remains owned; restart required')
        return previous[1]
    resources=NarrativeResources(process_preparation(session).scope)
    session._original_narrative_resources=(signature,resources)
    started=time.perf_counter()
    with shared_operation(session.pid):
        for row in content['ambient']:
            source=row['source'];resources.load(source+'.'+source.rsplit('/',1)[-1])
            for line in row['lines']:
                for name in ('dialogue_wave','sound'):
                    if line.get(name):resources.load(line[name])
                if line.get('sound_event'):resources.load(line['sound_event']['table'])
        for name in ('flower','jules'):resources.load(content[name]['source_class'],cls=True)
        resources.load(content['jules']['sound_override']['asset'])
    resources.ready=True
    logging.getLogger(__name__).info('Prepared %d narrative assets in %.1f ms; no scene hooks installed',len(resources.assets),(time.perf_counter()-started)*1000)
    return resources
