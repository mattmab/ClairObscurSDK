"""Explicit controller capabilities for the experimental Cinematics launcher."""
from expedition33.controller_commands import Command

def commands(session, loader, telemetry=None):
    from dataclasses import asdict
    from expedition33.catalog import capture_matching, capture_selected
    from expedition33 import _query
    identities = {}
    def current(name, class_name):
        # Cache only a selector for three static engine definitions, never values
        # or a world object. Native slot/serial/address checks still run each time.
        import time
        started, clock = time.time(), time.perf_counter()
        old = identities.get(name)
        success = False
        try:
            catalog = (capture_matching(session.pid, names=(name,)) if old is None else
                capture_selected(session.pid, ((old.index, old.serial, old.address),)))
            matches = [obj for obj in catalog.objects if obj.name==name and obj.class_name==class_name]
            if len(matches)!=1: raise RuntimeError('Expected one current reflected target')
            obj=matches[0]
            if old is not None: catalog.resolve(old)
            identities[name]=obj
            success=True
            return catalog, obj
        except Exception:
            identities.clear()
            raise  # Never retry a failed reader or use stale cached results.
        finally:
            if telemetry is not None:
                telemetry.record('reflection.selector', 'reader', started, time.perf_counter()-clock,
                    success, cache_hits=int(old is not None), cache_misses=int(old is None), ipc_round_trips=1)
    def lookup():
        catalog, obj = current('Default__Actor', 'Actor')
        rows = [asdict(obj) for obj in catalog.objects if obj.name == 'Default__Actor']
        if len(rows)!=1: raise RuntimeError('Expected one current Default__Actor')
        return rows[0]
    def inspect(kind):
        name = 'Actor' if kind=='properties' else 'GetPlayState'
        catalog, obj = current(name, 'Class' if kind=='properties' else 'Function')
        start, rows = _query(['--describe',str(session.pid),f'{obj.index}:{obj.serial}:{obj.address:x}'])
        return {'identity':asdict(obj),'rows':rows}
    def widget_profile():
        from inspect_widget_profile import run
        return run(mod)
    def widget_arm():
        from verify_cinematic_widget_hook import run
        return run(mod)
    def combined_arm():
        from verify_cinematic_combined import run
        return run(mod)
    def lease_audit():
        from audit_lease_usage import run
        return run(session,loader)
    def lease_stress():
        from verify_lease_growth import run
        return run(session)
    def component_probe():
        from verify_detached_cinematic_component import run
        return run(mod)
    mod = loader._loaded['Cinematics'][1]
    def status():
        result = mod.status()
        discovery = result.pop('discovery', {})
        result['discovery'] = {key:discovery.get(key) for key in
            ('state', 'error', 'definition_catalog_complete')}
        result['discovery']['definitions'] = len(discovery.get('all', ()))
        result['discovery']['unlocked'] = len(discovery.get('confirmed', ()))
        return result
    def discover():
        mod.discover()
        return status()
    def catalog(offset=0, limit=20):
        if type(offset) is not int or type(limit) is not int or offset < 0 or not 1 <= limit <= 20:
            raise ValueError('Expected nonnegative offset and limit 1..20')
        rows = mod.discovery.get('all', ())
        return {'total':len(rows), 'offset':offset, 'rows':rows[offset:offset+limit],
                'freshness':'last discovery; unlocks must be refreshed before playback'}
    def close_menu():
        if mod.stop() is False:
            return status()
        if mod.native.status().get("error"):
            mod.native.parent.dispose_menu()
        else:
            mod.native.close_menu()
        return status()
    def open_menu():
        mod.pause.open()
        return status()
    def inspect_menu():
        from menu_cached_diagnostics import snapshot
        return snapshot(mod.native.menu)
    def probe_menu():
        from menu_owned_probes import probe_owned_menu
        return probe_owned_menu(mod.native.menu)
    def play_title():
        if mod.title_replay is None:
            raise RuntimeError('Prepare the exact title first')
        return mod.title_replay.play()

    def play_scene(scene_id):
        """Use the same admission, unlock and ownership path as native menu Play."""
        if not isinstance(scene_id, str) or not scene_id or len(scene_id) > 1024:
            raise ValueError('Expected a catalog cinematic definition ID')
        if mod.native.menu is None or mod.native.menu.panel.state != 'open':
            raise RuntimeError('Open the Cinematics menu before playback')
        mod.control(scene_id, 1)
        return status()
    def inspect_title():
        from expedition33.values import read_values
        replay = mod.title_replay
        if replay is None or replay.sequence is None or replay.state == 'cleanup_pending':
            raise RuntimeError('An armed or playing title is required for observation')
        sequence = replay.sequence
        wanted = {'StartTime', 'DurationFrames', 'DurationSubFrames', 'PlaybackSettings',
                  'TickManager', 'Sequence', 'RootTemplateInstance', 'Status'}
        values = read_values(sequence.planner._catalog, sequence.player)
        observations = {}
        for key, kind in values.types.items():
            if key[1] in wanted:
                value = values.values.get(key)
                observations[key[1]] = dict(type=kind, value=value if isinstance(value,(str,int,float,bool,type(None)))
                    else repr(value)[:2000], error=values.errors.get(key), truncated=key in values.truncated)
        return dict(player=asdict(sequence.player), properties=observations, status=replay.status())
    def inspect_timing():
        from title_timing_probe import inspect_title_timing
        return inspect_title_timing(mod)
    def backatcamp_profile():
        from inspect_backatcamp_profile import run
        return run(session)
    def actor_imports():
        from inspect_actor_cinematic_imports import run
        return run(mod)
    def camera_capture():
        from verify_sequence_camera_capture import run
        return run(mod)
    def binding_query(profile=1):
        from verify_sequence_binding_query import run
        return run(mod,profile)
    def media_timing():
        if mod.video is None:
            raise RuntimeError('An owned media playback is required')
        return mod.video.media_time()
    def media_rebuild(count=6):
        from verify_media_rebuild import run
        return run(mod, count)
    def audio_status():
        audio=getattr(mod.video,'audio_dependency',None) if mod.video is not None else None
        if audio is None:return {'state':'idle','playback':mod.playback_status}
        dispatcher=audio.dispatcher
        timeline=dispatcher.timeline if dispatcher is not None else None
        return {'state':audio.state,'error':audio.error,
            'components':len(dispatcher.components) if dispatcher else 0,
            'position':timeline.position if timeline else None,
            'steps':timeline.serial if timeline else 0,
            'active_sections':sorted(timeline.active) if timeline else [],
            'unacknowledged_step':timeline.pending is not None if timeline else False}
    return {
        'cinematics.research.media_rebuild': Command('research_component', media_rebuild),
        'cinematics.audio.status': Command('inspect', audio_status),
        'cinematics.research.actor_imports': Command('research_component', actor_imports),
        'cinematics.research.camera_capture': Command('research_component', camera_capture),
        'cinematics.research.binding_query': Command('research_component', binding_query),
        'cinematics.play': Command('research_component', play_scene),
        'cinematics.media.timing': Command('inspect', media_timing),
        'cinematics.research.backatcamp_profile': Command('research_component', backatcamp_profile),
        'sdk.object.lookup': Command('inspect', lookup),
        'sdk.leases': Command('inspect', lease_audit),
        'sdk.research.lease_stress': Command('research_component', lease_stress),
        'sdk.properties': Command('inspect', lambda: inspect('properties')),
        'sdk.function.schema': Command('inspect', lambda: inspect('function')),
        'cinematics.research.component_probe': Command('research_component', component_probe),
        'cinematics.research.widget_profile': Command('research_component', widget_profile),
        'cinematics.research.widget_arm': Command('research_component', widget_arm),
        'cinematics.research.combined_arm': Command('research_component', combined_arm),
        'cinematics.title.arm': Command('research_component',mod.prepare_title),
        'cinematics.title.play': Command('research_component',play_title),
        'cinematics.title.inspect': Command('inspect',inspect_title),
        'cinematics.title.timing': Command('inspect',inspect_timing),
        'cinematics.title.stop': Command('playback_stop',mod.stop_title),
        'cinematics.title.status': Command('inspect',lambda:mod.title_replay.status() if mod.title_replay else {'state':'idle'}),
        'sdk.status': Command('inspect', lambda: {'pid':session.pid, 'stopping':loader.stop_requested}),
        'cinematics.status': Command('inspect', status),
        'cinematics.discover': Command('inspect', discover),
        'cinematics.menu.open': Command('menu', open_menu),
        'cinematics.menu.close': Command('menu', close_menu),
        'cinematics.menu.inspect': Command('inspect', inspect_menu),
        'cinematics.menu.probe': Command('inspect', probe_menu),
        'cinematics.catalog': Command('inspect', catalog),
        'cinematics.stop': Command('playback_stop', mod.stop),
        'sdk.shutdown': Command('lifecycle', mod.session.mods.request_shutdown),
    }
