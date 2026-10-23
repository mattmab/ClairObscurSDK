from contextlib import nullcontext
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,patch

from expedition33 import ui_shell_proof as proof, world_admission as world, ui_admission as ui

def ident(n):return (7,n,10+n,0x1000+n)

class PacketTests(unittest.TestCase):
    def test_world_packet_copies_gi_local_controller_identity_not_live_handles(self):
        w=N(pid=7,index=3,serial=13,address=0x1003,class_name='World')
        pc=N(index=4);cat=N(by_index={4:pc,9:object()},outer_chain=lambda obj:(w,))
        admission=world.Admission('world_ready','ready',(ident(3),ident(2),ident(8),0),True)
        observer=ui.UiAdmissionObserver.__new__(ui.UiAdmissionObserver)
        observer.pid=7;observer._reader=N(bind=lambda:nullcontext())
        observer._ui_controller=ident(4);observer._ui_local_player=ident(5)
        with patch.object(ui.WarmAdmissionObserver,'observe',return_value=admission), \
                patch.object(ui,'capture_selected',return_value=cat), \
                patch.object(ui,'read_values_many',return_value={4:N(types={(9,'PauseMenuWidget'):'ObjectProperty'})}), \
                patch.object(ui,'read_object_reference',return_value=(N(class_name='WBP_PauseMenu_C'),cat)):
            packet=observer.observe()
        self.assertEqual(packet.ui_context.signature,('world',ident(3),ident(2),ident(5),ident(4)))
        self.assertTrue(packet.menu_ready)

    def test_title_packet_requires_anchor_world_equal_current_title_binding(self):
        from expedition33 import title_menu
        for anchored,expected in ((ident(3),True),(ident(9),False)):
            observer=ui.UiAdmissionObserver.__new__(ui.UiAdmissionObserver)
            observer.pid=7;observer._reader=N(bind=lambda:nullcontext())
            observer._ui_anchor=(ident(10),ident(11),anchored,ident(2))
            observer._title_binding=({'world':ident(3),'controller':ident(4)},ident(5)[1:],
                ident(6)[1:],ident(7)[1:],ident(8)[1:])
            with patch.object(title_menu,'title_authority_current',return_value=True):
                result=observer._title_observation(world.Admission('inactive','save_not_loaded'))
            self.assertEqual(result.ui_context is not None,expected)
            if expected:self.assertEqual(result.ui_context.signature,('title',ident(3),ident(2),ident(5),ident(4)))

    def test_loading_packet_never_has_a_construction_context(self):
        observer=ui.UiAdmissionObserver.__new__(ui.UiAdmissionObserver)
        with patch.object(ui.WarmAdmissionObserver,'observe',return_value=world.Admission('loading','test')):
            packet=observer.observe()
        self.assertIsNone(packet.ui_context);self.assertFalse(packet.menu_ready)

if __name__=='__main__':unittest.main()
