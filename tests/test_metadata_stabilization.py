import struct,sys,unittest
from types import SimpleNamespace as NS
from contextlib import nullcontext
from unittest.mock import patch
from expedition33 import _metadata_stabilization as metadata

class Session:
 def __init__(self):self.pid=1;self._leases=set();self._closed=False;self.aborted=False;self._transport=NS(metadata_stabilization_protocol=1,_closed=False)
 def _check(self):pass
 def _abort_ownership(self):self.aborted=True
class Scope:
 def __init__(self):self._leases=[];self._closed=False
 def _lease_context(self):return nullcontext()

def reply(sent,*,fail=None):
 raw=bytearray(sent);count=metadata.HEADER.unpack_from(sent)[1];completed=count if fail is None else fail
 metadata.HEADER.pack_into(raw,0,1,count,0 if fail is None else 3922,completed,completed,0 if fail is None else fail)
 for i in range(completed):
  old=metadata.ROW.unpack_from(sent,metadata.HEADER.size+i*metadata.ROW.size)
  metadata.ROW.pack_into(raw,metadata.HEADER.size+i*metadata.ROW.size,*old[:3],old[0],old[1] or 1001+i,old[2],i+1,3922 if i+1==fail else 0,2 if i+1==fail else 1)
 return raw.hex()

