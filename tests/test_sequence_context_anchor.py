import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33._sequence_endpoint import current_owned_context
from expedition33.values import StoredValues


class SequenceContextAnchorTests(unittest.TestCase):
    def test_playback_parent_selector_keeps_fresh_context_brackets(self):
        sequence,catalog,read,context,*_=self.fixture()
        parent=N(_check=Mock(),_session=sequence.scope._session)
        sequence.scope._parent=lambda:parent
        observe=Mock(return_value=context)
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
             patch('expedition33.catalog.capture_selected',return_value=catalog),\
             patch('expedition33.values.read_values_with_references',side_effect=read),\
             patch('expedition33.cinematics.controller_anchor.for_scope',return_value=N(context=observe)) as anchor:
            self.assertEqual(current_owned_context(sequence)[0],context['world'])
        parent._check.assert_called_once_with()
        anchor.assert_called_once_with(parent)
        self.assertEqual(observe.call_count,2)

    def test_foreign_parent_is_rejected_before_selector_read(self):
        sequence,*_=self.fixture()
        sequence.scope._parent=lambda:N(_check=Mock(),_session=object())
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
             patch('expedition33.cinematics.controller_anchor.for_scope') as anchor:
            with self.assertRaisesRegex(RuntimeError,'another session'):current_owned_context(sequence)
        anchor.assert_not_called()

    def fixture(self,cap=1):
        def obj(i,kind):return N(pid=123,index=i,serial=i+1,address=0x10000+i*256,class_name=kind,class_index=i+100,object_flags=0,item_flags=0)
        world=obj(1,'World');pc=obj(2,'PlayerController');actor=obj(3,'LevelSequenceActor');player=obj(4,'LevelSequencePlayer')
        level=obj(5,'Level');asset=obj(6,'LevelSequence')
        actor.outer_index=level.index;actor.outer_serial=level.serial
        player.outer_index=actor.index;player.outer_serial=actor.serial
        objects=(world,pc,actor,player,level,asset)
        classes={o.class_index:N(path='/Script/LevelSequence.'+o.class_name) for o in objects}
        catalog=N(by_index={**{o.index:o for o in objects},**classes},path_name=lambda o:o.path)
        fields={world.index:dict(PersistentLevel=level),level.index:dict(OwningWorld=world,bIsVisible=True),
                actor.index:dict(SequencePlayer=player,LevelSequenceAsset=asset),player.index:dict(Sequence=asset)}
        def read(catalog,obj,*,fields):
            data={k:v for k,v in values[obj.index].items() if k in fields}
            return StoredValues(obj,{(obj.class_index,k):v for k,v in data.items()}, {},
                {(obj.class_index,k):'BoolProperty' if type(v) is bool else 'ObjectProperty' for k,v in data.items()}),catalog
        values=fields
        identity=lambda o:(o.pid,o.index,o.serial,o.address)
        context=dict(controller=identity(pc),world=identity(world),world_path='/Game/QA.Map')
        sequence=N(scope=N(pid=123,_check=Mock(),_session=N(_transport=N(stable_lease_protocol=cap,_executable='test'))),actor=actor,player=player,_asset=asset)
        return sequence,catalog,read,context,fields,actor,asset
    def test_retained_selector_still_brackets_owned_pair_with_fresh_context(self):
        sequence,catalog,read,context,*_=self.fixture();observe=Mock(return_value=context)
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
             patch('expedition33.catalog.capture_selected',return_value=catalog),\
             patch('expedition33.values.read_values_with_references',side_effect=read),\
             patch('expedition33.cinematics.controller_anchor.for_scope',return_value=N(context=observe)) as anchor,\
             patch('expedition33.cinematics.original_game_action.controller_context') as scan:
            result=current_owned_context(sequence)
        anchor.assert_called_once_with(sequence.scope);self.assertEqual(observe.call_count,2);scan.assert_not_called()
        self.assertEqual(result[0],context['world']);self.assertEqual(result[1],context['controller'])
    def test_anchor_does_not_hide_world_changes_or_foreign_asset(self):
        sequence,catalog,read,context,fields,actor,asset=self.fixture()
        observe=Mock(side_effect=(context,dict(context,world=(123,9,10,0x30000))))
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
             patch('expedition33.catalog.capture_selected',return_value=catalog),\
             patch('expedition33.values.read_values_with_references',side_effect=read),\
             patch('expedition33.cinematics.controller_anchor.for_scope',return_value=N(context=observe)):
            with self.assertRaisesRegex(RuntimeError,'changed during'):current_owned_context(sequence)
            observe.side_effect=None;observe.return_value=context
            fields[actor.index]['LevelSequenceAsset']=N(pid=123,index=99,serial=100,address=0x40000)
            with self.assertRaisesRegex(RuntimeError,'retained source asset'):current_owned_context(sequence)
    def test_older_runtime_retains_fresh_scan_path(self):
        sequence,catalog,read,context,*_=self.fixture(0)
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
             patch('expedition33.catalog.capture_selected',return_value=catalog),\
             patch('expedition33.values.read_values_with_references',side_effect=read),\
             patch('expedition33.cinematics.controller_anchor.for_scope') as anchor,\
             patch('expedition33.cinematics.original_game_action.controller_context',return_value=context) as scan:
            current_owned_context(sequence)
        self.assertEqual(scan.call_count,2);anchor.assert_not_called()

    def test_projected_reader_batches_values_without_losing_pair_validation(self):
        sequence,catalog,read,context,fields,actor,asset=self.fixture()
        fields[2]={}
        def projection(pid,identities,*,fields,references):
            self.assertTrue(references)
            return catalog,{i:read(catalog,catalog.by_index[i],fields=fields)[0] for i,_,_ in identities}
        observe=Mock(return_value=context)
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),\
             patch('expedition33._reader.active_reader',return_value=N(supports_catalog_values=True)),\
             patch('expedition33.values.capture_selected_values',side_effect=projection) as projected,\
             patch('expedition33.values.read_values_with_references') as individual,\
             patch('expedition33.catalog.capture_selected') as selected,\
             patch('expedition33.cinematics.controller_anchor.for_scope',return_value=N(context=observe)):
            self.assertEqual(current_owned_context(sequence)[0],context['world'])
            self.assertEqual(projected.call_count,2);individual.assert_not_called();selected.assert_not_called()
            sequence.catalog=catalog;projected.reset_mock();observe.reset_mock()
            self.assertEqual(current_owned_context(sequence)[0],context['world'])
            self.assertEqual(projected.call_count,1);self.assertEqual(observe.call_count,2)
            self.assertEqual(projected.call_args.args[1][-1],(5,6,0x10500))
            self.assertIn('bIsVisible',projected.call_args.kwargs['fields'])
            fields[5]['bIsVisible']=False
            with self.assertRaisesRegex(RuntimeError,'current and visible'):current_owned_context(sequence)
            fields[5]['bIsVisible']=True
            fields[actor.index]['SequencePlayer']=asset
            with self.assertRaisesRegex(RuntimeError,'not reciprocal'):current_owned_context(sequence)
