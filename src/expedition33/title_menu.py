"""Owned Mods entry in the exact authored title screen, separate from pause UI."""
import time
from dataclasses import replace
from .pause_menu import PauseMenuEntry
from .catalog import capture_matching,capture_selected
from .values import read_object_reference,read_values_many
from ._reader import ReadBatch
from ._scope import SessionScope
from ._pause_attachment import PauseAttachment
from ._pause_clicks import PauseClicks
from .invocation import prepare_call
from .cinematics.original_game_action import controller_context,NotReady

TITLE_WORLD='/Game/Levels/UI/MainMenu/Level_MainMenu.Level_MainMenu'

def resolve_title(scope):
    """Follow the persistent LocalPlayer's controller, never named templates."""
    with ReadBatch(scope.pid):
        context=controller_context(scope,project=True)
        if context['world_path']!=TITLE_WORLD:return None
        catalog=capture_selected(scope.pid,(context['controller'][1:],));player=catalog.by_index[context['controller'][1]]
        if player.class_name!='BP_jRPG_Controller_MainMenu_C':return None
        def ref(obj,owner,name,expected=None):
            nonlocal catalog
            target,catalog=read_object_reference(catalog,obj,catalog.by_index[catalog.find_class(owner).index],name,project=True)
            if target is None or expected and target.class_name!=expected:raise RuntimeError('Title reference changed: '+name)
            return target
        local=ref(player,'PlayerController','Player','LocalPlayer')
        backlink=ref(local,'Player','PlayerController','BP_jRPG_Controller_MainMenu_C')
        if _identity(backlink)!=_identity(player):raise RuntimeError('Title player backlink changed')
        main=ref(player,'BP_jRPG_Controller_MainMenu_C','MainMenuWidgetReference','WBP_MM_MainMenu_C')
        title=ref(main,'WBP_MM_MainMenu_C','TitleScreen','WBP_MM_TitleScreen_C')
        box=ref(title,'WBP_MM_TitleScreen_C','ButtonsBox','VerticalBox')
        restore_tree=ref(title,'UserWidget','WidgetTree','WidgetTree')
        restore_panel=ref(restore_tree,'WidgetTree','RootWidget','Overlay')
        ancestor=box
        for _ in range(8):
            if _identity(ancestor)==_identity(restore_panel):break
            ancestor_slot=ref(ancestor,'Widget','Slot')
            ancestor=ref(ancestor_slot,'PanelSlot','Parent')
        else:raise RuntimeError('Title button box is outside the verified root Overlay')
        source=ref(title,'WBP_MM_TitleScreen_C','SettingsButton','WBP_BaseButton_C')
        slot=ref(source,'Widget','Slot','VerticalBoxSlot')
        parent=ref(slot,'PanelSlot','Parent','VerticalBox')
        if (parent.index,parent.serial,parent.address)!=(box.index,box.serial,box.address):raise RuntimeError('Title source button parent changed')
        heading=ref(title,'WBP_MM_TitleScreen_C','SettingsText','WBP_HeadingText_C')
        wrapping=ref(heading,'WBP_HeadingText_C','Heading','WBP_WrappingText_C')
        text=ref(wrapping,'WBP_WrappingText_C','Text','CommonTextBlock')
        style=ref(text,'CommonTextBlock','Style','BlueprintGeneratedClass')
        if context!=controller_context(scope,project=True):raise RuntimeError('Title controller changed during discovery')
        return dict(context=context,catalog=catalog,local_player=local,player=player,main=main,title=title,box=box,restore_tree=restore_tree,restore_panel=restore_panel,source_button=source,source_slot=slot,style=style)

def _identity(obj):return obj.index,obj.serial,obj.address

