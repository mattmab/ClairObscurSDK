"""Exercise the transport gate, not only each packet serializer."""
import io,threading,unittest
from types import SimpleNamespace as N
from expedition33._session import SessionTransport
import test_story_cinematic_routes as routes

class GenericStoryTransport(unittest.TestCase):
 def transport(self,capability,version):
  t=SessionTransport.__new__(SessionTransport);t._owner=threading.get_ident();t._closed=False;t.mesh_protocol=3
  t._process=N(stdin=io.StringIO());setattr(t,capability,version)
  t._read=lambda:dict(event='session_response',command='mesh',closed=False)
  t._abort=lambda:setattr(t,'_closed',True)
  return t
 def test_updated_capabilities_dispatch_and_old_ones_reject_before_send(self):
  from expedition33.party import packet
  h=lambda i:N(object=N(index=i,serial=2,address=65536+i*16),_token=i+10)
  cases=[('story_cinematic_routes_protocol',bytes(routes.CinematicWireTests().packet(routes=1))),
         ('story_party_join_data_protocol',packet(99,h(1),h(2),h(3),'e33c5701000000010000000200000003',character='TestGuardian'))]
  from expedition33.inventory_rewards import packet as reward
  from test_enemy_loot_overlay import EnemyLootTests
  from test_story_character_tables import CharacterWire
  cases.extend([
   ('inventory_reward_protocol',reward(99,h(1),h(2),h(3),'e33c5701000000010000000200000003',item='TestReward')),
   ('story_enemy_loot_protocol',EnemyLootTests().packet()),
   ('story_character_tables_protocol',CharacterWire().sent('DT_jRPG_CharacterDefinitions'))])
  from test_encounter_action import EncounterActionWire
  from test_encounter_tables import Tests as EncounterTableWire
  cases.extend([('story_trial_data_protocol',EncounterActionWire().packet()),
                ('story_trial_tables_protocol',EncounterTableWire().make())])
  for cap,payload in cases:
   t=self.transport(cap,2);t.command('mesh',payload)
   self.assertEqual(t._process.stdin.getvalue(),'mesh '+payload.hex()+'\n')
   for version in (0,1):
    t=self.transport(cap,version)
    with self.assertRaises(ValueError):t.command('mesh',payload)
    self.assertEqual(t._process.stdin.getvalue(),'')
