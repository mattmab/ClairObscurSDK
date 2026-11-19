import struct,unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace as N
from expedition33 import story_character_tables as w

PROFILES={'DT_jRPG_CharacterDefinitions': {'source_package': '/Game/SDK/Sample/DT_jRPG_CharacterDefinitions', 'row': 'TestScholar'}, 'DT_jRPG_CharacterSaveStates': {'source_package': '/Game/SDK/Sample/DT_jRPG_CharacterSaveStates', 'row': 'TestScholar'}, 'DT_jRPG_WorldCharacters': {'source_package': '/Game/SDK/Sample/DT_jRPG_WorldCharacters', 'row': 'TestScholar'}, 'DT_WeaponDefinitions': {'source_package': '/Game/Gameplay/Pictos/Gear/Weapons/DT_WeaponDefinitions', 'row': 'TestScholar_Wand', 'template': 'ExampleSword'}}

def h(i):return N(object=N(index=i,serial=2,address=65536+i*16),_token=i+10)
class CharacterWire(unittest.TestCase):
 def sent(self,asset):return w.packet(99,dict(asset=asset,profile=PROFILES[asset],target=h(1),source=h(2),map_class=h(3),map_add=h(4)),h(5),'e33c5701000000010000000200000003',0)
 def test_only_reviewed_profiles_and_selected_identity(self):
  for asset in PROFILES:
   data=self.sent(asset);w.validate(data)
   for at in (4,136,392,2048,2159):
    bad=bytearray(data);bad[at]^=1
    with self.assertRaises(ValueError):w.validate(bytes(bad))
 def test_different_consumer_rows_and_templates_use_the_same_api(self):
  for name in ('TestScholar','TestGuardian'):
   asset='DT_jRPG_CharacterDefinitions'
   profile=dict(source_package='/Game/SDK/Other/'+asset,row=name)
   row=dict(asset=asset,profile=profile,target=h(1),source=h(2),map_class=h(3),map_add=h(4))
   data=w.packet(99,row,h(5),'e33c5701000000010000000200000003',0);w.validate(data)
   self.assertEqual(data[488:584].split(b'\0',1)[0].decode(),name)
  for invalid in ({}, {'Unsupported':{}},dict(PROFILES,DT_WeaponDefinitions=dict(PROFILES['DT_WeaponDefinitions'],template='bad/name'))):
   with self.assertRaises(ValueError):w.validate_profiles(invalid)
 def test_replaces_only_existing_character_rows_adds_one_weapon(self):
  for asset in PROFILES:
   data=self.sent(asset);reply=bytearray(data);struct.pack_into('<I',reply,12,1)
   delta=int(asset=='DT_WeaponDefinitions');struct.pack_into('<2I',reply,128,10,10+delta)
   self.assertEqual(w.decode(data,bytes(reply))['registered_rows'],10+delta)
   struct.pack_into('<I',reply,132,12)
   with self.assertRaises(RuntimeError):w.decode(data,bytes(reply))
 def test_ack_cannot_substitute_source_or_save(self):
  data=self.sent(next(iter(PROFILES)));reply=bytearray(data);struct.pack_into('<I',reply,12,1);struct.pack_into('<2I',reply,128,10,10)
  reply[2049]^=1
  with self.assertRaises(RuntimeError):w.decode(data,bytes(reply))

