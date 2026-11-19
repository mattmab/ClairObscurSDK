"""Owned, reversible runtime data-layer overrides for SDK story scenes."""
import logging
import time
from dataclasses import dataclass
from types import SimpleNamespace
from ._scope import SessionScope
from .catalog import capture_matching,capture_selected
from .map_runtime import context
from .enums import describe_enums

LOG=logging.getLogger('expedition33.story_layers')
METADATA_NAMES=('EDataLayerRuntimeState','GetDataLayerInstanceRuntimeState','SetDataLayerInstanceRuntimeState')


class LayerSelectorsPending(RuntimeError):
    """A read-only early inventory raced world construction; no state changed."""


@dataclass(frozen=True)
class LayerSelectorSnapshot:
    """Immutable copied identities only; never a world admission or engine lease."""
    world: tuple
    gi: tuple
    manager: tuple
    layers: tuple

    def __post_init__(self):
        ids=(self.world,self.gi)
        if any(type(v) is not tuple or len(v)!=4 or any(type(n) is not int for n in v) for v in ids):
            raise ValueError('Layer snapshot requires exact process identities')
        if self.world[0]!=self.gi[0] or self.world[0]<=0:raise ValueError('Layer snapshot process mismatch')
        if type(self.layers) is not tuple or len(self.layers)>512:raise ValueError('Bounded immutable layer selectors required')
        names=[];selectors=[self.manager]
        for row in self.layers:
            if type(row) is not tuple or len(row)!=2:raise ValueError('Immutable layer row required')
            name,value=row
            if type(name) is not str or not 1<=len(name)<=1024:raise ValueError('Exact layer name required')
            names.append(name);selectors.append(value)
        if len(set(names))!=len(names):raise ValueError('Unique layer selectors required')
        if any(type(v) is not tuple or len(v)!=3 or any(type(n) is not int for n in v) for v in selectors):
            raise ValueError('Exact copied layer identities required')


class LayerSelectorObserver:
    """Worker-local pure discovery, independent of Session, pawn and SaveLoaded."""
    def __init__(self,pid):
        self.pid=pid;self.snapshot=None;self.key=None;self.retry_at=0.

    def observe(self,catalog,chain):
        world,gi=chain[2:]
        key=((self.pid,*_identity(world)),(self.pid,*_identity(gi)))
        if key!=self.key:self.key=key;self.snapshot=None;self.retry_at=0.
        if self.snapshot is not None:return self.snapshot
        path=catalog.path_name(world)
        if path.startswith('/Game/Levels/UI/') or path=='/Game/Levels/Map_Game_Bootstrap.Map_Game_Bootstrap':return None
        now=time.monotonic()
        if now<self.retry_at:return None
        # A root may be visible before its partition graph. Throttle only this
        # optional read-only inventory; never delay or admit the main observer.
        self.retry_at=now+.5
        observed=capture_matching(self.pid,classes=('DataLayerManager','DataLayerInstanceWithAsset'))
        if not any(o.class_name=='DataLayerManager' and observed.path_name(o).startswith(path+':') for o in observed.objects):
            return None
        try:_,manager,layers=_layer_inventory(observed,SimpleNamespace(pid=self.pid),
                dict(world=path,visit=key[0][1:]))
        except RuntimeError as error:
            if _pending_root(error):return None
            raise
        self.snapshot=LayerSelectorSnapshot(*key,_identity(manager),tuple(sorted(layers.items())))
        return self.snapshot


def adopt_layer_selectors(scope,snapshot,ui_context=None):
    """Copy a worker's inventory; fresh admitted preparation is still required."""
    if not isinstance(snapshot,LayerSelectorSnapshot):raise TypeError('Immutable layer snapshot required')
    scope._check()
    if snapshot.world[0]!=scope.pid:raise RuntimeError('Layer preparation process changed')
    if ui_context is not None and (ui_context.kind!='world' or
            (ui_context.world,ui_context.gi)!=(snapshot.world,snapshot.gi)):
        return False
    session=getattr(scope,'_session',scope)
    session._story_layer_prepared_selectors=dict(binding=(snapshot.world,snapshot.gi),
        manager=snapshot.manager,layers=dict(snapshot.layers))
    return True


def _pending_root(error):
    return str(error).startswith(('Data-layer root observation incomplete:', 'Data-layer root binding changed:',
        'Data-layer manager ownership chain incomplete','Data-layer manager belongs to another world',
        'Current world data-layer container changed'))