def resolve_title_context(scope,*,local_identity=None):
    """Lean read-only title authority; optional exact LocalPlayer selector.

    Returns context/catalog/local_player/player/main/title/box, or None when
    the fresh chain is not the authored title UI. No settings/style discovery.
    """
    with ReadBatch(scope.pid):
        if local_identity is None:
            catalog=capture_matching(scope.pid,classes=('LocalPlayer',))
            rows=[o for o in catalog.objects if o.class_name=='LocalPlayer' and not o.object_flags&0x30]
            if len(rows)!=1:return None
            local=rows[0]
        else:
            catalog=capture_selected(scope.pid,(local_identity,));local=catalog.by_index[local_identity[0]]
        def ref(obj,owner,name):
            nonlocal catalog
            value,catalog=read_object_reference(catalog,obj,catalog.by_index[catalog.find_class(owner).index],name,project=True)
            return value
        player=ref(local,'Player','PlayerController')
        if player is None or player.class_name!='BP_jRPG_Controller_MainMenu_C':return None
        back=ref(player,'PlayerController','Player')
        if back is None or _identity(back)!=_identity(local):return None
        worlds=[o for o in catalog.outer_chain(player) if o.class_name=='World']
        if len(worlds)!=1 or catalog.path_name(worlds[0])!=TITLE_WORLD:return None
        context=dict(controller=(scope.pid,*_identity(player)),world=(scope.pid,*_identity(worlds[0])),world_path=TITLE_WORLD)
        main=ref(player,'BP_jRPG_Controller_MainMenu_C','MainMenuWidgetReference')
        if main is None or main.class_name!='WBP_MM_MainMenu_C':return None
        title=ref(main,'WBP_MM_MainMenu_C','TitleScreen')
        if title is None or title.class_name!='WBP_MM_TitleScreen_C':return None
        box=ref(title,'WBP_MM_TitleScreen_C','ButtonsBox')
        if box is None or box.class_name!='VerticalBox':return None
        return dict(context=context,catalog=catalog,local_player=local,player=player,main=main,title=title,box=box)

def title_authority_current(scope,binding,*,restore_tree=None,restore_panel=None):
    """Two bounded reads: selected identity closure + projected link batch.

    All target identities are old selectors, never trusted values. The reader
    validates every selector freshly; a changed/unreadable link grants no UI
    authority and never dispatches a mutation or substitutes another world.
    """
    context,local_id,main_id,title_id,box_id=binding
    player_id=context['controller'][1:];world_id=context['world'][1:]
    with ReadBatch(scope.pid):
        selected=(local_id,player_id,main_id,title_id,box_id,world_id)
        if restore_tree is not None and restore_panel is not None:selected+=(_identity(restore_tree),_identity(restore_panel))
        catalog=capture_selected(scope.pid,selected)
        local,player,main,title,box,world=(catalog.by_index[key[0]] for key in (local_id,player_id,main_id,title_id,box_id,world_id))
        if local.class_name!='LocalPlayer' or player.class_name!='BP_jRPG_Controller_MainMenu_C' or main.class_name!='WBP_MM_MainMenu_C' or title.class_name!='WBP_MM_TitleScreen_C' or box.class_name!='VerticalBox' or world.class_name!='World' or catalog.path_name(world)!=TITLE_WORLD:return False
        if any(getattr(obj,'object_flags',0)&0x30 for obj in (local,player,main,title,box,world)):return False
        worlds=[o for o in catalog.outer_chain(player) if o.class_name=='World']
        if len(worlds)!=1 or _identity(worlds[0])!=world_id:return False
        objects=(local,player,main,title);fields=('PlayerController','Player','MainMenuWidgetReference','TitleScreen','ButtonsBox')
        if restore_tree is not None and restore_panel is not None:
            tree=catalog.by_index[restore_tree.index];panel=catalog.by_index[restore_panel.index]
            if tree.class_name!='WidgetTree' or panel.class_name!='Overlay':return False
            objects+=(tree,);fields+=('WidgetTree','RootWidget')
        observed=read_values_many(catalog,objects,fields=fields)
        def link(obj,name,expected):
            value=observed[obj.index];keys=[key for key in value.types if key[1]==name]
            if len(keys)!=1 or value.types[keys[0]]!='ObjectProperty':
                raise RuntimeError('Title authority link schema unavailable: '+name)
            if keys[0] in value.errors or keys[0] in value.truncated or keys[0] not in value.values:
                raise NotReady('Title authority link unavailable: '+name)
            target=value.values[keys[0]]
            return target is not None and _identity(target)==expected
        if restore_tree is not None and restore_panel is not None and not (link(title,'WidgetTree',_identity(restore_tree)) and link(tree,'RootWidget',_identity(restore_panel))):return False
        return link(local,'PlayerController',player_id) and link(player,'Player',local_id) and link(player,'MainMenuWidgetReference',main_id) and link(main,'TitleScreen',title_id) and link(title,'ButtonsBox',box_id)

