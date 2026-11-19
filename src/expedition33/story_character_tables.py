"""Selected-save character row overlays and explicit weapon-template copies.

One row per table is supported. Character overlays replace existing rows; a
weapon template adds one named row. The caller supplies every content choice.
"""
import re,secrets,struct
from . import _story_item_wire as wire
from .story_original import _Owner
TABLES={name:'/Game/jRPGTemplate/Datatables/'+name for name in (
    'DT_jRPG_CharacterDefinitions','DT_jRPG_CharacterSaveStates','DT_jRPG_WorldCharacters')}
TABLES['DT_WeaponDefinitions']='/Game/Gameplay/Pictos/Gear/Weapons/DT_WeaponDefinitions'
TEMPLATE=2064;TAIL=2160

def validate_profiles(profiles):
    if type(profiles) is not dict or not 1<=len(profiles)<=len(TABLES):
        raise ValueError('One to four explicit character table profiles required')
    result={}
    for asset,row in profiles.items():
        if asset not in TABLES or type(row) is not dict:raise ValueError('Unsupported character table schema')
        weapon=asset=='DT_WeaponDefinitions'
        if set(row)!=({'source_package','row','template'} if weapon else {'source_package','row'}):
            raise ValueError('Character profile fields differ')
        package=row['source_package']
        if type(package)is not str or len(package)>=256 or re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+',package) is None:
            raise ValueError('Character source package path')
        if weapon:
            if package!=TABLES[asset]:raise ValueError('Weapon templates must use the original weapon table')
        elif not package.startswith('/Game/SDK/') or package.rsplit('/',1)[-1]!=asset:
            raise ValueError('Character definitions must name an SDK table asset')
        for field in ('row','template') if weapon else ('row',):
            if type(row[field])is not str or re.fullmatch(r'[A-Za-z0-9_]{1,95}',row[field]) is None:
                raise ValueError('Character row ID must be a bounded ASCII identifier')
        if weapon and row['row']==row['template']:raise ValueError('Weapon copy requires a new row ID')
        result[asset]=dict(row)
    return result


def validate(data):
    if type(data)is not bytes or len(data)!=wire.SIZE or struct.unpack_from('<I',data,4)[0]!=255:raise ValueError('Character table packet')
    wire.identity(data,2024)
    if not struct.unpack_from('<Q',data,2040)[0] or struct.unpack_from('<I',data,2048)[0]!=0xe33c5701:raise ValueError('Selected character story save identity')
    copy=bytearray(data);struct.pack_into('<I',copy,4,241);copy[2024:TAIL]=bytes(TAIL-2024)
    if data[392:488].split(b'\0',1)[0]==b'DT_WeaponDefinitions':copy[136:392]=b'/Game/SDK/WeaponTemplate'.ljust(256,b'\0')
    wire.validate(bytes(copy))
    package=data[136:392].split(b'\0',1)[0].decode('ascii');asset=data[392:488].split(b'\0',1)[0].decode('ascii')
    name=data[488:584].split(b'\0',1)[0].decode('ascii')
    template=data[TEMPLATE:TAIL].split(b'\0',1)[0]
    if data[TEMPLATE:TAIL]!=template.ljust(96,b'\0'):raise ValueError('Character template padding')
    profile=dict(source_package=package,row=name)
    if asset=='DT_WeaponDefinitions':profile['template']=template.decode('ascii')
    elif template:raise ValueError('Unexpected character template')
    validate_profiles({asset:profile})
    if struct.unpack_from('<I',data,124)[0]!=1:raise ValueError('One row per character table operation')
def packet(owner,row,gi,key,mode):
    profile=validate_profiles({row['asset']:row['profile']})[row['asset']]
    package,name=profile['source_package'],profile['row']
    data=bytearray(wire.definitions(owner,row['target'],row['source'],row['map_class'],row['map_add'],'/Game/SDK/WeaponTemplate' if row['asset']=='DT_WeaponDefinitions' else package,row['asset'],(name,),mode=mode))
    data[136:392]=package.encode('ascii').ljust(256,b'\0')
    struct.pack_into('<I',data,4,255);wire.put_id(data,2024,gi.object);struct.pack_into('<Q',data,2040,gi._token)
    if len(key)!=32:raise ValueError('Character story save identity')
    struct.pack_into('<4I',data,2048,*(int(key[i:i+8],16) for i in range(0,32,8)))
    data[TEMPLATE:TAIL]=profile.get('template','').encode('ascii').ljust(96,b'\0')
    result=bytes(data);validate(result);return result

