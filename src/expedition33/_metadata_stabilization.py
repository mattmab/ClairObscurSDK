"""Process-owned engine Script metadata identities; never invokes a function."""
import struct
from . import RuntimeQueryError
from .ownership import ObjectLease,LeaseError
from .invocation import UnsupportedInvocation
HEADER=struct.Struct('<6I');ROW=struct.Struct('<iiQiiQQ2I');CAPACITY=128;SIZE=HEADER.size+CAPACITY*ROW.size
SCRIPT_PACKAGES=frozenset('/Script/'+name for name in ('CoreUObject','Engine','UMG','CommonUI','SlateCore','InputCore'))
STYLE_PATHS=frozenset(('/Game/UI/Resources/Styles/Text/Heading/CTS_H2_Outline.CTS_H2_Outline_C','/Game/UI/Resources/Styles/Text/Body/Outline/CTS_B1_SmallLine_Outline.CTS_B1_SmallLine_Outline_C'))

def available(transport):
    value=getattr(transport,'metadata_stabilization_protocol',0)
    return type(value) is int and value==1

def request(identities):
    ids=tuple(identities)
    if not 1<=len(ids)<=CAPACITY:raise ValueError('Metadata batch requires1..128 identities')
    if len({i[0] for i in ids})!=len(ids) or len({i[2] for i in ids})!=len(ids):raise ValueError('Duplicate metadata identity')
    data=bytearray(SIZE);HEADER.pack_into(data,0,1,len(ids),0,0,0,0)
    for n,identity in enumerate(ids):
        if len(identity)!=3 or any(type(v) is not int for v in identity):raise ValueError('Metadata identity types')
        index,serial,address=identity
        if not 0<=index<2**31 or not 0<=serial<2**31 or not 0x10000<=address<2**64 or address&7:raise ValueError('Metadata identity bounds')
        ROW.pack_into(data,HEADER.size+n*ROW.size,index,serial,address,0,0,0,0,0,0)
    return bytes(data)

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Metadata request size')
    version,count,error,completed,active,failed=HEADER.unpack_from(data)
    if version!=1 or not 1<=count<=CAPACITY or error or completed or active or failed:raise ValueError('Metadata request header')
    ids=[ROW.unpack_from(data,HEADER.size+i*ROW.size)[:3] for i in range(count)]
    if request(ids)!=data:raise ValueError('Metadata request reserved fields')

def decode(sent,encoded):
    validate_request(sent)
    if type(encoded) is not str:raise ValueError('Metadata reply type')
    raw=bytes.fromhex(encoded)
    if len(raw)!=SIZE:raise ValueError('Metadata reply size')
    version,count,error,completed,active,failed=HEADER.unpack_from(raw)
    if (version,count)!=HEADER.unpack_from(sent)[:2] or completed>count or active>8192 or failed>count:raise ValueError('Metadata reply header')
    rows=[];tokens=set()
    for i in range(CAPACITY):
        row=ROW.unpack_from(raw,HEADER.size+i*ROW.size);old=ROW.unpack_from(sent,HEADER.size+i*ROW.size)
        before,after,token,effect,outcome=row[:3],row[3:6],row[6],row[7],row[8]
        if before!=old[:3]:raise ValueError('Metadata before identity changed')
        if i>=completed:
            if row!=old:raise ValueError('Metadata undispatched suffix changed')
        else:
            if outcome not in (1,2):raise ValueError('Metadata row outcome')
            if token:
                if token in tokens:raise ValueError('Metadata duplicate token')
                tokens.add(token)
            if outcome==1:
                if effect or not token or before[0]!=after[0] or before[2]!=after[2] or after[1]<=0 or (before[1] and before[1]!=after[1]) or (not before[1] and after[1]<1001):raise ValueError('Metadata stable identity ACK')
            elif i!=completed-1 or not error or effect!=error:raise ValueError('Metadata failed row ACK')
        if i<count:rows.append(dict(before=before,after=after,token=token,error=effect,outcome=outcome))
    if not error:
        if completed!=count or failed:raise ValueError('Metadata incomplete success')
    elif completed:
        if failed!=completed or rows[completed-1]['outcome']!=2:raise ValueError('Metadata failed prefix')
    elif not failed and error!=3920:raise ValueError('Metadata admission rejection')
    return dict(error=error,completed=completed,failed=failed,active=active,rows=tuple(rows))

