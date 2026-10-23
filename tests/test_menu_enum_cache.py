import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch,Mock
from expedition33 import menu

class MenuEnumCacheTests(unittest.TestCase):
 def test_primed_plan_cache_skips_enum_read_and_enum_identity_change_invalidates(self):
  objects=[]
  def row(name,**kw):
   kw.setdefault('class_name','Object');kw.setdefault('outer_index',0)
   result=NS(pid=1,index=len(objects)+1,serial=10,address=0x10000+len(objects)*16,name=name,object_flags=0,**kw);objects.append(result);return result
  widget=row('widget');child=row('child');player=row('player')
  engine=row('engine',class_name='GameEngine');library=row('Default__WidgetBlueprintLibrary',class_name='WidgetBlueprintLibrary')
  enum=row('EMouseLockMode',class_name='Enum')
  classes={name:row(name) for name in ('UserWidget','Widget','CommonActivatableWidget','WidgetBlueprintLibrary')}
  for owner,names in {'UserWidget':['AddToViewport'],'Widget':['IsInViewport','SetUserFocus','HasKeyboardFocus','HasUserFocus','RemoveFromParent'],'CommonActivatableWidget':['ActivateWidget','IsActivated','DeactivateWidget'],'WidgetBlueprintLibrary':['SetFocusToGameViewport','SetInputMode_UIOnlyEx','SetInputMode_GameOnly']}.items():
   for name in names:row(name,outer_index=classes[owner].index)
  class Catalog:
   pid=1
   def __init__(self):self.objects=objects
   def resolve(self,obj):return obj
   def select(self,cls):return [engine] if cls=='GameEngine' else [library]
   def find_class(self,cls):return classes[cls]
  leases=[NS(active=True,object=widget),NS(active=True,object=child)]
  session=NS(pid=1,_check=lambda:None,_transport=NS(menu_protocol=1,menu_input_protocol=1),_menus=set(),_leases=leases)
  descriptor=Mock();descriptor.value.return_value=object()
  with patch('expedition33.catalog.Catalog',Catalog),patch('expedition33.enums.describe_enums',return_value={enum.index:descriptor}) as read,patch('expedition33.menu.prepare_call',return_value=NS(wire_version=1)),patch('expedition33.menu.encode_plan',return_value=bytes(24648)):
   for _ in range(2):menu.prepare(session,widget,child,player,leases,catalog=Catalog(),_plan_only=True)
   self.assertEqual(read.call_count,1)
   enum.serial+=1
   menu.prepare(session,widget,child,player,leases,catalog=Catalog(),_plan_only=True)
   self.assertEqual(read.call_count,2)

if __name__=='__main__':unittest.main()
