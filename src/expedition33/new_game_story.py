"""Process-owned story choice in the native new-game options, before playback."""
import time
from .pause_menu import PauseMenuEntry
from ._scope import SessionScope
from ._reader import shared_operation
from ._pause_clicks import PauseClicks
from ._story_navigation import direction_events

_OPTION_ENTRY='/Game/UI/Widgets/InGame_Menu/Settings/WBP_Settings_OptionEntry.WBP_Settings_OptionEntry_C'
_BUTTON_CLASS='/Script/SFUIComponents.SFUIButtonBase'
_SELECTOR_CLASS='/Game/UI/Widgets/InGame_Menu/Settings/Selectors/WBP_SliderSelector.WBP_SliderSelector_C'
_DIRECTION_CALLBACK='/Script/SFUIComponents.SFUIValueSelectorWidget:OnConstrainedNavigationTriggered'


class Choice:
    """An Apply receipt arms one choice; existing saves never consume it."""
    def __init__(self):
        self.options=[(None,'Original game')];self.index=0;self.pending=None
        self.descriptions={None:'Play the original Clair Obscur: Expedition 33 story.\n\nChoose a story before pressing Apply. This choice belongs to the new save and does not change your other saves.'}
    def register(self,key,label,description=None):
        if type(key) is not str or not key or type(label) is not str or not label:raise ValueError('Story identity and label required')
        if key not in [k for k,_ in self.options]:self.options.append((key,label))
        self.descriptions[key]=description or ('Play '+label+' for this new save.')
    def events(self,events,slot):
        for _,kind in sorted(events,key=lambda row:row[0]):
            if kind in ('cycle','next'):self.index=(self.index+1)%len(self.options)
            elif kind=='previous':self.index=(self.index-1)%len(self.options)
            elif kind=='apply':self.pending=(slot,self.options[self.index][0])
            else:raise ValueError('Unknown story selection event')
    def consume(self,slot,*,fresh):
        pending=self.pending
        if pending is None:return None
        self.pending=None
        if not fresh or pending[0]!=slot:return None
        return {'pack':pending[1]}
    @property
    def name(self):return self.options[self.index][1]
    @property
    def label(self):return 'Story: '+self.name
    @property
    def description(self):return self.descriptions[self.options[self.index][0]]

def _current_button_metadata(source,current):
    """Resolve original metadata by qualified path, never reuse UI-era stamps."""
    cached=source['catalog'];metadata=[]
    for obj in cached.objects:
        if obj.class_name not in ('Class','Function','ScriptStruct','Enum','BlueprintGeneratedClass','WidgetBlueprintGeneratedClass') and not obj.name.startswith('Default__'):continue
        fresh=current.find_path(cached.path_name(obj))
        if fresh.class_name!=obj.class_name:raise RuntimeError('Story button metadata type changed')
        metadata.append(fresh)
    style=current.find_path(cached.path_name(source['style']))
    if style.class_name!=source['style'].class_name:raise RuntimeError('Story button style type changed')
    return metadata,dict(source,catalog=current,style=style)


