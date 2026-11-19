"""Process-owned story labels in the game's original save-slot list."""
import json,logging,os,time
from pathlib import Path
from .catalog import capture_matching,capture_selected
from .values import read_values_with_references,read_values_many_with_references,StoredArray
from ._scope import SessionScope
from .paths import settings_dir
from .save_story_labels import read_label
from .save_list_entries import read as list_item
from .enums import describe_enums
LOG=logging.getLogger(__name__)

# EnumProperty needs an identity-bearing EnumValue; older TEnumAsByte fields
# need an integer copied from the same observed UEnum. Never guess the backing
# storage or member number from a widget's apparent numeric default.
LAYOUT_ENUMS={
    '/Script/UMG.Widget:SetVisibility':('InVisibility','ESlateVisibility','HitTestInvisible'),
    '/Script/UMG.Widget:SetClipping':('InClipping','EWidgetClipping','ClipToBounds'),
    '/Script/UMG.TextLayoutWidget:SetJustification':('InJustification','ETextJustify','Center'),
    '/Script/UMG.SizeBoxSlot:SetHorizontalAlignment':('InHorizontalAlignment','EHorizontalAlignment','HAlign_Fill'),
    '/Script/UMG.SizeBoxSlot:SetVerticalAlignment':('InVerticalAlignment','EVerticalAlignment','VAlign_Bottom'),
    '/Script/UMG.GridSlot:SetHorizontalAlignment':('InHorizontalAlignment','EHorizontalAlignment','HAlign_Fill'),
    '/Script/UMG.GridSlot:SetVerticalAlignment':('InVerticalAlignment','EVerticalAlignment','VAlign_Fill'),
}
LAYOUT_PATHS=('/Script/Engine.GameplayStatics:SpawnObject','/Script/CommonUI.CommonTextBlock:SetStyle',
    '/Script/UMG.TextBlock:SetText','/Script/UMG.TextBlock:SetAutoWrapText','/Script/UMG.TextLayoutWidget:SetJustification',
    '/Script/UMG.GridPanel:AddChildToGrid','/Script/UMG.Widget:RemoveFromParent',
    '/Script/UMG.Widget:SetVisibility','/Script/UMG.Widget:SetClipping',
    '/Script/UMG.SizeBox:SetWidthOverride','/Script/UMG.SizeBox:SetHeightOverride','/Script/UMG.ContentWidget:SetContent',
    '/Script/UMG.SizeBoxSlot:SetHorizontalAlignment','/Script/UMG.SizeBoxSlot:SetVerticalAlignment',
    *('/Script/UMG.GridSlot:'+name for name in ('SetRowSpan','SetColumnSpan','SetLayer','SetHorizontalAlignment','SetVerticalAlignment')))
LAYOUT_OBJECTS=('/Script/CommonUI.CommonTextBlock','/Script/UMG.SizeBox','/Script/Engine.Default__GameplayStatics',
    '/Game/UI/Resources/Styles/Text/Body/Outline/CTS_B1_SmallLine_Outline.CTS_B1_SmallLine_Outline_C')


def layout_enum_arguments(catalog,descriptors,*,enum_reader=None):
    """Resolve layout choices from this build's exact function/type closure."""
    from .invocation import PARM,OUT,RETURN
    pending={};enums={}
    for path,(argument,enum_name,member_name) in LAYOUT_ENUMS.items():
        function=catalog.find_path(path);descriptor=descriptors[function.index]
        fields=[row for row in descriptor.properties if row['owner_index']==function.index and row['name']==argument]
        if len(fields)!=1:raise RuntimeError('Save layout enum parameter missing: '+path)
        field=fields[0]
        if (field['type'] not in ('EnumProperty','ByteProperty') or field['dimension']!=1 or
                field['element_size']!=1 or not field['flags']&PARM or field['flags']&(OUT|RETURN)):
            raise RuntimeError('Save layout enum storage differs: '+path)
        enum=catalog.by_index.get(field.get('enum_index'))
        if (enum is None or enum.name!=enum_name or field.get('enum_name')!=enum.name or
                field.get('enum_serial')!=enum.serial or int(field.get('enum_address','0'),16)!=enum.address):
            raise RuntimeError('Save layout enum identity differs: '+path)
        enums[enum.index]=enum;pending[path]=(argument,member_name,field['type'],enum)
    described=(enum_reader or describe_enums)(catalog,tuple(enums.values()));result={}
    for path,(argument,member_name,kind,enum) in pending.items():
        descriptor=described[enum.index]
        if catalog.resolve(descriptor.object)!=enum:raise RuntimeError('Save layout enum changed: '+path)
        members=[m for m in descriptor.members if m.name.rsplit('::',1)[-1]==member_name]
        if len(members)!=1:raise RuntimeError('Save layout enum member missing: '+path)
        member=descriptor.value(members[0].name)
        if type(member.value) is not int or not 0<=member.value<=255:
            raise RuntimeError('Save layout enum member outside byte storage: '+path)
        result[path]={argument:member if kind=='EnumProperty' else member.value}
    return result