def _identity(obj):return (obj.index,obj.serial,obj.address)


def _bound_key(scope,ctx):
    token=getattr(scope,'_world_binding_token',None)
    if token is None:return None
    if (not isinstance(token,(tuple,list)) or len(token)!=4 or
            not isinstance(token[0],(tuple,list)) or tuple(token[0])!=(scope.pid,*ctx['visit'])):
        raise RuntimeError('Layer discovery belongs to another admitted world')
    return tuple(tuple(value) if isinstance(value,(tuple,list)) else value for value in token)


def _root_graph(catalog,ctx,manager):
    """Prove selectors still belong to the current reflected partition graph."""
    from .values import read_values_many_with_references
    chain=catalog.outer_chain(manager)
    if len(chain)<5:raise RuntimeError('Data-layer manager ownership chain incomplete')
    world,level,settings,partition,manager=chain[-5:]
    for obj,kind in zip((world,level,settings,partition,manager),('World','Level','WorldSettings','WorldPartition','DataLayerManager')):
        if obj.object_flags&0x40000030 or catalog.path_name(catalog.by_index[obj.class_index])!='/Script/Engine.'+kind:
            raise RuntimeError('Data-layer manager ownership class changed')
    if _identity(world)!=tuple(ctx['visit']) or catalog.path_name(world)!=ctx['world']:
        raise RuntimeError('Data-layer manager belongs to another world')
    values,catalog=read_values_many_with_references(catalog,(world,level,settings,partition),
        fields=('PersistentLevel','OwningWorld','WorldSettings','WorldPartition','DataLayerManager','WorldDataLayers'))
    def field(obj,name):
        row=values[obj.index];found=[v for key,v in row.values.items() if key[1]==name]
        if row.errors or row.truncated or len(found)!=1 or found[0] is None:
            raise RuntimeError('Data-layer root observation incomplete: '+name)
        return found[0]
    for source,name,target in ((world,'PersistentLevel',level),(level,'OwningWorld',world),
            (level,'WorldSettings',settings),(settings,'WorldPartition',partition),(partition,'DataLayerManager',manager)):
        if _identity(field(source,name))!=_identity(target):raise RuntimeError('Data-layer root binding changed: '+name)
    layers=field(level,'WorldDataLayers')
    if (layers.object_flags&0x40000030 or layers.outer_index!=level.index or layers.outer_serial!=level.serial or
            catalog.path_name(catalog.by_index[layers.class_index])!='/Script/Engine.WorldDataLayers'):
        raise RuntimeError('Current world data-layer container changed')
    return catalog,layers


def _layer_inventory(catalog,scope,ctx,names=()):
    if catalog.pid!=scope.pid:raise RuntimeError('Scene process changed')
    managers=[o for o in catalog.objects if o.class_name=='DataLayerManager' and catalog.path_name(o).startswith(ctx['world']+':')]
    if len(managers)!=1:raise RuntimeError('One current-world layer manager required')
    manager=managers[0];catalog,container=_root_graph(catalog,ctx,manager)
    candidates=[o for o in catalog.objects if o.class_name=='DataLayerInstanceWithAsset' and
        (o.outer_index,o.outer_serial)==(container.index,container.serial) and not o.object_flags&0x40000030]
    if len(candidates)>512 or len({o.name for o in candidates})!=len(candidates):
        raise RuntimeError('Bounded unique current-world layer inventory required')
    selected={o.name:_identity(o) for o in candidates}
    if any(name not in selected for name in names):raise RuntimeError('Exact current-world data-layer instance required')
    return catalog,manager,selected


