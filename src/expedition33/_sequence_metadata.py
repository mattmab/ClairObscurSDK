"""Prepared sequence metadata selectors with fresh per-construction catalogs."""
from .catalog import capture_matching,capture_selected
from ._stable_lease import available,acquire_stable

NAMES=('LevelSequencePlayer','LevelSequenceActor','MovieSceneSequencePlayer','MovieSceneSequencePlaybackSettings',
 'Default__LevelSequencePlayer','Default__LevelSequenceActor','CreateLevelSequencePlayer',
 'K2_DestroyActor','Stop','Play','Pause','SetPlayRate','GetPlayRate','IsPlaying','IsPaused',
 'PlayerController','SetViewTargetWithBlend','EViewTargetBlendFunction',
 'GetCurrentTime','GetEndTime','QualifiedFrameTime','FrameTime','FrameRate','FrameNumber')
FUNCTIONS={'LevelSequencePlayer':('CreateLevelSequencePlayer',),'Actor':('K2_DestroyActor',),
 'PlayerController':('SetViewTargetWithBlend',),'MovieSceneSequencePlayer':
 ('Stop','Play','Pause','SetPlayRate','GetPlayRate','IsPlaying','IsPaused','GetCurrentTime','GetEndTime')}

class PreparedSequenceMetadata:
    def __init__(self,scope):
        scope._check();self.scope=scope;self.leases=();self.ready=False
        c=capture_matching(scope.pid,names=NAMES)
        def one(rows):
            rows=tuple(rows)
            if len(rows)!=1:raise ValueError('Ambiguous prepared sequence metadata')
            return rows[0]
        classes={name:one(o for o in c.objects if o.name==name and o.class_name=='Class')
                 for name in FUNCTIONS}
        roots=list(classes.values())
        for name in ('LevelSequenceActor',):
            roots.append(one(o for o in c.objects if o.name==name and o.class_name=='Class'))
        for name in ('MovieSceneSequencePlaybackSettings','QualifiedFrameTime','FrameTime','FrameRate','FrameNumber'):
            roots.append(one(o for o in c.objects if o.name==name and o.class_name=='ScriptStruct'))
        roots.append(one(o for o in c.objects if o.name=='EViewTargetBlendFunction' and o.class_name=='Enum'))
        for name in ('Default__LevelSequencePlayer','Default__LevelSequenceActor'):
            roots.append(one(o for o in c.objects if o.name==name))
        for owner,names in FUNCTIONS.items():
            roots.extend(one(o for o in c.objects if o.name==name and o.class_name=='Function' and
                             o.outer_index==classes[owner].index) for name in names)
        # Stabilize zero serials under native ownership before any sequence
        # construction can promote them. Each acquisition adopts its token
        # before fresh selected readback; unknown outcomes are never retried.
        stable=available(scope._session._transport)
        leases=[]
        for obj in roots:
            lease=acquire_stable(scope,obj)[0] if obj.serial==0 and stable else scope.retain(obj)
            leases.append(lease)
        self.leases=tuple(leases)
        self.unassigned=tuple(lease.object.name for lease in self.leases if lease.object.serial<=0)
        self.ready=True

    def capture(self,scope,*,names):
        self.scope._check();scope._check()
        if scope._session is not self.scope._session:
            raise RuntimeError('Prepared sequence metadata belongs to another SDK session')
        if not all(lease.active for lease in self.leases):
            raise RuntimeError('Prepared sequence metadata leases have been released')
        # Unreal can assign previously-zero serials while a sequence factory
        # loads its cast. Such selectors are not stable across construction.
        # Use fresh discovery for this pool rather than replaying a zero serial
        # or treating a rejected exact selector as permission to retry it.
        if self.unassigned:
            return capture_matching(scope.pid,names=NAMES)
        return capture_selected(scope.pid,tuple((lease.object.index,lease.object.serial,lease.object.address)
                                                for lease in self.leases))
