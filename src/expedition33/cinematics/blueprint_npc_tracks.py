"""Owned Blueprint NPC intervals driven by the actual preview player cursor.

Intervals use native player frames, inclusive start and exclusive end. Scrubbing
out of an interval retires its actor; entering again constructs a new owner.
No campaign actor, encounter, or manually assembled skeletal mesh is involved.
"""
import copy,math
from .authored_timeline import validate
from .authored_replacement import placement_pose
from .blueprint_actor import BlueprintActor


class BlueprintNpcTracks:
    def __init__(self,scope,document,anchor,scene_yaw=0.):
        self._initialize(scope,validate(document)['npc_tracks'],anchor,scene_yaw)

    @classmethod
    def _from_snapshot(cls,scope,document,anchor,scene_yaw=0.):
        """Use the preview owner's already validated, independent document.

        The public constructor still validates untrusted callers. Only the
        synchronous preview path owns an immutable validated source snapshot;
        copy its small NPC list so track state remains independent of it.
        """
        instance=cls.__new__(cls)
        instance._initialize(scope,copy.deepcopy(document['npc_tracks']),anchor,scene_yaw)
        return instance

    def _initialize(self,scope,tracks,anchor,scene_yaw):
        self.scope=scope;self.tracks=tracks
        from .scene_transform import actor_placement
        actor_placement(anchor,(0.,0.,0.),0.,scene_yaw)
        self.anchor=tuple(anchor);self.scene_yaw=scene_yaw;self.actors={};self.failed=False;self.closed=False

    def needs_sync(self,frame):
        return set(self.actors)!={r['id'] for r in self.tracks if r['start']<=frame<r['end']}

    def sync(self,frame):
        if self.closed or self.failed:raise RuntimeError('NPC timeline is closed or uncertain')
        if type(frame) not in (int,float) or not math.isfinite(frame):raise ValueError('Finite native player frame required')
        try:
            # Close expired actors first, so nonoverlapping intervals reuse slots.
            for row in self.tracks:
                actor=self.actors.get(row['id'])
                active=row['start']<=frame<row['end']
                if actor is not None and not active:
                    if not actor.close():return False
                    del self.actors[row['id']]
            for row in self.tracks:
                if not row['start']<=frame<row['end'] or row['id'] in self.actors:continue
                actor=BlueprintActor(self.scope)
                self.actors[row['id']]=actor # Retain before any dispatch.
                actor.prepare(row['profile'],placement_pose(row,self.anchor,0,self.scene_yaw))
                actor.reveal()
            return True
        except BaseException:
            self.failed=True
            raise

    def close(self):
        for key,actor in reversed(tuple(self.actors.items())):
            if not actor.close():return False
            del self.actors[key]
        self.closed=True
        return True

    def validate_reanchor(self,anchor,scene_yaw=None):
        """Validate all active destinations before any owner is moved."""
        if self.closed or self.failed:raise RuntimeError('NPC timeline is closed or uncertain')
        if type(anchor) not in (tuple,list) or len(anchor)!=3 or any(
                type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e7 for v in anchor):
            raise ValueError('Finite bounded scene anchor required')
        from .scene_transform import actor_placement
        yaw=self.scene_yaw if scene_yaw is None else scene_yaw
        actor_placement(anchor,(0.,0.,0.),0.,yaw)
        # Check every destination before dispatching the first move. An anchor
        # and each offset can individually be in bounds while their sum is not.
        # Reject such input without leaving earlier actors at a new position.
        moves=[]
        for row in self.tracks:
            actor=self.actors.get(row['id'])
            if actor is None:continue
            location,rotation=actor_placement(anchor,row['placement']['offset'],row['placement']['yaw'],yaw)
            if any(not math.isfinite(v) or abs(v)>1e7 for v in location):
                raise ValueError('NPC destination exceeds placement bounds')
            moves.append((actor,location,rotation))
        return tuple(moves)

    def reanchor(self,anchor,scene_yaw=None):
        """Keep active intervals and actor identities when moving the scene."""
        moves=self.validate_reanchor(anchor,scene_yaw)
        yaw=self.scene_yaw if scene_yaw is None else scene_yaw
        try:
            for actor,location,rotation in moves:
                actor.move(location,rotation)
            self.anchor=tuple(anchor);self.scene_yaw=yaw
        except BaseException:
            self.failed=True;raise

    def retire_world(self):
        for key,actor in reversed(tuple(self.actors.items())):
            if not actor.retire_world():return False
            del self.actors[key]
        self.closed=True
        return True