def prepare_layer_selectors(scope,ui_context):
    """Discover only layer identities before possession, without world authority.

    The copied World/GI must still be linked through the process-owned engine
    and viewport. No runtime state, plan, lease or admission is retained here.
    Admitted ``prepare`` reselects these identities and proves the root graph
    before querying original states or preparing any mutation.
    """
    from .values import capture_selected_values
    scope._check()
    if ui_context.kind!='world':return False
    if ui_context.world[0]!=scope.pid or ui_context.gi[0]!=scope.pid:
        raise RuntimeError('Layer preparation process changed')
    session=getattr(scope,'_session',scope)
    construction=getattr(session,'_story_construction_resources',None)
    if construction is None:return False
    key=(tuple(ui_context.world),tuple(ui_context.gi))
    saved=getattr(session,'_story_layer_prepared_selectors',None)
    if saved is not None and saved['binding']==key:return True
    session._story_layer_prepared_selectors=None
    if construction.session is not session:
        raise RuntimeError('Layer preparation resources belong to another session')
    ids=(_identity(construction.engine),_identity(construction.viewport),key[0][1:],key[1][1:])
    c,values=capture_selected_values(scope.pid,ids,
        fields=('GameViewport','World','OwningGameInstance'),references=True)
    if c.pid!=scope.pid:raise RuntimeError('Scene process changed')
    objects=tuple(c.by_index[row[0]] for row in ids)
    if tuple(map(_identity,objects))!=ids:raise LayerSelectorsPending('Layer preparation context changed')
    for obj,kind in zip(objects,('GameEngine','GameViewportClient','World','BP_jRPG_GI_Custom_C')):
        if obj.object_flags&0x40000030 or c.find_class(kind).index not in c.ancestors(obj.class_index):
            raise RuntimeError('Layer preparation context class changed')
    for obj,name,target in zip(objects,('GameViewport','World','OwningGameInstance'),objects[1:]):
        row=values[obj.index];keys=[key for key in row.types if key[1]==name]
        if (len(keys)!=1 or keys[0][0] not in c.ancestors(obj.class_index) or row.types[keys[0]]!='ObjectProperty'
                or keys[0] in row.errors or keys[0] in row.truncated or keys[0] not in row.values):
            raise RuntimeError('Layer preparation active context field is incomplete: '+name)
        if row.values[keys[0]] is None or _identity(row.values[keys[0]])!=_identity(target):
            raise LayerSelectorsPending('Layer preparation active context changed: '+name)
    ctx=dict(world=c.path_name(objects[2]),visit=ids[2])
    c=capture_matching(scope.pid,classes=('DataLayerManager','DataLayerInstanceWithAsset'))
    if not any(o.class_name=='DataLayerManager' and c.path_name(o).startswith(ctx['world']+':') for o in c.objects):
        return False  # Bootstrap and other nonpartition worlds have no layers.
    try:c,manager,layers=_layer_inventory(c,scope,ctx)
    except RuntimeError as error:
        if _pending_root(error):
            raise LayerSelectorsPending(str(error)) from error
        raise
    session._story_layer_prepared_selectors=dict(binding=key,manager=_identity(manager),layers=layers)
    return True


def _discover_layers(scope,ctx,names,construction):
    key=_bound_key(scope,ctx) if construction is not None else None
    if key is None:
        return capture_matching(scope.pid,classes=('DataLayerManager',),
            names=tuple(names)+(METADATA_NAMES if construction is None else ())),None,'registry'
    saved=getattr(scope._session,'_story_layer_selectors',None)
    reusable=saved is not None and saved['binding']==key and all(name in saved['layers'] for name in names)
    early=getattr(scope._session,'_story_layer_prepared_selectors',None)
    prepared=(not reusable and early is not None and early['binding']==key[:2]
        and all(name in early['layers'] for name in names))
    if prepared:saved=early
    try:
        if reusable or prepared:
            ids=(saved['manager'],)+tuple(saved['layers'][name] for name in names)
            catalog=capture_selected(scope.pid,ids)
        else:
            # One bounded world inventory lets later owners request different
            # exact names without another full GUObject registry scan. These
            # are only selectors: no layer runtime state is cached or leased.
            catalog=capture_matching(scope.pid,classes=('DataLayerManager','DataLayerInstanceWithAsset'))
        catalog,manager,selected=_layer_inventory(catalog,scope,ctx,names)
        if reusable or prepared:
            if _identity(manager)!=saved['manager'] or any(selected[name]!=saved['layers'][name] for name in names):
                raise RuntimeError('Prepared data-layer selectors changed')
        if not reusable:
            scope._session._story_layer_selectors=dict(binding=key,manager=_identity(manager),layers=dict(saved['layers']) if prepared else selected)
        return catalog,manager,('active-world selectors' if reusable else
            'loading-prepared selectors' if prepared else 'registry and root graph')
    except BaseException:
        # A terminal reader must yield; do not turn a stale selector into a
        # second scan/dispatch in this operation. Next preparation rediscovers.
        scope._session._story_layer_selectors=None
        scope._session._story_layer_prepared_selectors=None
        raise

