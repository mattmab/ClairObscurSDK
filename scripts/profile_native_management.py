"""Profile one explicit operation on the existing management owner.

Use from persistent console Python. Never attaches another controller, retries
a mutation, or discards the service owner after a failed operation.
"""
import cProfile
import json
from pathlib import Path
import pstats
import time
from contextlib import nullcontext

ROOT = Path(__file__).resolve().parents[1]


def measure_combined(management, *, profile=False):
    """Rebuild both owned trees; never time a cached reopen as construction.

    Invoke on the existing controller's owner thread, with other testing idle.
    Cleanup is reported separately; discovery, worker startup, pause attachment,
    menu construction, initial paint and menu-plan preparation are all timed.
    """
    from expedition33.pause_menu import PauseMenuEntry
    from expedition33._reader import ReadBatch, active_reader

    service = management.native
    previous = management.pause
    if service.travel_recovery_pending or previous.state != 'attached':
        raise ValueError('Expected an attached pause entry outside travel recovery')
    if service.menu is not None and service.menu.panel.state == 'open':
        raise ValueError('Close the Mods menu before benchmarking construction')
    cleanup = time.perf_counter()
    previous.close()
    service.dispose_menu()
    cleanup_ms = (time.perf_counter() - cleanup) * 1000
    # Publish each owner before any construction can fail. Never retry/release
    # an uncertain mutation or leave the mod pointing at an old closed entry.
    management.pause = PauseMenuEntry(previous.parent_scope, service, label=previous.label)
    service._warmup_attempted = False
    report = dict(operation='combined_cold_build', completed=False, target_ms=500.,
                  cleanup_ms=cleanup_ms, profile_enabled=profile,
                  shared_reader_already_active=active_reader() is not None)
    profiler = cProfile.Profile() if profile else None
    started = time.perf_counter()
    try:
        if profiler:
            profiler.enable()
        reader = nullcontext() if active_reader() is not None else ReadBatch(service.scope.pid, share=True)
        with reader:
            if not management.pause.install():
                raise RuntimeError('Current pause entry was unavailable')
            report['pause_ready_ms'] = (time.perf_counter() - started) * 1000
            service.prepare()
            if service._failure or service.menu is None or service.menu.panel.state != 'built':
                raise RuntimeError(service._failure or 'Menu did not finish construction')
        report['completed'] = True
    except BaseException as error:
        report['error'] = f'{type(error).__name__}: {error}'
        if management.pause.state != 'attached':
            management.pause.state = 'failed'
            management.pause.error = report['error']
        raise
    finally:
        report['total_ms'] = (time.perf_counter() - started) * 1000
        report['target_met'] = report['completed'] and report['total_ms'] <= report['target_ms']
        report['pause_stages'] = dict(management.pause.timings)
        report['menu_stages'] = dict(service.menu.panel.timings) if service.menu else {}
        evidence = ROOT / 'evidence'
        evidence.mkdir(exist_ok=True)
        if profiler:
            profiler.disable()
            profiler.dump_stats(str(evidence / 'management-combined-build.prof'))
        (evidence / 'management-combined-build.json').write_text(
            json.dumps(report, indent=2), encoding='utf-8')
    return report


def arm_navigation(management):
    """Time the next real native-button dispatch, restoring the method afterward."""
    menu = management.native.menu
    if menu is None or menu.panel.state != 'open' or 'submit' in vars(menu):
        raise ValueError('Expected an open menu without existing instrumentation')
    original = menu.submit
    def measured(*args, **kwargs):
        started = time.perf_counter()
        report = {'before': menu.frame.title, 'completed': False}
        try:
            result = original(*args, **kwargs)
            report.update(completed=True, after=menu.frame.title)
            return result
        except BaseException as error:
            report['error'] = f'{type(error).__name__}: {error}'
            raise
        finally:
            del menu.submit
            report['seconds'] = time.perf_counter() - started
            (ROOT / 'evidence/management-navigation-timing.json').write_text(
                json.dumps(report, indent=2), encoding='utf-8')
            print(f"Navigation: {report['seconds']:.3f}s; completed={report['completed']}")
    menu.submit = measured
    return 'Next native menu click will be timed'


def measure(management, operation, *, profile=True):
    service = management.native
    if operation not in ('open', 'refresh', 'close', 'warmup'):
        raise ValueError('Expected open, refresh, close or warmup')
    method = {'open': service.open, 'refresh': service.refresh, 'close': service.close_menu,
              'warmup': service.prepare}[operation]
    before = service.status()
    if operation == 'open' and before['state'] not in ('not_created', 'closed'):
        raise ValueError('Profile a fresh explicit open only')
    if operation == 'warmup' and (service.menu is not None or service._warmup_attempted):
        raise ValueError('Warmup measurement requires an explicitly disposed, unprepared menu')
    profiler = cProfile.Profile() if profile else None
    started = time.perf_counter()
    report = {'operation': operation, 'before': before, 'completed': False,
              'profile_enabled': profile}
    prefix = ROOT / 'evidence' / (('management-profile-' if profile else 'management-timing-') + operation)
    try:
        result = profiler.runcall(method) if profiler else method()
        if operation == 'warmup' and service.status()['error']:
            raise RuntimeError(service.status()['error'])
        report['completed'] = True
        return result
    except BaseException as error:
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        report['seconds'] = time.perf_counter() - started
        if profiler:
            profiler.dump_stats(str(prefix.with_suffix('.prof')))
        stats = pstats.Stats(profiler).stats if profiler else {}
        report['functions'] = [
            dict(file=key[0], line=key[1], function=key[2], primitive_calls=value[0],
                 calls=value[1], own_seconds=value[2], cumulative_seconds=value[3])
            for key, value in sorted(stats.items(), key=lambda item: item[1][3], reverse=True)[:100]]
        report['after'] = service.status()
        prefix.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f"{'Profile' if profile else 'Timing'} {operation}: {report['seconds']:.3f}s; completed={report['completed']}")
