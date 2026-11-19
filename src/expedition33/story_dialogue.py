"""Native NPC conversation observer and original-dialogue presentation driver."""
from . import RuntimeQueryError
from .native_dialogue import NativeDialogueText
from ._reader import shared_operation


def identity(obj):return (obj.index,obj.serial,obj.address) if obj is not None else None


def field(values,name):
    keys=[key for key in values.types if key[1]==name]
    if len(keys)!=1 or keys[0] in values.errors or keys[0] not in values.values:
        raise RuntimeQueryError('Native conversation observation is incomplete: '+name)
    return values.values[keys[0]]


def controller_dialogue_system(pid,controller):
    """Read the exact current controller's component, without a registry scan."""
    from .values import capture_selected_values
    controller=tuple(controller)
    catalog,values=capture_selected_values(pid,(controller,),
        fields=('BP_DialogueSystemComponent',),references=True)
    owner=catalog.by_index[controller[0]];value=values[owner.index]
    if owner.object_flags&0x30 or value.errors or value.truncated:
        raise RuntimeQueryError('Current dialogue controller is unavailable')
    system=field(value,'BP_DialogueSystemComponent')
    if (system is None or system.class_name!='BP_DialogueSystemComponent_C' or
            system.object_flags&0x30 or (system.outer_index,system.outer_serial)!=controller[:2]):
        raise RuntimeQueryError('Current controller dialogue component differs')
    return catalog,system


def observe(scope,npc_identity):
    from .values import capture_selected_values
    from .cinematics.controller_anchor import for_scope
    scope._check()
    catalog,values=capture_selected_values(scope.pid,(npc_identity,),fields=('IsInDialog','SpawnedDialog'),references=True)
    npc=catalog.by_index[npc_identity[0]];value=values[npc.index]
    talking=field(value,'IsInDialog');dialogue=field(value,'SpawnedDialog')
    if type(talking) is not bool:raise RuntimeQueryError('Native conversation state is invalid')
    if not talking or dialogue is None:return None
    if dialogue.class_name!='BP_Dialogue_C':raise RuntimeQueryError('The story NPC opened a different dialogue class')
    context=for_scope(scope).context();controller=context['controller'][1:]
    catalog,system=controller_dialogue_system(scope.pid,controller)
    catalog,values=capture_selected_values(scope.pid,(identity(system),identity(dialogue)),
        fields=('ActiveDialogue','LastChoice','IsComplete'),references=True)
    active=field(values[system.index],'ActiveDialogue')
    complete=field(values[dialogue.index],'IsComplete');choice=field(values[system.index],'LastChoice')
    if type(complete) is not bool or type(choice) is not int:raise RuntimeQueryError('Invalid native dialogue completion state')
    return dict(system=system,dialogue=dialogue,active=active,complete=complete,choice=choice)


def observe_owned(scope,npc_identity,system,dialogue):
    """Read completion from this exact retained presentation in one batch.

    Original native text dispatch separately validates ActiveDialogue, the
    current LocalPlayer controller and world on the game thread every time.
    """
    from .values import capture_selected_values
    catalog,values=capture_selected_values(scope.pid,(npc_identity,identity(system),identity(dialogue)),
        fields=('IsInDialog','SpawnedDialog','ActiveDialogue','IsComplete','LastChoice'),references=True)
    npc_value=values[npc_identity[0]]
    if field(npc_value,'IsInDialog') is not True or identity(field(npc_value,'SpawnedDialog'))!=identity(dialogue):return None
    active=field(values[system.index],'ActiveDialogue')
    if identity(active)!=identity(dialogue):return None
    complete=field(values[dialogue.index],'IsComplete');choice=field(values[system.index],'LastChoice')
    if type(complete) is not bool or type(choice) is not int:raise RuntimeQueryError('Invalid native dialogue completion state')
    return dict(system=catalog.by_index[system.index],dialogue=catalog.by_index[dialogue.index],active=active,complete=complete,choice=choice)


