"""Process-owned pause schemas; world widgets are always discovered freshly."""
from ._reader import ReadBatch
from .catalog import capture_matching,capture_selected
from ._metadata_stabilization import prepare_discovery,script_function
from ._planning_metadata import MetadataObservations
from .reflection import describe
from .enums import describe_enums

NAMES=('WBP_PauseMenu_C','WBP_BaseButton_C','CommonButtonBase','CommonActivatableWidget',
    'CommonTextBlock','TextBlock','TextLayoutWidget','Widget','UserWidget','WidgetTree',
    'GridPanel','GridSlot','PanelSlot','ContentWidget','WidgetBlueprintLibrary','GameplayStatics',
    'Default__WidgetBlueprintLibrary','Default__GameplayStatics','Margin',
    'Create','SpawnObject','SetContent','AddChildToGrid','SetPadding','SetHorizontalAlignment',
    'SetVerticalAlignment','SetText','SetStyle','SetJustification','SetMinDimensions',
    'SetIsSelectable','SetIsToggleable','SetFocusToGameViewport','SetUserFocus',
    'IsActivated','RemoveFromParent','HandleButtonClicked',
    'Overlay','OverlaySlot','PanelWidget','AddChildToOverlay',
    'GetRenderOpacity','SetRenderOpacity','GetIsEnabled','SetIsEnabled',
    'GetChildrenCount','GetChildAt','CommonTextBlock_178',
    'ETextJustify','EHorizontalAlignment','EVerticalAlignment')
WORLD_NAMES=('WBP_PauseMenu_C','WBP_BaseButton_C','CommonTextBlock_178')
# Slate's enum is read-only metadata outside the retained Script whitelist.
FRESH_NAMES=(*WORLD_NAMES,'ETextJustify')

def prepare(session):
    if getattr(session,'_pause_entry_metadata_selectors',None) is not None:return
    with ReadBatch(session.pid):
        catalog,_=prepare_discovery(session,lambda:capture_matching(session.pid,
            names=tuple(name for name in NAMES if name not in WORLD_NAMES)+
                ('PlayerController','LocalPlayer','CommonTextStyle')))
        admitted=[]
        for obj in catalog.objects:
            try:script_function(catalog,obj)
            except ValueError:continue
            if obj.serial<=0:raise RuntimeError('Pause preparation metadata is not retained')
            admitted.append(obj)
        selectors=tuple((obj.index,obj.serial,obj.address) for obj in admitted)
        if not 1<=len(selectors)<=1024:raise RuntimeError('Pause metadata exceeds selected bound')
        metadata=MetadataObservations()
        owners={
            'WidgetBlueprintLibrary':('Create','SetFocusToGameViewport'),
            'GameplayStatics':('SpawnObject',),'ContentWidget':('SetContent',),
            'GridPanel':('AddChildToGrid',),'GridSlot':('SetPadding','SetHorizontalAlignment','SetVerticalAlignment'),
            'CommonTextBlock':('SetStyle',),'TextBlock':('SetText',),
            'TextLayoutWidget':('SetJustification',),
            'CommonButtonBase':('SetMinDimensions','SetIsSelectable','SetIsToggleable','HandleButtonClicked'),
            'Widget':('GetRenderOpacity','SetRenderOpacity','GetIsEnabled','SetIsEnabled','RemoveFromParent','SetUserFocus'),
            'CommonActivatableWidget':('IsActivated',),'Overlay':('AddChildToOverlay',),
            'OverlaySlot':('SetHorizontalAlignment','SetVerticalAlignment'),
            'PanelWidget':('GetChildrenCount','GetChildAt')}
        functions=tuple(o for o in admitted if o.class_name=='Function' and
            o.name in owners.get(catalog.by_index[o.outer_index].name,()))
        metadata.read('struct',catalog,functions+tuple(o for o in admitted if o.class_name=='ScriptStruct'),describe)
        metadata.read('enum',catalog,tuple(o for o in admitted if o.class_name=='Enum'),describe_enums)
        session._pause_schema_observations=metadata
        session._pause_readonly_metadata_selectors=tuple((o.index,o.serial,o.address)
            for o in catalog.objects if o.class_name=='Enum' and o.name=='ETextJustify')
        import logging
        logging.getLogger(__name__).info('Pause metadata prepared during loading: %s retained descriptors',len(selectors))
        session._pause_entry_metadata_selectors=selectors

