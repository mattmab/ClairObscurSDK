"""Controller-side timings; no work is added to the game thread."""
import cProfile
import functools
import io
import pstats
import time

def measured(name):
    def decorate(method):
        @functools.wraps(method)
        def run(self, *args, **kwargs):
            started = time.perf_counter()
            profiler = cProfile.Profile() if name == 'menu_build' and (self.library.store.root.parent/'profile-menu-build').exists() else None
            if profiler: profiler.enable()
            try:
                return method(self, *args, **kwargs)
            finally:
                if profiler:
                    profiler.disable()
                    output = io.StringIO()
                    pstats.Stats(profiler, stream=output).sort_stats('cumulative').print_stats(70)
                    (self.library.store.root.parent / 'menu-build-profile.txt').write_text(output.getvalue(), encoding='utf8')
                if hasattr(self, 'library'):self.library.mark(name, started)
        return run
    return decorate