def value(row,name):
    entries=[v for k,v in row.values.items() if k[1]==name]
    if row.errors or len(entries)!=1:raise RuntimeError('Save row observation incomplete: '+name)
    return entries[0]
def ident(obj):return (obj.index,obj.serial,obj.address)


class LabelMetadata:
    """Retained layout metadata only; no row, model, grid or save-state cache."""
    def __init__(self,session):
        self.session=session;self.scope=SessionScope(session,lease_owner='SaveStoryMetadata')
        self.ready=False;self.observations=None;self.getter=None;self.enum_arguments={}
    def prepare(self):
        from ._metadata_stabilization import prepare_discovery
        from .reflection import describe_selected
        from .save_list_entries import GetterMetadata,GETTER_PATHS
        self.scope._check()
        paths=LAYOUT_PATHS+LAYOUT_OBJECTS+GETTER_PATHS
        names=tuple(dict.fromkeys(tuple(path.rsplit(':',1)[-1].rsplit('.',1)[-1] for path in paths)+
            tuple(row[1] for row in LAYOUT_ENUMS.values())))
        discovered,_=prepare_discovery(self.session,lambda:capture_matching(self.scope.pid,names=names))
        # Discard broad discovery before saving observations. Only the exact
        # immutable function/type/style closure survives across row recycling.
        catalog=capture_selected(self.scope.pid,tuple(ident(discovered.find_path(path)) for path in paths))
        reflected=describe_selected(self.scope.pid,tuple(ident(catalog.find_path(path)) for path in LAYOUT_PATHS))
        catalog=catalog.with_observations(reflected.catalog)
        with self.scope.invocation_planner(catalog=catalog,selected_results=True) as planner:
            planner._metadata.read('struct',catalog,tuple(d.object for d in reflected.descriptors.values()),
                lambda catalog,objects:reflected.descriptors)
            self.enum_arguments=layout_enum_arguments(catalog,reflected.descriptors,
                enum_reader=lambda c,objects:planner._metadata.read('enum',c,objects,describe_enums))
            self.observations=planner.observations()
        self.getter=GetterMetadata(self.scope,catalog)
        self.ready=True
    def planner(self,scope,catalog):
        scope._check();self.scope._check()
        if not self.ready or scope._session is not self.session:
            raise RuntimeError('Save label metadata is unavailable or belongs to another session')
        planner=scope.invocation_planner(observations=self.observations,selected_results=True)
        try:planner.adopt_observations(catalog)
        except BaseException:planner.close();raise
        return planner
    def close(self):
        self.ready=False;self.scope.close()


