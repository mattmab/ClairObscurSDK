from unittest.mock import patch
from test_title_menu import TitleAttachmentTests
from expedition33 import _metadata_stabilization as metadata
class MetadataTitleHookTests(TitleAttachmentTests):
 def test_preparation_precedes_planner_and_owned_widget_mutation(self):
  self.parent._session._transport.metadata_stabilization_protocol=1
  self.scope.invocation_planner=lambda **kw:self.events.append('planner') or self.planner
  def prepare(session,discover):
   self.assertEqual(self.events,[])
   discover();self.events.append('metadata')
   return discover(),()
  import importlib
  current_metadata=importlib.import_module('expedition33._metadata_stabilization')
  with patch.object(current_metadata,'prepare_discovery',side_effect=prepare) as prepared:
   self.assertTrue(self.install())
  prepared.assert_called_once()
  self.assertLess(self.events.index('metadata'),self.events.index('planner'))
  self.assertLess(self.events.index('planner'),self.events.index('Create'))
