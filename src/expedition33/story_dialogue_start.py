"""One-shot entry through the original NPC interaction event.

This only requests the native conversation. NativeStoryDialogueDriver continues
to own text, cameras, input and EndDialogue; this adapter never advances a line
or changes save flags. An uncertain request is observed, never replayed.
"""
import logging,time

from . import RuntimeQueryError
from .story_dialogue import field, identity

INTERACTION = '/Game/LevelTools/NPCs/BP_jRPG_NPC_Dialog.BP_jRPG_NPC_Dialog_C:OnInteractionRequested'
LOG=logging.getLogger('expedition33.story_dialogue_start')


def validate_plan(plan):
    # The same source event/schema already audited by native/story_portal.h.
    fields = tuple((p.name,p.kind,p.offset,p.width,p.dimension,p.flags,p.boolean_encoding)
                   for p in plan.parameters)
    expected = (
        ('InteractingWorldCharacter','ObjectProperty',0,8,1,2251868533162644,None),
        ('Instant','BoolProperty',8,1,1,2251869606904468,0xff010001),
    )
    if (plan.function_flags != 201457664 or plan.entry_rva != 0x13937a0 or
            plan.parameter_size != 9 or plan.return_offset != 65535 or fields != expected):
        raise RuntimeQueryError('Original NPC interaction schema differs')


def interaction_context(scope,npc_identity,visit):
    """Fresh local controller, its pawn, and its own dialogue system only."""
    from .story_dialogue import controller_dialogue_system
    from .values import capture_selected_values
    from .cinematics.controller_anchor import for_scope
    context=for_scope(scope).context()
    if tuple(context['world'][1:])!=tuple(visit):
        raise RuntimeQueryError('Story interaction world visit changed')
    controller=tuple(context['controller'][1:])
    catalog,values=capture_selected_values(scope.pid,(controller,npc_identity),
        fields=('Pawn','IsInDialog','SpawnedDialog'),references=True)
    npc=catalog.by_index[npc_identity[0]]
    from .cinematics.blueprint_actor import STORY_NPC
    if npc.class_name!=STORY_NPC.rsplit('.',1)[-1] or npc.object_flags&0x30:
        raise RuntimeQueryError('The owned story NPC is unavailable')
    pawn=field(values[controller[0]],'Pawn')
    if pawn is None or pawn.object_flags&0x30:return None
    worlds=[o for o in catalog.outer_chain(pawn) if o.class_name=='World']
    npc_worlds=[o for o in catalog.outer_chain(npc) if o.class_name=='World']
    if (len(worlds)!=1 or identity(worlds[0])!=tuple(visit) or
            len(npc_worlds)!=1 or identity(npc_worlds[0])!=tuple(visit)):
        raise RuntimeQueryError('Story interaction pawn/NPC world differs')
    talking=field(values[npc.index],'IsInDialog')
    dialogue=field(values[npc.index],'SpawnedDialog')
    if type(talking) is not bool:raise RuntimeQueryError('Story interaction state is incomplete')
    systems,system=controller_dialogue_system(scope.pid,controller)
    observed,data=capture_selected_values(scope.pid,(identity(system),),fields=('ActiveDialogue',),references=True)
    active=field(data[system.index],'ActiveDialogue')
    state='owned' if talking and dialogue is not None and identity(active)==identity(dialogue) else (
        'busy' if talking or active is not None else 'idle')
    catalog=catalog.with_observations(systems).with_observations(observed)
    return dict(state=state,catalog=catalog,npc=npc,pawn=pawn,controller=controller)


class StoryDialogueStart:
    """Retain one request until accepted, completed, or its world retires."""
    def __init__(self,npc,*,save_key,visit):
        from .story_npc import StoryNpc
        from ._scope import SessionScope
        from .story_save_identity import StorySaveIdentity
        if not isinstance(npc,StoryNpc):raise TypeError('An owned StoryNpc is required')
        npc.scope._check()
        self.npc=npc;self.scope=SessionScope(npc.scope)
        self.save_key=save_key;self.visit=tuple(visit)
        self.identity_reader=StorySaveIdentity(self.scope)
        self.planner=None;self.call=None;self.attempted=False;self.acknowledged=False
        self.unknown=False;self.closed=False;self.started_at=None;self.issue=None

    def poll(self):
        if self.closed:raise RuntimeError('Story dialogue request is closed')
        if self.acknowledged:return 'acknowledged'
        current=interaction_context(self.scope,self.npc.identity,self.visit)
        if current is None:return 'waiting'
        if self.identity_reader.read()!=self.save_key:
            raise RuntimeQueryError('Story interaction save identity changed')
        if current['state']=='owned':
            # A manual E request may win the race. Adopt its normal dialogue;
            # do not dispatch another event or restart its first line.
            self.acknowledged=True;self.unknown=False;self.issue=None
            return 'acknowledged'
        if self.attempted:
            if time.monotonic()-self.started_at>=2 and self.issue is None:
                self.issue='Native dialogue did not become active within 2 seconds; request retained without replay'
                LOG.warning('%s; npc=%s visit=%s controller=%s pawn=%s state=%s unknown=%s',
                    self.issue,self.npc.identity,self.visit,current['controller'],identity(current['pawn']),current['state'],self.unknown)
            return 'pending'
        if (current['state']!='idle' or self.npc.state!='visible' or
                not getattr(self.npc,'_interaction_enabled',False)):
            return 'waiting'
        from .catalog import capture_matching
        catalog=current['catalog'].with_observations(capture_matching(self.scope.pid,names=('OnInteractionRequested',)))
        self.planner=self.scope.invocation_planner(catalog=catalog,selected_results=True)
        self.call=self.planner.prepare_blueprint(current['npc'],catalog.find_path(INTERACTION),
            InteractingWorldCharacter=current['pawn'],Instant=False)
        validate_plan(self.call._plan)
        # Preparation is read-only. Recheck controller ownership and activity
        # immediately before committing the one and only invocation attempt.
        fresh=interaction_context(self.scope,self.npc.identity,self.visit)
        if (fresh is None or fresh['state']!='idle' or fresh['controller']!=current['controller']
                or identity(fresh['pawn'])!=identity(current['pawn'])):
            self.planner.close();self.planner=None;self.call=None
            return 'waiting'
        if self.identity_reader.read()!=self.save_key:
            raise RuntimeQueryError('Story interaction save changed during preparation')
        self.attempted=True;self.started_at=time.monotonic()
        try:
            with self.call.invoke():pass
        except BaseException:
            self.unknown=True
            raise
        return 'requested'

    def close(self,*,world_retired=False):
        if self.closed:return True
        # No speculative EndDialogue. The ordinary conversation driver owns
        # its lifecycle, including a request whose immediate result was lost.
        if self.attempted and not self.acknowledged and not world_retired:return False
        if self.planner is not None:self.planner.close()
        if not self.identity_reader.close():return False
        self.scope.close();self.closed=True
        return True