def image_cell(catalog,tree,grid):
    """Qualify the original fixed-height image cell, not a new grid row.

    WBP_MM_SaveSlot's cooked layout has five rows. SizeBox_0 contains the
    LevelImageRetainer in row0/column0 spanning those five rows. The other
    column contains the original title/date/party/playtime and stays untouched.
    """
    values,catalog=read_values_with_references(catalog,grid,fields=('Slots',))
    slots=value(values,'Slots')
    if not isinstance(slots,StoredArray) or slots.length!=len(slots.items) or not 1<=slots.length<=32:
        raise RuntimeError('Complete original save grid required')
    for slot in slots.items:
        if (slot is None or slot.outer_index!=grid.index or slot.outer_serial!=grid.serial or
                catalog.path_name(catalog.by_index[slot.class_index])!='/Script/UMG.GridSlot'):
            raise RuntimeError('Original save grid slot ownership differs')
    fields=('Parent','Content','Row','Column','RowSpan','ColumnSpan','Layer')
    rows,catalog=read_values_many_with_references(catalog,slots.items,fields=fields)
    if set(rows)!={slot.index for slot in slots.items}:raise RuntimeError('Save grid observation incomplete')
    found=[]
    for slot in slots.items:
        entry=rows[slot.index]
        if entry.errors or entry.truncated or len(entry.values)!=len(fields):raise RuntimeError('Save grid observation incomplete')
        row={name:value(entry,name) for name in fields};content=row['Content']
        if row['Parent'] is None or ident(row['Parent'])!=ident(grid):raise RuntimeError('Save grid parent changed')
        if content is None or content.name!='SizeBox_0':continue
        if (content.outer_index!=tree.index or content.outer_serial!=tree.serial or
                catalog.path_name(catalog.by_index[content.class_index])!='/Script/UMG.SizeBox'):
            raise RuntimeError('Original save image cell differs: container ownership/class')
        if any(type(row[name]) is not int or row[name]<0 for name in ('Row','Column','RowSpan','ColumnSpan')):
            raise RuntimeError('Original save image cell differs: invalid cell values')
        # The installed native Default__GridSlot stores both spans as zero.
        # The cooked image overrides RowSpan=5 and omits ColumnSpan, leaving
        # the default single column. Normalize that implicit span only on our
        # copied cell; never write to the original slot or add another column.
        cell_position=(row['Row'],row['Column'],max(1,row['RowSpan']),max(1,row['ColumnSpan']))
        if cell_position!=(0,0,5,1):
            raise RuntimeError('Original save image cell differs: cell '+repr(cell_position))
        if type(row['Layer']) is not int or not 0<=row['Layer']<100:
            raise RuntimeError('Original save image cell differs: layer')
        found.append((content,row))
    if len(found)!=1:raise RuntimeError('One original save image cell required')
    content,cell=found[0]
    values,catalog=read_values_with_references(catalog,content,fields=('Slots',))
    children=value(values,'Slots')
    if not isinstance(children,StoredArray) or children.length!=1 or len(children.items)!=1:
        raise RuntimeError('Original save image container differs')
    slot=children.items[0]
    if (slot is None or slot.outer_index!=content.index or slot.outer_serial!=content.serial or
            catalog.path_name(catalog.by_index[slot.class_index])!='/Script/UMG.SizeBoxSlot'):
        raise RuntimeError('Original save image slot ownership differs')
    values,catalog=read_values_with_references(catalog,slot,fields=('Parent','Content'))
    parent=value(values,'Parent');image=value(values,'Content')
    if (parent is None or ident(parent)!=ident(content) or image is None or image.name!='LevelImageRetainer' or
            image.outer_index!=tree.index or image.outer_serial!=tree.serial or
            catalog.path_name(catalog.by_index[image.class_index])!='/Script/UMG.RetainerBox'):
        raise RuntimeError('Original save image binding differs')
    result={name:cell[name] for name in ('Row','Column','RowSpan','ColumnSpan','Layer')}
    result['RowSpan']=max(1,result['RowSpan']);result['ColumnSpan']=max(1,result['ColumnSpan'])
    return result,catalog