def decode(sent,reply):
    validate(sent)
    if type(reply)is not bytes or len(reply)!=len(sent):raise RuntimeError('Character registry acknowledgement size')
    error,state=struct.unpack_from('<2I',reply,8);copy=bytearray(reply);copy[8:16]=sent[8:16];copy[128:136]=sent[128:136]
    if bytes(copy)!=sent:raise RuntimeError('Character registry acknowledgement changed')
    if error:raise wire.OriginalNarrativeError(error)
    if state!=struct.unpack_from('<I',sent,120)[0]+1:raise RuntimeError('Character registry acknowledgement state')
    old,new=struct.unpack_from('<2I',reply,128)
    asset=sent[392:488].split(b'\0',1)[0].decode('ascii')
    if state in (1,2) and (old<1 or new!=old+(asset=='DT_WeaponDefinitions')):raise RuntimeError('Character registry row count mismatch')
    return dict(original_rows=old,registered_rows=new)

class CharacterTables:
    def __init__(self,parent,key,definitions,*,profiles,resources=None):
        self.profiles=validate_profiles(profiles)
        from ._scope import SessionScope
        if getattr(parent._session._transport,'story_character_tables_protocol',0)!=2:raise RuntimeError('Character registration requires table protocol 2')
        self._scope=parent;self.scope=SessionScope(parent);self.key=key;self.definitions=definitions;self.resources=resources
        self.held=[];self._held_by_identity={};self.rows=[];self.unknown=False;self.closed=False
        self.inputs_ready=False;self.resolution_attempted=False;self.preparation_error=None
        parent._register_native_owner(self);parent._close_before_descendants(self)
    def hold(self,obj):return _Owner.hold(self,obj)
    @property
    def ready(self):
        return bool(not self.closed and not self.unknown and self.preparation_error is None and
                    self.inputs_ready and len(self.rows)==len(self.profiles) and
                    all(r['attempted'] and r['acknowledged'] and r['started'] for r in self.rows))
    @property
    def state(self):
        return ('closed' if self.closed else 'unknown' if self.unknown else
                'failed' if self.preparation_error is not None else 'registered' if self.ready else 'preparing')
    def preflight(self):
        """Resolve every input before the first character-table mutation.

        Only initial save-context discovery is retryable. Resource loading and
        lease acquisition can dispatch native work, so any failure after that
        boundary is terminal and its retained owner remains available to close.
        """
        from .story_save_identity import observe
        from .story_preflight import observe as read_preflight
        from .story_items import load_resource_asset
        from .assets import load_asset
        if self.closed or self.unknown or self.preparation_error is not None:raise RuntimeError('Character registration preparation is unavailable')
        if self.inputs_ready:return self
        if self.resolution_attempted:raise RuntimeError('Character input resolution was already attempted')
        # A process-owned GI is sufficient: native op255 independently proves
        # the selected save and this GI before applying every row.
        gi=getattr(self.resources,'gi',None)
        if gi is None:*_,gi,_=read_preflight(observe,self.scope)
        self.resolution_attempted=True
        try:
            self.gi=self.hold(gi)
            map_class=self.hold(self.definitions.map_class.object);map_add=self.hold(self.definitions.map_add.object)
            for asset,profile in self.profiles.items():
                package=profile['source_package']
                row=dict(owner=secrets.randbits(64)or 1,asset=asset,profile=profile,started=False,
                         attempted=False,acknowledged=False,receipt=None)
                self.rows.append(row)
                row['source']=self.hold(self.resources.load(package+'.'+asset) if self.resources is not None else load_resource_asset(self.scope,package+'.'+asset).return_value)
                folder='/Game/Gameplay/Pictos/Gear/Weapons/' if asset=='DT_WeaponDefinitions' else '/Game/jRPGTemplate/Datatables/'
                row['target']=self.hold(self.resources.load(folder+asset+'.'+asset) if self.resources is not None else load_asset(self.scope,folder+asset+'.'+asset).return_value)
                row['map_class']=map_class;row['map_add']=map_add
            # Validate all local packets before any row can be committed. Native
            # dispatch repeats its own lease/identity/save checks for each row.
            for row in self.rows:packet(row['owner'],row,self.gi,self.key,0)
            self.inputs_ready=True
        except BaseException as error:
            self.preparation_error=str(error);raise
        return self
    def prepare(self):
        self.preflight()
        for row in self.rows:
            if row['acknowledged']:continue
            if row['attempted']:raise RuntimeError('Character row outcome is unresolved; no replay')
            row['attempted']=True
            try:
                row['receipt']=self.send(row,0)
                row['acknowledged']=True;row['started']=True
            except BaseException as error:
                self.preparation_error=str(error);raise
        return self
    def send(self,row,mode):
        sent=packet(row['owner'],row,self.gi,self.key,mode)
        try:return decode(sent,bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet']))
        except wire.OriginalNarrativeError as error:
            if error.code==4251:self.unknown=True
            raise
        except BaseException:self.unknown=True;raise
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        for row in reversed(self.rows):
            if row['started']:self.send(row,2);row['started']=False
        self.scope.close();self.closed=True;return True
