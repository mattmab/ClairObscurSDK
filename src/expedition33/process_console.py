"""Owner-thread console delivery before gameplay; no gameplay mod polling."""
import threading
import math
import time
from .title_management import TitleRegistryFacade


class StartupConsoleInfo:
    """Local console summaries only; never copies settings or error payloads."""
    def __init__(self, console, loader, version):
        self.console=console;self.loader=loader;self.version=version
        self._last=None;self._world=False;self._finished=False;self._results=set();self._frontend_warning=False
        self._native_reported=False;self._color_warning=False
        self._game_state=None
        self._enable_total_ms=0.0
        self._usable_results=set()
        self._timing_rows={}

    def _write(self, *lines):
        def prefix(line):
            if line.startswith(('ClairObscurSDK','Native runtime v')):return 'SDK'
            if 'activation failed' in line or 'usability check failed' in line:return 'ERROR'
            if ('FAILURES' in line or 'with failures' in line or
                    line.startswith(('Title frontend unavailable','Native console colors unavailable'))):return 'WARN'
            if 'READY' in line:return 'READY'
            if 'unavailable' in line or 'deferred' in line:return 'WAIT'
            if line in ('Gameplay world detected','Activating enabled world-dependent mods'):return 'EVENT'
            if (line.endswith((': initialized',': complete',': activated')) or ': activated (' in line or ': usable (' in line or
                    line.startswith(('Console ready.','World readiness validated')) or
                    line=='Title screen detected'):return 'OK'
            return 'INFO'
        self.console.write(''.join('['+prefix(line)+'] '+line+'\n' for line in lines))

    def begin_world_cycle(self):
        """Start a fresh admitted activation report; process bootstrap stays once."""
        self._results.clear();self._usable_results.clear();self._timing_rows.clear()
        self._enable_total_ms=0.0;self._finished=False;self._world=False

    def activation(self, name, succeeded, enable_ms=None, preparation_ms=None):
        if enable_ms is not None and (isinstance(enable_ms,bool) or
                not isinstance(enable_ms,(int,float)) or not math.isfinite(enable_ms) or enable_ms<0):
            raise ValueError('Enable duration must be finite nonnegative milliseconds')
        if not self.console._enabled or name in self._results:return
        self._results.add(name)
        if enable_ms is not None:self._enable_total_ms+=enable_ms
        self._timing_rows[name]=dict(preparation_ms=preparation_ms,activation_ms=enable_ms,
            usable_ms=None,usability='pending' if succeeded else 'activation failed',succeeded=succeeded)
        self._write(f'{name}: '+('activated' if succeeded else 'activation failed'))

    def command(self, argument=''):
        """Show retained measurements without re-enabling or querying engine state."""
        if argument.strip():return 'Usage: startuptiming'
        self._write('Startup timing — measured preparation / activation / time until usable')
        def duration(value):return 'unreported' if value is None else f'{value:.1f} ms'
        for name,row in self._timing_rows.items():
            usable=duration(row['usable_ms']) if row['usable_ms'] is not None else row['usability']
            prefix='ERROR' if not row['succeeded'] else 'WAIT' if (row['activation_ms'] or 0)>200 else 'OK'
            self.console.write(f"[{prefix}] {name}: preparation {duration(row['preparation_ms'])} | activation {duration(row['activation_ms'])} | usable {usable}\n")
        if not self._timing_rows:self._write('No saved mod activation measurements yet')
        self._write(f'Total activation work: {self._enable_total_ms:.1f} ms')
        return None

    def _poll_usable(self):
        registry=self.loader.registry
        starts=getattr(registry,'_startup_activation_started',{})
        for mod_id,started in tuple(starts.items()):
            if mod_id in self._usable_results:continue
            entry=getattr(registry,'_entries',{}).get(mod_id)
            if entry is None:continue
            record=getattr(self.loader,'_loaded',{}).get(entry.name)
            if record is None or record[2] is None:continue
            name=entry.definition.title
            if name not in self._results:continue
            ready=getattr(record[1],'startup_ready',None)
            if ready is None:
                self._timing_rows[name]['usability']='unreported'
                self._usable_results.add(mod_id)
                continue
            try:value=ready()
            except Exception:
                self._timing_rows[name]['usability']='check failed'
                self._usable_results.add(mod_id)
                continue
            if value is True:
                self._timing_rows[name]['usable_ms']=(time.perf_counter()-started)*1000
                self._timing_rows[name]['usability']='ready'
                self._usable_results.add(mod_id)

    def poll(self, *, world_active=False, title_ready=False, frontend_failed=False):
        if not self.console._enabled:return
        self._poll_usable()
        native_status=getattr(self.console,'native_color_status',None)
        statuses=tuple(self.loader.status())
        prepared=len(getattr(self.loader,'_startup_preparations',{}))
        loaded=len(statuses);active=sum(bool(row.enabled) for row in statuses)
        failed=sum(bool(row.preparation_error or row.cleanup_error) for row in statuses)
        failed=max(failed,len(getattr(self.loader,'_preparation_failures',{})),
            self.loader.registry._startup_progress.get('failed',0))
        packages=len(self.loader.discover());deferred=max(0,packages-loaded)
        signature=(prepared,deferred,loaded,active,failed)
        game_state='WORLD_READY' if world_active else 'TITLE_SCREEN' if title_ready is True else 'INITIALIZING'
        if self._last is None:
            self._write(f'ClairObscurSDK v{self.version}',
                ('Native runtime: initialized' if native_status is None else
                    f"Native runtime v{native_status['native_version']} detected"),'Bootstrap: complete',
                'Game state: '+game_state,
                f'Mod discovery: {packages} packages found',
                'Early preparation: '+('complete' if not getattr(self.loader,'_preparation_failures',{}) else 'finished with failures'),
                'Gameplay world: '+('available' if world_active else 'unavailable'),
                'World-dependent activation: '+('admitted' if world_active else 'deferred'),
                'SDK READY'+('' if world_active else ' \u2014 awaiting gameplay world'),
                'Console ready. Type help for commands.')
            self._native_reported=native_status is not None
            self._game_state=game_state
        elif game_state!='INITIALIZING' and game_state!=self._game_state:
            # Missing/uncertain observations never demote the last known state.
            # Gameplay wins over a simultaneously copied old title observation.
            self._write('Game state: '+game_state)
            if game_state=='TITLE_SCREEN':self._write('Title screen detected')
            self._game_state=game_state
        if native_status is not None:
            # Only strict native action138/validated poll metadata populates
            # this copied cache. Never infer a loaded build from a filename.
            if not self._native_reported:
                self._write(f"Native runtime v{native_status['native_version']} detected")
                self._native_reported=True
            if (native_status['disabled'] or native_status['unsupported'] or native_status['faults']) and not self._color_warning:
                self._write('Native console colors unavailable; standard console remains available')
                self._color_warning=True
        if signature!=self._last:
            self._write(f'Mods: prepared {prepared}, deferred {deferred}, loaded {loaded}, active {active}, failed {failed}')
            self._last=signature
        if frontend_failed and not self._frontend_warning:
            self._write('Title frontend unavailable; SDK core and console remain available')
            self._frontend_warning=True
        if world_active and not self._world:
            self._write('Gameplay world detected','World readiness validated',
                'Activating enabled world-dependent mods')
            self._world=True
        progress=self.loader.registry._startup_progress
        if progress.get('finished') and not self._finished:
            count=f"{progress.get('completed',0)}/{progress.get('total',0)}"
            failures=progress.get('failed',0)
            self._write(f'Saved mod restoration complete: {count}, failed {failures}',
                'GAMEPLAY READY' if not failures else 'GAMEPLAY READY WITH MOD FAILURES')
            self._finished=True


