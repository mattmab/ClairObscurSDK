import io,struct,unittest,threading
from types import SimpleNamespace
from expedition33.qa_encounter import validate_request
from expedition33._session import SessionTransport

class QAEncounterTests(unittest.TestCase):
 def packet(self,op=1):
  return struct.pack('<4I',1,op,0,0)+struct.pack('<iiQ',1,2,4096)*5+bytes(8)
 def test_operations_admitted_to_transport(self):
  for op in (1,2,3,4):
   t=object.__new__(SessionTransport);t._owner=threading.get_ident();t._closed=False;t.qa_encounter_protocol=1
   t._process=SimpleNamespace(stdin=io.StringIO())
   t._read=lambda:{'event':'session_response','command':'qa-encounter-reset','closed':False}
   t._command('qa-encounter-reset',self.packet(op))
   self.assertEqual(t._process.stdin.getvalue(),'qa-encounter-reset '+self.packet(op).hex()+'\n')
 def test_malformed_packets_rejected(self):
  p=self.packet()
  for bad in (p[:-1],self.packet(5),p[:16]+bytes(16)+p[32:],p[:-1]+b'\x01'):
   with self.assertRaises(ValueError):validate_request(bad)
 def test_capability_required(self):
  t=object.__new__(SessionTransport);t._owner=threading.get_ident();t._closed=False
  with self.assertRaises(ValueError):t._command('qa-encounter-reset',self.packet())
