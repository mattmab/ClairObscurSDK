"""Immutable Character preparation must never install gameplay owners at title."""
import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import battle_qte as combat,character_skills as skills

from skill_samples import PROFILE as SKILLS
from test_battle_qte import PROFILE as COMBAT

class CharacterPreflightTests(unittest.TestCase):
 def resources(self):
  transport=N(battle_qte_protocol=3,character_skills_protocol=3,command=Mock())
  resources=N(scope=N(_check=Mock(),pid=1,_session=N(_transport=transport)),held={})
  def hold(obj):
   if obj.path not in resources.held:resources.held[obj.path]=N(object=obj,active=True)
   return resources.held[obj.path]
  resources.hold=Mock(side_effect=hold)
  resources.load=Mock(side_effect=lambda path,**kw:N(path=path))
  catalog=N(find_path=Mock(side_effect=lambda path:N(path=path)))
  return resources,catalog
 def test_warm_retains_required_assets_without_gi_hooks_or_native_dispatch(self):
  for module,count,loads in ((skills,80,34),(combat,9,2)):
   with self.subTest(module=module.__name__):
    resources,catalog=self.resources()
    with patch('expedition33.catalog.capture_matching',return_value=catalog) as capture:
     first=module.warm(resources,profile=SKILLS if module is skills else COMBAT);second=module.warm(resources,profile=SKILLS if module is skills else COMBAT)
    self.assertEqual(first,second);self.assertEqual(len(first),count)
    self.assertEqual(resources.load.call_count,loads);capture.assert_called_once()
    resources.scope._session._transport.command.assert_not_called()
    self.assertFalse(hasattr(resources,'gi'))
    if module is skills:self.assertIsNone(first[0])
 def test_partial_dependency_failure_is_retained_not_replayed(self):
  for module in (skills,combat):
   with self.subTest(module=module.__name__):
    resources,catalog=self.resources()
    resources.load.side_effect=[N(path='first retained asset'),RuntimeError('load failed after first asset')]
    with patch('expedition33.catalog.capture_matching',return_value=catalog):
     with self.assertRaisesRegex(RuntimeError,'load failed'):module.warm(resources,profile=SKILLS if module is skills else COMBAT)
     with self.assertRaisesRegex(RuntimeError,'Incomplete'):module.warm(resources,profile=SKILLS if module is skills else COMBAT)
    self.assertEqual(resources.load.call_count,2)
    self.assertTrue(resources.held['first retained asset'].active)
    resources.scope._session._transport.command.assert_not_called()
 def test_expired_immutable_lease_rejects_reuse_without_reloading(self):
  for module in (skills,combat):
   with self.subTest(module=module.__name__):
    resources,catalog=self.resources()
    with patch('expedition33.catalog.capture_matching',return_value=catalog):module.warm(resources,profile=SKILLS if module is skills else COMBAT)
    next(iter(resources.held.values())).active=False
    before=resources.load.call_count
    with self.assertRaisesRegex(RuntimeError,'lease expired'):module.warm(resources,profile=SKILLS if module is skills else COMBAT)
    self.assertEqual(resources.load.call_count,before)
 def test_owner_still_installs_once_using_current_gi_after_process_warm(self):
  for module,owner_type in ((skills,skills.CharacterSkills),(combat,combat.BattleQTE)):
   with self.subTest(module=module.__name__):
    resources,catalog=self.resources()
    with patch('expedition33.catalog.capture_matching',return_value=catalog) as capture:
     module.warm(resources,profile=SKILLS if module is skills else COMBAT)
     old_load_count=resources.load.call_count
     resources.gi=N(path='current game instance')
     owner=owner_type.__new__(owner_type);owner.profile=SKILLS if module is skills else COMBAT;owner.scope=resources.scope;owner.resources=resources
     owner.started=False;owner.held=[];owner.send=Mock()
     def hold(obj):
      held=resources.hold(obj);owner.held.append(held);return held
     owner.hold=hold;owner.prepare()
     self.assertTrue(owner.started);owner.send.assert_called_once_with(0)
     self.assertIs(owner.objects[0].object,resources.gi)
     self.assertEqual(resources.load.call_count,old_load_count);capture.assert_called_once()
     with self.assertRaisesRegex(RuntimeError,'one-shot'):owner.prepare()
 def test_missing_native_capability_loads_nothing(self):
  for module,field in ((skills,'character_skills_protocol'),(combat,'battle_qte_protocol')):
   with self.subTest(module=module.__name__):
    resources,_=self.resources();setattr(resources.scope._session._transport,field,0)
    with self.assertRaises(RuntimeError):module.warm(resources,profile=SKILLS if module is skills else COMBAT)
    resources.load.assert_not_called();resources.hold.assert_not_called()
 def test_previous_skill_protocol_cannot_load_new_packet_or_install_hooks(self):
  resources,_=self.resources();resources.scope._session._transport.character_skills_protocol=1
  with self.assertRaisesRegex(RuntimeError,'protocol 3'):skills.warm(resources,profile=SKILLS)
  owner=skills.CharacterSkills.__new__(skills.CharacterSkills);owner.scope=resources.scope
  with self.assertRaisesRegex(RuntimeError,'protocol 3'):owner.prepare()
  resources.load.assert_not_called();resources.hold.assert_not_called()

if __name__=='__main__':unittest.main()
