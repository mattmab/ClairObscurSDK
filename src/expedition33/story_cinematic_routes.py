"""Process-owned call-local cinematic routing with explicit save/menu admission."""
import re,secrets,struct
from ._scope import SessionScope
from ._story_original_wire import put_id,identity,guid
SIZE=20984;COUNT=16;LEASES=280;MODE=408;KEYS=416;MENU=1440;STATS=1484;ROUTE_COUNT=1492;MENU_DIRECTION=1496;MAX_ROUTES=5
def validate(data):
    if type(data)is not bytes or len(data)!=SIZE or struct.unpack_from('<4I',data)!=(3,269,0,0) or not struct.unpack_from('<Q',data,16)[0]:raise ValueError('Cinematic route header')
    routes=struct.unpack_from('<I',data,ROUTE_COUNT)[0]
    if not 1<=routes<=MAX_ROUTES:raise ValueError('Cinematic route count')
    active=6+2*routes
    for at in range(24,24+active*16,16):identity(data,at)
    if any(data[24+active*16:LEASES]) or any(data[LEASES+active*8:MODE]):raise ValueError('Unused cinematic identities must be empty')
    mode,n=struct.unpack_from('<2I',data,MODE)
    if mode>4 or n>64 or not all(struct.unpack_from('<'+str(active)+'Q',data,LEASES)) or any(data[KEYS+n*16:MENU]) or any(data[STATS:ROUTE_COUNT]) or any(data[MENU_DIRECTION+16:]):raise ValueError('Cinematic route bounds/ownership')
    for at in range(KEYS,KEYS+n*16,16):
        if struct.unpack_from('<I',data,at)[0]!=0xe33c5701:raise ValueError('Cinematic story namespace')
    if mode==3:
        identity(data,MENU);identity(data,MENU+16)
        if any(data[MENU_DIRECTION:MENU_DIRECTION+16]):identity(data,MENU_DIRECTION)
        selected,choices,target=struct.unpack_from('<3I',data,1472)
        if not 1<=choices<=32 or selected>=choices or target>=choices:raise ValueError('Cinematic menu choice bounds')
    elif any(data[MENU:STATS]):raise ValueError('Unexpected cinematic menu payload')
    elif any(data[MENU_DIRECTION:MENU_DIRECTION+16]):raise ValueError('Unexpected cinematic menu direction identity')

def validate_routes(document):
    """One to five caller-owned source/replacement pairs, without implicit routes."""
    if type(document) is not dict or type(document.get('routes')) is not list:
        raise ValueError('Cinematic routes must be a list')
    rows=document['routes']
    if not 1<=len(rows)<=MAX_ROUTES:raise ValueError('Cinematic routing supports one to five pairs')
    sources=set();result=[]
    for row in rows:
        if type(row) is not dict or set(row)!={'source','replacement'}:
            raise ValueError('Each cinematic route requires source and replacement')
        for field in ('source','replacement'):
            path=row[field]
            if type(path) is not str or len(path)>512 or re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+\.[A-Za-z0-9_]+',path) is None:
                raise ValueError('Cinematic asset path must be an absolute game asset')
        if row['source']==row['replacement'] or row['source'] in sources:
            raise ValueError('Cinematic sources must be unique and replacements distinct')
        sources.add(row['source']);result.append(dict(row))
    return tuple(result)

