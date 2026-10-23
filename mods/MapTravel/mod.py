"""Standalone map browser using the game's normal entrance transition."""
import logging
import re
import time
from contextlib import nullcontext

from expedition33.paths import game_root
from expedition33.management import Action, ModDefinition, ManagementError
from expedition33.management_view import MenuControl, MenuFrame
from expedition33.pause_menu import PauseMenuEntry
from expedition33.invocation import InvocationError
from expedition33._reader import ReadBatch
from expedition33.cinematics.original_game_action import (
    controller_context, ready_history, NotReady,
)
from expedition33.zone_travel import available, routes, attach_routes, travel_to_entrance

LOG = logging.getLogger('expedition33.map_travel')


def installed_maps(lines):
    """Only standalone level packages; never World Partition streaming cells."""
    found = {}
    for line in lines:
        path = line.split('\t', 1)[0].strip().replace('\\', '/')
        if (not path.startswith('Sandfall/Content/Levels/') or not path.endswith('.umap')
                or '/_Generated_/' in path or '/UI/' in path
                or path.endswith('/Map_Game_Bootstrap.umap')):
            continue
        package = '/Game/' + path[len('Sandfall/Content/'):-5]
        if not re.fullmatch(r'/Game/[A-Za-z0-9_/]+', package):
            raise ValueError('Invalid installed map package')
        name = package.rsplit('/', 1)[-1]
        title = re.sub(r'^(?:ConceptLevel|SmallLevel|LevelMain|Level)_', '', name)
        title = re.sub(r'^(?:Main|Side|Small|Mini|Cave|Bonus)_', '', title)
        title = re.sub(r'_(?:Main|Blockout|WP)(?=_|$)', '', title)
        title = re.sub(r'_V\d+$', '', title).replace('OraneForest', 'OrangeForest')
        title = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', title).replace('_', ' ')
        found[package] = dict(package=package, world_path=package + '.' + name,
                              title=title, experimental='/ConceptLevels/' in path)
    return sorted(found.values(), key=lambda row: (row['title'].casefold(), row['package']))


class Travel:
    """One normal transition invocation, with fresh destination readiness checks."""
    def __init__(self, session, destination):
        self.session, self.destination = session, destination
        self.state, self.error = 'new', None
        self.deadline = self.next_poll = 0.

    @property
    def active(self):
        return self.state == 'traveling'

    def start(self):
        if self.state != 'new':
            raise ManagementError('This travel request has already been dispatched')
        if not self.destination.get('normal_route'):
            raise ManagementError('This map has no verified normal entrance route')
        started = time.perf_counter()
        with ReadBatch(self.session.pid, share=True):
            self.before = controller_context(self.session)
        LOG.info('Travel phase controller_check: %.3fs', time.perf_counter() - started)
        self.deadline = time.monotonic() + 120
        self.state = 'traveling'
        try:
            LOG.info('Travel phase normal_transition_dispatch: %s', self.destination['normal_route']['level_id'])
            travel_to_entrance(self.session, self.destination['normal_route'])
        except Exception as error:
            self.state, self.error = 'unknown', str(error)
            raise

    def poll(self):
        if not self.active or time.monotonic() < self.next_poll:
            return
        self.next_poll = time.monotonic() + .25
        if time.monotonic() >= self.deadline:
            self.state, self.error = 'failed', 'Travel timed out; no command was retried.'
            return
        try:
            with ReadBatch(self.session.pid, share=True):
                current = controller_context(self.session)
            if current['controller'] == self.before['controller']:
                raise NotReady('Waiting for the new player controller')
            if current['world_path'] != self.destination['world_path']:
                raise NotReady('Waiting for the destination map')
            # The game's spawn manager handles the entrance during this load.
            with ReadBatch(self.session.pid, share=True):
                ready_history(self.session)
                if controller_context(self.session) != current:
                    raise NotReady('Destination is still loading')
            self.state, self.error = 'arrived', None
        except NotReady as error:
            self.error = str(error)
        except Exception as error:
            self.state, self.error = 'failed', str(error)


from .browser import MapView