class _TitleConsoleRegistry(TitleRegistryFacade):
    def request_shutdown(self):
        return self._registry.request_shutdown()


class ProcessConsole:
    def __init__(self, session, management_menu):
        self._owner=threading.get_ident()
        self.session=session;self.management_menu=management_menu
        self._registry=management_menu.registry;self._native=management_menu.native
        self._title_registry=_TitleConsoleRegistry(self._registry)
        self._attach_attempted=False
        self._world_active=False
        self._native_status_queried=False
        # Definitions/preferences remain usable, but existing callbacks must
        # not unexpectedly activate gameplay while the player is at title.
        management_menu.registry=self._title_registry
        management_menu.native=None

    def _check(self):
        if threading.get_ident()!=self._owner:
            raise RuntimeError('Process console requires its Session owner thread')

    def enable_for_title(self, ready):
        self._check()
        if ready is not None and type(ready) is not bool:
            raise TypeError('Title readiness must be bool or None')
        if ready is not True or self.session.console._enabled:return
        if self._attach_attempted:
            raise RuntimeError('Console attachment was already attempted; no automatic replay')
        self._attach_attempted=True
        self.session.console.enable()

    def title_active(self):
        self._check()
        self._world_active=False
        self.management_menu.registry=self._title_registry
        self.management_menu.native=None

    def world_active(self):
        self._check()
        self._world_active=True
        self.management_menu.registry=self._registry
        self.management_menu.native=self._native

    def poll(self):
        self._check()
        # Console.poll invokes copied user commands on this owner thread only;
        # it constructs no global key router and polls no gameplay mod.
        if self.session.console._enabled:
            if not self._native_status_queried:
                self._native_status_queried=True
                cap=getattr(self.session._transport,'console_color_status_protocol',0)
                if type(cap) is int and cap==1:
                    response=self.session._transport.command('console-color-status')
                    self.session.console._native_color_status=dict(response['console_color_status'])
            return self.session.console.poll()
        return ()