class StoryDataLayers:
    def __init__(self,parent):
        self._scope=parent;self.scope=SessionScope(parent);self.planner=None
        self.state='new';self.rows=[];self.visit=None;self.unknown=False
        self.timings={}
        parent._register_native_owner(self);parent._close_before_descendants(self)
    def prepare(self,ctx,states):
        if self.state!='new' or not ctx or not ctx['ready']:raise RuntimeError('Fresh scene owner and ready world required')
        if (not states or len(states)>16 or any(type(v) is not int or v not in (0,1,2) for v in states.values()) or
                any(type(name) is not str or not 1<=len(name)<=1024 or any(ch in name for ch in ',\r\n\t\0') for name in states)):
            raise ValueError('Explicit bounded layer states required')
        construction=getattr(self.scope._session,'_story_construction_resources',None)
        fresh=context(self.scope,require_bound_world=construction is not None)
        if not fresh or fresh['visit']!=ctx['visit']:raise RuntimeError('Scene world changed before preparation')
        started=time.perf_counter()
        # An admitted world can reuse copied selectors, with fresh current
        # root/instance proof. Only requested exact names become mutable plans;
        # original layer states are always queried again through the engine.
        c,_,self.discovery_source=_discover_layers(self.scope,ctx,states,construction)
        if c.pid!=self.scope.pid:raise RuntimeError('Scene process changed')
        managers=[o for o in c.objects if o.class_name=='DataLayerManager' and c.path_name(o).startswith(ctx['world']+':')]
        if len(managers)!=1:raise RuntimeError('One current-world layer manager required')
        manager=managers[0]
        self._timing('discovery',started);started=time.perf_counter()
        if construction is not None:
            c=c.with_observations(construction.catalog(self.scope,METADATA_NAMES))
            typed=dict(construction.layer_values)
            self.planner=construction.movement_planner(self.scope,c)
        else:
            enum=c.find_path('/Script/Engine.EDataLayerRuntimeState')
            descriptor=describe_enums(c,(enum,))[enum.index]
            typed={n:descriptor.value('EDataLayerRuntimeState::'+name) for n,name in enumerate(('Unloaded','Loaded','Activated'))}
            self.planner=self.scope.invocation_planner(catalog=c,selected_results=True)
        self.visit=tuple(ctx['visit'])
        from .story_layer_batch import available
        self._batch_controller=tuple(fresh['controller']) if available(self.scope) else None
        get=c.find_path('/Script/Engine.DataLayerManager:GetDataLayerInstanceRuntimeState')
        set_=c.find_path('/Script/Engine.DataLayerManager:SetDataLayerInstanceRuntimeState')
        pending=[]
        for name,wanted in states.items():
            instances=[o for o in c.objects if o.name==name and o.class_name=='DataLayerInstanceWithAsset' and c.path_name(o).startswith(ctx['world']+':')]
            if len(instances)!=1:raise RuntimeError('Exact data-layer instance required: '+name)
            obj=instances[0];read=self.planner.prepare(manager,get,InDataLayerInstance=obj)
            pending.append((name,wanted,obj,read))
        if self._batch_controller is not None:
            previous_values=self._batch(tuple(row[3] for row in pending))
        else:
            previous_values=[]
            for _,_,_,read in pending:
                with read.invoke() as result:previous_values.append(result.return_value)
        for (name,wanted,obj,read),previous in zip(pending,previous_values):
            if previous.value not in typed:raise RuntimeError('Unknown original layer state')
            row=dict(name=name,get=read,previous=previous.value,wanted=wanted,attempted=False,applied=False)
            row['states']={n:self.planner.prepare(manager,set_,InDataLayerInstance=obj,InState=typed[n],bInIsRecursive=False) for n in typed}
            row['set']=row['states'][wanted];row['restore']=row['states'][previous.value]
            self.rows.append(row)
        self._timing('planning and original states',started)
        LOG.info('Story layers prepared; source=%s active timings=%s',self.discovery_source,self.timings)
        self.state='prepared';return self
    def _timing(self,name,started):
        elapsed=(time.perf_counter()-started)*1000
        timings=getattr(self,'timings',None)
        if timings is None:self.timings=timings={}
        timings[name]=elapsed
    def _batch(self,calls):
        from .story_layer_batch import execute
        try:return execute(self.scope,self.visit,self._batch_controller,calls)
        except BaseException:
            self.unknown=True;self.state='unknown';raise
    def apply(self):
        if self.state!='prepared':raise RuntimeError('Prepared scene owner required')
        started=time.perf_counter()
        self.state='applying'
        if getattr(self,'_batch_controller',None) is not None:
            from ._story_layer_batch_wire import LayerBatchError
            pending=[row for row in self.rows if row['previous']!=row['wanted']]
            if pending:
                try:
                    results=self._batch(tuple(row['set'] for row in pending))
                    if any(value is not True for value in results):raise RuntimeError('Data layer rejected requested state')
                    for row in pending:row['attempted']=row['applied']=True
                except BaseException as error:
                    # Prefix receipts identify exactly which calls reached the
                    # dispatcher. The failing call and owner stay quarantined;
                    # neither a rejected tail nor uncertain work is replayed.
                    if isinstance(error,LayerBatchError):
                        for row,receipt in zip(pending,error.receipts):
                            row['attempted']=receipt.outcome!='not_dispatched'
                            row['applied']=(receipt.outcome=='dispatch_returned' and not receipt.error and
                                receipt.data[row['set']._plan.return_offset]==1)
                    self.unknown=True;self.state='unknown';raise
            self._timing('apply',started);self.state='active';return self
        for row in self.rows:
            if row['previous']==row['wanted']:continue
            row['attempted']=True
            try:
                with row['set'].invoke() as result:
                    if result.return_value is not True:raise RuntimeError('Data layer rejected requested state')
                row['applied']=True
            except BaseException:self.unknown=True;self.state='unknown';raise
        self._timing('apply',started)
        LOG.info('Story layers applied; active timings=%s',self.timings)
        self.state='active';return self
    def requested_ready(self):
        if self.state!='active' or self.unknown:return False
        if getattr(self,'_batch_controller',None) is not None:
            results=self._batch(tuple(row['get'] for row in self.rows))
            return all(value.value==row['wanted'] for row,value in zip(self.rows,results))
        for row in self.rows:
            with row['get'].invoke() as result:
                if result.return_value.value!=row['wanted']:return False
        return True
    def transition(self,states):
        """Change only this owner's prepared layer states, preserving restoration."""
        if self.state!='active' or self.unknown:raise RuntimeError('Active layer owner required')
        if set(states)-{r['name'] for r in self.rows} or any(type(v) is not int or v not in (0,1,2) for v in states.values()):raise ValueError('Prepared layer states required')
        for row in self.rows:
            wanted=states.get(row['name'],row['wanted'])
            if wanted==row['wanted']:continue
            with row['get'].invoke() as result:
                if result.return_value.value!=row['wanted']:raise RuntimeError('Layer changed outside this scene owner')
            row['attempted']=True
            try:
                with row['states'][wanted].invoke() as result:
                    if result.return_value is not True:raise RuntimeError('Layer transition rejected')
            except BaseException:self.unknown=True;self.state='unknown';raise
            row['wanted']=wanted;row['applied']=wanted!=row['previous']
    def close(self):
        if self.state=='closed':return True
        if self.unknown:return False
        fresh=context(self.scope)
        if self.visit is not None and (not fresh or tuple(fresh['visit'])!=self.visit):return False
        for row in reversed(self.rows):
            if not row['applied']:continue
            with row['get'].invoke() as result:current=result.return_value.value
            # Restore only while this owner still controls the requested state.
            if current==row['wanted']:
                try:
                    with row['restore'].invoke() as result:
                        if result.return_value is not True:raise RuntimeError('Layer restoration rejected')
                except BaseException:self.unknown=True;self.state='unknown';raise
            row['applied']=False
        return self._release()
    def _release(self):
        if self.planner is not None:self.planner.close();self.planner=None
        self.scope.close();self.state='closed';return True
    def retire_world(self,*,retirement=None):
        if self.unknown:return False
        fresh=context(self.scope)
        verified=(retirement is not None and retirement.reason in ('title','epoch_changed','loading_world_changed') and tuple(retirement.previous_token[0][1:])==self.visit)
        if not verified and (not fresh or tuple(fresh['visit'])==self.visit):return False
        # World destruction owns the retired instances. Never restore into a replacement world.
        return self._release()
