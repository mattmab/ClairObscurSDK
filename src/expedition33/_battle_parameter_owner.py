"""Scoped private copy-test owner; ordinary encounter spawning is separate."""
import secrets
import threading
from ._battle_parameter_wire import build_request,validate_response,ParameterOperationError

class ParameterResearchOwner:
    def __init__(self,scope):
        scope._check();self._scope=scope;self._transport=scope._session._transport
        capability=getattr(self._transport,'battle_parameter_frame_research_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Candidate parameter-copy capability unavailable')
        if getattr(self._transport,'_parameter_research_owner',None) is not None:raise RuntimeError('Parameter research already owned')
        self._thread=threading.get_ident();self._owner=secrets.randbits(64) or 1
        self._attempted=False;self._unknown=False;self._closed=False
        self._transport._parameter_research_owner=self
        scope._reference_owners.append(self)

    def _command(self,operation,identities=(),**options):
        if threading.get_ident()!=self._thread or self._closed:raise RuntimeError('Parameter owner thread/lifetime mismatch')
        if self._unknown:raise RuntimeError('Parameter outcome unknown; native controller cleanup required')
        request=build_request(self._owner,operation,identities,**options)
        try:
            reply=self._transport.command('mesh',request)
            response=bytes.fromhex(reply['mesh_packet'])
            validate_response(request,response)
            return response
        except ParameterOperationError as error:
            if error.native_error in (408,3056):self._unknown=True
            raise
        except BaseException:
            self._unknown=True;raise

    def match(self,identities):
        self._scope._check()
        if self._attempted:raise RuntimeError('Copy already attempted')
        return self._command(124,identities)

    def copy_cleanup(self,identities):
        self._scope._check()
        if self._attempted:raise RuntimeError('Parameter copy already attempted; no replay')
        self._attempted=True
        return self._command(125,identities)

    def policy_cleanup(self,identities,*,mode,anchor_owner):
        self._scope._check()
        capability=getattr(self._transport,'battle_parameter_policy_research_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Policy-copy candidate capability unavailable')
        if self._attempted:raise RuntimeError('Parameter policy already attempted; no replay')
        self._attempted=True
        return self._command(127,identities,mode=mode,anchor_owner=anchor_owner)

    def close(self):
        if self._closed:return True
        if self._attempted:
            try:self._command(126)
            except ParameterOperationError as error:
                if error.native_error==407:return False
                raise
        self._closed=True
        if getattr(self._transport,'_parameter_research_owner',None) is self:self._transport._parameter_research_owner=None
        if self in self._scope._reference_owners:self._scope._reference_owners.remove(self)
        return True

    def dispatch_trigger_cleanup(self,identities,*,anchor,arena,mode=1):
        """One isolated original entry, with a held trigger and grounded owned arena.

        Native source, private ID, exact arena lease and fresh placement proofs
        remain authoritative. Both native actors survive unknown startup.
        """
        self._scope._check()
        capability=getattr(self._transport,'enemy_trigger_entry_research_protocol',0)
        if type(capability) is not int or capability!=1:
            raise RuntimeError('Original trigger entry capability unavailable')
        if (anchor._scope is not self._scope or arena._scope is not self._scope or
            anchor._transport is not self._transport or arena._transport is not self._transport or
            not anchor._trigger_anchor or anchor._closed or not anchor._prepared or anchor._grounded or
            anchor.phase!='spawned' or arena._closed or arena.phase!='spawned' or arena._component_uncertain):
            raise RuntimeError('Same-scope held trigger and owned arena required')
        if (not arena.grounding or not arena.grounding.get('verified') or
            not arena.camera_focus or not arena.camera_focus.get('verified')):
            raise RuntimeError('Verified owned arena grounding and original camera focus required')
        if tuple(anchor.arena_identity or ())!=tuple(arena.actor_identity or ()) or not arena.actor_identity:
            raise RuntimeError('Exact owned arena binding required')
        identities=tuple(identities)
        if len(identities)!=6 or tuple((identities[3].index,identities[3].serial,identities[3].address))!=tuple(anchor.actor_identity or ()):
            raise ValueError('Exact trigger parameter identity required')
        return self.entry_arena_cleanup(identities,mode=mode,anchor_owner=anchor._owner,dispatch=True,arena_policy=1)

    def entry_preflight_cleanup(self,identities,*,mode,anchor_owner):
        self._scope._check()
        capability=getattr(self._transport,'battle_entry_preflight_research_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Entry-preflight candidate capability unavailable')
        if self._attempted:raise RuntimeError('Parameter entry preflight already attempted; no replay')
        self._attempted=True
        return self._command(128,identities,mode=mode,anchor_owner=anchor_owner)

    def entry_arena_cleanup(self,identities,*,mode,anchor_owner,dispatch=False,arena_policy=0):
        self._scope._check()
        if type(dispatch) is not bool or (dispatch and mode not in (1,2)):raise ValueError('Explicit isolated dispatch required')
        for name in ('battle_entry_preflight_research_protocol','battle_entry_arena_research_protocol')+(
                ('battle_entry_dispatch_research_protocol',) if dispatch else ()):
            capability=getattr(self._transport,name,0)
            expected=2 if name=='battle_entry_arena_research_protocol' else 1
            if type(capability) is not int or capability!=expected:raise RuntimeError('Owned entry/arena candidate capability unavailable')
        if self._attempted:raise RuntimeError('Parameter entry already attempted; no replay')
        self._attempted=True
        return self._command(130 if dispatch else 129,identities,mode=mode,anchor_owner=anchor_owner,arena_policy=arena_policy)