class Label:
    def __init__(self,session):
        self.scope=SessionScope(session,lease_owner='SaveStoryLabel');self.planner=None;self.widget=None;self.frame=None;self.cell=None;self.added=False;self.unknown=False
        self.binding=None;self.verified=False;self.closed=False
        self.metadata=getattr(getattr(session,'_save_story_ui',None),'metadata',None)
    def _adopt(self,obj):
        if obj is None:raise RuntimeError('Save story layout creation failed')
        self.planner.adopt_observations(capture_selected(self.scope.pid,(ident(obj),)))
    def publish(self,grid,text,call,still_bound):
        # A leased row UObject can be assigned another list model while it is
        # still alive. Never mistake its stable UObject identity for a stable
        # save binding. Text preparation itself can cross another engine tick.
        self.verified=False
        if not still_bound():return False
        with call(self.widget,'/Script/UMG.TextBlock:SetText',InText='Story: '+text):pass
        if not still_bound():return False
        # The owned frame has zero desired dimensions before attachment. Its
        # contents fit inside the original image cell; even the attachment tick
        # cannot increase the list entry's desired height or scroll extent.
        with call(grid,'/Script/UMG.GridPanel:AddChildToGrid',Content=self.frame,
                  InRow=self.cell['Row'],InColumn=self.cell['Column']) as added:slot=added.return_value
        self.added=True
        if not still_bound():return False
        self._adopt(slot)
        for function,arguments in (
                ('SetRowSpan',dict(InRowSpan=self.cell['RowSpan'])),
                ('SetColumnSpan',dict(InColumnSpan=self.cell['ColumnSpan'])),
                ('SetLayer',dict(InLayer=self.cell['Layer']+1)),
                ('SetHorizontalAlignment',{}),
                ('SetVerticalAlignment',{})):
            with call(slot,'/Script/UMG.GridSlot:'+function,**arguments):pass
        if not still_bound():return False
        self.verified=True;return True
    def build(self,row,catalog,text,*,still_bound):
        if not still_bound():return False
        values,catalog=read_values_with_references(catalog,row,fields=('WidgetTree','SlotGrid'))
        tree=value(values,'WidgetTree');grid=value(values,'SlotGrid')
        self.cell,catalog=image_cell(catalog,tree,grid)
        if self.metadata is not None:
            self.planner=self.metadata.planner(self.scope,catalog)
            catalog=self.planner._catalog;enum_arguments=self.metadata.enum_arguments
        else:
            extra=capture_matching(self.scope.pid,names=tuple(dict.fromkeys(('CommonTextBlock','SizeBox','Default__GameplayStatics',
                'CTS_B1_SmallLine_Outline_C',*(path.rsplit(':',1)[1] for path in LAYOUT_PATHS)))))
            catalog=catalog.with_observations(extra)
            from .reflection import describe_selected
            functions=tuple(ident(catalog.find_path(path)) for path in LAYOUT_PATHS)
            reflected=describe_selected(self.scope.pid,functions)
            catalog=catalog.with_observations(reflected.catalog)
            enum_arguments=layout_enum_arguments(catalog,reflected.descriptors)
            self.planner=self.scope.invocation_planner(catalog=catalog,selected_results=True)
        def call(target,path,**arguments):
            if path in enum_arguments:
                if arguments:raise RuntimeError('Save layout enum arguments are schema-owned')
                arguments=enum_arguments[path]
            prepared=self.planner.prepare(target,catalog.find_path(path),**arguments)
            self.unknown=True;result=prepared.invoke();self.unknown=False;return result
        from ._stable_lease import acquire_stable
        with call(catalog.find_path('/Script/Engine.Default__GameplayStatics'),'/Script/Engine.GameplayStatics:SpawnObject',
            ObjectClass=catalog.by_index[catalog.find_class('CommonTextBlock').index],Outer=tree) as created:
            if created.return_value is None:raise RuntimeError('Save story label construction failed')
            held,_=acquire_stable(self.scope,created.return_value);self.widget=held.object
        if self.widget is None:raise RuntimeError('Save story label construction failed')
        self.planner.adopt_observations(capture_selected(self.scope.pid,(ident(self.widget),)))
        style=[o for o in catalog.objects if o.name=='CTS_B1_SmallLine_Outline_C']
        if len(style)!=1:raise RuntimeError('Save story label style unavailable')
        with call(self.widget,'/Script/CommonUI.CommonTextBlock:SetStyle',InStyle=style[0]):pass
        with call(self.widget,'/Script/UMG.TextBlock:SetAutoWrapText',InAutoTextWrap=True):pass
        with call(self.widget,'/Script/UMG.TextLayoutWidget:SetJustification'):pass
        with call(catalog.find_path('/Script/Engine.Default__GameplayStatics'),'/Script/Engine.GameplayStatics:SpawnObject',
            ObjectClass=catalog.by_index[catalog.find_class('SizeBox').index],Outer=tree) as created:
            if created.return_value is None:raise RuntimeError('Save story frame construction failed')
            held,_=acquire_stable(self.scope,created.return_value);self.frame=held.object
        self._adopt(self.frame)
        with call(self.frame,'/Script/UMG.SizeBox:SetWidthOverride',InWidthOverride=0.):pass
        with call(self.frame,'/Script/UMG.SizeBox:SetHeightOverride',InHeightOverride=0.):pass
        with call(self.frame,'/Script/UMG.Widget:SetVisibility'):pass
        with call(self.frame,'/Script/UMG.Widget:SetClipping'):pass
        with call(self.frame,'/Script/UMG.ContentWidget:SetContent',Content=self.widget) as content:slot=content.return_value
        self._adopt(slot)
        with call(slot,'/Script/UMG.SizeBoxSlot:SetHorizontalAlignment'):pass
        with call(slot,'/Script/UMG.SizeBoxSlot:SetVerticalAlignment'):pass
        return self.publish(grid,text,call,still_bound)
    def close(self):
        if self.unknown:return False
        if self.frame is not None and self.added:
            # Title rows and their outers can be replaced while our leased
            # label survives. Rebuild only the live cleanup closure; merging
            # the original discovery catalog rejects unrelated recycled slots.
            metadata=getattr(self,'metadata',None)
            if metadata is not None:
                fresh=capture_selected(self.scope.pid,(ident(self.frame),))
                planner=metadata.planner(self.scope,fresh)
                self.planner.close();self.planner=planner;c=planner._catalog
            else:
                from .reflection import describe_selected
                c=capture_matching(self.scope.pid,names=('RemoveFromParent',))
                function=c.find_path('/Script/UMG.Widget:RemoveFromParent')
                c=c.with_observations(describe_selected(self.scope.pid,(ident(function),)).catalog)
                c=c.with_observations(capture_selected(self.scope.pid,(ident(self.frame),)))
                self.planner.refresh_from(c)
            call=self.planner.prepare(c.resolve(self.frame),c.find_path('/Script/UMG.Widget:RemoveFromParent'))
            self.unknown=True
            with call.invoke():pass
            self.unknown=False;self.widget=None;self.frame=None
        self.widget=None;self.frame=None
        if self.planner is not None:self.planner.close();self.planner=None
        self.scope.close();self.added=False;self.verified=False;self.closed=True;return True

