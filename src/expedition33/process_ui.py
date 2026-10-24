"""Prototype process-owned UI shell with separate context entry owners.

This router NEVER enables/disables/polls gameplay mods. A host must still make
its independent gameplay lifecycle decision. In particular this does not fix
legacy world-mod retirement or the host's runtime_polling_started latch.
"""
import threading
from contextlib import contextmanager
from .ui_shell_proof import OwnedUiProof,UiProofPending,UiProofMismatch,UiProofPreflightRejected


_PENDING_CLOSE=frozenset((
    'Pause entry detach deferred; retain its owner','Title entry detach deferred; retain its owner',
    'Native menu detach is pending; keep its owner',
    'Native menu cleanup is pending; keep its owner and try close after polling'))


class UiCapacityRebuild(Exception):
    """Detached, mutation-free capacity decision; retire before a larger build."""


class UiFrontendHeld(Exception):
    """Service already retained a failed frontend; no reconstruction is allowed."""


class LeaseJournal:
    def __init__(self):self.leases=[]
    def capture(self,scope):
        seen=set();pending=[scope];known={id(lease) for lease in self.leases}
        while pending:
            current=pending.pop()
            if current is None or id(current) in seen:continue
            seen.add(id(current))
            for lease in tuple(getattr(current,'_leases',())):
                if id(lease) not in known and getattr(lease,'_state',None)!='released':
                    self.leases.append(lease);known.add(id(lease))
            pending.extend(tuple(getattr(current,'_children',())))
    def acknowledged(self):return all(getattr(lease,'_state',None)=='released' for lease in self.leases)


class UiEntryOwner:
    def __init__(self,session,service,context):
        from ._scope import SessionScope
        from .title_menu import TitleMenuEntry
        from .pause_menu import PauseMenuEntry
        self.scope=SessionScope(session,lease_owner='SDKProcessUIEntry')
        self.ready=True;self.journal=LeaseJournal()
        factory=TitleMenuEntry if context.kind=='title' else PauseMenuEntry
        self.entry=factory(self.scope,service,readiness=lambda:self.ready)
        self.entry._process_owned_shell=True
        if context.kind=='world':self.entry._expected_controller=context.controller
        else:self.scope._title_local_selector=context.local_player[1:]
    def poll(self):
        self.entry.poll()
        return self.entry.state=='attached'
    def prepare(self):
        # Loading may attach a current pause widget, but never dispatch clicks.
        if self.entry.state in ('new','prepared'):self.entry.install()
        return self.entry.state=='attached'
    def close(self):
        self.ready=False;self.journal.capture(self.scope)
        if not self.scope._closed:
            try:self.entry.close()
            except RuntimeError as error:
                if str(error) in _PENDING_CLOSE:return False
                raise
            self.journal.capture(self.scope)
            self.scope.close()
        return self.journal.acknowledged()


