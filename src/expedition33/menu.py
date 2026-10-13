"""Experimental single-user viewport-backed native menu ownership.

Only the verified base CommonActivatableWidget/Button specimen is supported.
This owns lifecycle and optional v16 button actions, not layout or key dispatch.
"""
import secrets
import weakref

from . import RuntimeQueryError
from . import _menu_wire as wire
from ._invocation_wire import encode_plan
from .catalog import capture
from .invocation import prepare_call


class MenuError(RuntimeQueryError):
    def __init__(self, message, *, outcome, native_error=None):
        self.outcome, self.native_error = outcome, native_error
        super().__init__(f'{message} (outcome={outcome}, native_error={native_error})')


class NativeMenu:
    def __init__(self, session, leases):
        self._session = weakref.ref(session)
        self._leases = tuple(leases)
        self._owner = secrets.randbits(64) or 1
        self._state = 'preparing'
        self._button_reference_state = None
        self._action = None
        self._controls = None

    @property
    def active(self):
        return self._state not in ('closed', 'target_exited')

    @property
    def close_pending(self):
        return self._state == 'close_pending'

    def protects(self, lease):
        return self.active and (lease in self._leases or
                                (self._controls is not None and self._controls.protects(lease)))

    def _send(self, operation, **kwargs):
        session = self._session()
        if session is None: raise MenuError('Menu session unavailable', outcome='unknown')
        session._check()
        if self._state == 'unknown': raise MenuError('Menu outcome is unknown; do not retry', outcome='unknown')
        try:
            sent = wire.request(operation, self._owner, **kwargs)
            if getattr(session._transport,'menu_input_protocol',0)==1 and len(sent)==wire.SIZE:
                sent += bytes(2*wire.CALL_SIZE)
        except (ValueError, TypeError):
            if operation in ('prepare','open'):
                self._state = 'closed'
                session._menus.discard(self)
            raise
        previous = self._state
        self._state = 'unknown'
        try:
            response = session._transport.command('menu', sent)
            reply = wire.decode(sent, response['menu_packet'])
            if getattr(session._transport, 'button_reference_protocol', 0) == 1:
                state = response.get('button_reference_state')
                if type(state) is not int or state not in range(5):
                    raise ValueError('Invalid button reference acknowledgement')
                if not reply.error and state != (2 if operation in ('attach', 'focus','open') else 0):
                    raise ValueError('Unexpected button reference ownership state')
                self._button_reference_state = state
        except (RuntimeQueryError, ValueError, KeyError) as error:
            session._abort_ownership()
            raise MenuError('Menu acknowledgement unavailable', outcome='unknown') from error
        if reply.outcome == 'unknown' or reply.error == 814:
            session._abort_ownership()
            raise MenuError('Native menu ownership is quarantined', outcome='unknown', native_error=reply.error)
        if not reply.active:
            self._state = 'closed'
            session._menus.discard(self)
        elif operation == 'close' or (operation in ('prepare','open') and reply.error):
            self._state = 'close_pending'
        elif not reply.error:
            self._state = {'prepare':'prepared', 'attach':'attached', 'focus':'focused','open':'attached'}[operation]
        else:
            self._state = previous
        if reply.error == 813:
            return False
        if reply.error:
            raise MenuError('Native menu request rejected', outcome=reply.outcome, native_error=reply.error)
        if reply.active != (operation != 'close'):
            self._state = 'unknown'
            session._abort_ownership()
            raise MenuError('Native menu acknowledgement has inconsistent ownership', outcome='unknown')
        return True

    def attach(self):
        if self._state in ('attached','focused'): return True
        if self._state != 'prepared': raise MenuError('Menu must be prepared before attachment', outcome='not_started')
        return self._send('attach')

    def focus(self):
        if self._state == 'focused': return True
        if self._state != 'attached': raise MenuError('Menu must be attached before focus', outcome='not_started')
        return self._send('focus')

    def close(self):
        session = self._session()
        if session is not None: session._transport._check_thread()
        if self._state == 'closed': return True
        action = self._action
        if action is not None: action._revoke('menu_closing')
        if self._controls is not None: self._controls.revoke('menu_closing')
        result = self._send('close')
        if result and action is not None: action._revoke()
        if result and self._controls is not None: self._controls.revoke()
        return result

    def bind_control(self, child, callback):
        if self._controls is None:
            from .multi_controls import MenuControls
            self._controls = MenuControls(self)
        return self._controls.bind(child, callback)

    def bind_controls(self, bindings):
        if self._controls is None:
            from .multi_controls import MenuControls
            self._controls = MenuControls(self)
        return self._controls.bind_many(bindings)

    def remove_controls(self, controls):
        return self._controls.remove_many(controls) if self._controls is not None else not controls

    def bind_action(self, callback):
        session = self._session()
        if session is None: raise MenuError('Menu session unavailable', outcome='unknown')
        session._check()
        if not session.supports_button_actions or self._state not in ('attached', 'focused'):
            raise MenuError('Button actions require an attached v16 menu', outcome='not_started')
        if not callable(callback): raise TypeError('Button callback must be callable')
        if self._action is not None and self._action._state != 'closed':
            raise MenuError('This menu already owns an action', outcome='not_started')
        from .button_actions import ButtonAction
        action = ButtonAction(self, callback)
        self._action = action  # Publish Python ownership before native binding.
        action._bind()
        return action

    def __enter__(self): return self
    def __exit__(self, *_exc): self.close()


