"""Profile one explicit operation on the existing management owner.

Use from persistent console Python. Never attaches another controller, retries
a mutation, or discards the service owner after a failed operation.
"""
import cProfile
import json
from pathlib import Path
import pstats
import time

ROOT = Path(__file__).resolve().parents[1]


def measure(management, operation, *, profile=True):
    service = management.native
    if operation not in ('open', 'refresh', 'close'):
        raise ValueError('Expected open, refresh or close')
    method = {'open': service.open, 'refresh': service.refresh, 'close': service.close_menu}[operation]
    before = service.status()
    if operation == 'open' and before['state'] not in ('not_created', 'closed'):
        raise ValueError('Profile a fresh explicit open only')
    profiler = cProfile.Profile() if profile else None
    started = time.perf_counter()
    report = {'operation': operation, 'before': before, 'completed': False,
              'profile_enabled': profile}
    prefix = ROOT / 'evidence' / (('management-profile-' if profile else 'management-timing-') + operation)
    try:
        result = profiler.runcall(method) if profiler else method()
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