class MetadataTests(unittest.TestCase):
 def test_batch_bounds_and_entire_input_validation(self):
  ids=[(i,0,0x10000+i*16) for i in range(128)]
  sent=metadata.request(ids);metadata.validate_request(sent)
  ack=metadata.decode(sent,reply(sent));self.assertEqual(ack['completed'],128)
  for invalid in ([],ids+[(129,0,0x20000)],[(1,0,0x10000)]*2,[(1,-1,0x10000)],[(1,0,0x10001)]):
   with self.assertRaises(ValueError):metadata.request(invalid)
 def test_reply_rejects_changed_identity_stale_zero_duplicate_tokens_and_suffix(self):
  sent=metadata.request([(1,0,0x10000),(2,8,0x10010)])
  good=bytearray.fromhex(reply(sent))
  for offset,value,fmt in ((metadata.HEADER.size,3,'<i'),(metadata.HEADER.size+20,0,'<i'),(metadata.HEADER.size+metadata.ROW.size+32,1,'<Q')):
   bad=good.copy();struct.pack_into(fmt,bad,offset,value)
   with self.assertRaises(ValueError):metadata.decode(sent,bad.hex())
  unknown=bytearray.fromhex(reply(sent,fail=1));metadata.decode(sent,unknown.hex())
  struct.pack_into('<I',unknown,metadata.HEADER.size+metadata.ROW.size+44,1)
  with self.assertRaises(ValueError):metadata.decode(sent,unknown.hex())
 def test_adopts_every_token_before_fresh_read_and_keeps_process_owner(self):
  session=Session();owner=metadata.MetadataPreparation.__new__(metadata.MetadataPreparation);owner.session=session;owner.scope=Scope();owner._known={};owner._journal=[]
  old=[NS(index=i,serial=0,address=0x10000+i*16,name='Fn'+str(i)) for i in (1,2)]
  fresh=[NS(index=o.index,serial=1001+i,address=o.address,name=o.name) for i,o in enumerate(old)]
  catalog=NS(path_name=lambda o:'/Script/UMG.Widget:'+o.name)
  current=NS(by_index={o.index:o for o in fresh},path_name=catalog.path_name)
  session._transport.command=lambda command,sent:{'metadata_stabilization_packet':reply(sent)}
  def read(pid,ids):
   self.assertEqual(len(session._leases),2);self.assertEqual(len(owner.scope._leases),2)
   self.assertFalse(session.aborted);return current
  with patch.object(metadata,'script_function',side_effect=lambda c,o:o),patch('expedition33.catalog.capture_selected',side_effect=read) as capture:
   self.assertIs(owner.prepare(catalog,old),current)
   self.assertEqual(capture.call_count,2)
  self.assertTrue(all(lease.active and lease.object in fresh for lease in owner.scope._leases))
  self.assertFalse(session.aborted)
 def test_partial_failure_adopts_known_tokens_before_abort_and_never_reads_or_replays(self):
  session=Session();owner=metadata.MetadataPreparation.__new__(metadata.MetadataPreparation);owner.session=session;owner.scope=Scope();owner._known={};owner._journal=[]
  old=[NS(index=i,serial=0,address=0x10000+i*16,name='Fn'+str(i)) for i in (1,2)]
  calls=[]
  def command(op,sent):calls.append(op);return {'metadata_stabilization_packet':reply(sent,fail=1)}
  session._transport.command=command
  with patch.object(metadata,'script_function',side_effect=lambda c,o:o),patch('expedition33.catalog.capture_selected') as capture:
   with self.assertRaises(Exception):owner.prepare(NS(),old)
   capture.assert_not_called()
  self.assertTrue(session.aborted);self.assertEqual(len(session._leases),1);self.assertEqual(calls,['metadata-stabilize'])
 def test_script_kinds_and_native_cdo_admission(self):
  package=NS(index=3,class_name='Package',outer_index=-1)
  cls=NS(index=2,class_name='Class',outer_index=3,name='WidgetBlueprintLibrary')
  catalog=NS(resolve=lambda o:o,by_index={2:cls,3:package},path_name=lambda o:'/Script/UMG')
  for kind in ('Class','Enum','ScriptStruct'):
   obj=NS(class_name=kind,outer_index=3,object_flags=0)
   self.assertIs(metadata.script_function(catalog,obj),obj)
  cdo=NS(class_name='WidgetBlueprintLibrary',class_index=2,outer_index=3,object_flags=0x10,name='Default__WidgetBlueprintLibrary')
  self.assertIs(metadata.script_function(catalog,cdo),cdo)
  for mutation in ('flag','name','package','blueprint'):
   candidate=NS(**vars(cdo));parent=NS(**vars(cls));catalog.by_index[2]=parent
   if mutation=='flag':candidate.object_flags=0
   if mutation=='name':candidate.name='Default__Other'
   if mutation=='package':candidate.outer_index=4
   if mutation=='blueprint':parent.class_name='BlueprintGeneratedClass'
   with self.assertRaises(ValueError):metadata.script_function(catalog,candidate)
 def test_exact_style_paths_require_native_common_text_style_and_reject_before_command(self):
  script=NS(index=4,class_name='Package',outer_index=-1)
  package=NS(index=3,class_name='Package',outer_index=-1)
  parent=NS(index=2,class_name='Class',name='CommonTextStyle',outer_index=4)
  obj=NS(index=1,serial=0,address=0x10000,class_name='BlueprintGeneratedClass',name='CTS_H2_Outline_C',outer_index=3,object_flags=0)
  path=next(p for p in metadata.STYLE_PATHS if 'CTS_H2_' in p)
  catalog=NS(resolve=lambda o:o,by_index={2:parent,3:package,4:script},ancestors=lambda i:(1,2),path_name=lambda o:path if o is obj else '/Script/CommonUI')
  catalog.by_index[1]=obj
  self.assertIs(metadata.script_function(catalog,obj),obj)
  session=Session();session._transport.command=lambda *args:self.fail('rejected input must not reach native mutation')
  owner=metadata.MetadataPreparation.__new__(metadata.MetadataPreparation);owner.session=session;owner.scope=Scope();owner._known={};owner._journal=[]
  for mutation in ('path','parent','world','widget','cdo'):
   bad=NS(**vars(obj));ancestor=NS(**vars(parent));catalog.by_index[2]=ancestor
   catalog.path_name=lambda o:path if o is bad else '/Script/CommonUI'
   if mutation=='path':catalog.path_name=lambda o:'/Game/UI/Other.Other_C' if o is bad else '/Script/CommonUI'
   if mutation=='parent':ancestor.name='OtherStyle'
   if mutation=='world':package.outer_index=9
   if mutation=='widget':bad.class_name='WidgetBlueprintGeneratedClass';bad.class_index=2
   if mutation=='cdo':bad.class_name='CTS_H2_Outline_C';bad.name='Default__CTS_H2_Outline_C';bad.class_index=1;bad.object_flags=0x10
   with self.assertRaises(ValueError):owner.prepare(catalog,(bad,))
   package.outer_index=-1
 def test_discovery_discards_old_catalog_and_rebuilds_before_returning(self):
  session=Session()
  old=NS(index=1,serial=0,address=0x10000,name='Fn',class_name='Function',object_flags=0)
  new=NS(**{**vars(old),'serial':1002})
  first=NS(objects=(old,),by_index={1:old},path_name=lambda o:'/Script/UMG.Widget:Fn')
  fresh=NS(objects=(new,),by_index={1:new},path_name=first.path_name)
  calls=[]
  def discover():calls.append('discover');return first if len(calls)==1 else fresh
  owner=NS(prepare=lambda c,items:fresh)
  with patch.object(metadata,'script_function',side_effect=lambda c,o:o),patch.object(metadata,'process_preparation',return_value=owner):
   result,uncovered=metadata.prepare_discovery(session,discover)
  self.assertIs(result,fresh);self.assertIsNot(result,first);self.assertEqual(calls,['discover','discover']);self.assertEqual(uncovered,())
  with patch.object(metadata,'script_function',side_effect=lambda c,o:o),patch.object(metadata,'process_preparation',return_value=owner):
   with self.assertRaises(Exception):metadata.prepare_discovery(session,lambda:first)
 def test_process_owner_is_independent_of_world_scope(self):
  from expedition33._scope import SessionScope
  session=Session();session.console=NS();session._transport._check_thread=lambda:None
  owner=metadata.process_preparation(session)
  world=SessionScope(session);world.close()
  self.assertFalse(owner.scope._closed)
  self.assertIs(metadata.process_preparation(session),owner)
  owner.close();self.assertTrue(owner.scope._closed)
 def test_script_provenance_rejects_blueprint_world_unknown_module_and_forbidden(self):
  package=NS(index=3,class_name='Package',outer_index=-1)
  owner=NS(index=2,class_name='Class',outer_index=3)
  fn=NS(index=1,class_name='Function',outer_index=2,object_flags=0)
  catalog=NS(resolve=lambda o:o,by_index={2:owner,3:package},path_name=lambda o:'/Script/UMG')
  self.assertIs(metadata.script_function(catalog,fn),fn)
  owner.class_name='BlueprintGeneratedClass'
  with self.assertRaises(ValueError):metadata.script_function(catalog,fn)
  owner.class_name='Class';catalog.path_name=lambda o:'/Game/World'
  with self.assertRaises(ValueError):metadata.script_function(catalog,fn)
  catalog.path_name=lambda o:'/Script/Unapproved'
  with self.assertRaises(ValueError):metadata.script_function(catalog,fn)
  catalog.path_name=lambda o:'/Script/UMG';fn.object_flags=0x40000000
  with self.assertRaises(ValueError):metadata.script_function(catalog,fn)
if __name__=='__main__':unittest.main()