class Mod:
    def __init__(self):
        self.session = self.native = self.pause = self.request = None
        self.maps = []
        self._prepared_maps=None;self._manifest_signature=None
        self.message = 'Ready'
        self.pending_open = False
        self.pending_travel = None
        self._world_retiring=False;self._retirement_result=None

    @property
    def busy(self):
        return self.request is not None and self.request.active

    def management(self):
        return ModDefinition('sdk.map_travel', 'Map Travel', version='0.2.4',
            description='Browse installed maps and travel to their native entrance.',
            actions=(Action('open', 'Open Map Travel', self.open_menu),
                     Action('status', 'Travel status', self.status),))

    def prepare_startup(self, context):
        # Installed package names are filesystem facts, not engine/world state.
        self._prepare_installed_maps()

    def _prepare_installed_maps(self):
        path=game_root()/'Manifest_UFSFiles_Win64.txt'
        signature=lambda stat:(stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns)
        before=signature(path.stat())
        with path.open(encoding='utf-8-sig') as stream:rows=installed_maps(stream)
        if signature(path.stat())!=before:
            raise ManagementError('Installed manifest changed during preparation')
        if not rows:raise ManagementError('No standalone maps found in the installed manifest')
        self._prepared_maps=tuple(tuple(row.items()) for row in rows)
        self._manifest_signature=before

    def _activation_maps(self):
        path=game_root()/'Manifest_UFSFiles_Win64.txt'
        stat=path.stat();current=(stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns)
        if self._prepared_maps is None or current!=self._manifest_signature:
            self._prepare_installed_maps()
        # Fresh mutable dictionaries: route attachment must never contaminate
        # the immutable process-prepared package list or another world cycle.
        return [dict(row) for row in self._prepared_maps]

    def prepare_loading_ui(self,session):
        from .loading_entry import LoadingEntry
        return LoadingEntry(self,session)

    def enable(self, session):
        if self._retirement_result == 'ack':self.request=None
        self._world_retiring=False;self._retirement_result=None
        if not available(session._session._transport):
            raise ManagementError('Map Travel requires the normal zone-transition SDK runtime (v67)')
        shared = getattr(session._session, '_native_menu_service', None)
        if shared is None:
            raise ManagementError('Enable SDK Management first')
        self.session = session
        self.maps=self._activation_maps()
        prepared_routes=getattr(self,'_loading_routes',None)
        # Only copied route labels/IDs are prepared; the normal native travel
        # operation still reads the current level table before every dispatch.
        attach_routes(self.maps, routes(session.pid) if prepared_routes is None else prepared_routes)
        self.native = shared.for_view(lambda registry: MapView(registry, self))
        prepared=getattr(self,'_loading_entry',None)
        token=session.mods._loader.world_lifecycle.current_token if prepared is not None else None
        if (prepared is not None and prepared.entry is not None and prepared.entry.state=='attached'
                and token is not None and (prepared.context.world,prepared.context.gi)==token[:2]):
            self.pause=prepared.entry;prepared.adopted=True
        elif prepared is not None and prepared.entry is not None and prepared.entry.state not in ('new','closed'):
            raise ManagementError('Loading pause entry has not acknowledged its world handoff')
        else:
            if prepared is not None:
                # Activation chose the legacy unbuilt fallback. Revoke the
                # loading preparer before a later tick can create a duplicate.
                prepared.adopted=True
                prepared.entry=None
            self.pause = self._new_pause_entry()
        session.console.expose('map_travel', self)
        session.actions.register('map_travel.status', self.status, mutates=False)

    def _new_pause_entry(self):
        readiness=getattr(self.session._session,'_menu_readiness',None)
        if not callable(readiness):readiness=None
        return PauseMenuEntry(self.session,self.native,label='Map Travel',readiness=readiness)

    def open_menu(self, _=None):
        self.pending_open = True
        return 'Opening Map Travel'

    def travel(self, package):
        if self.busy or self.native.parent.travel_recovery_pending:
            raise ManagementError('Wait for the current travel to finish')
        destination = next((row for row in self.maps if row['package'] == package), None)
        if destination is None:
            raise ManagementError('Choose an installed standalone map')
        if not destination.get('normal_route'):
            raise ManagementError('This map has no verified normal entrance route')
        # Reject stale routes and unsupported contexts before disposing menus.
        try:
            travel_to_entrance(self.session, destination['normal_route'], validate_only=True)
        except InvocationError as error:
            if error.outcome != 'not_dispatched' or error.native_error != 1810:
                raise
            self.message = 'Travel unavailable: entrance route rejected for ' + destination['title']
            LOG.warning('%s; route=%r', self.message, destination['normal_route'])
            # Stay in the native pause menu. Automatically reopening from this
            # failure path can capture stale Slate focus and close the SDK.
            self.pending_open = False
            return
        request = Travel(self.session, destination)
        started = time.perf_counter()
        LOG.info('Travel phase begin_cleanup')
        # Dispose the shared widget tree and this entry before world teardown.
        menu = self.native.parent.menu
        with self.pause.cleanup_feedback() if self.pause else nullcontext():
            if menu is not None and callable(getattr(menu.panel, 'close_owned_tree', None)):
                # The closed browser has already detached native input. Keep the
                # read worker scoped to cleanup; never carry it across map travel.
                with menu._read_operation():
                    if not menu.panel.close_owned_tree():
                        raise ManagementError('Menu input cleanup is still pending')
            self.native.parent.dispose_menu()
        LOG.info('Travel phase menu_cleanup: %.3fs', time.perf_counter() - started)
        if menu is not None and menu.panel.state != 'closed':
            raise ManagementError('The menu must fully dispose before travel')
        if self.pause:
            pause_started = time.perf_counter()
            self.pause.close()
            self.pause = None
            LOG.info('Travel phase pause_cleanup: %.3fs', time.perf_counter() - pause_started)
        self.request = request
        self.native.parent.travel_recovery = request
        self.message = 'Traveling to ' + destination['title']
        try:
            request.start()
            LOG.info('Travel phase cleanup_to_transition: %.3fs', time.perf_counter() - started)
        except Exception:
            if request.state == 'new':
                request.state = 'failed'
            self._finish()
            raise

    def _finish(self):
        request = self.request
        self.message = ('Arrived: ' + request.destination['title'] if request.state == 'arrived'
                        else 'Travel ' + request.state + ': ' + (request.error or 'Unavailable'))
        LOG.info('%s', self.message)
        if self.native.parent.travel_recovery is request:
            self.native.parent.travel_recovery = None
        if self.pause is None:
            self.pause = self._new_pause_entry()

    def poll(self):
        if self._world_retiring:return
        if self.pending_open:
            self.pending_open = False
            self.native.parent.close_menu()
            self.native.open()
        if self.pending_travel is not None:
            package, self.pending_travel = self.pending_travel, None
            self.travel(package)
        if self.busy:
            self.request.poll()
            if self.busy:
                return
            self._finish()
        if self.pause:
            self.pause.poll()

    def status(self, _=None):
        return dict(maps=len(self.maps), message=self.message,
                    state=self.request.state if self.request else 'idle',
                    error=self.request.error if self.request else None,
                    pause_state=self.pause.state if self.pause else None)

    def revoke_world(self,context):
        self._world_retiring=True
        self.pending_open=False;self.pending_travel=None

    def begin_world_retirement(self,context):
        if self._retirement_result is not None:return self._retirement_result
        self._world_retiring=True
        return self.poll_world_retirement(context)

    def poll_world_retirement(self,context):
        if self._retirement_result in ('ack','unknown'):return self._retirement_result
        entry=self.pause
        attachment=getattr(entry,'attachment',None) if entry is not None else None
        # PauseAttachment.close restores borrowed game state before detaching.
        # Until an epoch-aware close exists, retain every active owner untouched.
        held=(entry is not None and (entry.state not in ('new','closed')
              or entry.observer is not None
              or attachment is not None and attachment.state not in ('empty','closed')))
        ambiguous=self.request is not None and self.request.state=='unknown'
        if ambiguous:
            self._retirement_result='unknown';return 'unknown'
        if held:
            retire=getattr(entry,'retire_world',None)
            if not callable(retire):
                self._retirement_result='unknown';return 'unknown'
            try:
                outcome=retire()
                if type(outcome) is not str or outcome not in ('ack','pending'):raise RuntimeError('Invalid pause retirement ACK')
            except BaseException:
                self._retirement_result='unknown';return 'unknown'
            self._retirement_result=outcome
            if outcome=='ack':self.pause=None
        else:self._retirement_result='ack'
        return self._retirement_result

    def disable(self):
        if self.busy:
            raise ManagementError('Wait for travel to finish before disabling Map Travel')
        if self.native:
            self.native.close()
        if self.pause:
            self.pause.close()
        self.native = self.pause = self.session = None