class CachedProcessShell:
    def __init__(self,session,registry):
        from ._scope import SessionScope
        from .management_service import NativeMenuService
        from .mods_workspace_scroll import ScrollWorkspaceMenu
        self.scope=SessionScope(session,lease_owner='SDKProcessUI')
        self.ready=None;self.journal=LeaseJournal();self.proof=OwnedUiProof(self.scope)
        self.service=NativeMenuService(self.scope,registry,menu_factory=ScrollWorkspaceMenu,
            readiness=lambda:self.ready)
        self.service._keep_menu_plan_warm=True
        self.registry=registry;self.context=None

    def _factory(self,kind):
        from .title_management import TitleWorkspaceView
        from .mods_workspace_scroll import ScrollWorkspaceView
        return TitleWorkspaceView if kind=='title' else ScrollWorkspaceView

    def prepare_loading(self,context):
        return self.prepare(context,preparing=True)

    def prepare(self,context,*,preparing=False):
        self.needs_capacity_rebuild() # Reject an unsupported registry before any build.
        from .pause_preparation import prepare as prepare_pause
        prepare_pause(self.scope._session)
        self.ready=True;self.service._view_options['view_factory']=self._factory(context.kind)
        self.service.prepare()
        if self.service._failure:raise UiFrontendHeld('Prepared process UI frontend failed; retain its owner')
        menu=self.service.menu
        if menu is None or menu.panel.state!='built':return False
        from ._reader import ReadBatch,shared_operation
        from .ui_shell_proof import prepare_panel_metadata
        with shared_operation(self.scope.pid):
            prepare_panel_metadata(menu.panel)
            if preparing:self.proof.verify(menu.panel,context,preparing=True)
            else:self.proof.verify(menu.panel,context)
            # Proof metadata stabilization invalidates the process menu plan.
            # Rebuild it on this retained reader before publishing the entry.
            menu.panel.prime_menu_plan()
        self.service._primed_menu_cache=getattr(getattr(self.scope,'_session',None),'_menu_plan_cache',None)
        self.context=context
        return True

    def needs_capacity_rebuild(self):
        from .mods_workspace_scroll import MAX_FIXED_KEY_ROWS
        bindings=sum(len(view['keybinds']) for view in self.registry.views())
        if bindings>MAX_FIXED_KEY_ROWS:
            raise UiProofMismatch('Process UI bindings exceed the supported fixed row bound')
        menu=self.service.menu
        return menu is not None and bindings>menu.panel.key_row_capacity

    def detach(self):
        # Hide releases every native menu/Slate/button/focus baseline, retaining
        # only the process-owned UObject tree. Never call dispose for reuse.
        self.ready=None
        if self.service._failure:raise UiProofMismatch('Failed frontend cannot be reused')
        menu=self.service.menu
        if menu is None:return True
        try:self.service.close_menu()
        except RuntimeError as error:
            if str(error) in _PENDING_CLOSE:return False
            raise
        if menu.panel.state!='built' or menu.panel.menu is not None:return False
        if any(getattr(control,'active',False) for control in menu.actions):
            raise UiProofMismatch('Old UI callbacks remain active after native close ACK')
        cancel=getattr(menu,'_cancel_key_capture',None)
        if callable(cancel):cancel()
        return True

    def rebind(self,context,*,preparing=False):
        from ._reader import ReadBatch,shared_operation
        # One read-only worker for proof and detached repaint. Nested operation
        # batches borrow it without redoing executable validation at each step.
        with shared_operation(self.scope.pid):
            return self._rebind(context,preparing=preparing)

    def _rebind(self,context,*,preparing=False):
        menu=self.service.menu
        if menu is None and not self.service._failure:
            # dispose_menu clears this reference only after acknowledged tree
            # cleanup. Retire the shell owner before constructing a replacement;
            # waiting for a disposed tree to become detached cannot progress.
            raise UiCapacityRebuild('Disposed process UI shell requires acknowledged replacement')
        if menu is None or menu.panel.state!='built' or menu.panel.menu is not None:
            raise UiProofPending('Detached process UI shell required')
        # Deferred legacy definitions may add bindings after title preparation.
        # Decide before SetOwningPlayer, presenter replacement, or repaint.
        from .mods_workspace_scroll import MAX_FIXED_KEY_ROWS
        bindings=sum(len(view['keybinds']) for view in self.registry.views())
        if bindings>MAX_FIXED_KEY_ROWS:
            raise UiProofMismatch('Process UI bindings exceed the supported fixed row bound')
        if bindings>menu.panel.key_row_capacity:
            raise UiCapacityRebuild('Detached process UI requires a larger key capacity')
        if preparing:self.proof.verify(menu.panel,context,rebind=True,preparing=True)
        else:self.proof.verify(menu.panel,context,rebind=True)
        # Metadata and native menu plans were refreshed by proof before any
        # presenter/callback is moved to the new context. No scope is reparented.
        menu.view.close()
        menu.actions.clear();menu._binding_tokens={};menu._bound_frame=None
        menu._field_context=None;menu._accept_input=False
        menu._presentation_owner=None;menu._presentation_suspended=False;menu._presentation_dirty=False
        factory=self._factory(context.kind)
        menu._view_factory=factory;menu.view=factory(self.registry)
        self.service._view_options['view_factory']=factory
        self.service._observed=None;self.service._prepared_view_state=None
        menu._reuse_prepared_frame=False
        # Rebinding creates a fresh planner. Keep detached render planning on
        # one bounded reader, as initial preparation does.
        from ._reader import ReadBatch,shared_operation
        with ReadBatch(self.scope.pid):
            menu.frame=menu._render_view();menu._paint()
        # The detached repaint has fully acknowledged. Preserve exactly the
        # same prepared-frame evidence as initial service.prepare; a changed
        # registry/presenter still invalidates it through the existing checks.
        self.service._observed=self.service._snapshot()
        self.service._prepared_view_state=menu.prepared_view_state()
        self.service._primed_menu_cache=getattr(getattr(self.scope,'_session',None),'_menu_plan_cache',None)
        self.context=context;self.ready=True
        return True

    def poll(self):
        self.service.poll()
        if self.service._failure:
            raise UiFrontendHeld('Process UI service failed; retain its owner')
        menu=self.service.menu
        if self.ready is True and menu is not None:menu.poll_scroll()

    def close(self):
        self.ready=None;self.journal.capture(self.scope)
        if not self.service._closed:
            try:self.service.close()
            except RuntimeError as error:
                if str(error) in _PENDING_CLOSE:return False
                raise
        self.journal.capture(self.scope)
        if not self.scope._closed:self.scope.close()
        return self.journal.acknowledged() and not self.proof.pending()


