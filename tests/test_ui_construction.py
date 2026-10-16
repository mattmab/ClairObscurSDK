import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from expedition33 import _ui_construction as construction


class ConstructionTests(unittest.TestCase):
    def panel(self):
        return NS(_planner=NS(prepare=lambda target, fn, **args: (target, fn, args)),
                  scope=NS(), _mutate=lambda fn, *args: fn(*args))

    def test_dependency_layers_are_bounded_and_resolve_nested_slots_and_index_keys(self):
        recipe = construction.Construction()
        panel = self.panel()
        children = [recipe.record('tree', 'spawn', {}).return_value for _ in range(50)]
        slots = [recipe.record('canvas', 'add', {'Content': child}).return_value for child in children]
        panel.rows = list(zip(children, slots))
        panel.bounds = {child.index: (slot, 100, 20) for child, slot in panel.rows}
        calls = []
        def invoke(scope, planner, plans):
            self.assertFalse(any(isinstance(target, construction.Pending) for target, _, _ in plans))
            self.assertFalse(any(isinstance(v, construction.Pending) for _, _, args in plans for v in args.values()))
            calls.append(plans)
            return [NS(index=len(calls)*100+i) for i in range(len(plans))]
        with patch.object(construction, 'invoke_group', side_effect=invoke):
            recipe.flush(panel)
        self.assertEqual([len(group) for group in calls], [24,24,2,24,24,2])
        self.assertEqual([fn for group in calls for _,fn,_ in group], ['spawn']*50+['add']*50)
        for child, slot in panel.rows:
            self.assertIs(panel.bounds[child.index][0], slot)

    def test_failed_group_stops_without_replaying_or_resolving_panel(self):
        recipe=construction.Construction();panel=self.panel()
        panel.children=[recipe.record('tree','spawn',{}).return_value for _ in range(50)]
        with patch.object(construction,'invoke_group',side_effect=RuntimeError('unknown')) as invoke:
            with self.assertRaisesRegex(RuntimeError,'unknown'):recipe.flush(panel)
            self.assertEqual(invoke.call_count,1)
        self.assertIsInstance(panel.children[0],construction.Pending)
        self.assertEqual(recipe.calls,[])

    def test_missing_dependency_fails_before_dispatch(self):
        recipe=construction.Construction()
        recipe.record(construction.Pending(99),'add',{})
        with patch.object(construction,'invoke_group') as invoke:
            with self.assertRaisesRegex(ValueError,'dependency'):recipe.flush(self.panel())
            invoke.assert_not_called()

    def test_missing_capability_never_dispatches(self):
        session=NS(_transport=NS(ui_batch_protocol=1))
        with patch('expedition33._ui_batch.execute') as execute:
            with self.assertRaises(ValueError):construction.invoke_group(NS(_session=session),NS(),[NS()])
            execute.assert_not_called()

    def test_catalog_failure_after_native_dispatch_aborts_all_ownership(self):
        from contextlib import nullcontext
        class Session:
            _closed=False
        session=Session(); session._leases=set()
        session._transport=NS(ui_batch_protocol=1,ui_construction_protocol=1)
        session._abort_ownership=Mock()
        planner=NS(_catalog=Mock(),_generation=0)
        plan=NS(function=NS(name='SpawnObject'))
        call=NS(_plan=plan,_check=lambda:(planner,session))
        scope=NS(_session=session,_lease_context=nullcontext)
        reply=NS(outcome='dispatch_returned',error=0,objects=((0,1,2,3),))
        with patch.object(construction._retained_wire,'encode_plan',return_value=bytes(26192)), \
             patch.object(construction._ui_batch,'execute',return_value=[{'retained_packet':'test'}]), \
             patch.object(construction._retained_wire,'decode_reply',return_value=(reply,((0,99),))), \
             patch('expedition33.catalog.capture_selected',side_effect=RuntimeError('stale')):
            session.pid=1
            with self.assertRaisesRegex(RuntimeError,'stale'):construction.invoke_group(scope,planner,[call])
        self.assertEqual(len(session._leases),1)
        session._abort_ownership.assert_called_once()
        self.assertIsNone(planner._catalog)
        self.assertEqual(planner._generation,1)


if __name__=='__main__':unittest.main()