def script_function(catalog,obj):
    # Name retained for proposal compatibility; admits only the explicit kinds.
    obj=catalog.resolve(obj)
    if obj.object_flags&0x40000000:raise ValueError('Forbidden metadata object')
    def package_ok(package):
        return package is not None and package.class_name=='Package' and package.outer_index==-1 and catalog.path_name(package) in SCRIPT_PACKAGES
    outer=catalog.by_index.get(obj.outer_index)
    if obj.class_name=='BlueprintGeneratedClass':
        admitted=False
        if outer is not None and outer.class_name=='Package' and outer.outer_index==-1 and catalog.path_name(obj) in STYLE_PATHS:
            for index in catalog.ancestors(obj.index):
                parent=catalog.by_index[index]
                if parent.class_name=='Class' and parent.name=='CommonTextStyle' and catalog.path_name(catalog.by_index[parent.outer_index])=='/Script/CommonUI':
                    admitted=True;break
    elif obj.class_name=='Function':
        admitted=outer is not None and outer.class_name=='Class' and package_ok(catalog.by_index.get(outer.outer_index))
    elif obj.class_name in ('Class','Enum','ScriptStruct'):
        admitted=package_ok(outer)
    else:
        cls=catalog.by_index.get(obj.class_index)
        admitted=(bool(obj.object_flags&0x10) and cls is not None and cls.class_name=='Class'
            and cls.name==obj.class_name and obj.name=='Default__'+cls.name
            and cls.outer_index==obj.outer_index and package_ok(outer))
    if not admitted:raise ValueError('Object is outside the explicit Script metadata/CDO whitelist')
    return obj

class MetadataPreparation:
    """One persistent SDKMetadata scope per Session, surviving world retirement.

    Call only during process preparation, before constructing immutable plans.
    Discard the original discovery catalog after success; returned observations
    contain only newly stabilized metadata closures and grant no world authority.
    """
    def __init__(self,session):
        from ._scope import SessionScope
        session._check();self.session=session
        self.scope=SessionScope(session,lease_owner='SDKMetadata')
        self._known={};self._journal=[]
    def prepare(self,catalog,functions):
        from .catalog import capture_selected
        self.session._check()
        if not available(self.session._transport):raise LeaseError('Metadata stabilization unavailable',outcome='not_dispatched')
        functions=tuple(script_function(catalog,obj) for obj in functions)
        ids=tuple((obj.index,obj.serial,obj.address) for obj in functions)
        if not 1<=len(ids)<=CAPACITY or len(set(ids))!=len(ids):raise ValueError('Metadata preparation requires1..128 unique functions')
        missing=[identity for identity in ids if identity not in self._known]
        if missing:
            sent=request(missing)
            try:
                with self.scope._lease_context():response=self.session._transport.command('metadata-stabilize',sent)
                reply=decode(sent,response['metadata_stabilization_packet'])
            except BaseException:
                self.session._abort_ownership();raise
            # ALL native ownership is adopted before any catalog/schema read.
            adopted=[]
            try:
                existing={lease._token for lease in self.session._leases}
                if existing&{row['token'] for row in reply['rows'] if row['token']}:raise ValueError('Metadata token aliases existing lease')
                import weakref
                for row in reply['rows']:
                    if row['token']:
                        lease=ObjectLease(self.session,row['token'],None)
                        lease._scope=weakref.ref(self.scope)
                        self.session._leases.add(lease);self.scope._leases.append(lease)
                        self._journal.append(lease)
                        adopted.append((row,lease))
                if reply['error']:raise LeaseError('Metadata stabilization failed',outcome='unknown',native_error=reply['error'])
                fresh=capture_selected(self.session.pid,tuple(row['after'] for row in reply['rows']))
                originals={obj.index:obj for obj in functions}
                for row,lease in adopted:
                    current=script_function(fresh,fresh.by_index[row['after'][0]])
                    original=originals[current.index]
                    if (current.index,current.serial,current.address)!=row['after'] or current.name!=original.name or fresh.path_name(current)!=catalog.path_name(original):raise RuntimeQueryError('Metadata provenance changed after stabilization')
                    lease._object=current;self._known[row['after']]=current
            except BaseException:
                self.session._abort_ownership();raise
        # Do not merge serial transitions into old planning catalogs. A caller
        # must rebuild discovery/planners/schema after this explicit boundary.
        stable=[]
        for obj in functions:
            matches=[known for identity,known in self._known.items() if identity[0]==obj.index and identity[2]==obj.address]
            if len(matches)!=1:raise RuntimeQueryError('Metadata preparation identity unavailable')
            stable.append((matches[0].index,matches[0].serial,matches[0].address))
        return capture_selected(self.session.pid,tuple(stable))
    def close(self):
        try:self.scope.close()
        finally:self._journal=[lease for lease in self._journal if lease._state!='released']