class NativeStoryDialogueDriver:
    def __init__(self,npc,speakers,*,observer=observe,participants=(),cast_resolver=None):
        self.npc=npc;self.scope=npc.scope;self.speakers=dict(speakers);self.observer=observer
        self.call=None;self.pending=None;self.choice_count=0;self.participants=tuple(participants)
        self.cast_resolver=cast_resolver

    def prepare_conversation(self):
        """Resolve the current cast before story flags or lines are advanced.

        A known content error ends only this NPC's original empty dialogue.
        Uncertain native outcomes still retain the call for explicit cleanup.
        """
        if self.cast_resolver is None:return None
        speakers,participants,issue=self.cast_resolver()
        if issue is None:
            self.speakers=dict(speakers);self.participants=tuple(participants)
            return None
        value=self._current()
        if value is None:raise RuntimeQueryError('The owned NPC conversation is no longer active')
        if self.call is not None or self.pending is not None:
            raise RuntimeQueryError('Cannot reject a conversation after presentation started')
        self.call=NativeDialogueText(self.scope,value['system'],value['dialogue'])
        self.call.end()
        if not self.call.close():raise RuntimeQueryError('Native dialogue cleanup is pending')
        self.call=None
        return issue

    def _current(self):
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            value=observe_owned(self.scope,self.npc.identity,self.call.system,self.call.dialogue) if self.call is not None and self.observer is observe else self.observer(self.scope,self.npc.identity)
        if value is None:return None
        if identity(value['dialogue'])!=identity(value['active']):return None
        return value

    def available(self):
        if self.pending is not None or self.npc.state!='visible':return False
        return self._current() is not None

    def _ensure(self):
        value=self._current()
        if value is None:raise RuntimeQueryError('The owned NPC conversation is no longer active')
        if self.call is None:
            self._ended_cleanly=False
            self._native_end_acknowledged=False
            gate=getattr(self.npc,'set_interaction_enabled',None)
            if gate is not None:gate(False)
            for npc in self.participants:
                if not getattr(npc,'presentation_only',False):continue
                if getattr(npc,'borrowed_actor',None) is not None:continue
                if npc.state=='prepared':npc.reveal(visual=False)
                npc.set_interaction_enabled(False)
                media=getattr(npc,'_standby_pose',None)
                if media is not None:
                    selection=npc._standby_selection
                    body,clip,duration=media.prepare(npc.visual.identity,selection)
                    media.play(npc.visual.identity,selection)
                    media._call(body,'SkeletalMeshComponent','SetPosition',InPos=min(.05,duration),bFireNotifies=False)
            stage=getattr(self,'authored_cast',None)
            if stage is not None:
                carrier=stage.standin
                if carrier is not None and carrier.state=='prepared':
                    carrier.reveal(visual=False);carrier.set_interaction_enabled(False)
                stage.begin()
            self.call=NativeDialogueText(self.scope,value['system'],value['dialogue'])
            self._cast_revealed=False
            if len(self.participants)>1:self.call.register_participants(self.participants)
        elif identity(self.call.dialogue)!=identity(value['dialogue']) or identity(self.call.system)!=identity(value['system']):
            raise RuntimeQueryError('Native conversation identity changed')
        return value

    def _reveal_cast(self):
        if getattr(self,'_cast_revealed',False):return
        for npc in self.participants:
            if getattr(npc,'presentation_only',False) and getattr(npc,'borrowed_actor',None) is None:npc.set_visual_visible(True)
        self._cast_revealed=True

    def _prepare_dispatch(self):
        if self.call is None or self.observer is not observe:self._ensure()
        else:self.call.scope._check()

    def _begin(self,kind,nonce):
        self.pending=(identity(self.call.dialogue),nonce,kind)
        return self.pending

    def operation(self):
        return shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable)

    def prepare_media(self,document,dialogue_id=None):
        from ._reader import shared_operation
        # Preparation happens before entering the original conversation UI.
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            for key,dialogue in document['dialogues'].items():
                if dialogue_id is not None and key!=dialogue_id:continue
                for node in dialogue['nodes'].values():
                    for row in (node,*node['choices']):
                        if row.get('animation'):self.animate(row['animation'],prepare=True)
                        if row.get('audio'):
                            self._audio_owner().prepare(row['audio'])

    def _audio_owner(self):
        from .story_audio import DialogueAudio
        if not hasattr(self,'audio'):self.audio=DialogueAudio(self.scope)
        return self.audio

    def play_audio(self,selection):
        if selection is not None:self._audio_owner().play(selection)

    def poll_media(self):
        if hasattr(self,'audio'):self.audio.poll()

    def _close_audio(self,*,world_retired=False):
        audio=getattr(self,'audio',None)
        if audio is not None:
            if not audio.close(world_retired=world_retired):return False
            del self.audio
        return True

    def animate(self,selection,*,prepare=False):
        if selection is None:return 0.
        from .story_animation import DialogueAnimations
        if not hasattr(self,'animations'):self.animations=DialogueAnimations(self.scope)
        target=selection['target']
        stage=getattr(self,'authored_cast',None)
        authored_actor=stage.actor if stage is not None else None
        if target=='player' and authored_actor is not None:
            actor=authored_actor
        elif target=='player' and hasattr(self,'_player_animation_actor'):
            actor=self._player_animation_actor
        elif target=='player':
            from .cinematics.controller_anchor import for_scope
            from .values import capture_selected_values
            ctx=for_scope(self.scope).context()
            c,v=capture_selected_values(self.scope.pid,(ctx['controller'][1:],),fields=('Pawn',),references=True)
            pawn=field(v[ctx['controller'][1]],'Pawn')
            if pawn is None:raise ValueError('Player character is unavailable')
            actor=identity(pawn);self._player_animation_actor=actor
        else:
            if target not in self.speakers:raise ValueError('Place the animation character on this map first')
            candidates=[a for a in self.participants if identity(a.speaker)==identity(self.speakers[target])]
            if len(candidates)!=1:raise ValueError('Animation needs one unambiguous conversation actor')
            actor=getattr(candidates[0],'borrowed_actor',None) or candidates[0].visual.identity
        method=self.animations.prepare_playback if prepare else self.animations.play
        return method(actor,selection,player=target=='player' and not (stage is not None and stage.replacement))

    def animate_line(self,view):
        return self.animate(view.get('animation'))

    def start_response_animation(self,selection):
        return self.animate(selection)

    def _close_animations(self,*,world_retired=False):
        animations=getattr(self,'animations',None)
        if animations is not None:
            if not animations.close(world_retired=world_retired):return False
            del self.animations
        if hasattr(self,'_player_animation_actor'):del self._player_animation_actor
        return True

    def present(self,view):
        # One short-lived reader worker for the entire presentation. The native
        # calls still validate exact retained identities on every dispatch.
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            self._prepare_dispatch()
            self.animate_line(view)
            presentation=self.start_lines(view['speaker_id'],(view['text'],))
            self.play_audio(view.get('audio'))
            return presentation

    def start_lines(self,speaker,texts):
        if self.pending is not None:raise RuntimeError('Wait for the native presentation to finish')
        if speaker not in self.speakers:raise ValueError('This story speaker has no native character binding')
        # Keep fresh reads in one short-lived worker across discovery, leases
        # and camera setup. Each read still validates current identities; this
        # does not cache a dialogue, a world admission or any observations.
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            self._prepare_dispatch()
            self._reveal_cast()
            presentation=self._begin('lines',self.call.lines(self.speakers[speaker],texts))
            camera=next((actor for actor in self.participants if identity(actor.speaker)==identity(self.speakers[speaker])),None)
            stage=getattr(self,'authored_cast',None)
            if speaker=='gustave' and stage is not None and stage.standin is not None:camera=stage.standin
            if camera is not None:
                try:self.call.frame_speaker(self.npc,camera)
                except RuntimeQueryError as error:
                    # Text already has its acknowledged nonce. A camera proof
                    # rejection must not lose that presentation or redispatch
                    # it. Unknown camera outcomes still retain/quarantine it.
                    if (getattr(error,'native_error',None)!=3910 or
                            getattr(error,'outcome',None)!='not_dispatched' or self.call.unknown):raise
                    import logging
                    logging.getLogger(__name__).warning('Dialogue camera framing rejected (proof %s); preserving acknowledged text and current view',getattr(error,'native_reason',None))
                else:self._framed_speaker=identity(camera.speaker)
        return presentation

    def start_choices(self,texts):
        if self.pending is not None:raise RuntimeError('Wait for the native presentation to finish')
        self._prepare_dispatch();nonce=self.call.choices(texts);self.choice_count=len(texts)
        return self._begin('choices',nonce)

    def completion(self,presentation):
        if self.pending is None or presentation!=self.pending:raise RuntimeQueryError('Stale native presentation')
        value=self._ensure()
        if not value['complete']:return None
        result=dict(presentation=self.pending,kind=self.pending[2])
        if self.pending[2]=='choices':
            index=value['choice']
            if type(index) is not int or not 0<=index<self.choice_count:raise RuntimeQueryError('Native response index is invalid')
            result['index']=index
        self.pending=None;return result

    def replace_presentation(self,kind,view):
        """Explicit authoring redisplay, on this driver's owned dialogue only."""
        if kind not in ('lines','choices'):raise ValueError('Unknown presentation kind')
        if view['speaker_id'] not in self.speakers:raise ValueError('Speaker has no native binding')
        self._ensure()
        if kind=='choices':
            texts=tuple(c['text'] for c in view['choices'])
            if not texts:raise ValueError('No available responses')
            nonce=self.call.choices(texts);self.choice_count=len(texts)
        else:nonce=self.call.lines(self.speakers[view['speaker_id']],(view['text'],))
        return self._begin(kind,nonce)

    def end(self):
        if self.pending is not None:raise RuntimeError('Finish the current native presentation first')
        for npc in self.participants:
            if getattr(npc,'presentation_only',False):npc.set_visual_visible(False)
        if not self._close_audio():
            raise RuntimeQueryError('Conversation audio cleanup is pending')
        if not self._close_animations():raise RuntimeQueryError('Conversation animation cleanup is pending')
        if self.pending is not None:raise RuntimeError('Finish the current native presentation first')
        if not getattr(self,'_native_end_acknowledged',False):
            self._prepare_dispatch();self.call.end();self._native_end_acknowledged=True
        if not self.call.close():raise RuntimeQueryError('Native dialogue cleanup is pending')
        from ._story_dialogue_camera_cleanup import finish
        stage=getattr(self,'authored_cast',None)
        if not finish(self.scope,getattr(stage,'pawn',None)):
            raise RuntimeQueryError('Gameplay camera restoration is pending')
        self.call=None;self._framed_speaker=None
        for npc in self.participants:
            if getattr(npc,'presentation_only',False):npc.set_visual_visible(False)
        stage=getattr(self,'authored_cast',None)
        if stage is not None:stage.close()
        self._ended_cleanly=True

    def retire(self):
        # A completed one-shot placement can retire its parent scope before
        # Conversations removes the now-idle driver. End already restored its
        # camera, animations and cast; never touch its destroyed participants.
        if getattr(self,'_ended_cleanly',False) and self.call is None:return True
        for npc in self.participants:
            if getattr(npc,'presentation_only',False):npc.set_visual_visible(False)
        if not self._close_audio():
            return False
        if not self._close_animations():return False
        if self.call is None:
            stage=getattr(self,'authored_cast',None)
            return stage.close() if stage is not None else True
        if self.call.unknown:return False
        value=self._current()
        if value is not None and identity(value['dialogue'])==identity(self.call.dialogue):self.call.end()
        if not self.call.close():return False
        self.call=None;self.pending=None;self._framed_speaker=None
        for npc in self.participants:
            if getattr(npc,'presentation_only',False):npc.set_visual_visible(False)
        stage=getattr(self,'authored_cast',None)
        return stage.close() if stage is not None else True

    def retire_world(self):
        if not self._close_audio(world_retired=True):
            return False
        if not self._close_animations(world_retired=True):return False
        # The game owns its HUD/input restoration across world destruction.
        # Never dispatch EndDialogue against a purged or replacement controller.
        if self.call is not None:
            if self.call.unknown:return False
            if not self.call.retire_camera_world():return False
            from ._retired_tracking import close_lease_only_scope
            if not close_lease_only_scope(self.call.scope):return False
            self.call.closed=True;self.call=None
        stage=getattr(self,'authored_cast',None)
        if stage is not None:stage.close(world_retired=True)
        self.pending=None;return True