def _current_widgets(session,controller):
    """Follow the current Resume button's named-slot content, without a scan.

    This copies borrowed properties only. The ordinary entry installation still
    rechecks the current controller/pause pair before acquiring any UI owners.
    An unsupported shape returns None before construction for legacy discovery.
    """
    from . import RuntimeQueryError
    from .catalog import CatalogObject
    from .values import capture_selected_values,read_values_with_references,StoredArray,StoredStruct
    if (type(controller) is not tuple or len(controller)!=4 or controller[0]!=session.pid):
        raise ValueError('Expected current pause controller identity')
    catalog,rows=capture_selected_values(session.pid,(controller[1:],),
        fields=('Player','PauseMenuWidget'),references=True)
    pc=catalog.by_index[controller[1]]
    if catalog.find_class('PlayerController').index not in catalog.ancestors(pc.class_index):
        raise RuntimeQueryError('Pause controller class changed')
    def value(row,name,kind):
        keys=[key for key in row.types if key[1]==name]
        if len(keys)!=1 or row.types[keys[0]]!=kind or keys[0] in row.errors or keys[0] in row.truncated:
            raise RuntimeQueryError('Pause property is unavailable or ambiguous: '+name)
        return row.values.get(keys[0])
    local=value(rows[pc.index],'Player','ObjectProperty')
    pause=value(rows[pc.index],'PauseMenuWidget','ObjectProperty')
    if local is None or pause is None:return catalog
    if local.class_name!='LocalPlayer' or pause.class_name!='WBP_PauseMenu_C':return None
    observed,catalog=read_values_with_references(catalog,pause,fields=('WidgetTree','ResumeButton'))
    tree=value(observed,'WidgetTree','ObjectProperty')
    resume=value(observed,'ResumeButton','ObjectProperty')
    if tree is None or resume is None:return catalog
    def references(item,depth=0):
        if depth>8:raise RuntimeQueryError('Pause named-slot depth limit')
        if isinstance(item,StoredArray):
            if item.length!=len(item.items) or item.length>32:raise RuntimeQueryError('Pause named-slot array bound')
            for child in item.items:yield from references(child,depth+1)
        elif isinstance(item,StoredStruct):
            if item.errors or item.truncated:raise RuntimeQueryError('Incomplete pause named-slot struct')
            for child in item.fields.values():yield from references(child,depth+1)
        elif isinstance(item,CatalogObject):yield item
    pending=(resume,);seen=set()
    for _ in range(8):
        if not pending:return None
        observed,rows=capture_selected_values(session.pid,tuple((o.index,o.serial,o.address) for o in pending),
            fields=('Slots','Content','NamedSlotBindings'),references=True)
        catalog=catalog.with_observations(observed)
        candidates=[o for o in observed.objects if o.name=='CommonTextBlock_178'
            and (o.outer_index,o.outer_serial)==(tree.index,tree.serial)]
        if len(candidates)>1:raise RuntimeQueryError('Ambiguous pause text style source')
        if candidates:
            target=candidates[0]
            if catalog.find_class('CommonTextBlock').index not in catalog.ancestors(target.class_index):
                raise RuntimeQueryError('Pause text style source class changed')
            return catalog
        seen.update(o.index for o in pending);following={}
        for row in rows.values():
            if row.errors or row.truncated:raise RuntimeQueryError('Incomplete pause content projection')
            for item in row.values.values():
                for obj in references(item):
                    if obj.index not in seen:following[obj.index]=obj
        if len(seen)+len(following)>96:raise RuntimeQueryError('Pause content graph bound')
        pending=tuple(following.values())
    return None


def capture(session,*,controller=None):
    from . import RuntimeQueryError
    selectors=getattr(session,'_pause_entry_metadata_selectors',None)
    if selectors is None:return None
    # Both catalogs are current observations. Cached data consists only of
    # retained Script identities; no world/controller/widget copy is reused.
    readonly=getattr(session,'_pause_readonly_metadata_selectors',None)
    try:metadata=capture_selected(session.pid,selectors+(readonly or ()))
    except RuntimeQueryError:
        # Pure descriptor acquisition failed before UI construction. A later
        # scheduled operation may rediscover the unretained enum; never replay
        # this request or replace retained Script identities on failure.
        if readonly is not None:session._pause_readonly_metadata_selectors=None
        raise
    world=_current_widgets(session,controller) if controller is not None and readonly is not None else None
    if world is None:
        world=capture_matching(session.pid,names=FRESH_NAMES,
            classes=('PlayerController','LocalPlayer','WBP_PauseMenu_C'))
        session._pause_readonly_metadata_selectors=tuple((o.index,o.serial,o.address)
            for o in world.objects if o.class_name=='Enum' and o.name=='ETextJustify')
    catalog=metadata.with_observations(world)
    previous=getattr(session,'_pause_schema_observations',None)
    if previous is not None:
        checked=MetadataObservations()
        for key,entry in previous._entries.items():
            try:
                for dependency in entry[1]:catalog.resolve(dependency)
            except RuntimeQueryError:continue
            checked._entries[key]=entry
        # Boundary-only pure cache invalidation, before creating an entry. A
        # changed unretained enum must be described freshly, never substituted
        # in an existing plan. Unrelated title-entry schemas need no world copy.
        session._pause_schema_observations=checked
    return catalog