class StoryRow(PauseMenuEntry):
    def build(self,session):
        from .catalog import capture_matching,capture_selected
        from .values import read_values_with_references
        from .title_menu import resolve_title_context,_identity
        started=time.perf_counter()
        found=resolve_title_context(self.parent_scope)
        if found is None:return False
        if getattr(session._transport,'new_game_story_start_protocol',0)!=1:
            raise RuntimeError('New-game story selection requires native runtime 289 or newer')
        native_direction=getattr(session._transport,'new_game_story_direction_protocol',0)==1
        source=getattr(session,'_pause_button_source',None)
        from .pause_preparation import NAMES,prepare,capture_metadata
        if source is None:prepare(session)
        cached_names=tuple(o.name for o in source['catalog'].objects
            if o.class_name in ('Class','Function','ScriptStruct','Enum','BlueprintGeneratedClass','WidgetBlueprintGeneratedClass') or o.name.startswith('Default__')) if source else ()
        direction_names=('WBP_Settings_OptionEntry_C','OnConstrainedNavigationTriggered','SFUIButtonBase','SFUIValueSelectorWidget',
                         'SetIsNavigationConstrained','SetConstrainOrientation','SetIsFocusable',
                         'EUINavigation','EOrientation','WBP_SliderSelector_C',
                         'SizeBox','SetWidthOverride','SetVisibility','ESlateVisibility') if native_direction else ()
        names=tuple(dict.fromkeys(NAMES+cached_names+('AddChild','IsHovered','HasAnyUserFocus',
            'HasFocusedDescendants','OnStartGameSettingsApplied','CTS_B1_SmallLine_Outline_C')+direction_names))
        # Loaded gameplay leaves many matching metadata names resident.
        # Bound each discovery request instead of exhausting the query limit.
        c=found['catalog'].with_observations(capture_matching(session.pid,
            classes=('WBP_Settings_StartGameOptionsList_C','BP_SaveManager_C')))
        for start in range(0,len(names),8):
            c=c.with_observations(capture_matching(session.pid,names=names[start:start+8]))
        full=c;main=found['main'];self.player=found['player']
        def owned(obj):return any(x.index==main.index for x in c.outer_chain(obj))
        lists=[o for o in c.objects if o.class_name=='WBP_Settings_StartGameOptionsList_C' and not o.object_flags&48 and owned(o)]
        if not lists:return False
        options=self.one(lists)
        values,c=read_values_with_references(c,options,fields=('ScrollBox',))
        scroll=self.one(v for k,v in values.values.items() if k[1]=='ScrollBox')
        if scroll is None or scroll.class_name!='ScrollBox':raise RuntimeError('Native start-options list changed')
        if source is None:
            # A story selector must not wait for the optional Mods frontend to
            # finish constructing its entire editor tree or title entry.
            base=capture_metadata(session)
            if base is None:return False
            button=full.by_index[full.find_class('WBP_BaseButton_C').index]
            style=full.find_path('/Game/UI/Resources/Styles/Text/Body/Outline/CTS_B1_SmallLine_Outline.CTS_B1_SmallLine_Outline_C')
            base=base.with_observations(full.subset((button,style)))
            source=dict(catalog=base,style=style)
        # Keep metadata and the exact borrowed controls, not every transient UI
        # object in a full catalogue. Owned-tree stabilization refreshes this
        # closure; unrelated animated widgets can legitimately disappear.
        page=self.one(o for o in c.outer_chain(options) if o.class_name=='WBP_Settings_StartGameOptions_C')
        manager=self.one(o for o in c.objects if o.class_name=='BP_SaveManager_C' and not o.object_flags&48)
        metadata,source=_current_button_metadata(source,full)
        extras=[c.find_path('/Script/UMG.'+path) for path in ('PanelWidget:AddChild','Widget:IsHovered',
            'Widget:HasAnyUserFocus','Widget:HasFocusedDescendants')]
        direction_metadata=[]
        if native_direction:
            extras.extend(c.find_path(path) for path in ('/Script/CommonUI.CommonButtonBase:SetIsFocusable',
                '/Script/UMG.SizeBox:SetWidthOverride','/Script/UMG.Widget:SetVisibility'))
            direction_metadata=[c.find_path(path) for path in (_OPTION_ENTRY,
                _DIRECTION_CALLBACK,_BUTTON_CLASS,
                _BUTTON_CLASS+':SetIsNavigationConstrained',_BUTTON_CLASS+':SetConstrainOrientation',
                '/Script/SlateCore.EUINavigation','/Script/SlateCore.EOrientation',_SELECTOR_CLASS,
                '/Script/UMG.ESlateVisibility')]
        chosen=metadata+[main,self.player,options,scroll,manager,page]+extras+direction_metadata
        c=capture_selected(session.pid,tuple({(o.index,o.serial,o.address) for o in chosen}))
        from ._metadata_stabilization import process_preparation
        from ._stable_lease import fresh_catalog_replacing
        stable=process_preparation(session).prepare(c,extras)
        c=fresh_catalog_replacing(c,stable.objects)
        self.scope=SessionScope(self.parent_scope)
        # The observer outlives title visibility. Retain exact identities before
        # registering its filter; a zero-serial discovery cannot be that filter.
        from ._stable_lease import acquire_stable
        function=full.find_path('/Game/UI/Widgets/MainMenu/WBP_MM_MainMenu.WBP_MM_MainMenu_C:OnStartGameSettingsApplied')
        held_main,_=acquire_stable(self.scope,main)
        held_function,_=acquire_stable(self.scope,function)
        full=capture_selected(session.pid,tuple((o.index,o.serial,o.address)
            for o in (held_main.object,held_function.object)))
        main=full.by_index[held_main.object.index];function=full.by_index[held_function.object.index]
        self._story_main=main
        from . import _traces
        self.apply_trace=_traces.start(session,function,main,target=main,duration_ms=300000,limit=100,catalog=full)
        self.scope._traces.append(self.apply_trace)
        retained=[]
        for obj in direction_metadata:
            if obj.class_name=='Function':
                owner,_=acquire_stable(self.scope,obj)
                retained.append(owner.object)
        c=fresh_catalog_replacing(c,(main,function,*retained))
        self.planner=self.scope.invocation_planner(catalog=c,selected_results=True)
        self.library=c.find_path('/Script/UMG.Default__WidgetBlueprintLibrary')
        gameplay=c.find_path('/Script/Engine.Default__GameplayStatics')
        self._direction_receiver=None;self.direction_trace=None
        self._value_widget=None;self._arrow_clicks=[]
        if native_direction:
            attachment=self.build_option_entry(session,gameplay,source['style'])
        else:
            self._build_button(gameplay,source['style'],(790,52))
            self.flush_layout()
            attachment=self.button
        self.observer=PauseClicks(session,self.fn('CommonButtonBase','HandleButtonClicked'),self.button,self.planner._catalog)
        if native_direction:
            for direction,arrow in zip(('previous','next'),self._arrows):
                self._arrow_clicks.append((direction,PauseClicks(session,self.observer.function,arrow,self.planner._catalog)))
        self.manager=self.one(o for o in c.objects if o.class_name=='BP_SaveManager_C' and not o.object_flags&48)
        self.manager=self.scope.retain(self.manager).object
        self.prepare_tooltip(page)
        if native_direction:
            # Native game settings constrain just the horizontal axis. Up and
            # down still follow the surrounding options list.
            self.call(self.button,'SFUIButtonBase','SetConstrainOrientation',InConstrainOrientation=0)
            self.call(self.button,'SFUIButtonBase','SetIsNavigationConstrained',bInIsNavigationConstrained=True)
            self.call(self.button,'CommonButtonBase','SetIsFocusable',bInIsFocusable=True)
        self.create(scroll,'PanelWidget','AddChild',Content=attachment)
        if native_direction:
            self.call(self._label_widget,'TextBlock','SetText',InText='Story')
        self.state='attached'
        self.timings['build_ms']=(time.perf_counter()-started)*1000
        import logging
        logging.getLogger(__name__).info('New-game story selector attached (%.1f ms)',self.timings['build_ms'])
        return True
    def build_option_entry(self,session,gameplay,style):
        from . import _traces
        entry=self.create(self.library,'WidgetBlueprintLibrary','Create',WorldContextObject=self.player,
                          WidgetType=self.cls('WBP_Settings_OptionEntry_C'),OwningPlayer=self.player)
        self.button=self.reference(entry,'WBP_Settings_OptionEntry_C','BaseButton')
        label=self.reference(entry,'WBP_Settings_OptionEntry_C','TextBlock_OptionName')
        slot=self.reference(entry,'WBP_Settings_OptionEntry_C','NamedSlot_WidgetSelector')
        self._label_widget=self.reference(label,'WBP_WrappingText_C','Text')
        if self.button is None or self._label_widget is None or slot is None:raise RuntimeError('Story option controls are unavailable')
        self.stabilize_borrowed_targets((self.button,self._label_widget,slot))
        c=self.planner._catalog
        # The option subscribes to constrained navigation only with a native
        # value-selector child in its named slot during widget construction.
        selector=self.create(self.library,'WidgetBlueprintLibrary','Create',WorldContextObject=self.player,
                             WidgetType=self.cls('WBP_SliderSelector_C'),OwningPlayer=self.player)
        self.call(c.by_index[slot.index],'ContentWidget','SetContent',Content=selector)
        self.layout_story_value(selector,gameplay,style)
        c=self.planner._catalog
        self.button=c.by_index[self.button.index]
        self._label_widget=c.by_index[self._label_widget.index]
        self._option_entry=c.by_index[entry.index]
        self._direction_receiver=c.by_index[selector.index]
        function=c.find_path(_DIRECTION_CALLBACK)
        self.direction_trace=_traces.start(session,function,self._direction_receiver,
            target=self._direction_receiver,duration_ms=300000,limit=1000,catalog=c)
        self.scope._traces.append(self.direction_trace)
        return self._option_entry

    def layout_story_value(self,selector,gameplay,style):
        from .enums import describe_enums
        owner='WBP_SliderSelector_C'
        slider=self.reference(selector,owner,'Slider')
        slider_slot=self.reference(slider,'Widget','Slot')
        box=self.reference(slider_slot,'PanelSlot','Parent')
        percentage=self.reference(selector,owner,'SizeBox_Value')
        arrows=tuple(self.reference(selector,owner,'WBP_ArrowButton_'+name) for name in ('Downgrade','Upgrade'))
        if box.class_name!='SizeBox' or any(arrow is None for arrow in arrows):
            raise RuntimeError('Native Story arrow layout changed')
        self.stabilize_borrowed_targets((box,percentage,*arrows))
        tree=self.reference(selector,'UserWidget','WidgetTree')
        self._value_widget=self.create(gameplay,'GameplayStatics','SpawnObject',
            ObjectClass=self.cls('CommonTextBlock'),Outer=tree)
        c=self.planner._catalog
        box=c.by_index[box.index];percentage=c.by_index[percentage.index]
        self._arrows=tuple(c.by_index[arrow.index] for arrow in arrows)
        visibility=c.find_path('/Script/UMG.ESlateVisibility')
        collapsed=describe_enums(c,(visibility,))[visibility.index].value('ESlateVisibility::Collapsed')
        self.call(percentage,'Widget','SetVisibility',InVisibility=collapsed)
        self.call(box,'SizeBox','SetWidthOverride',InWidthOverride=424.)
        self.call(self._value_widget,'CommonTextBlock','SetStyle',InStyle=style)
        self.call(self._value_widget,'TextLayoutWidget','SetJustification',InJustification=1)
        self.call(box,'ContentWidget','SetContent',Content=self._value_widget)

    def show_choice(self,choice):
        if self._value_widget is None:
            self.call(self._label_widget,'TextBlock','SetText',InText=choice.label)
        else:
            self.call(self._value_widget,'TextBlock','SetText',InText=choice.name)

    def has_story_focus(self):
        return (self.call(self.button,'Widget','HasAnyUserFocus') or
                self.call(self.button,'Widget','HasFocusedDescendants'))

    def prepare_tooltip(self,page):
        from .values import read_values_with_references
        def ref(obj,name):
            values,c=read_values_with_references(self.planner._catalog,obj,fields=(name,))
            self.planner.adopt_observations(c)
            return self.one(v for k,v in values.values.items() if k[1]==name)
        tip=ref(page,'WBP_Settings_OptionTooltip')
        self.tip_name=ref(ref(tip,'OptionName'),'Text')
        self.tip_description=ref(ref(tip,'OptionDescription'),'Text')
        self.stabilize_borrowed_targets((self.tip_name,self.tip_description))
        self.tip_name=self.planner._catalog.by_index[self.tip_name.index]
        self.tip_description=self.planner._catalog.by_index[self.tip_description.index]
        self._tip_hover=self._tip_focus=False
    def tooltip(self,choice,*,changed=False):
        hovered=self.call(self.button,'Widget','IsHovered')
        focused=self._navigation_focus
        show=(hovered and not self._tip_hover) or (focused and not self._tip_focus) or (changed and (hovered or focused))
        self._tip_hover,self._tip_focus=hovered,focused
        if show:
            self.call(self.tip_name,'TextBlock','SetText',InText=choice.label)
            hint='\n\nUse Left / Right to change story.' if self._direction_receiver is not None else ''
            self.call(self.tip_description,'TextBlock','SetText',InText=choice.description+hint)
    def slot(self):
        from .values import capture_selected_values
        o=self.manager
        _,values=capture_selected_values(o.pid,((o.index,o.serial,o.address),),fields=('SelectedSlot',))
        value=values[o.index]
        if value.errors:raise RuntimeError('New-game save slot is unavailable')
        return self.one(v for k,v in value.values.items() if k[1]=='SelectedSlot')
    def drain(self,*,navigate=False):
        events=[(e.monotonic_ms,'cycle') for e in self.observer.read()]
        for direction,clicks in self._arrow_clicks:
            events.extend((event.monotonic_ms,direction) for event in clicks.read(poll=False))
        if self.direction_trace is not None:
            events.extend(direction_events(self.direction_trace.read()))
            if self.direction_trace.state=='active' and time.monotonic()>=getattr(self,'_direction_renew',0.):
                self.direction_trace.renew();self._direction_renew=time.monotonic()+120
        events.extend((e.monotonic_ms,'apply') for e in self.apply_trace.read())
        if navigate:
            self._navigation_focus=self.has_story_focus()
        if self.apply_trace.state=='active' and time.monotonic()>=getattr(self,'_apply_renew',0.):
            self.apply_trace.renew();self._apply_renew=time.monotonic()+120
        return events
    def close(self):
        if self.state=='attached' and getattr(self,'_direction_receiver',None) is not None:
            self.call(self._option_entry,'Widget','RemoveFromParent')
        trace=getattr(self,'apply_trace',None)
        if trace is not None:trace.close();self.apply_trace=None
        for _,clicks in getattr(self,'_arrow_clicks',()):clicks.close()
        self._arrow_clicks=[]
        return super().close()