class TitleMenuEntry(PauseMenuEntry):
    def __init__(self,scope,service,*,readiness):
        if not callable(readiness):raise TypeError('Title readiness callback required')
        super().__init__(scope,service,label='Mods',readiness=readiness)
        self._title_binding=None
        self._title_restore_pending=False
        self._title_restore_unknown=False
        self._title_restore_disposition=None
    def _update_readiness(self):pass # The authored title entry always reads Mods.
    def install(self):
        if self.state!='new' or self._readiness() is not True or not self.available:return False
        with ReadBatch(self.parent_scope.pid,share=True):
            found=resolve_title(self.parent_scope)
            if found is None:return False
            names=('WBP_BaseButton_C','CommonButtonBase','CommonActivatableWidget','CommonTextBlock','TextBlock','TextLayoutWidget','Widget','UserWidget','WidgetTree','VerticalBox','VerticalBoxSlot','PanelSlot','ContentWidget','WidgetBlueprintLibrary','GameplayStatics','Default__WidgetBlueprintLibrary','Default__GameplayStatics','Create','SpawnObject','SetContent','AddChildToVerticalBox','SetPadding','SetHorizontalAlignment','SetVerticalAlignment','SetText','SetStyle','SetJustification','SetMinDimensions','SetIsSelectable','SetIsToggleable','SetFocusToGameViewport','SetUserFocus','IsActivated','RemoveFromParent','HandleButtonClicked','Overlay','OverlaySlot','AddChildToOverlay','GetRenderOpacity','SetRenderOpacity','GetIsEnabled','SetIsEnabled','Margin','EHorizontalAlignment','EVerticalAlignment','ETextJustify','SetInputMode_UIOnlyEx','EMouseLockMode')
            from ._metadata_stabilization import available,prepare_discovery
            if available(getattr(self.parent_scope._session,'_transport',None)):
                latest=[]
                def discover_metadata():
                    refreshed=resolve_title(self.parent_scope)
                    if refreshed is None:raise RuntimeError('Title changed during metadata preparation')
                    latest[:]=[refreshed]
                    return refreshed['catalog'].with_observations(capture_matching(self.parent_scope.pid,names=names))
                catalog,uncovered=prepare_discovery(self.parent_scope._session,discover_metadata)
                self.metadata_uncovered_count=len(uncovered);self._metadata_stable_ui=True
                found=latest[0]
            else:catalog=found['catalog'].with_observations(capture_matching(self.parent_scope.pid,names=names))
            self.restore_tree=found['restore_tree'];self.restore_panel=found['restore_panel']
            self.player=found['player'];self.pause=found['title'];self.grid=found['box'];self._title_binding=(found['context'],_identity(found['local_player']),_identity(found['main']),_identity(found['title']),_identity(found['box']))
            self.scope=SessionScope(self.parent_scope);self.state='building'
            self.planner=self.scope.invocation_planner(selected_results=True,catalog=catalog)
            self.planner._require_stable_ui_identities=getattr(self,'_metadata_stable_ui',False)
            stable_targets=self._prepare_borrowed_title_targets()
            catalog=self.planner._catalog
            self.library=self.one(o for o in catalog.objects if o.name=='Default__WidgetBlueprintLibrary')
            gameplay=self.one(o for o in catalog.objects if o.name=='Default__GameplayStatics')
            dimensions=read_values_many(catalog,(found['source_button'],),fields=('MinWidth','MinHeight'))[found['source_button'].index].values
            padding=read_values_many(catalog,(found['source_slot'],),fields=('Padding',))[found['source_slot'].index].values
            self.button=self.create(self.library,'WidgetBlueprintLibrary','Create',WorldContextObject=self.player,WidgetType=self.cls('WBP_BaseButton_C'),OwningPlayer=self.player)
            self.attachment=PauseAttachment(self.scope)
            lease=self.one(l for l in self.scope._leases if l.active and l.object==self.button)
            self.attachment.arm(lease,prepare_call(self.planner._catalog,self.button,self.fn('Widget','RemoveFromParent'),{}))
            tree=self.reference(self.button,'UserWidget','WidgetTree');content=self.reference(self.button,'WBP_BaseButton_C','ButtonContent')
            label=self.create(gameplay,'GameplayStatics','SpawnObject',ObjectClass=self.cls('CommonTextBlock'),Outer=tree)
            self.layout(label,'CommonTextBlock','SetStyle',InStyle=found['style']);self.layout(label,'TextBlock','SetText',InText='Mods');self.layout(label,'TextLayoutWidget','SetJustification',InJustification=1)
            frame=self.create(gameplay,'GameplayStatics','SpawnObject',ObjectClass=self.cls('Overlay'),Outer=tree)
            label_slot=self.create(frame,'Overlay','AddChildToOverlay',Content=label)
            self.layout(label_slot,'OverlaySlot','SetHorizontalAlignment',InHorizontalAlignment=2);self.layout(label_slot,'OverlaySlot','SetVerticalAlignment',InVerticalAlignment=2)
            self.call(content,'ContentWidget','SetContent',Content=frame)
            self.layout(self.button,'CommonButtonBase','SetMinDimensions',InMinWidth=dimensions[self.cls('CommonButtonBase').index,'MinWidth'],InMinHeight=dimensions[self.cls('CommonButtonBase').index,'MinHeight'])
            self.layout(self.button,'CommonButtonBase','SetIsSelectable',bInIsSelectable=False);self.layout(self.button,'CommonButtonBase','SetIsToggleable',bInIsToggleable=False)
            retained=stable_targets.get(self.restore_panel.index)
            if retained is None:retained=self.scope.retain(self.restore_panel)
            opacity=self.call(self.restore_panel,'Widget','GetRenderOpacity');enabled=self.call(self.restore_panel,'Widget','GetIsEnabled')
            def simple(name,**args):return replace(self.planner.prepare(self.restore_panel,self.fn('Widget',name),**args)._plan,wire_version=1)
            self.attachment.arm_restore(retained,simple('SetRenderOpacity',InOpacity=opacity),simple('SetIsEnabled',bInIsEnabled=enabled))
            self._hide_opacity=simple('SetRenderOpacity',InOpacity=0.);self._hide_enabled=simple('SetIsEnabled',bInIsEnabled=False)
            self.observer=PauseClicks(self.scope._session,self.fn('CommonButtonBase','HandleButtonClicked'),self.button,self.planner._catalog)
            self.flush_layout()
            if not self._current_title():raise RuntimeError('Title changed before borrowed container attachment')
            slot=self.create(self.grid,'VerticalBox','AddChildToVerticalBox',Content=self.button)
            self.call(slot,'VerticalBoxSlot','SetPadding',InPadding=dict(padding[self.cls('VerticalBoxSlot').index,'Padding'].fields))
            self.call(slot,'VerticalBoxSlot','SetHorizontalAlignment',InHorizontalAlignment=0);self.call(slot,'VerticalBoxSlot','SetVerticalAlignment',InVerticalAlignment=0)
            self._active_call=self.planner.prepare(self.pause,self.fn('CommonActivatableWidget','IsActivated'))
            self._viewport_focus=self.planner.prepare(self.library,self.fn('WidgetBlueprintLibrary','SetFocusToGameViewport'))
            self._button_focus=self.planner.prepare(self.button,self.fn('Widget','SetUserFocus'),PlayerController=self.player)
            self._loading_label=self._cleanup_label=self._normal_label=self.planner.prepare(label,self.fn('TextBlock','SetText'),InText='Mods')
            self._title_input=self._prepare_title_input()
            self._label_widget=label;self.state='attached'
        return True
    def _prepare_borrowed_title_targets(self):
        leases=self.stabilize_borrowed_targets((self.pause,self.grid,self.restore_panel))
        if leases:
            catalog=self.planner._catalog
            self.pause=catalog.by_index[self.pause.index];self.grid=catalog.by_index[self.grid.index]
            self.restore_tree=catalog.by_index[self.restore_tree.index]
            self.restore_panel=catalog.by_index[self.restore_panel.index]
            context,local_id,main_id,_,_=self._title_binding
            self._title_binding=(context,local_id,main_id,_identity(self.pause),_identity(self.grid))
            if not self._current_title():raise RuntimeError('Title authority changed during target preparation')
        return leases

    def _prepare_title_input(self):
        # Typed reflected enum plan: no integer guess and no input mutation now.
        if getattr(self.parent_scope._session._transport,'menu_input_protocol',0)!=1:
            raise RuntimeError('Title input restoration requires the verified menu input protocol')
        from .enums import describe_enums
        enum=self.one(o for o in self.planner._catalog.objects if o.class_name=='Enum' and o.name=='EMouseLockMode')
        mode=describe_enums(self.planner._catalog,(enum,))[enum.index].value('EMouseLockMode::DoNotLock')
        return self.planner.prepare(self.library,self.fn('WidgetBlueprintLibrary','SetInputMode_UIOnlyEx'),
            PlayerController=self.player,InWidgetToFocus=self.button,InMouseLockMode=mode,bFlushInput=False)

    def _open_from_pause(self):
        self._title_restore_pending=True
        self._title_restore_disposition='pending'
        return super()._open_from_pause()

    def _sdk_hidden_acknowledged(self):
        if getattr(self.service,'_failure',None):return False
        menu=self.service.menu
        if menu is None:return True # Service clears only after acknowledged close.
        panel=menu.panel
        return panel.state in ('built','closed') and getattr(panel,'menu',None) is None and not panel.uncertain and not getattr(menu,'failure',None)

    def restore_title_input_after_menu_close(self):
        """Restore title UIOnly only after SDK detach ACK and fresh title proof.

        A different current title authority retires this pending presentation;
        it never redirects input to another controller. Unknown calls retain
        the journal and are never replayed. Host calls before entry scope close.
        """
        if self._title_restore_unknown:raise RuntimeError('Title input restoration unknown; retain owner without replay')
        if not self._title_restore_pending:return True
        if not self._sdk_hidden_acknowledged():return False
        if not self._current_title():
            self._title_restore_pending=False;self._return_focus=False
            self._title_restore_disposition='context_retired'
            return True
        if not self.invoke(self._active_call):raise RuntimeError('Title is not active; input restoration pending')
        if not self.attachment.restore():raise RuntimeError('Title Overlay restoration deferred; retain owner')
        try:
            self.invoke(self._title_input)
            self.invoke(self._button_focus)
        except BaseException:
            self._title_restore_unknown=True
            raise
        self._title_restore_pending=False;self._return_focus=False
        self._title_restore_disposition='restored'
        return True

    def close(self):
        try:
            if self._title_restore_pending or self._title_restore_unknown:
                if not self.restore_title_input_after_menu_close():
                    raise RuntimeError('SDK menu hide not acknowledged; retain title presentation owner')
        except NotReady:
            raise RuntimeError('Title entry detach deferred; retain its owner') from None
        return super().close()

    def _current_title(self):
        return self._timed('title_authority_current',title_authority_current,self.parent_scope,self._title_binding,restore_tree=self.restore_tree,restore_panel=self.restore_panel)
    def open(self):
        if self._readiness() is not True or not self._current_title():raise RuntimeError('Title context changed; Mods open deferred')
        return super().open()
    def poll(self):
        try:return self._poll_title()
        except NotReady:return # Unreadable authority retains owners and suppresses input callbacks.
    def _poll_title(self):
        ready=self._readiness()
        if ready is None:return
        if type(ready) is not bool:raise TypeError('Title readiness must return bool or None')
        if not ready:
            if self.state not in ('new','closed'):self.close()
            return
        if self.state=='new':self.install();return
        if self.state!='attached':return
        if time.monotonic()<self._next_poll:return
        self._next_poll=time.monotonic()+.02
        if time.monotonic()>=self._next_world_check:
            self._next_world_check=time.monotonic()+.25
            with self._world_read_operation():
                if not self._current_title():self.close();return
        for event in self.observer.read():
            if self._readiness() is True and self._current_title() and self.invoke(self._active_call):self._open_from_pause()
        menu=self.service.menu
        if self._return_focus and (menu is None or menu.panel.state!='open'):
            self.restore_title_input_after_menu_close()
