import struct,unittest
from expedition33.story_cinematic_routes import validate,SIZE
class CinematicWireTests(unittest.TestCase):
    def test_invalid_admission_never_pollutes_guid_inventory(self):
        from unittest.mock import Mock
        from expedition33.story_cinematic_routes import CinematicRoutes
        owner=CinematicRoutes.__new__(CinematicRoutes);owner.keys={'e33c5701000000000000000000000001'};owner.send=Mock()
        before=set(owner.keys)
        with self.assertRaises((ValueError,TypeError,AttributeError)):owner.allow(None)
        self.assertEqual(owner.keys,before);owner.send.assert_not_called()
    def test_new_game_confirms_playthrough_identity_before_runtime_activation(self):
        from types import SimpleNamespace as N
        from unittest.mock import Mock,patch
        from expedition33.new_game_story import NewGameStories,Choice
        guid='e33c5701000000000000000000000001';router=N(allow=Mock(),closed=False)
        owner=NewGameStories.__new__(NewGameStories);owner.poll=lambda:None;owner.error=None
        owner.choice=Choice();owner.choice.register('sample.story','Sample Story');owner.choice.index=1;owner.choice.pending=(9,'sample.story')
        owner.session=N(pid=123);owner._cinematic_binding=('sample.story',router)
        live=N(resolved=True,candidate=guid,identity=N(scope=object(),read=lambda:None),
               runtime=N(key=None),playthroughs=N(key=guid),choices=lambda:{'token':'qa'},choose=Mock())
        gi=N(index=1,serial=11,address=0x10000);manager=N(index=2,serial=22,address=0x20000)
        reads=[(N(values={(1,'SaveManager'):manager}),N()),(N(values={(2,'SelectedSlot'):9}),N())]
        with patch('expedition33.story_save_identity.observe',return_value=(None,None,None,None,gi,None)),patch('expedition33.catalog.capture_selected',return_value=N()),patch('expedition33.values.read_values_with_references',side_effect=reads):
            self.assertTrue(owner.consume(live))
        router.allow.assert_called_once_with(guid)
    def packet(self,mode=0,routes=5):
        p=bytearray(SIZE);struct.pack_into('<4IQ',p,0,3,269,0,0,123)
        for i in range(6+2*routes):struct.pack_into('<iiQ',p,24+i*16,i+1,i+100,0x10000+i*8)
        struct.pack_into('<'+str(6+2*routes)+'Q',p,280,*range(1,7+2*routes));struct.pack_into('<I',p,1492,routes);struct.pack_into('<2I',p,408,mode,1)
        struct.pack_into('<4I',p,416,0xe33c5701,2,3,4)
        return p
    def test_fixed_owned_routes_and_exact_save_keys(self):
        for mode in (0,1,2,4):validate(bytes(self.packet(mode)))
        p=self.packet();struct.pack_into('<I',p,416,0)
        with self.assertRaises(ValueError):validate(bytes(p))
    def test_key_overflow_or_unowned_routes_rejected(self):
        for offset,value in ((412,65),(408,5),(280,0)):
            p=self.packet();struct.pack_into('<I',p,offset,value)
            with self.assertRaises(ValueError):validate(bytes(p))
    def test_menu_requires_exact_live_identities_and_selection_bounds(self):
        p=self.packet(3)
        for i in range(2):struct.pack_into('<iiQ',p,1440+i*16,101+i,201+i,0x20000+i*8)
        struct.pack_into('<3I',p,1472,1,2,1);validate(bytes(p))
        struct.pack_into('<I',p,1472,2)
        with self.assertRaises(ValueError):validate(bytes(p))
        struct.pack_into('<I',p,1472,0);struct.pack_into('<i',p,1444,0)
        with self.assertRaises(ValueError):validate(bytes(p))
    def test_native_direction_receiver_is_only_admitted_for_a_live_menu_binding(self):
        p=self.packet(3)
        for i in range(2):struct.pack_into('<iiQ',p,1440+i*16,101+i,201+i,0x20000+i*8)
        struct.pack_into('<3I',p,1472,0,2,1)
        struct.pack_into('<iiQ',p,1496,103,203,0x20010);validate(bytes(p))
        struct.pack_into('<i',p,1500,0)
        with self.assertRaises(ValueError):validate(bytes(p))
        p=self.packet(2);struct.pack_into('<iiQ',p,1496,103,203,0x20010)
        with self.assertRaises(ValueError):validate(bytes(p))
    def test_padding_and_stats_cannot_be_injected(self):
        for offset in (440,1484,1496,SIZE-1):
            p=self.packet();p[offset]=1
            with self.assertRaises(ValueError):validate(bytes(p))
    def test_variable_route_counts_require_empty_unused_slots(self):
        for routes in (1,3,5):validate(bytes(self.packet(routes=routes)))
        for routes in (0,6):
            p=self.packet();struct.pack_into('<I',p,1492,routes)
            with self.assertRaises(ValueError):validate(bytes(p))
        for offset in (24+8*16,280+8*8):
            p=self.packet(routes=1);p[offset]=1
            with self.assertRaises(ValueError):validate(bytes(p))
    def test_consumer_routes_are_explicit_and_distinct(self):
        from expedition33.story_cinematic_routes import validate_routes
        rows=[{'source':'/Game/Tests/Original.Original','replacement':'/Game/SDK/Example/Film.Film'}]
        self.assertEqual(validate_routes({'routes':rows}),tuple(rows))
        for invalid in ([],rows*2,[dict(rows[0],replacement=rows[0]['source'])],
                        [dict(rows[0],source='../Private')],[dict(rows[0],extra=1)]):
            with self.assertRaises(ValueError):validate_routes({'routes':invalid})
    def test_binding_admits_only_same_session_and_one_active_owner(self):
        from types import SimpleNamespace as N
        from unittest.mock import Mock
        from expedition33.new_game_story import NewGameStories,Choice
        service=NewGameStories.__new__(NewGameStories)
        service.closed=False;service.session=N();service.choice=Choice();service.row=object()
        router=N(closed=False,_scope=N(_session=service.session),bind_menu=Mock())
        service.bind_cinematics('sample.story',router)
        service._bind_cinematic_menu();router.bind_menu.assert_not_called()
        service.choice.register('sample.story','Sample Story');service._bind_cinematic_menu()
        router.bind_menu.assert_called_once_with(service.row,service.choice,'sample.story')
        with self.assertRaises(RuntimeError):service.bind_cinematics('other.story',router)
        with self.assertRaises(ValueError):service.bind_cinematics('sample.story',N(closed=False,_scope=N(_session=N())))
        router.closed=True;service._bind_cinematic_menu();self.assertEqual(router.bind_menu.call_count,1)

if __name__=='__main__':unittest.main()
