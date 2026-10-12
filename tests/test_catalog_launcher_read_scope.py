"""Exercise the actual launcher loop AST without attaching a runtime."""
import ast
from pathlib import Path
from types import SimpleNamespace as N
from unittest import TestCase
from unittest.mock import Mock

class CatalogLauncherReadScopeTests(TestCase):
    def test_idle_loop_does_not_create_controller_lifetime_or_per_tick_reader(self):
        source=Path(__file__).resolve().parents[1]/'scripts/run_cinematics_catalog_game_owned_candidate.py'
        tree=ast.parse(source.read_text());loop=next(n for n in ast.walk(tree) if isinstance(n,ast.While))
        events=[];loader=N(stop_requested=False);count=[0]
        Batch=Mock(side_effect=AssertionError('Idle loop must not construct a reader'))
        def poll():
            # A component can catch a read error and retain its failed owner;
            # the loop must nevertheless exit that read context this iteration.
            count[0]+=1;events.append(('poll',count[0]))
            if count[0]==2:loader.stop_requested=True
        loader.poll=poll
        module=ast.fix_missing_locations(ast.Module(body=[loop],type_ignores=[]))
        exec(compile(module,str(source),'exec'),dict(loader=loader,ReadBatch=Batch,session=N(pid=1),server=N(poll=lambda:None),telemetry=N(poll_wait=lambda _:None)))
        self.assertEqual(events,[('poll',1),('poll',2)]);Batch.assert_not_called()
        for node in ast.walk(tree):
            if isinstance(node,ast.With) and any(isinstance(n,ast.While) for n in ast.walk(node)):
                self.assertFalse(any(isinstance(item.context_expr,ast.Call) and getattr(item.context_expr.func,'id',None)=='ReadBatch' for item in node.items))
