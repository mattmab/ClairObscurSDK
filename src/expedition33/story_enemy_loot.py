"""Selected-save guaranteed loot row overlay; the original battle awards the loot."""
import re,struct
from .story_original import _Owner
from . import _story_item_wire as items

def packet(owner,target,source,map_class,map_add,package,asset,gi,key,mode=0,*,enemy,reward):
    data=bytearray(items.definitions(owner,target,source,map_class,map_add,package,asset,(enemy,),mode=mode))
    struct.pack_into('<I',data,4,251)
    items.put_id(data,2024,gi.object);struct.pack_into('<Q',data,2040,gi._token)
    if len(key)!=32:raise ValueError('Story identity length')
    struct.pack_into('<4I',data,2048,*(int(key[i:i+8],16) for i in range(0,32,8)))
    if type(reward)is not str or re.fullmatch(r'[A-Za-z0-9_]{1,95}',reward) is None:raise ValueError('Reward item ID required')
    data[2064:2160]=reward.encode('ascii').ljust(96,b'\0')
    result=bytes(data);validate(result);return result

def validate(data):
    if type(data) is not bytes or len(data)!=items.SIZE:raise ValueError('Enemy loot packet size')
    if struct.unpack_from('<I',data,4)[0]!=251:raise ValueError('Enemy loot opcode')
    items.identity(data,2024)
    if not struct.unpack_from('<Q',data,2040)[0] or struct.unpack_from('<I',data,2048)[0]!=0xe33c5701:raise ValueError('Enemy loot selected-save identity')
    clean=bytearray(data);struct.pack_into('<I',clean,4,241);clean[2024:2160]=bytes(136)
    items.validate(bytes(clean))
    reward=data[2064:2160].split(b'\0',1)[0]
    if data[2064:2160]!=reward.ljust(96,b'\0') or len(reward)==96 or re.fullmatch(rb'[A-Za-z0-9_]+',reward) is None:
        raise ValueError('Enemy reward ID or padding')
    if struct.unpack_from('<I',data,124)[0]!=1:raise ValueError('One enemy row per guaranteed loot overlay')

def decode(sent,reply):
    validate(sent)
    if type(reply) is not bytes or len(reply)!=len(sent):raise RuntimeError('Enemy loot acknowledgement size')
    error,state=struct.unpack_from('<2I',reply,8)
    clean=bytearray(reply);clean[8:16]=sent[8:16];clean[128:136]=sent[128:136]
    if bytes(clean)!=sent:raise RuntimeError('Enemy loot acknowledgement context changed')
    if error:raise items.OriginalNarrativeError(error)
    if state!=struct.unpack_from('<I',sent,120)[0]+1:raise RuntimeError('Enemy loot acknowledgement state')
    old,new=struct.unpack_from('<2I',reply,128)
    if state in (1,2) and (old<1 or new!=old):raise RuntimeError('Enemy loot changed the enemy inventory')
    return dict(original_rows=old,registered_rows=new)

class EnemyLootOverlay(_Owner):
    def prepare(self,path,definitions,*,enemy,reward):
        if getattr(self.scope._session._transport,'story_enemy_loot_protocol',0)!=2:raise RuntimeError('Enemy loot requires protocol 2')
        for value in (enemy,reward):
            if type(value)is not str or re.fullmatch(r'[A-Za-z0-9_]{1,95}',value) is None:raise ValueError('Enemy and reward IDs are required')
        self.enemy=enemy;self.reward=reward
        from .assets import load_asset
        from .story_items import load_resource_asset
        if self.started or self.held:raise RuntimeError('Enemy overlay preparation is one-shot')
        self.definitions=definitions
        if reward not in definitions.rows:raise RuntimeError('Enemy reward item definition is missing')
        from ._reader import shared_operation
        with shared_operation(self.scope.pid):
            self.context();self.package,self.asset=path.split('.')
            target_path='/Game/jRPGTemplate/Datatables/DT_jRPG_Enemies.DT_jRPG_Enemies'
            self.source=self.hold(self.resources.load(path) if self.resources is not None else load_resource_asset(self.scope,path).return_value)
            self.target=self.hold(self.resources.load(target_path) if self.resources is not None else load_asset(self.scope,target_path).return_value)
            self.map_class=self.hold(definitions.map_class.object);self.map_add=self.hold(definitions.map_add.object)
            self.receipt=self.send(0);self.started=True
        return self
    def send(self,mode):
        sent=packet(self.owner,self.target,self.source,self.map_class,self.map_add,self.package,self.asset,self.gi,self.key,mode,enemy=self.enemy,reward=self.reward)
        try:
            reply=self.scope._session._transport.command('mesh',sent)
            return decode(sent,bytes.fromhex(reply['mesh_packet']))
        except items.OriginalNarrativeError as error:
            if error.code==4211:self.unknown=True
            raise
        except BaseException:
            self.unknown=True;raise
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:self.send(2);self.started=False
        self.scope.close();self.closed=True;return True
