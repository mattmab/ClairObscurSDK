"""Internal opt-in stable ownership of a verified child of an owned widget.

This is scope ownership, never process metadata admission or a call retry.
"""
import weakref
from . import RuntimeQueryError
from .ownership import ObjectLease, LeaseError
from . import _lease_wire


def available(transport):
    value=getattr(transport,'stable_lease_protocol',0)
    return type(value) is int and value==1


def decode(sent,encoded,*,capacity):
    packet=_lease_wire.PACKET
    if type(capacity) is not int or not 1<=capacity<=8192:raise ValueError('Stable lease capacity')
    if type(sent) is not bytes or len(sent)!=packet.size or type(encoded) is not str or len(encoded)!=packet.size*2:
        raise ValueError('Stable lease packet size')
    raw=bytes.fromhex(encoded)
    if len(raw)!=packet.size:raise ValueError('Stable lease reply size')
    old=packet.unpack(sent)
    if old[:4]!=(1,0,0,0) or old[4]<0 or old[5]<0 or old[6]<=0 or old[7]:raise ValueError('Stable lease request fields')
    version,error,outcome,active,index,serial,address,token=packet.unpack(raw)
    if (version!=1 or outcome not in (0,1,2) or active>capacity or
        index!=old[4] or address!=old[6] or serial<0 or
        (old[5]>0 and serial!=old[5]) or (not old[5] and serial!=0 and serial<1001)):
        raise ValueError('Stable lease identity or header changed')
    if not error:
        if outcome!=1 or not token or serial<=0:raise ValueError('Stable lease success lacks ownership')
    elif error not in (*range(400,414),):raise ValueError('Stable lease error code')
    elif outcome==0 and (token or serial!=old[5]):raise ValueError('Stable lease rejected after effect')
    elif outcome==1:raise ValueError('Stable acquisition failure requires uncertain ownership')
    return dict(error=error,outcome=outcome,active=active,identity=(index,serial,address),token=token)


def acquire_stable(scope,obj,*,selectors=(),capture=None):
    """Internal scope acquisition returning lease plus fresh selected catalog."""
    from .catalog import capture_selected
    capture=capture or capture_selected
    scope._check();session=scope._session
    if getattr(obj,'pid',None)!=session.pid:raise ValueError('Stable acquired object must belong to this session')
    if not available(session._transport):raise LeaseError('Stable acquisition unavailable',outcome='not_dispatched')
    if getattr(obj,'pid',None)!=session.pid:raise ValueError('Stable acquired object belongs to another process')
    sent=_lease_wire.request('lease-acquire',object=obj)
    try:
        with scope._lease_context():response=session._transport.command('stable-lease-acquire',sent)
        reply=decode(sent,response['lease_packet'],capacity=getattr(session._transport,'lease_limit',128))
    except BaseException:
        session._abort_ownership();raise
    lease=None
    if reply['token']:
        if any(value._token==reply['token'] for value in session._leases):
            session._abort_ownership();raise RuntimeQueryError('Stable lease token aliases ownership')
        lease=ObjectLease(session,reply['token'],None)
        lease._scope=weakref.ref(scope)
        # Adopt ownership BEFORE any reader call or postcondition validation.
        session._leases.add(lease);scope._leases.append(lease)
    if reply['error']:
        if reply['outcome']==2:session._abort_ownership()
        raise LeaseError('Stable tree acquisition failed',outcome=('not_dispatched','completed','unknown')[reply['outcome']],native_error=reply['error'])
    fresh=capture(session.pid,(reply['identity'],)+tuple(selectors))
    current=fresh.by_index[obj.index]
    lease._object=current
    if (current.index,current.serial,current.address)!=reply['identity']:
        raise RuntimeQueryError('Stable acquired identity changed')
    return lease,fresh


def _owned_child_chain(catalog,parent,child,field):
    if field=='WidgetTree':
        valid=child.class_name=='WidgetTree' and child.outer_index==parent.index
    elif field=='ButtonContent':
        outer=catalog.by_index.get(child.outer_index)
        valid=(parent.class_name=='WBP_BaseButton_C' and child.class_name=='NamedSlot' and
            outer is not None and outer.class_name=='WidgetTree' and outer.outer_index==parent.index)
    else:
        valid=False
    if not valid:raise RuntimeQueryError('Child is outside the explicit owned widget property chain')


