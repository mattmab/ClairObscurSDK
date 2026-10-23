import unittest
from types import SimpleNamespace as N
from contextlib import nullcontext
from unittest.mock import Mock,patch
from expedition33 import RuntimeQueryError
from expedition33 import pause_preparation as m

class PausePreparationTests(unittest.TestCase):
 def test_prepare_keeps_only_retained_metadata_and_runs_once(self):
  function=N(index=1,serial=4,address=0x10000,class_name='Function',outer_index=9,name='GetIsEnabled')
  world=N(index=2,serial=5,address=0x20000,class_name='World')
  catalog=N(objects=(function,world),by_index={9:N(name='Widget')});session=N(pid=7)
  def admitted(c,o):
   if o is world:raise ValueError('world is not metadata')
  metadata=Mock()
  with patch.object(m,'ReadBatch',return_value=nullcontext()),patch.object(m,'prepare_discovery',return_value=(catalog,())) as discovery,patch.object(m,'script_function',side_effect=admitted),patch.object(m,'MetadataObservations',return_value=metadata):
   m.prepare(session);m.prepare(session)
  discovery.assert_called_once()
  self.assertEqual(session._pause_entry_metadata_selectors,((1,4,0x10000),))
  self.assertIs(session._pause_schema_observations,metadata)
 def test_capture_refreshes_metadata_and_world_without_reusing_widgets(self):
  selectors=((1,4,0x10000),);session=N(pid=7,_pause_entry_metadata_selectors=selectors)
  metadata=Mock();world=N(objects=())
  with patch.object(m,'capture_selected',return_value=metadata) as selected,patch.object(m,'capture_matching',return_value=world) as matching:
   self.assertIs(m.capture(session),metadata.with_observations.return_value)
  selected.assert_called_once_with(7,selectors)
  metadata.with_observations.assert_called_once_with(world)
  self.assertEqual(matching.call_args.kwargs['names'],m.FRESH_NAMES)
 def test_changed_retained_selector_is_visible_without_discovery_fallback(self):
  with patch.object(m,'capture_selected',side_effect=RuntimeQueryError('changed')),patch.object(m,'capture_matching') as matching:
   with self.assertRaises(RuntimeQueryError):m.capture(N(pid=7,_pause_entry_metadata_selectors=((1,4,0x10000),)))
  matching.assert_not_called()
 def test_unprepared_session_preserves_existing_discovery_path(self):
  with patch.object(m,'capture_matching') as matching:self.assertIsNone(m.capture(N()))
  matching.assert_not_called()
 def test_boundary_discards_only_unresolved_schema_copies_before_building(self):
  current=N(index=1);stale=N(index=2)
  def resolve(obj):
   if obj is stale:raise RuntimeQueryError('unretained enum changed')
   return obj
  catalog=N(resolve=resolve);metadata=Mock();metadata.with_observations.return_value=catalog
  cache=m.MetadataObservations();cache._entries={'current':('descriptor',(current,)),'stale':('descriptor',(stale,))}
  session=N(pid=7,_pause_entry_metadata_selectors=((1,4,0x10000),),_pause_schema_observations=cache)
  with patch.object(m,'capture_selected',return_value=metadata),patch.object(m,'capture_matching'):
   self.assertIs(m.capture(session),catalog)
  self.assertEqual(session._pause_schema_observations._entries,{'current':('descriptor',(current,))})
  self.assertEqual(set(cache._entries),{'current','stale'})

 def test_known_controller_follows_live_content_without_global_discovery(self):
  selectors=((1,4,0x10000),);readonly=((2,0,0x20000),)
  session=N(pid=7,_pause_entry_metadata_selectors=selectors,_pause_readonly_metadata_selectors=readonly)
  metadata=Mock();world=object();controller=(7,3,6,0x30000)
  with patch.object(m,'capture_selected',return_value=metadata) as selected,patch.object(m,'_current_widgets',return_value=world) as current,patch.object(m,'capture_matching') as matching:
   self.assertIs(m.capture(session,controller=controller),metadata.with_observations.return_value)
  selected.assert_called_once_with(7,selectors+readonly);current.assert_called_once_with(session,controller)
  matching.assert_not_called()

 def test_changed_readonly_enum_is_invalidated_for_a_later_operation_without_replay(self):
  selectors=((1,4,0x10000),)
  session=N(pid=7,_pause_entry_metadata_selectors=selectors,_pause_readonly_metadata_selectors=((2,0,0x20000),))
  with patch.object(m,'capture_selected',side_effect=RuntimeQueryError('DESCRIPTOR_IDENTITY_CHANGED')) as selected,patch.object(m,'capture_matching') as matching:
   with self.assertRaises(RuntimeQueryError):m.capture(session,controller=(7,3,6,0x30000))
  selected.assert_called_once();matching.assert_not_called()
  self.assertIsNone(session._pause_readonly_metadata_selectors)
  self.assertEqual(session._pause_entry_metadata_selectors,selectors)