class ProcessUI:
    """Single shell per exact GI/LocalPlayer, entries per current UI context.

    The supplied UiContext must come from admitted title/world observations.
    The shell independently refreshes anchors, graph and typed getter evidence
    before creating a new entry. None inhibits construction and retains owners.
    Unknown failures latch this router; no alternate shell or mutation replay.
    """
    def __init__(self,session,registry,*,shell_factory=CachedProcessShell,entry_factory=UiEntryOwner,reader_factory=None):
        self.session=session;self.registry=registry;self._owner=threading.get_ident()
        self._shell_factory=shell_factory;self._entry_factory=entry_factory
        from ._reader import ReadBatch
        self._reader_factory=reader_factory or (lambda pid:ReadBatch(pid,share=True))
        self._read_worker=None
        self.shell=self.entry=self.context=None;self.failed=False;self.phase='inactive';self._shell_key=None
        self._entry_context=None
        self._rebuild_requested=False
        self._pending_reason=None
        self._prewarmed_signature=None
        self._prepared_pause=None;self._prepared_pause_key=None;self._pause_preparation_failed=False
        self._prepared_title=None;self._prepared_title_key=None
        self.frontend_failed=None;self._frontend_record=None

    def _check(self):
        if threading.get_ident()!=self._owner:raise RuntimeError('Process UI requires its Session owner thread')
        self.session._check()

    @contextmanager
    def _read_operation(self):
        self._check()
        if self._read_worker is None:self._read_worker=self._reader_factory(self.session.pid)
        reader=self._read_worker
        try:
            with reader.bind():yield
        finally:
            if reader._closed:
                reader.close();self._read_worker=None

    def prepare_queries(self):
        """Warm process validation during loading; copy no UObject observations."""
        with self._read_operation():pass

    def close_queries(self):
        """Read-only IO may close even while engine UI owners await cleanup."""
        self._check()
        if self._read_worker is not None:
            self._read_worker.close();self._read_worker=None

    @property
    def service(self):return None if self.shell is None else self.shell.service

    @property
    def gameplay_ui_ready(self):
        return self.phase=='ready' and self.context is not None and self.context.kind=='world'

    @property
    def title_cleanup_ready(self):
        # A retained title entry or an unfinished old-context handoff blocks
        # gameplay restoration even when its service/menu has already hidden.
        if self.entry is None:return True
        if self._entry_context is not None:return self._entry_context.kind=='world'
        # A missing observation changes phase, not the retained entry's origin.
        # Only a title entry is the title-cleanup barrier; an already committed
        # world entry must not turn uncertainty into authoritative teardown.
        return self.context is not None and self.context.kind=='world'

    def observe(self,packet):
        """Copied scheduling only; actual handoff independently proves context."""
        context=(getattr(packet,'ui_context',None) or getattr(packet,'prewarm_context',None)) if packet is not None else None
        if context is not None:
            from ._reader import active_reader
            if active_reader() is None:
                with self._read_operation():return self._observe(packet)
        return self._observe(packet)

    def _observe(self,packet):
        context=getattr(packet,'ui_context',None) if packet is not None else None
        prewarm=getattr(packet,'prewarm_context',None) if packet is not None else None
        request=getattr(self,'_travel_recovery',None)
        if request is not None and getattr(request,'state',None)=='traveling':
            # Arrival is pure observation, serviced even after the old world
            # mod has retired. Never replay the normal-transition dispatch.
            request.poll()
            from ._reader import active_reader
            reader=active_reader()
            if reader is not None and reader._closed:
                self.phase='travel_pending';return False
            if request.state!='traveling':
                import logging
                logging.getLogger(__name__).info('Process travel observation finished: %s',request.state)
        if request is not None and getattr(request,'state',None) in ('traveling','recovering'):
            destination=context or prewarm
            # An in-flight transition can leave one last old-world sample.
            # Never rebuild/attach against it or an unready destination.
            if (destination is None or destination.signature==getattr(self,'_travel_origin',None)
                    or getattr(packet,'menu_ready',None) is not True):
                if self.shell is not None:self.shell.ready=None
                if self.entry is not None:self.entry.ready=None
                self.phase='travel_pending';return False
        if prewarm is not None and prewarm.kind=='world':
            if self.shell is None:return self.poll(prewarm,_prepare_only=True)
            # Build/rebind detached widgets while the loading screen still owns
            # presentation. No pause entry, input, or gameplay enable is granted.
            stage=(getattr(packet,'menu_ready',None) is True and
                not getattr(getattr(packet,'admission',None),'activation_ready',False))
            if stage and self.shell is not None:
                return self.poll(prewarm,_prepare_only=True,_stage_entry=True)
            if self.shell is not None and self._prewarmed_signature==prewarm.signature:
                if getattr(packet,'menu_ready',None) is not True:return False
            elif self.shell is not None:
                return self.poll(prewarm,_prepare_only=True)
        if context is None and prewarm is not None and prewarm.kind=='title':
            # Attachment has its own fresh authored-widget proof. Stage it
            # during the title fade; clicks remain disabled until admission.
            return self.poll(prewarm,_prepare_only=True,_stage_entry=True)
        if context is not None and context.kind=='world':
            prior=(self.context is not None and self.context.signature==context.signature)
            if (not prior and packet.admission.activation_ready and
                    getattr(packet,'menu_ready',None) is not True):
                # Retire only the old frontend entry. Backend mod admission
                # needs this ACK barrier, not a newly constructed pause UI.
                self.quiesce()
                return False
            if getattr(packet,'menu_ready',None) is not True or (not prior and not packet.admission.activation_ready):
                context=None
        elif context is not None and getattr(packet,'title_ready',None) is not True:
            context=None
        return self.poll(context)

    def quiesce(self):
        """ACK old native entry/input ownership, retain the detached GI shell."""
        self._check()
        if self.failed or self.frontend_failed is not None:return False
        self.phase='entry_retirement'
        if self.shell is not None and not self.shell.detach():return False
        if self.entry is not None:
            if not self.entry.close():return False
            self.entry=None;self._entry_context=None
        self.phase='waiting_for_gameplay_menu'
        return True

    def status(self):
        self._check()
        rows=self.registry.views()
        return dict(phase=self.phase,pending_reason=self._pending_reason if self.phase=='proof_pending' else None,kind=None if self.context is None else self.context.kind,
            failed=self.failed or self.frontend_failed is not None,staging_ready=self.phase=='ready' and self.context.kind=='title',
            gameplay_activation_deferred=not self.gameplay_ui_ready,
            staged_enabled=sum(row.get('desired_enabled',row.get('enabled',False)) is True for row in rows),
            actual_enabled=sum(row.get('enabled') is True for row in rows),
            shell_cached=self.shell is not None,entry_state=None if self.entry is None else self.entry.entry.state)

    def open(self):
        self._check()
        if self.failed or self.phase!='ready' or self.context is None or self.context.kind!='title':
            raise RuntimeError('Title staging UI is not ready')
        try:return self.entry.entry.open()
        except BaseException as error:
            from .frontend_rejection import known_rejection
            record=known_rejection(error)
            if record is None:
                self.failed=True;self.phase='quarantined';raise
            self._suspend_frontend(record)
            return 'Title frontend rejected invocation; core console remains available'

    def _suspend_frontend(self,record):
        self._frontend_record=record
        self.frontend_failed=dict(type=record.kind,native_error=record.native_error,outcome=record.outcome)
        if getattr(record,'role',None) is not None:self.frontend_failed['role']=record.role
        self.phase='frontend_cleanup_pending'
        return self._recover_frontend()

    def _recover_frontend(self):
        if self._frontend_record is None:return False # Generic held service: no outcome inference.
        service=self.service
        if self.shell is not None:self.shell.journal.capture(self.shell.scope)
        if service is not None and service.menu is not None:
            try:service.dispose_menu()
            except RuntimeError as error:
                if str(error) in _PENDING_CLOSE:return False
                raise
        if self.entry is not None and self.context is not None and self.context.kind=='title':
            if not self.entry.entry.restore_title_input_after_menu_close():return False
        self.phase='frontend_suspended'
        return True

    def _recorded_rejection(self):
        from .frontend_rejection import FrontendRejection
        service=self.service
        record=getattr(service,'_frontend_rejection',None)
        if record is None:record=getattr(getattr(service,'menu',None),'_frontend_rejection',None)
        return record if isinstance(record,FrontendRejection) else None

    def _prepare_pause_contents(self,context):
        source=getattr(self.session,'_pause_button_source',None)
        if source is None or self._prepared_pause is not None or self._pause_preparation_failed:return
        from dataclasses import replace
        self._prepared_pause=self._entry_factory(self.session,self.shell.service,replace(context,kind='world'))
        self._prepared_pause_key=context.persistent_key
        try:self._prepared_pause.entry.prepare_detached(source)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Detached pause preparation held; retiring its exact owner')
            self._pause_preparation_failed=True
            if self._prepared_pause.close():
                self._prepared_pause=None;self._prepared_pause_key=None

    def _new_entry(self,context):
        if context.kind=='title' and self._prepared_title is not None and self._prepared_title_key==context.persistent_key:
            cached=self._prepared_title;self._prepared_title=None;self._prepared_title_key=None
            return cached
        cached=self._prepared_pause
        if cached is not None and self._pause_preparation_failed:
            if not cached.close():raise UiProofPending('Detached pause preparation cleanup pending')
            self._prepared_pause=None;self._prepared_pause_key=None;cached=None
        if context.kind=='world' and cached is not None and self._prepared_pause_key==context.persistent_key:
            self._prepared_pause=None;self._prepared_pause_key=None
            cached.entry._expected_controller=context.controller
            return cached
        return self._entry_factory(self.session,self.shell.service,context)

    def _prepare_title_contents(self,context):
        if self._prepared_title is not None or self._entry_factory is not UiEntryOwner:return
        if self.context is not None or self.entry is not None:return
        from dataclasses import replace
        from .pause_preparation import capture_metadata
        from .catalog import capture_selected
        panel=self.shell.service.menu.panel
        catalog=panel._planner._catalog.with_observations(capture_metadata(self.session))
        catalog=catalog.with_observations(capture_selected(self.session.pid,(context.controller[1:],context.local_player[1:])))
        one=lambda name:panel._one(o for o in catalog.objects if o.name==name)
        source=dict(catalog=catalog,gi=context.gi[1:],local=context.local_player[1:],
            player=catalog.by_index[context.controller[1]],library=one('Default__WidgetBlueprintLibrary'),
            gameplay=one('Default__GameplayStatics'),style=one('CTS_B1_SmallLine_Outline_C'),
            dimensions=(0,0),stable=panel._metadata_stable_ui)
        self._prepared_title=self._entry_factory(self.session,self.shell.service,replace(context,kind='title'))
        self._prepared_title_key=context.persistent_key
        self._prepared_title.entry.prepare_detached(source)

    def _prepare_entry(self,context):
        if self.entry is None:
            self.entry=self._new_entry(context)
            self._entry_context=context
        self.entry.prepare()
        self.entry.ready=None

    def poll(self,context,*,_prepare_only=False,_stage_entry=False):
        self._check()
        if self.failed:raise RuntimeError('Process UI outcome is unknown; retain owners and close explicitly')
        if self.frontend_failed is not None:
            self._recover_frontend()
            return False
        record=self._recorded_rejection()
        if record is not None:
            self._suspend_frontend(record)
            return False
        if context is None:
            if self.shell is not None:self.shell.ready=None
            if self.entry is not None:self.entry.ready=None
            self.phase='observation_pending';return False
        try:
            if _prepare_only and self._prewarmed_signature==context.signature:
                if _stage_entry:self._prepare_entry(context)
                self.phase='prewarmed';self.shell.ready=None;return False
            if self.entry is not None and self._entry_context is not None and self._entry_context.signature==context.signature:
                self.shell.ready=True
                self.entry.ready=True
                if self.entry.poll() is False:self.phase='entry_pending';return False
                if context.kind=='title' and isinstance(self.entry,UiEntryOwner):self._prepare_pause_contents(context)
                self.context=context;self._entry_context=None;self.phase='ready';return True
            capacity_changed=self._rebuild_requested or (self.shell is not None and
                getattr(self.shell,'needs_capacity_rebuild',lambda:False)())
            if self.entry is not None and self.context is not None and self.context.signature==context.signature and self._entry_context is None and not capacity_changed:
                self.shell.ready=True;self.entry.ready=True
                self.shell.poll()
                if self.entry.poll() is False:self.phase='entry_pending';return False
                record=self._recorded_rejection()
                if record is not None:self._suspend_frontend(record);return False
                if context.kind=='title' and isinstance(self.entry,UiEntryOwner):self._prepare_pause_contents(context)
                self.phase='ready';return True
            self.phase='detaching'
            if self.shell is not None and not self.shell.detach():return False
            if self.entry is not None:
                if not self.entry.close():return False
                self.entry=None;self._entry_context=None
            if self.shell is not None and self._rebuild_requested:
                self.phase='explicit_tree_retirement'
                if not self.shell.close():return False
                self.shell=None;self.context=None;self._shell_key=None;self._rebuild_requested=False
            if self._prepared_pause is not None and self._prepared_pause_key!=context.persistent_key:
                if not self._prepared_pause.close():return False
                self._prepared_pause=None;self._prepared_pause_key=None
            if self._prepared_title is not None and self._prepared_title_key!=context.persistent_key:
                if not self._prepared_title.close():return False
                self._prepared_title=None;self._prepared_title_key=None
            if self.shell is not None and self._shell_key!=context.persistent_key:
                self.phase='retiring_game_instance'
                if not self.shell.close():return False
                self.shell=None;self.context=None;self._shell_key=None
            if self.shell is None:
                self.shell=self._shell_factory(self.session,self.registry)
                self._shell_key=context.persistent_key
            if self.context is None:
                self.phase='preparing'
                prepared=getattr(self.shell,'context',None)
                if prepared is None:
                    prepare=(getattr(self.shell,'prepare_loading',None) if _prepare_only else None) or self.shell.prepare
                    if not prepare(context):return False
                elif prepared.signature!=context.signature:
                    if _prepare_only and context.kind=='world':
                        if not self.shell.rebind(context,preparing=True):return False
                    elif not self.shell.rebind(context):return False
            else:
                self.phase='rebinding'
                try:
                    if self._prewarmed_signature!=context.signature:
                        self._prewarmed_signature=None
                        if _prepare_only and context.kind=='world':
                            if not self.shell.rebind(context,preparing=True):return False
                        elif not self.shell.rebind(context):return False
                except UiCapacityRebuild:
                    self.phase='capacity_rebuild'
                    if not self.shell.close():return False
                    self.shell=None;self.context=None;self._shell_key=None
                    # No second tree is built before all first-tree ACKs. The
                    # next observation must reauthorize even this clean rebuild.
                    return False
            if _prepare_only:
                self._prepare_title_contents(context)
                self._prewarmed_signature=context.signature
                if _stage_entry:self._prepare_entry(context)
                self.phase='prewarmed';self.shell.ready=None;return False
            self.phase='entry'
            self.entry=self._new_entry(context)
            self._entry_context=context
            if self.entry.poll() is False:self.phase='entry_pending';return False
            if context.kind=='title' and isinstance(self.entry,UiEntryOwner):self._prepare_pause_contents(context)
            self.context=context;self._entry_context=None;self.phase='ready';return True
        except UiProofPending as error:
            reason=str(error)[:256]
            if reason!=self._pending_reason:
                import logging
                logging.getLogger(__name__).info('Process UI handoff pending: %s',reason)
            self._pending_reason=reason
            self.phase='proof_pending';return False
        except UiProofPreflightRejected:
            # Only pure read/shape proof failures enter this state. Do not
            # infer cleanup or retry construction; explicit close owns ACKs.
            self.frontend_failed=dict(type='UiProofPreflightRejected',outcome='held')
            self.phase='frontend_held';return False
        except UiFrontendHeld:
            record=self._recorded_rejection()
            if record is not None:self._suspend_frontend(record);return False
            # NativeMenuService retained the exact owners and failure. This
            # optional frontend remains suspended without replay or inferred ACK.
            self.frontend_failed=dict(type='service_preparation',outcome='held')
            self.phase='frontend_held';return False
        except BaseException as error:
            from .frontend_rejection import known_rejection
            record=known_rejection(error)
            if record is not None:
                self._suspend_frontend(record);return False
            self.failed=True;self.phase='quarantined';raise

    def close(self):
        self._check();self.phase='closing'
        self.close_queries()
        if self._prepared_title is not None:
            if not self._prepared_title.close():return False
            self._prepared_title=None;self._prepared_title_key=None
        if self._prepared_pause is not None:
            if not self._prepared_pause.close():return False
            self._prepared_pause=None;self._prepared_pause_key=None
        if self.shell is not None:
            # Explicit retirement of a failed shell uses its full acknowledged
            # close path, never a reuse attempt or an alternate construction.
            if self.failed or self.frontend_failed is not None:
                self.shell.journal.capture(self.shell.scope)
                try:self.shell.service.close_menu()
                except RuntimeError as error:
                    if str(error) in _PENDING_CLOSE:return False
                    raise
            elif not self.shell.detach():return False
        if self.entry is not None:
            if not self.entry.close():return False
            self.entry=None;self._entry_context=None
        if self.shell is not None:
            if not self.shell.close():return False
            self.shell=None
        self.context=None;self._shell_key=None;self.phase='closed';return True