def prepare(session, widget, child, player, leases, *, z_order=1000, catalog=None, _plan_only=False):
    session._check()
    if getattr(session._transport, 'menu_protocol', 0) != 1:
        raise MenuError('Menu ownership requires v14', outcome='not_started')
    if any(menu.active for menu in session._menus):
        raise MenuError('This session already owns a menu', outcome='not_started')
    if type(z_order) is not int or not 0 <= z_order <= 10000:
        raise ValueError('Z order must be an integer from 0 through 10000')
    def one(rows):
        rows = list(rows)
        if len(rows) != 1: raise ValueError('Expected exactly one live menu identity or owned lease')
        return rows[0]
    def owned(obj):
        return one(lease for lease in leases if lease.active and lease in session._leases and
                   (lease.object.pid,lease.object.index,lease.object.serial,lease.object.address)==
                   (obj.pid,obj.index,obj.serial,obj.address))
    selected = (owned(widget), owned(child))
    if selected[0] is selected[1]: raise ValueError('Menu widget and child need distinct owned leases')
    if catalog is None:
        catalog = capture()
    else:
        from .catalog import Catalog
        if not isinstance(catalog, Catalog) or catalog.pid != session.pid:
            raise ValueError('Expected a planning catalog from this process')
    # Observations only: every plan and menu identity is validated natively.
    widget, child, player = (catalog.resolve(obj) for obj in (widget, child, player))
    library = one(o for o in catalog.select('WidgetBlueprintLibrary') if o.name=='Default__WidgetBlueprintLibrary')
    engine = one(o for o in catalog.select('GameEngine') if not o.object_flags & 0x10)
    def function(owner, name):
        cls = catalog.find_class(owner).index
        return one(o for o in catalog.objects if o.outer_index==cls and o.name==name)
    specs = ((widget,'UserWidget','AddToViewport',{'ZOrder':z_order}),
             (widget,'Widget','IsInViewport',{}),
             (widget,'CommonActivatableWidget','ActivateWidget',{}),
             (widget,'CommonActivatableWidget','IsActivated',{}),
             (child,'Widget','SetUserFocus',{'PlayerController':player}),
             (child,'Widget','HasKeyboardFocus',{}),
             (child,'Widget','HasUserFocus',{'PlayerController':player}),
             (widget,'CommonActivatableWidget','DeactivateWidget',{}),
             (widget,'Widget','RemoveFromParent',{}),
             (library,'WidgetBlueprintLibrary','SetFocusToGameViewport',{}))
    ui_input = getattr(session._transport, 'menu_input_protocol', 0) == 1
    if ui_input:
        from .enums import describe_enums
        enum=one(o for o in catalog.objects if o.class_name=='Enum' and o.name=='EMouseLockMode')
        mode=describe_enums(catalog,(enum,))[enum.index].value('EMouseLockMode::DoNotLock')
        specs=list(specs)
        specs.append((library,'WidgetBlueprintLibrary','SetInputMode_UIOnlyEx',
                  {'PlayerController':player,'InWidgetToFocus':child,'InMouseLockMode':mode,'bFlushInput':False}))
        specs.append((library,'WidgetBlueprintLibrary','SetInputMode_GameOnly',{'PlayerController':player,'bFlushInput':False}))
    def encode_menu_plan(obj,fn,args):
        plan=prepare_call(catalog,obj,fn,args,enum_values=ui_input and fn.name=='SetInputMode_UIOnlyEx')
        if plan.wire_version==4:
            from ._enum_wire import encode_plan as encode_enum
            from ._invocation_wire import SIZE
            return encode_enum(plan)[:SIZE]
        return encode_plan(plan)
    # Keep one bounded set of planning bytes per session. This is not native
    # ownership: every prepare captures a fresh focus baseline and the target
    # validates all identities and schemas again. A changed player/widget or
    # function identity cannot reuse the previous plan set.
    functions = tuple(function(owner, name) for _, owner, name, _ in specs)
    key = (z_order, tuple((o.pid, o.index, o.serial, o.address)
                        for o in (engine, widget, child, player, library, *functions)))
    cached = getattr(session, '_menu_plan_cache', None)
    if cached is not None and cached[0] == key:
        plans = cached[1]
    else:
        plans = tuple(encode_menu_plan(obj, fn, args)
                      for (obj, _, _, args), fn in zip(specs, functions))
        session._menu_plan_cache = (key, plans)
    if _plan_only:
        return
    menu = NativeMenu(session, selected)
    session._menus.add(menu)  # Durable Python owner exists before any native acquisition.
    if not menu._send('open' if ui_input else 'prepare', leases=tuple(lease._token for lease in selected),
                      identities=(engine,widget,child,player,library), plans=plans):
        raise MenuError('Menu preparation cleanup deferred; poll the session', outcome='returned', native_error=813)
    return menu