class CurrentPauseContentTests(unittest.TestCase):
 def setUp(self):
  from expedition33.catalog import CatalogObject
  from expedition33.values import StoredArray,StoredStruct
  def obj(i,name,kind,outer=-1):
   return CatalogObject(pid=7,index=i,serial=1,address=0x10000+i*8,name=name,class_name=kind,
       metaclass_name='Class',class_index=100+i,outer_index=outer,outer_serial=1 if outer>=0 else 0,object_flags=0,item_flags=0)
  self.pc=obj(1,'PC','PlayerController');self.local=obj(2,'LP','LocalPlayer');self.pause=obj(3,'Pause','WBP_PauseMenu_C')
  self.tree=obj(4,'Tree','WidgetTree');self.resume=obj(5,'Resume','WBP_BaseButton_C');self.overlay=obj(6,'Overlay','Overlay')
  self.slot=obj(7,'Slot','OverlaySlot');self.text=obj(8,'CommonTextBlock_178','CommonTextBlock',4)
  def catalog(objects):
   objects=tuple(objects)
   result=N(objects=objects,by_index={o.index:o for o in objects},find_class=lambda kind:N(index={'PlayerController':101,'CommonTextBlock':108}[kind]),ancestors=lambda index:(index,))
   result.with_observations=lambda other:catalog({**result.by_index,**other.by_index}.values())
   return result
  def row(obj,**fields):
   return N(types={(obj.class_index,name):kind for name,(kind,value) in fields.items()},
       values={(obj.class_index,name):value for name,(kind,value) in fields.items()},errors={},truncated=set())
  self.catalog=catalog;self.row=row
  named=StoredArray((StoredStruct(None,{'Content':self.overlay},{},{'Content':'ObjectProperty'},False),),1)
  self.responses=[(catalog((self.pc,self.local,self.pause)),{1:row(self.pc,Player=('ObjectProperty',self.local),PauseMenuWidget=('ObjectProperty',self.pause))}),
      (catalog((self.resume,self.overlay)),{5:row(self.resume,NamedSlotBindings=('ArrayProperty',named))}),
      (catalog((self.overlay,self.slot)),{6:row(self.overlay,Slots=('ArrayProperty',StoredArray((self.slot,),1)))}),
      (catalog((self.slot,self.text)),{7:row(self.slot,Content=('ObjectProperty',self.text))})]
  self.pause_result=(row(self.pause,WidgetTree=('ObjectProperty',self.tree),ResumeButton=('ObjectProperty',self.resume)),catalog((self.pc,self.local,self.pause,self.tree,self.resume)))
 def capture(self):
  with patch('expedition33.values.capture_selected_values',side_effect=self.responses) as selected,patch('expedition33.values.read_values_with_references',return_value=self.pause_result),patch.object(m,'capture_matching') as scan:
   result=m._current_widgets(N(pid=7),(7,1,1,self.pc.address))
  scan.assert_not_called()
  return result,selected
 def test_resume_named_slot_and_live_slots_reach_exact_pause_owned_style_source(self):
  result,selected=self.capture()
  self.assertEqual(result.by_index[8],self.text);self.assertEqual(selected.call_count,4)
  self.assertEqual([call.args[1][0][0] for call in selected.call_args_list],[1,5,6,7])
 def test_truncated_named_slot_array_is_never_treated_as_complete(self):
  from expedition33.values import StoredArray
  row=self.responses[1][1][5];key=next(iter(row.values));row.values[key]=StoredArray(row.values[key].items,2)
  with self.assertRaisesRegex(RuntimeQueryError,'array bound'):self.capture()
 def test_wrong_style_source_class_rejects_before_construction(self):
  from dataclasses import replace
  wrong=replace(self.text,class_index=999)
  self.responses[-1]=(self.catalog((self.slot,wrong)),{7:self.row(self.slot,Content=('ObjectProperty',wrong))})
  with self.assertRaisesRegex(RuntimeQueryError,'class changed'):self.capture()
