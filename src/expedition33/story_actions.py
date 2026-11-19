"""Observe exact original game-action completions for one selected save.

Receipts remain queued until acknowledged. World-bound callers must durably
drain receipts and close this owner before acknowledging world retirement.
"""
import secrets
from . import _story_action_wire as wire

class ActionCompletions:
    def __init__(self,parent):
        parent._check()
        cap=getattr(parent._session._transport,'story_action_completion_protocol',0)
        if type(cap) is not int or cap!=1:raise RuntimeError('Story action completion SDK runtime required')
        from ._scope import SessionScope
        self._scope=parent
        self.scope=SessionScope(parent);self.owner=secrets.randbits(64) or 1;self.held=[];self.started=False;self.closed=False;self.unknown=False;self.after=0;self.delivered=0
        parent._register_native_owner(self);parent._close_before_descendants(self)
    @property
    def state(self):return 'closed' if self.closed else 'unknown' if self.unknown else 'observing' if self.started else 'new'
    def prepare(self,key,paths):
        from .assets import load_asset
        from .catalog import capture_matching
        from .story_save_identity import observe
        from ._stable_lease import acquire_stable
        if self.started or self.held:raise RuntimeError('Action observer preparation is one-shot')
        def hold(obj):
            if obj is None:raise RuntimeError('Original action definition unavailable')
            held,_=acquire_stable(self.scope,obj);self.held.append(held);return held
        _,_,_,_,gi,_=observe(self.scope)
        c=capture_matching(self.scope.pid,names=('OnGameActionExecutionFinished',))
        self.function=hold(c.find_path('/Game/Gameplay/GameActionsSystem/BP_GameActionExecutorComponent.BP_GameActionExecutorComponent_C:OnGameActionExecutionFinished'))
        self.gi=hold(gi);self.sources=tuple(hold(load_asset(self.scope,path).return_value) for path in paths);self.key=key
        self._send(0);self.started=True;return self
    def _send(self,mode):
        packet=wire.encode(self.owner,self.function,self.gi,self.sources,self.key,mode=mode,after=self.after)
        try:
            reply=self.scope._session._transport.command('mesh',packet)
            return wire.decode(packet,bytes.fromhex(reply['mesh_packet']))
        except BaseException:
            self.unknown=True;raise
    def poll(self):
        self.scope._check()
        if not self.started or self.closed or self.unknown:raise RuntimeError('Action observer unavailable')
        rows=self._send(1)
        if rows:self.delivered=rows[-1]['sequence']
        return rows
    def acknowledge(self,sequence):
        if type(sequence) is not int or not self.after<=sequence<=self.delivered:raise ValueError('Acknowledge only delivered action receipts')
        self.after=sequence
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:self._send(2);self.started=False
        self.scope.close();self.closed=True;return True
