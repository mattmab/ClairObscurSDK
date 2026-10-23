"""SDK-owned original NPC presentation and once-only isolated encounter entry."""
import secrets,time
from ._scope import SessionScope
from ._npc_staging_research import NativeStagingOwner
from ._npc_approach_trigger import ApproachTrigger,OverlapTrigger
from ._npc_encounter_preparation import prepare_original,bind_original_arena,prepare_dispatch,dispatch_original,interaction_queries,CLASS,SOURCE,ALICIA_CLASS,ALICIA_SOURCE,CURATOR_CLASS,CURATOR_SOURCE,FRANCOIS_CLASS,FRANCOIS_SOURCE

VARIANTS=('collisionless_proximity','collision_overlap','custom_dialogue')

def routes():
    return (dict(id='clea-normal',name='Clea',presentation_class=CLASS,source_path=SOURCE,
        encounter_row='CFH_Boss_Clea',variants=VARIANTS,policy='isolated',original_arena_verified=False,
        limitation='Explicit current-map standard arena; original Flying House arena and Alpha are not included'),
        dict(id='alicia-reacher',name='Alicia',presentation_class=ALICIA_CLASS,
            source_path=ALICIA_SOURCE,
            encounter_row='RC_Alicia',variants=('collisionless_proximity',),policy='isolated',original_arena_verified=False,
            verification='Appearance, idle, proximity entry, fight, victory and owned cleanup verified; own turn not confirmed',
            limitation='Current-map standard arena; original Reacher arena and campaign sequences not included'),
        dict(id='curator-lumiere',name='Curator / Renoir - Lumiere',presentation_class=CURATOR_CLASS,
            source_path=CURATOR_SOURCE,encounter_row='L_Boss_Curator_P1',
            variants=('collisionless_proximity',),policy='isolated',original_arena_verified=False,
            verification='Assembly, idle, approach entry, phase 2, final cutscene, battle completion and owned cleanup verified',
            authored_sequences=True,campaign_state_isolation_verified=False,
            limitation='Preserves authored Renoir / Sirene phase transitions and cutscenes. Participants may float outside the original map. Campaign flag isolation is unverified.'),
        dict(id='francois-esquienest',name='Francois',presentation_class=FRANCOIS_CLASS,
            source_path=FRANCOIS_SOURCE,encounter_row='EN_Francois',
            variants=('collisionless_proximity',),policy='isolated',original_arena_verified=False,
            verification='Original assembly, grounded spawn, approach entry, user-confirmed fight and win, owned cleanup verified',
            limitation='Current-map standard arena. Original static NPC includes its quest-conditioned rock sculpture. Own turn was not separately described.'))