class CinematicRoutes:
    def __init__(self,parent,resources,context,document,keys):
        routes=validate_routes(document)
        self.route_count=len(routes)
        self._scope=parent;self.scope=SessionScope(parent);self.resources=resources;self.owner=secrets.randbits(64) or 1
        self.closed=False;self.unknown=False;self.started=False;self.objects=[];self.keys=set(keys);self.menu=None
        parent._register_native_owner(self);parent._close_before_descendants(self)
        if getattr(parent._session._transport,'story_cinematic_routes_protocol',0)!=2:raise RuntimeError('Updated cinematic routing runtime required')
        resources.load('/Game/UI/Widgets/MainMenu/WBP_MM_MainMenu.WBP_MM_MainMenu_C',cls=True)
        from .catalog import capture_matching,capture_selected
        paths=('/Game/Gameplay/CinematicSystem/BP_CinematicSystem.BP_CinematicSystem_C:TriggerCinematic',
               '/Game/Gameplay/CinematicSystem/S_TriggerCinematicVariables.S_TriggerCinematicVariables',
               '/Script/CommonUI.CommonButtonBase:HandleButtonClicked',
               '/Game/UI/Widgets/MainMenu/WBP_MM_MainMenu.WBP_MM_MainMenu_C:OnStartGameSettingsApplied')
        # Resolve struct by exact observed path; fail rather than guess a layout.
        c=capture_matching(parent.pid,names=tuple(p.rsplit(':',1)[-1].rsplit('.',1)[-1] for p in paths))
        chosen=[resources.hold(o) for o in (capture_selected(parent.pid,(context.gi[1:],context.local_player[1:])).by_index[context.gi[1]],)]
        live=capture_selected(parent.pid,(context.local_player[1:],));chosen.append(resources.hold(live.by_index[context.local_player[1]]))
        chosen.extend(resources.hold(c.find_path(path)) for path in paths)
        for row in routes:
            chosen.extend(resources.hold(resources.load(row[k])) for k in ('source','replacement'))
        self.objects=tuple(chosen)
        self.send(0);self.started=True
    @property
    def _closed(self):return self.closed
    def send(self,mode,*,menu=None,direction=None):
        data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,269,0,0,self.owner)
        for i,h in enumerate(self.objects):put_id(data,24+16*i,h.object)
        struct.pack_into('<'+str(len(self.objects))+'Q',data,LEASES,*(h._token for h in self.objects))
        struct.pack_into('<I',data,ROUTE_COUNT,self.route_count)
        keys=sorted(self.keys)
        struct.pack_into('<2I',data,MODE,mode,len(keys))
        for i,k in enumerate(keys):struct.pack_into('<4I',data,KEYS+16*i,*guid(k))
        if menu is not None:
            button,main,selected,choices,target=menu;put_id(data,MENU,button);put_id(data,MENU+16,main)
            struct.pack_into('<3I',data,1472,selected,choices,target)
        if direction is not None:put_id(data,MENU_DIRECTION,direction)
        sent=bytes(data);validate(sent)
        try:
            with self.scope._lease_context():reply=bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet'])
            if len(reply)!=SIZE:raise RuntimeError('Cinematic acknowledgement size')
            clean=bytearray(reply);clean[8:16]=sent[8:16];clean[STATS:STATS+8]=sent[STATS:STATS+8]
            if bytes(clean)!=sent:raise RuntimeError('Cinematic acknowledgement context')
            error,state=struct.unpack_from('<2I',reply,8)
            if error or state!=mode+1:raise RuntimeError('Cinematic routing rejected '+str(error))
            return dict(zip(('routed','vanilla'),struct.unpack_from('<2I',reply,STATS)))
        except BaseException:self.unknown=True;raise
    def allow(self,key):
        guid(key)
        if key not in self.keys and len(self.keys)>=64:raise RuntimeError('Cinematic save inventory bound')
        self.keys.add(key);self.send(2)
    def bind_menu(self,row,choice,story):
        target=next(i for i,(key,_) in enumerate(choice.options) if key==story)
        token=(row.button.index,row.button.serial,row.button.address,len(choice.options),target)
        if self.menu==token:return
        # The exact widget instance/function receipt owns the first-new-save
        # exception. Existing save playback must prove an allow-listed GUID.
        main=row._story_main
        direction=getattr(row,'_direction_receiver',None)
        menu=(row.button,main,choice.index,len(choice.options),target)
        if direction is None:self.send(3,menu=menu)
        else:self.send(3,menu=menu,direction=direction)
        self.menu=token
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:self.send(4);self.started=False
        for media in getattr(self,'media_sources',()):
            if not media.close():return False
        self.scope.close();self.closed=True;return True