def process_preparation(session):
    session._check()
    owner=getattr(session,'_metadata_preparation',None)
    if owner is None:owner=MetadataPreparation(session);session._metadata_preparation=owner
    return owner


def prepare_discovery(session,discover):
    """Stabilize admitted zero-serial plan metadata, then rebuild discovery.

    `discover` is the caller's existing bounded read-only discovery callable.
    It must return a fresh Catalog; no supplied world object is retained here.
    Returns(catalog,uncovered_zero_metadata) for explicit coverage reporting.
    The caller must create new planners/caches only after this boundary.
    """
    session._check();catalog=discover();selected=[];uncovered=[]
    for obj in catalog.objects:
        if obj.serial:continue
        candidate=(obj.class_name in ('Function','Class','Enum','ScriptStruct','BlueprintGeneratedClass','WidgetBlueprintGeneratedClass') or bool(obj.object_flags&0x10))
        if not candidate:continue
        try:script_function(catalog,obj)
        except ValueError:uncovered.append(obj)
        else:selected.append(obj)
    if not selected:return catalog,tuple(uncovered)
    owner=process_preparation(session);expected={}
    for start in range(0,len(selected),CAPACITY):
        observed=owner.prepare(catalog,selected[start:start+CAPACITY])
        for obj in selected[start:start+CAPACITY]:
            current=observed.by_index[obj.index]
            expected[obj.index]=(current.serial,current.address,current.name,observed.path_name(current))
    # Invalidate all copied menu plans before rebuilding descriptor identities.
    session._menu_plan_cache=None
    # No merge into a stale catalog: rebuild every caller discovery relation.
    fresh=discover()
    for index,identity in expected.items():
        current=fresh.by_index.get(index)
        if current is None or (current.serial,current.address,current.name,fresh.path_name(current))!=identity:
            raise RuntimeQueryError('Metadata discovery changed after stabilization')
    return fresh,tuple(uncovered)


class UnstableUIIdentity(UnsupportedInvocation):
    """Known pure preflight rejection; contains no object or argument payload."""
    ROLES=frozenset(('target','function','constraint','object_patch'))
    outcome='not_dispatched'
    native_error=0
    def __init__(self,role):
        if type(role) is not str or role not in self.ROLES:raise ValueError('Invalid UI identity role')
        self.role=role
        super().__init__('UI plan has an unstabilized '+role+' identity; detached frontend suspended')


def require_positive_plan_identities(plan):
    """Pure detached UI guard; never fixes, refreshes, pins or dispatches."""
    identities=[('target',plan.target),('function',plan.function)]
    identities.extend(('constraint',parameter.constraint) for parameter in plan.parameters if parameter.constraint is not None)
    identities.extend(('object_patch',patch.object) for patch in plan.objects if patch.object is not None)
    for role,obj in identities:
        if role in ('constraint','object_patch') and getattr(obj,'index',None)==-1 and obj.serial==0 and getattr(obj,'address',None)==0:continue
        if type(obj.serial) is not int or obj.serial<=0:
            import logging
            logging.getLogger(__name__).error(
                'UI plan zero identity role=%s index=%s serial=%s address=%#x class=%s name=%s function_index=%s function_name=%s',
                role,getattr(obj,'index',None),obj.serial,getattr(obj,'address',0),
                str(getattr(obj,'class_name',''))[:128],str(getattr(obj,'name',''))[:128],
                getattr(plan.function,'index',None),str(getattr(plan.function,'name',''))[:128])
            raise UnstableUIIdentity(role)
    return plan