class NpcEncounter:
    def __init__(self,scope,*,route='clea-normal',variant='collisionless_proximity',tuning=None):
        from .encounter_tuning import settings,EncounterTuningOwner
        self.tuning=settings(tuning);EncounterTuningOwner.check_available(scope,self.tuning);self._tuning=None
        if variant not in VARIANTS:raise ValueError('Unknown Clea spawn variation')
        if route not in ('clea-normal','alicia-reacher','curator-lumiere','francois-esquienest'):raise ValueError('No prepared NPC encounter route for this identity')
        if route=='alicia-reacher' and variant!='collisionless_proximity':raise ValueError('Alicia candidate supports proximity only')
        if route=='curator-lumiere' and variant!='collisionless_proximity':raise ValueError('Curator candidate supports proximity only')
        if route=='francois-esquienest' and variant!='collisionless_proximity':raise ValueError('Francois candidate supports proximity only')
        scope._check()
        if route=='alicia-reacher' and getattr(scope._session._transport,'npc_alicia_encounter_protocol',0)!=1:raise RuntimeError('Current Alicia encounter runtime required')
        if route=='curator-lumiere' and getattr(scope._session._transport,'npc_curator_encounter_protocol',0)!=1:raise RuntimeError('Current Curator encounter runtime required')
        if route=='francois-esquienest' and getattr(scope._session._transport,'npc_francois_encounter_protocol',0)!=1:raise RuntimeError('Current Francois encounter runtime required')
        if getattr(scope._session._transport,'npc_proximity_research_protocol',0)!=1:raise RuntimeError('Current NPC approach runtime required')
        if variant!='collisionless_proximity' and getattr(scope._session._transport,'npc_interaction_variants_protocol',0)!=1:raise RuntimeError('Current NPC collision/overlap runtime required')
        self._route=route
        self.variant=variant;self._overlap_queries=None;self._prepared_entry=None;self._dispatch_seconds=None
        self._scope=SessionScope(scope);self._owner=NativeStagingOwner(self._scope,secrets.randbits(64) or 1)
        self.phase='new';self.error=None;self._queries=None;self._trigger=None;self._next_poll=0.
        self._last=None;self._dispatch_attempted=False;self._dispatch_returned=False;self._battle_completed=False
    def status(self):
        return dict(route=self._route,variant=self.variant,phase=self.phase,error=self.error,owner_token=self._owner.token,
            actor_identity=self._last.get('actor_identity') if self._last else None,
            dispatch_attempted=self._dispatch_attempted,dispatch_returned=self._dispatch_returned,battle_completed=self._battle_completed,approach_armed=bool(self._trigger and self._trigger.armed),
            native=self._last,dispatch_seconds=self._dispatch_seconds)
    def stage(self,arena_identity):
        self._scope._check()
        if self.phase!='new':raise RuntimeError('NPC construction is never replayed')
        self.phase='preparing'
        try:
            self._last,self._queries=(prepare_original(self._scope,self._owner) if self._route=='clea-normal' else prepare_original(self._scope,self._owner,route=self._route))
            if self._last['native_error']:raise RuntimeError('NPC construction rejected: '+str(self._last['native_error']))
            bound=bind_original_arena(self._scope,self._owner,arena_identity)
            if bound['native_error']:raise RuntimeError('NPC arena binding rejected: '+str(bound['native_error']))
            # Restore grounded placement readback required by the existing reveal API.
            self._owner.placement_status();self._last=self._owner.reveal()
            if self._last['native_error']:raise RuntimeError('NPC reveal rejected: '+str(self._last['native_error']))
            if self.variant!='collisionless_proximity':
                functions=interaction_queries(self._scope)
                self._last=self._owner.enable_collision(functions[:4])
                if self._last['native_error']:raise RuntimeError('Solid collision configuration failed: '+str(self._last['native_error']))
                self._overlap_queries=tuple(self._queries)+(functions[4],)
            self._prepared_entry=(prepare_dispatch(self._scope,self._owner) if self._route=='clea-normal' else prepare_dispatch(self._scope,self._owner,route=self._route))
            if not self.tuning.is_default:
                from .encounter_tuning import EncounterTuningOwner
                self._tuning=EncounterTuningOwner(self._scope,self._owner.token,self.tuning)
                self._tuning.arm(self._last['actor_identity'],npc=True)
            self._trigger=(OverlapTrigger(self._owner.token,self._last['actor_identity']) if self.variant=='collision_overlap' else ApproachTrigger(self._owner.token,self._last['actor_identity']))
            self.phase='waiting_for_approach'
            return self.status()
        except BaseException as error:
            self.phase='failed';self.error=f'{type(error).__name__}: {error}';raise
    def poll(self):
        if self.phase not in ('waiting_for_approach','battle_pending','battle_active'):return self.status()
        if time.monotonic()<self._next_poll:return self.status()
        self._next_poll=time.monotonic()+.25
        try:
            if self.phase=='waiting_for_approach':
                self._last=(self._owner.overlap(self._overlap_queries) if self.variant=='collision_overlap' else self._owner.proximity(self._queries))
                if self._trigger.observe(self._last):
                    if self.variant=='custom_dialogue':self.phase='dialogue_ready'
                    else:self._begin_battle()
            else:
                self._last=self._owner.status()
                if self._last['native_error']:raise RuntimeError('NPC battle status rejected')
                if self._last['entry_phase']==2:self.phase='battle_active'
                elif self._last['entry_phase']==3:
                    self._battle_completed=True
                    if not self.close():raise RuntimeError('Completed NPC retirement deferred')
            return self.status()
        except BaseException as error:
            self.phase='failed';self.error=f'{type(error).__name__}: {error}';raise
    def _begin_battle(self):
        if self._dispatch_attempted:raise RuntimeError('Battle entry is never replayed')
        self._dispatch_attempted=True;self.phase='battle_pending'
        self._scope._session._native_menu_service.close_menu()
        started=time.monotonic()
        try:dispatch_original(self._scope,self._owner,self._prepared_entry)
        finally:self._dispatch_seconds=time.monotonic()-started
        self._dispatch_returned=True
    def dialogue(self):
        if self.phase!='dialogue_ready':raise RuntimeError('No active Clea conversation')
        return dict(speaker='Clea',text='Have you come to challenge me?',choices=(('fight','Fight Clea'),('leave','Leave')),
            custom=True,original_campaign_dialogue=False)
    def choose_dialogue(self,choice):
        self._scope._check()
        if self.phase!='dialogue_ready' or choice not in ('fight','leave'):raise ValueError('Choose an active dialogue option')
        if choice=='leave':
            self._trigger=ApproachTrigger(self._owner.token,self._last['actor_identity'])
            self.phase='waiting_for_approach';return self.status()
        try:self._begin_battle()
        except BaseException as error:
            self.phase='failed';self.error=f'{type(error).__name__}: {error}';raise
        return self.status()
    def close(self):
        if self.phase=='closed':return True
        if getattr(self,'_tuning',None) is not None:self._tuning.close()
        if not self._owner.close():
            self._last=self._owner.last_result
            return False
        self._last=self._owner.last_result
        self._scope.close();self._prepared_entry=None;self.phase='closed';return True