class SaveStoryUI:
    def __init__(self,session):
        self.session=session;self.titles={};self.labels={};self.cache={};self.next_poll=0.;self.failed=None;self._closed=False
        self.metadata=None;self.timings={}
        self.root=Path(os.environ['LOCALAPPDATA'])/'Sandfall/Saved/SaveGames'
    def _measure(self,phase,operation,*args,**kwargs):
        started=time.perf_counter()
        try:return operation(*args,**kwargs)
        finally:
            if not hasattr(self,'timings'):self.timings={}
            duration=(time.perf_counter()-started)*1000
            row=self.timings.setdefault(phase,dict(calls=0,total_ms=0.,max_ms=0.))
            row['calls']+=1;row['total_ms']+=duration;row['max_ms']=max(row['max_ms'],duration)
    def _prepare_metadata(self):
        from ._metadata_stabilization import available
        if not available(getattr(self.session,'_transport',None)):return
        metadata=getattr(self,'metadata',None)
        if metadata is not None:
            if not metadata.ready:raise RuntimeError('Save label metadata preparation incomplete; not replayed')
            return
        self.metadata=LabelMetadata(self.session)
        self._measure('metadata',self.metadata.prepare)
    def register(self,key,title):
        if self.titles.get(key)!=title:
            self.titles[key]=title;self.cache.clear();self.next_poll=0.
    def _binding(self,row,catalog):
        metadata=getattr(self,'metadata',None)
        model=self._measure('model',list_item,self.session,row,catalog,metadata=metadata.getter if metadata is not None else None)
        if model is None:return None
        values,_=read_values_with_references(capture_selected(self.session.pid,(ident(model),)),model,fields=('SlotIndex',))
        slot=value(values,'SlotIndex')
        if type(slot) is not int or not 0<=slot<100:raise RuntimeError('Save row slot index invalid')
        return ident(model),slot
    def _retire(self,key):
        previous=self.labels.get(key)
        if previous is None:return True
        if not self._measure('retire',previous[0].close):return False
        del self.labels[key];return True
    def _label(self,slot):
        files=list(self.root.rglob(f'EXPEDITION_{slot}.sav'))
        files=[p for p in files if 'backup' not in str(p.relative_to(self.root)).lower()]
        if len(files)!=1:return 'Story unknown'
        file=files[0];stat=file.stat();store=settings_dir()/'StoryPacks/playthroughs.json'
        stamp=(file,stat.st_size,stat.st_mtime_ns,store.stat().st_mtime_ns if store.exists() else 0)
        if stamp not in self.cache:
            data=json.loads(store.read_text(encoding='utf8'))['playthroughs'] if store.exists() else {}
            self.cache={stamp:read_label(file,data,self.titles),**dict(list(self.cache.items())[-63:])}
        return self.cache[stamp]
    def poll(self,context):
        try:return self._poll(context)
        except Exception as error:
            from . import RuntimeQueryError
            if isinstance(error,RuntimeQueryError) and not any(o.unknown for o,_,_ in self.labels.values()):
                LOG.warning('Save story label cleanup discovery deferred: %s',error)
                return
            self.failed=str(error);LOG.exception('Save story labels suspended; exact owners retained')
    def _poll(self,context):
        if self._closed or self.failed:return
        if context is None or context.kind!='title':
            for key,(owner,_,_) in tuple(self.labels.items()):
                if not owner.close():return
                del self.labels[key]
            return
        if time.monotonic()<self.next_poll:return
        self.next_poll=time.monotonic()+.2
        verified=set()
        try:
            self._prepare_metadata()
            c=self._measure('discovery',capture_matching,self.session.pid,classes=('WBP_MM_SaveSlot_C',),
                names=() if getattr(self,'metadata',None) is not None else ('GetListItemObject','Default__UserObjectListEntryLibrary'))
            rows=[o for o in c.objects if o.class_name=='WBP_MM_SaveSlot_C' and not o.object_flags&0x40000030]
            if len(rows)>128:raise RuntimeError('Save list widget population exceeds observation bound')
            current={ident(o) for o in rows}
            for key,(owner,_,_) in tuple(self.labels.items()):
                if key not in current:
                    if not owner.close():return
                    del self.labels[key]
            pending=[]
            for row in rows:
                key=ident(row);binding=self._binding(row,c)
                if binding is None:
                    if not self._retire(key):return
                    verified.add(key);continue
                slot=binding[1];text=self._measure('save label',self._label,slot)
                previous=self.labels.get(key)
                if previous and previous[1:]==(slot,text) and getattr(previous[0],'binding',None)==binding and getattr(previous[0],'verified',False):
                    verified.add(key);continue
                if previous:
                    if not self._retire(key):return
                verified.add(key);pending.append((row,binding,text))
            # Reconcile every existing label before allocating one replacement.
            # Otherwise the build budget leaves later recycled rows mislabeled.
            if pending:
                row,binding,text=pending[0];key=ident(row);slot=binding[1]
                owner=Label(self.session);owner.binding=binding;self.labels[key]=(owner,slot,text)
                def still_bound():
                    return self._binding(row,c)==binding and self._label(slot)==text
                if not self._measure('build',owner.build,row,c,text,still_bound=still_bound):
                    if not self._retire(key):return
        except Exception as error:
            from . import RuntimeQueryError
            if not any(o.unknown for o,_,_ in self.labels.values()):
                for key,(owner,_,_) in tuple(self.labels.items()):
                    # A failed model read leaves its label unproven. A failed
                    # post-attachment check must retire the new label too.
                    if key not in verified or not getattr(owner,'verified',False):
                        if not owner.close():return
                        del self.labels[key]
            if isinstance(error,RuntimeQueryError) and not any(o.unknown for o,_,_ in self.labels.values()):
                if getattr(self,'deferred',None)!=str(error):LOG.warning('Save story label discovery deferred: %s',error)
                self.deferred=str(error)
                return
            self.failed=str(error);LOG.exception('Save story labels suspended; exact owners retained')
    def close(self):
        for key,(owner,_,_) in tuple(self.labels.items()):
            if not owner.close():return False
            del self.labels[key]
        metadata=getattr(self,'metadata',None)
        if metadata is not None:metadata.close()
        self._closed=True;return True

def install(session):
    if getattr(session._transport,'save_list_entry_protocol',0)!=1:return None
    service=getattr(session,'_save_story_ui',None)
    if service is None:
        service=SaveStoryUI(session);session._save_story_ui=service
        from ._metadata_stabilization import process_preparation
        process_preparation(session).scope._reference_owners.append(service)
    return service
