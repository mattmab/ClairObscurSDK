"""Explicit world callback admission and noncompensating owner retirement.

Copied observations schedule work, never authorize native writes. Domain adapters
must prove their own native cleanup. Missing metadata/unknown outcomes retain
owners; this coordinator never invokes ordinary disable on a retired world.
"""
from dataclasses import dataclass,field
import threading


class WorldLifecycleError(RuntimeError):pass


@dataclass(frozen=True)
class RetirementContext:
    previous_token: tuple
    next_token: tuple | None
    reason: str


@dataclass
class Binding:
    token: tuple
    instance: object=field(repr=False)
    scope: object=field(repr=False)
    state: str='bound'
    context: RetirementContext | None=None
    begun: bool=False
    domain_ack: bool=False
    scope_close_started: bool=False
    leases: list=field(default_factory=list,repr=False)
    scopes: list=field(default_factory=list,repr=False)
    error: str | None=None


def token_copy(token):
    if type(token) is not tuple or len(token)!=4:
        raise ValueError('Expected a copied world admission token')
    for identity in token[:3]:
        if type(identity) is not tuple or len(identity)!=4 or any(type(n) is not int for n in identity):
            raise ValueError('Expected copied world/GI/manager identities')
    if type(token[3]) is not int or token[3]<0:raise ValueError('Invalid selected slot')
    if len({identity[0] for identity in token[:3]})!=1:raise ValueError('World token process mismatch')
    return token