def stabilize_owned_tree(scope,catalog,parent,tree,owner_class,*,field='WidgetTree',read_reference=None,capture=None):
    """Return a fresh selected tree catalog after adopting its durable lease.

    Caller must discard its prior tree catalog/plans and rediscover metadata.
    The parent must already have a live lease in this exact scope.
    """
    from .values import read_object_reference
    from .catalog import capture_selected
    read_reference=read_reference or read_object_reference
    capture=capture or capture_selected
    scope._check();session=scope._session
    if not available(session._transport):raise LeaseError('Stable acquisition unavailable',outcome='not_dispatched')
    if not any(lease.active and lease._object is not None and
               (lease._object.index,lease._object.serial,lease._object.address)==(parent.index,parent.serial,parent.address)
               for lease in scope._leases):
        raise LeaseError('Owned tree requires an active parent scope lease',outcome='not_dispatched')
    parent=catalog.resolve(parent);tree=catalog.resolve(tree)
    _owned_child_chain(catalog,parent,tree,field)
    observed,before=read_reference(catalog,parent,owner_class,field,project=True)
    if observed is None or (observed.index,observed.serial,observed.address)!=(tree.index,tree.serial,tree.address):
        raise RuntimeQueryError('Owned widget tree property changed before acquisition')
    _owned_child_chain(before,parent,observed,field)
    lease,fresh=acquire_stable(scope,tree,
        selectors=((parent.index,parent.serial,parent.address),),capture=capture)
    reply={'identity':(lease.object.index,lease.object.serial,lease.object.address)}
    try:
        current=fresh.by_index[tree.index];new_parent=fresh.resolve(parent)
        lease._object=current
        if (current.index,current.serial,current.address)!=reply['identity']:
            raise RuntimeQueryError('Stable owned tree identity changed')
        _owned_child_chain(fresh,new_parent,current,field)
        after,selected=read_reference(fresh,new_parent,fresh.by_index[owner_class.index],field,project=True)
        if after is None or (after.index,after.serial,after.address)!=reply['identity']:
            raise RuntimeQueryError('Owned widget tree property changed after acquisition')
        _owned_child_chain(selected,new_parent,after,field)
        return after,selected
    except BaseException:
        # The exact lease remains scope-owned for ordered cleanup, even if the
        # property was replaced. Do not discard the token or repeat acquisition.
        raise


def rediscover_owned_tree(pid,discover,parent,stable_tree,owner_class_index,*,capture=None,read_reference=None):
    """Discard pre-stabilization observations and verify the leased child again."""
    from .catalog import capture_selected
    from .values import read_object_reference
    capture=capture or capture_selected
    read_reference=read_reference or read_object_reference
    catalog=discover()
    # Static metadata discovery excludes this newly-created root. Only the
    # freshly selected root closure may be added; never the old child catalog.
    root=capture(pid,((parent.index,parent.serial,parent.address),))
    catalog=catalog.with_observations(root)
    tree,current=read_reference(catalog,parent,catalog.by_index[owner_class_index],'WidgetTree',project=True)
    if (tree is None or (tree.index,tree.serial,tree.address)!=
            (stable_tree.index,stable_tree.serial,stable_tree.address) or tree.outer_index!=parent.index):
        raise RuntimeQueryError('Owned tree changed during detached rediscovery')
    return catalog,tree,current


def refresh_owned_tree_catalog(catalog,parent,old_tree,stable_tree,owner_class_index,*,field='WidgetTree',capture=None,read_reference=None):
    """Recapture existing authority/metadata without merging a serial transition."""
    from .catalog import capture_selected
    from .values import read_object_reference
    capture=capture or capture_selected
    read_reference=read_reference or read_object_reference
    identities=[(obj.index,obj.serial,obj.address) for obj in catalog.objects if obj.index!=old_tree.index]
    identities.append((stable_tree.index,stable_tree.serial,stable_tree.address))
    fresh=None
    for offset in range(0,len(identities),1024):
        observed=capture(catalog.pid,tuple(identities[offset:offset+1024]))
        fresh=observed if fresh is None else fresh.with_observations(observed)
    current,selected=read_reference(fresh,parent,fresh.by_index[owner_class_index],field,project=True)
    if (current is None or (current.index,current.serial,current.address)!=
            (stable_tree.index,stable_tree.serial,stable_tree.address)):
        raise RuntimeQueryError('Owned entry tree changed during detached refresh')
    _owned_child_chain(selected,parent,current,field)
    return current,selected


def fresh_catalog_replacing(catalog,objects,*,capture=None):
    """Discard every prior observation; replace only acknowledged identities."""
    from .catalog import capture_selected
    capture=capture or capture_selected
    replacements={obj.index:obj for obj in objects}
    identities=[(replacements.get(obj.index,obj).index,replacements.get(obj.index,obj).serial,
                 replacements.get(obj.index,obj).address) for obj in catalog.objects]
    identities.extend((obj.index,obj.serial,obj.address) for obj in objects if obj.index not in catalog.by_index)
    fresh=None
    for offset in range(0,len(identities),1024):
        observed=capture(catalog.pid,tuple(identities[offset:offset+1024]))
        fresh=observed if fresh is None else fresh.with_observations(observed)
    return fresh