class NewGameStories:
    def __init__(self,session,parent):
        self.session=session;self.parent=parent;self.choice=Choice();self.row=None
        self.error=None;self.closed=False;self._cinematic_binding=None;self.next_poll=0.;self._original=session.poll
        def poll(*args,**kwargs):
            self.poll();return self._original(*args,**kwargs)
        self._wrapper=poll;session.poll=poll;parent._reference_owners.append(self)
    @property
    def state(self):return 'closed' if self.closed else 'unknown' if self.error else 'active'
    def register(self,key,label,description=None):self.choice.register(key,label,description)
    def bind_cinematics(self,story_id,router):
        """Bind the process's cinematic route owner to one consumer's story.

        The native router currently admits one owner per process. Rebinding a
        live owner to another story is rejected; closure permits replacement.
        Registration may precede title-menu option creation.
        """
        if type(story_id) is not str or not story_id:raise ValueError('Story ID is required')
        if self.closed or router.closed or router._scope._session is not self.session:
            raise ValueError('Cinematic routes require the same active session')
        binding=getattr(self,'_cinematic_binding',None)
        if binding is not None and not binding[1].closed and binding!=(story_id,router):
            raise RuntimeError('Another story owns cinematic routing in this process')
        self._cinematic_binding=(story_id,router)
    def _bind_cinematic_menu(self):
        binding=getattr(self,'_cinematic_binding',None)
        if binding is not None and not binding[1].closed and binding[0] in dict(self.choice.options):
            binding[1].bind_menu(self.row,self.choice,binding[0])
    def _context(self):
        router=self.session._process_ui
        return router.observed_context if hasattr(router,'observed_context') else getattr(router,'context',None)
    def poll(self):
        if self.closed or self.error or time.monotonic()<self.next_poll:return
        self.next_poll=time.monotonic()+.2
        context=self._context()
        if (context is None or context.kind!='title') and self.row is None:return
        try:
            with shared_operation(self.session.pid):
                context=self._context()
                if self.row is None:
                    if context is None or context.kind!='title':return
                    self.row=StoryRow(self.parent,None,label='Story')
                    if not self.row.build(self.session):self.row=None;return
                    self.row.show_choice(self.choice)
                if context is None or context.kind!='title':
                    events=self.row.drain()
                    if events:self.choice.events(events,self.row.slot())
                    self.row.close();self.row=None;return
                events=self.row.drain(navigate=True)
                if events:
                    self.choice.events(events,self.row.slot())
                    self.row.show_choice(self.choice)
                self._bind_cinematic_menu()
                self.row.tooltip(self.choice,changed=bool(events))
                if context is not None and context.kind=='world':
                    self.row.close();self.row=None
        except Exception as error:
            self.error=str(error)
            import logging
            logging.getLogger(__name__).exception('New-game story row stopped; owners retained')
    def consume(self,live):
        # Poll copied Apply/click receipts before considering the admitted save.
        self.poll()
        if self.error or not live.resolved or self.choice.pending is None:return False
        from .story_save_identity import observe
        from .values import read_values_with_references
        from .catalog import capture_selected
        _,_,_,_,gi,_=observe(live.identity.scope)
        c=capture_selected(self.session.pid,((gi.index,gi.serial,gi.address),))
        values,c=read_values_with_references(c,gi,fields=('SaveManager',))
        manager=next(v for k,v in values.values.items() if k[1]=='SaveManager')
        values,c=read_values_with_references(c,manager,fields=('SelectedSlot',))
        slot=next(v for k,v in values.values.items() if k[1]=='SelectedSlot')
        selected=self.choice.consume(slot,fresh=live.candidate is not None and live.identity.read() is None)
        if selected is None:return False
        request=live.choices()
        if request is None:raise RuntimeError('New-game choice has no admitted story request')
        live.choose(request,selected['pack'])
        binding=getattr(self,'_cinematic_binding',None)
        if binding is not None and selected['pack']==binding[0] and not binding[1].closed:
            binding[1].allow(live.playthroughs.key)
        return True
    def close(self):
        if self.closed:return True
        if self.row is not None:self.row.close();self.row=None
        if self.session.poll is self._wrapper:self.session.poll=self._original
        self.closed=True;return True


def install(session):
    existing=getattr(session,'_new_game_stories',None)
    if existing is not None and not existing.closed:return existing
    from ._metadata_stabilization import process_preparation
    service=NewGameStories(session,process_preparation(session).scope)
    session._new_game_stories=service;return service
