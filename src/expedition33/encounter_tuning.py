"""Encounter-local level, health and difficulty settings; defaults are a no-op."""
from dataclasses import dataclass,asdict
import math
import struct
from ._reader import ReadBatch
from .catalog import capture_matching,capture_selected
from .cinematics.original_game_action import controller_context
from ._npc_encounter_preparation import _controller_battle_manager

SIZE=20984
PREFIX='/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager.AC_jRPG_BattleManager_C:'
DIFFICULTIES=('Game setting','Easy','Normal','Hard')

@dataclass(frozen=True)
class EncounterTuning:
    level_mode:str='authored'
    level:int=0
    health:float=1.
    difficulty:int=-1
    def __post_init__(self):
        if self.level_mode not in ('authored','offset','override'):raise ValueError('Unknown encounter level mode')
        if type(self.level) is not int or not (self.level==0 if self.level_mode=='authored' else -98<=self.level<=98 if self.level_mode=='offset' else 1<=self.level<=99):raise ValueError('Encounter level must be authored, offset -98..98 or override 1..99')
        if type(self.health) not in (int,float) or not math.isfinite(self.health) or not .1<=self.health<=1000:raise ValueError('Health multiplier must be 0.1..1000')
        if type(self.difficulty) is not int or self.difficulty not in (-1,0,1,2):raise ValueError('Unknown battle difficulty')
    @property
    def is_default(self):return self.level_mode=='authored' and self.health==1 and self.difficulty==-1
    def summary(self):
        level='Authored level' if self.level_mode=='authored' else f'Level {self.level}' if self.level_mode=='override' else f'Level {self.level:+d}'
        return f'{level} | HP {self.health:g}x | {DIFFICULTIES[self.difficulty+1]}'
    def to_dict(self):return asdict(self)

def settings(value=None):
    if value is None:return EncounterTuning()
    if isinstance(value,EncounterTuning):return value
    if type(value) is dict:return EncounterTuning(**value)
    raise ValueError('Expected encounter tuning settings')

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Encounter tuning packet size')
    version,op,error,state,token=struct.unpack_from('<4IQ',data)
    if version!=3 or op not in (157,158,159) or error or state or not token:raise ValueError('Encounter tuning header')
    canonical=bytearray(SIZE);canonical[:24]=data[:24]
    if op==157:
        kind,mode,level,diff,hp=struct.unpack_from('<IIiid',data,24)
        if kind not in (0,1) or mode>2:raise ValueError('Encounter tuning mode')
        config=EncounterTuning(('authored','offset','override')[mode],level,hp,diff)
        if config.is_default:raise ValueError('Default settings need no native tuning owner')
        canonical[24:48]=data[24:48]
        for offset in range(88,184,16):
            index,serial,address=struct.unpack_from('<iiQ',data,offset)
            if index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff:raise ValueError('Observed identity required')
        canonical[88:184]=data[88:184]
    if bytes(canonical)!=data:raise ValueError('Reserved encounter tuning bytes')

class EncounterTuningOwner:
    def __init__(self,scope,token,config):
        self.scope=scope;self._scope=scope;self.token=token;self.config=settings(config);self.attempted=False;self.closed=False;self.last=None
        self.check_available(scope,self.config)
    @staticmethod
    def check_available(scope,config):
        if not settings(config).is_default and getattr(scope._session._transport,'encounter_tuning_protocol',0)!=1:
            raise RuntimeError('Encounter tuning requires the updated SDK candidate')
        if settings(config).health>100 and getattr(scope._session._transport,'encounter_tuning_max_health_multiplier',100)<settings(config).health:
            raise RuntimeError('Health above 100x requires the 1000x SDK candidate')
    def _exchange(self,op,query=(),kind=0):
        self.scope._check();data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,op,0,0,self.token)
        if op==157:
            c=self.config;struct.pack_into('<IIiid',data,24,kind,('authored','offset','override').index(c.level_mode),c.level,c.difficulty,c.health)
            for i,o in enumerate(query):struct.pack_into('<iiQ',data,88+i*16,o.index,o.serial,o.address)
        request=bytes(data);validate_request(request)
        reply=bytes.fromhex(self.scope._session._transport.command('mesh',request)['mesh_packet'])
        if type(reply) is not bytes or len(reply)!=SIZE:raise RuntimeError('Uncertain encounter tuning reply; no replay')
        version,operation,error,state,token=struct.unpack_from('<4IQ',reply)
        expected=bytearray(request);expected[8:16]=reply[8:16];expected[4096:4168]=reply[4096:4168]
        if (version,operation,token)!=(3,op,self.token) or bytes(expected)!=reply:raise RuntimeError('Encounter tuning acknowledgement mismatch; no replay')
        if error:raise RuntimeError(f'Encounter tuning native error {error}; ownership retained for cleanup')
        if state!=1:raise RuntimeError('Unacknowledged encounter tuning operation; no replay')
        active,seen,finished,spawns,diffs,native_error=struct.unpack_from('<6I',reply,4096)
        observations=struct.unpack_from('<6d',reply,4120)
        self.last=dict(settings=self.config.to_dict(),active=bool(active),battle_observed=bool(seen),restored=bool(finished),spawn_calls=spawns,difficulty_calls=diffs,error=native_error,
            level_before=observations[0],level_applied=observations[1],health_before=observations[2],health_applied=observations[3],difficulty_before=observations[4],difficulty_applied=observations[5])
        return self.last
    def arm(self,actor_identity,*,npc=False):
        if self.config.is_default:return None
        if self.attempted:raise RuntimeError('Encounter tuning was already attempted; no replay')
        with ReadBatch(self.scope.pid):
            context=controller_context(self.scope._session)
            c=capture_matching(self.scope.pid,names=('SpawnEnemyOnSpot','GetCurrentBattleDifficulty'),classes=('AC_jRPG_BattleManager_C',))
            c=c.with_observations(capture_selected(self.scope.pid,(context['world'][1:],context['controller'][1:],tuple(actor_identity))))
            world=c.by_index[context['world'][1]];pc=c.by_index[context['controller'][1]]
            manager,c=_controller_battle_manager(c,pc)
            def exact(name):
                matches=[o for o in c.objects if c.path_name(o)==PREFIX+name]
                if len(matches)!=1:raise RuntimeError('Missing exact encounter function '+name)
                return matches[0]
            query=(world,pc,manager,c.by_index[actor_identity[0]],exact('SpawnEnemyOnSpot'),exact('GetCurrentBattleDifficulty'))
            if controller_context(self.scope._session)!=context:raise RuntimeError('World changed before encounter tuning')
        self.scope._register_native_owner(self)
        self.attempted=True
        return self._exchange(157,query,kind=int(npc))
    def status(self):
        if self.attempted and not self.closed:return self._exchange(158)
        return self.last
    def close(self):
        if not self.attempted or self.closed:return True
        self._exchange(159);self.closed=True;return True