class WorldLifecycle:
    def __init__(self,loader,*,process_mods=('SDKManagement',)):
        self.loader=loader;self.process_mods=frozenset(process_mods)
        self._owner=threading.get_ident();self.current_token=None;self.ready=False
        self.bindings={};self._polling=False;self.ever_admitted=False

    def _check(self):
        if threading.get_ident()!=self._owner:raise WorldLifecycleError('World lifecycle requires its owner thread')

    def observe(self,admission=None,*,title=False):
        """None is uncertainty. Only an explicit fresh title/new token retires."""
        self._check()
        if type(title) is not bool:raise TypeError('Title must be an explicit verified boolean')
        self.ready=False
        world=admission is not None and admission.state=='world_ready'
        if title and world:raise ValueError('Conflicting title and gameplay observations')
        if title:
            self._retire(None,'title');self.current_token=None;return
        if not world:return
        token=token_copy(admission.token)
        if self.current_token is not None and token!=self.current_token:self._retire(token,'epoch_changed')
        if self.current_token is None or token!=self.current_token:
            if admission.activation_ready:self.current_token=token
            else:return
        # Combat in an already admitted epoch retains callback admission.
        self.ready=True
        self.ever_admitted=True

    def _retire(self,next_token,reason):
        for name,binding in self.bindings.items():
            if binding.state!='bound':continue
            if next_token is not None and binding.token==next_token:continue
            binding.state='retiring'
            binding.context=RetirementContext(binding.token,next_token,reason)
            self.loader.registry.changed(name) # Revoke captured selections before hooks.

    def observe_loading_world(self,world,gi):
        """Fresh host-confirmed destination revokes old callbacks before save admission.

        This grants no destination activation. Adapters must still acknowledge
        their own native retirement before scopes or leases can be released.
        """
        self._check()
        for value in (world,gi):
            if type(value) is not tuple or len(value)!=4 or any(type(n) is not int for n in value):
                raise ValueError('Expected copied destination identity')
        if self.current_token is None or self.current_token[:2]==(world,gi):return
        if world[0]!=self.current_token[0][0] or gi[0]!=world[0]:raise ValueError('Destination process mismatch')
        self.ready=False
        self._retire(None,'loading_world_changed')

    @property
    def cleanup_ready(self):
        return all(row.state in ('bound','retired') for row in self.bindings.values())

    def allows(self,name):
        self._check()
        if name in self.process_mods:return True
        row=self.bindings.get(name)
        return bool(self.ready and row is not None and row.state=='bound' and row.token==self.current_token)

    def require_callback(self,name):
        if not self.allows(name):raise WorldLifecycleError('Gameplay callback is waiting for its admitted world')

    def allows_scope(self,name,scope):
        if name in self.process_mods:return True
        row=self.bindings.get(name)
        return self.allows(name) and row.scope is scope

    def require_activation(self,name):
        self._check()
        if name in self.process_mods:return
        if not self.ready or self.current_token is None or not self.cleanup_ready:
            raise WorldLifecycleError('Gameplay activation waits for world admission and prior cleanup ACK')
        row=self.bindings.get(name)
        if row is not None and row.state not in ('bound','retired'):
            raise WorldLifecycleError('Previous world owner is retained')

    def bind(self,name,instance,scope):
        self.require_activation(name)
        if name in self.process_mods:return
        row=self.bindings.get(name)
        if row is not None and row.state!='retired':raise WorldLifecycleError('World owner already bound')
        self.bindings[name]=Binding(self.current_token,instance,scope)
        # Preserve admission on the scope while the process moves to a new
        # token. Fresh domain observations can then reject a cross-world race.
        scope._world_binding_token=self.current_token

    def forget(self,name):
        self._check();self.bindings.pop(name,None)

    def retained(self,name):
        row=self.bindings.get(name)
        return row is not None and row.state in ('retiring','unknown')

    def _capture(self,row):
        known={id(lease) for lease in row.leases};known_scopes={id(scope) for scope in row.scopes}
        seen=set();pending=[row.scope]
        while pending:
            scope=pending.pop()
            if id(scope) in seen:continue
            seen.add(id(scope))
            if id(scope) not in known_scopes:row.scopes.append(scope);known_scopes.add(id(scope))
            for lease in tuple(getattr(scope,'_leases',())):
                if id(lease) not in known:
                    row.leases.append(lease);known.add(id(lease))
            pending.extend(tuple(getattr(scope,'_children',())))
        if len(row.leases)>8192 or len(row.scopes)>8192:raise WorldLifecycleError('World owner journal exceeds its fixed bound')

    def _scope_domain_ack(self,scope):
        # These lists may restore borrowed/gameplay state on ordinary close.
        # Domain ACK must have retired them already; do not compensate here.
        for child in tuple(getattr(scope,'_children',())):
            if not self._scope_domain_ack(child):return False
        for field_name in ('_native_owners','_sequence_owners','_reference_owners',
                '_enemy_spawn_owners','_audio_owners','_menus'):
            for owner in tuple(getattr(scope,field_name,())):
                if getattr(owner,'_closed',False) is True:continue
                if getattr(owner,'state',None) in ('closed','released','retired'):continue
                return False
        return True

    def poll_cleanup(self):
        self._check()
        if self._polling:raise WorldLifecycleError('Recursive world retirement is unsupported')
        self._polling=True
        try:
            for name,row in tuple(self.bindings.items()):
                if row.state!='retiring':continue
                try:
                    self._capture(row)
                    if not row.domain_ack:
                        if not row.begun:
                            row.begun=True # Never replay a throwing/unknown begin.
                            revoke=getattr(row.instance,'revoke_world',None)
                            begin=getattr(row.instance,'begin_world_retirement',None)
                            poll=getattr(row.instance,'poll_world_retirement',None)
                            if not all(callable(fn) for fn in (revoke,begin,poll)):
                                row.state='unknown';row.error='UnsupportedAdapter';continue
                            revoke(row.context)
                            outcome=begin(row.context)
                        else:outcome=row.instance.poll_world_retirement(row.context)
                        if outcome=='unknown':row.state='unknown';row.error='AdapterUnknown';continue
                        if outcome not in ('ack','pending'):raise WorldLifecycleError('Invalid retirement adapter outcome')
                        if outcome=='pending':continue
                        row.domain_ack=True
                    self._capture(row)
                    if not row.scope_close_started:
                        if not all(self._scope_domain_ack(scope) for scope in row.scopes):
                            row.state='unknown';row.error='DomainOwnersRemain';continue
                        row.scope_close_started=True
                        for scope in reversed(row.scopes):
                            if getattr(scope,'_closed',False) is not True:scope.close()
                    if any(getattr(scope,'_closed',False) is not True for scope in row.scopes):
                        row.state='unknown';row.error='ScopeCloseUnacknowledged';continue
                    states={getattr(lease,'_state',None) for lease in row.leases}
                    if states-{'released','pending_release'}:
                        row.state='unknown';row.error='UnacknowledgedLeaseOutcome';continue
                    if 'pending_release' in states:continue
                    record=self.loader._loaded.get(name)
                    if record is None or record[2] is not row.scope:
                        raise WorldLifecycleError('World owner record changed during retirement')
                    record[2]=None;row.state='retired'
                    self.loader.registry.changed(name)
                except BaseException as error:
                    row.state='unknown';row.error=type(error).__name__
                    import logging
                    logging.getLogger(__name__).exception('World owner retirement held: %s',name)
        finally:self._polling=False

    def status(self):
        self._check()
        return dict(admitted=self.ready,cleanup_ready=self.cleanup_ready,
            owners={name:dict(state=row.state,error=row.error,pending_leases=sum(
                getattr(lease,'_state',None)!='released' for lease in row.leases))
                for name,row in self.bindings.items()})


class GatedActions:
    def __init__(self,actions,coordinator,name,scope):self.actions=actions;self.coordinator=coordinator;self.name=name;self.scope=scope
    @property
    def _bridge(self):
        # Harness consumes the scoped bridge interface. Keep its dispatch
        # behind this same world gate instead of exposing the raw bridge.
        return self
    @property
    def OPERATIONS(self):return self.actions._bridge.OPERATIONS
    def dispatch(self,request):
        if not self.coordinator.allows_scope(self.name,self.scope):
            raise WorldLifecycleError('Action belongs to an inactive world owner')
        return self.actions._bridge.dispatch(request)
    def register(self,name,callback,**options):
        def guarded(**arguments):
            if not self.coordinator.allows_scope(self.name,self.scope):
                raise WorldLifecycleError('Action belongs to an inactive world owner')
            return callback(**arguments)
        return self.actions.register(name,guarded,**options)
    def unregister(self,name):return self.actions.unregister(name)
    def _close(self):return self.actions._close()
