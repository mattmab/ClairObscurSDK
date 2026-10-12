"""Execute acknowledged timeline steps through existing retained SDK audio calls.

No scene/profile admission occurs here. Caller retains the isolated audio owner,
its scoped music assignment and presentation until native cleanup is confirmed.
"""
from .media_audio_timeline import MediaAudioPlanner

class OwnedAudioTimelineDispatcher:
    def __init__(self,audio_owner,planner,panel,sections):
        self.audio=audio_owner;self.planner=planner;self.panel=panel
        transport=audio_owner.scope._session._transport
        capacity=getattr(transport,'owned_sound_capacity',16)
        volume_max=getattr(transport,'owned_sound_volume_max',1)
        self.timeline=MediaAudioPlanner(sections,capacity=capacity-len(getattr(audio_owner,'_sounds',())),volume_max=volume_max)
        self.components={};self.uncertain=False;self.prepared=False

    def prepare(self,sources):
        if self.prepared or self.components or self.uncertain:raise RuntimeError('Timeline dispatcher already used')
        catalog=self.planner._catalog
        # Check every exact source before the first native component allocation.
        for section in self.timeline.sections:
            source=sources.get(section.source)
            if source is None or catalog.path_name(catalog.resolve(source))!=section.source:
                raise ValueError('Missing or changed exact timeline sound source')
        owners=[o for o in catalog.objects if o.name=='AudioComponent' and o.class_name=='Class']
        if len(owners)!=1:raise ValueError('Ambiguous audio component metadata')
        def function(name):
            rows=[o for o in catalog.objects if o.outer_index==owners[0].index and o.name==name and o.class_name=='Function']
            if len(rows)!=1:raise ValueError('Missing exact audio operation '+name)
            return rows[0]
        functions={name:function(name) for name in ('Play','Stop','SetVolumeMultiplier')}
        defaults=[o for o in catalog.objects if o.name=='Default__AudioComponent' and o.class_index==owners[0].index]
        if len(defaults)!=1:raise ValueError('Audio schema preflight requires its exact default object')
        # Plan only: verify all scalar signatures before any component factory.
        for name,args in (('Play',{'StartTime':0.}),('Stop',{}),('SetVolumeMultiplier',{'NewVolumeMultiplier':0.})):
            self.planner.prepare(defaults[0],functions[name],**args)
        for section in self.timeline.sections:
            self.uncertain=True
            component=self.audio.create_sound(self.planner,self.panel,sources[section.source],volume=0.,pitch=1.)
            self.uncertain=False;self.components[section.identity]=component
        self.functions=functions;self.prepared=True
        return self

    def advance(self,seconds,*,playing):
        if not self.prepared or self.uncertain:raise RuntimeError('Audio dispatcher is unavailable')
        step=self.timeline.plan(seconds,playing=playing)
        if step is None:return None
        for action in step.actions:
            component=self.components[action.section]
            if action.operation=='gain':name='SetVolumeMultiplier';args={'NewVolumeMultiplier':action.value}
            elif action.operation=='play':name='Play';args={'StartTime':action.value}
            elif action.operation=='stop':name='Stop';args={}
            else:raise ValueError('Unknown timeline operation')
            prepared=self.planner.prepare(component,self.functions[name],**args)
            self.uncertain=True
            with prepared.invoke():pass
            self.uncertain=False
        self.timeline.commit(step)
        return dict(position=step.position,actions=len(step.actions),active=len(step.active))

    def close_audio(self):
        # Stop/Destroy is native-owned and remains valid after a failed user call;
        # arbitrary timeline operations are never retried after uncertainty.
        if not self.audio.close():return False
        self.timeline.discard_after_cleanup();self.prepared=False
        return True