class CharacterPreparation(unittest.TestCase):
 def owner(self):
  owner=w.CharacterTables.__new__(w.CharacterTables)
  owner.profiles=w.validate_profiles(PROFILES)
  owner.key='e33c5701000000010000000200000003'
  owner.held=[];owner._held_by_identity={};owner.rows=[];owner.unknown=False;owner.closed=False
  owner.inputs_ready=False;owner.resolution_attempted=False;owner.preparation_error=None
  owner.definitions=N(map_class=h(10),map_add=h(11))
  owner.resources=N(gi=h(12).object,load=Mock(side_effect=lambda path:h(20+owner.resources.load.call_count).object))
  def hold(obj):
   result=N(object=obj,_token=obj.index+100);owner.held.append(result);return result
  owner.hold=hold;calls=[]
  def command(name,sent):
   self.assertEqual(name,'mesh');self.assertTrue(owner.inputs_ready)
   self.assertEqual(owner.resources.load.call_count,8) # No table edit during resolution.
   asset=sent[392:488].split(b'\0',1)[0].decode();mode=struct.unpack_from('<I',sent,120)[0]
   calls.append((asset,mode));reply=bytearray(sent)
   struct.pack_into('<I',reply,12,mode+1);struct.pack_into('<2I',reply,128,10,10+(asset=='DT_WeaponDefinitions'))
   return {'mesh_packet':bytes(reply).hex()}
  owner.scope=N(_session=N(_transport=N(command=Mock(side_effect=command))),close=Mock())
  return owner,calls
 def test_all_inputs_resolved_before_first_row_and_acknowledged_rows_never_replay(self):
  o,calls=self.owner();o.prepare()
  self.assertTrue(o.ready);self.assertEqual(o.state,'registered');self.assertEqual(len(calls),4)
  self.assertTrue(all(r['attempted'] and r['acknowledged'] and r['started'] for r in o.rows))
  o.prepare();self.assertEqual(len(calls),4);self.assertEqual(o.resources.load.call_count,8)
 def test_resource_failure_leaves_all_tables_untouched_and_is_not_retried(self):
  o,calls=self.owner();load=o.resources.load.side_effect
  def fail(path):
   if o.resources.load.call_count==3:raise RuntimeError('unresolved resource outcome')
   return load(path)
  o.resources.load.side_effect=fail
  with self.assertRaisesRegex(RuntimeError,'unresolved resource'):o.prepare()
  self.assertEqual(calls,[]);self.assertFalse(o.ready);self.assertEqual(o.state,'failed')
  self.assertTrue(all(not row['attempted'] for row in o.rows))
  with self.assertRaisesRegex(RuntimeError,'unavailable'):o.prepare()
  self.assertEqual(o.resources.load.call_count,3)
 def test_initial_read_only_context_failure_has_no_native_attempt(self):
  from expedition33 import RuntimeQueryError
  from expedition33.story_preflight import PreflightReadDeferred
  o,calls=self.owner();o.resources.gi=None
  with patch('expedition33.story_save_identity.observe',side_effect=RuntimeQueryError('loading read race')):
   with self.assertRaises(PreflightReadDeferred):o.prepare()
  self.assertFalse(o.resolution_attempted);self.assertEqual(o.rows,[]);self.assertEqual(o.held,[])
  self.assertIsNone(o.preparation_error);self.assertEqual(calls,[])
  o.resources.gi=h(12).object;o.prepare();self.assertTrue(o.ready)
 def test_known_row_rejection_retains_prefix_for_acknowledged_reverse_cleanup(self):
  o,calls=self.owner();dispatch=o.scope._session._transport.command.side_effect
  def reject(name,sent):
   if struct.unpack_from('<I',sent,120)[0]==0 and len(calls)==1:
    calls.append(('rejected',0));reply=bytearray(sent);struct.pack_into('<I',reply,8,4250)
    return {'mesh_packet':bytes(reply).hex()}
   return dispatch(name,sent)
  o.scope._session._transport.command.side_effect=reject
  with self.assertRaises(w.wire.OriginalNarrativeError):o.prepare()
  self.assertFalse(o.unknown);self.assertFalse(o.ready);self.assertEqual(o.state,'failed')
  self.assertTrue(o.rows[0]['acknowledged']);self.assertTrue(o.rows[1]['attempted']);self.assertFalse(o.rows[1]['acknowledged'])
  self.assertFalse(o.rows[2]['attempted'])
  with self.assertRaises(RuntimeError):o.prepare()
  self.assertEqual(len(calls),2)
  self.assertTrue(o.close());self.assertEqual(calls[-1],(next(iter(PROFILES)),2));o.scope.close.assert_called_once()
 def test_unknown_row_outcome_preserves_native_owner_and_never_replays(self):
  o,calls=self.owner();dispatch=o.scope._session._transport.command.side_effect
  def uncertain(name,sent):
   if len(calls)==1:
    calls.append(('uncertain',0));reply=bytearray(sent);struct.pack_into('<I',reply,8,4251)
    return {'mesh_packet':bytes(reply).hex()}
   return dispatch(name,sent)
  o.scope._session._transport.command.side_effect=uncertain
  with self.assertRaises(w.wire.OriginalNarrativeError):o.prepare()
  self.assertTrue(o.unknown);self.assertEqual(o.state,'unknown');self.assertFalse(o.close())
  with self.assertRaises(RuntimeError):o.prepare()
  self.assertEqual(len(calls),2);o.scope.close.assert_not_called()
 def test_packet_validation_finishes_for_every_row_before_dispatch(self):
  o,calls=self.owner();real=w.packet
  def reject(owner,row,*args):
   if row['asset']=='DT_WeaponDefinitions':raise ValueError('bad last row')
   return real(owner,row,*args)
  with patch.object(w,'packet',side_effect=reject):
   with self.assertRaisesRegex(ValueError,'bad last row'):o.prepare()
  self.assertEqual(calls,[]);self.assertFalse(o.ready);self.assertTrue(all(not r['attempted'] for r in o.rows))

