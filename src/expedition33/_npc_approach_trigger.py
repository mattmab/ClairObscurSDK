"""Once-only latch for a native-owned NPC's validated approach observations."""
import math

class ApproachTrigger:
    def __init__(self,owner_token,actor_identity,*,radius=180.,release_margin=100.):
        if type(owner_token) is not int or not 0<owner_token<2**64:raise ValueError('Exact owner token required')
        if len(actor_identity)!=3 or any(type(v) is not int for v in actor_identity):raise ValueError('Exact actor identity required')
        if not all(math.isfinite(v) and v>0 for v in (radius,release_margin)):raise ValueError('Positive finite approach distances required')
        self.owner_token=owner_token;self.actor_identity=list(actor_identity)
        self.radius_squared=radius*radius;self.release_squared=(radius+release_margin)**2
        self.armed=False;self.consumed=False
    def observe(self,result):
        if self.consumed:return False
        if result.get('owner_token')!=self.owner_token or result.get('actor_identity')!=self.actor_identity:
            self.consumed=True;raise RuntimeError('Approach owner identity changed; do not reuse trigger')
        if result.get('native_error') or not result.get('has_work') or result.get('entry_phase')!=0:return False
        value=result.get('proximity',{}).get('distance_squared')
        if type(value) not in (float,int) or not math.isfinite(value) or value<0:raise ValueError('Validated native distance required')
        if value>=self.release_squared:self.armed=True
        if self.armed and value<=self.radius_squared:
            # Consume before dispatch. A rejected or unknown outcome must never
            # auto-retry while the player remains close to the NPC.
            self.consumed=True;return True
        return False

class OverlapTrigger:
    """Once-only clear-to-overlapping edge from the actual native shape query."""
    def __init__(self,owner_token,actor_identity):
        self.owner_token=owner_token;self.actor_identity=list(actor_identity);self.armed=False;self.consumed=False
    def observe(self,result):
        if self.consumed:return False
        if result.get('owner_token')!=self.owner_token or result.get('actor_identity')!=self.actor_identity:
            self.consumed=True;raise RuntimeError('Overlap owner identity changed')
        if result.get('native_error') or not result.get('has_work') or result.get('entry_phase')!=0:return False
        overlap=result.get('overlap')
        if type(overlap) is not bool or not result.get('collision',{}).get('verified'):raise ValueError('Native collision-overlap proof required')
        if not overlap:self.armed=True
        if self.armed and overlap:self.consumed=True;return True
        return False
