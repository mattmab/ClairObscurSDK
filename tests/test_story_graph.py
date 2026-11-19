import copy,importlib,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock
import test_story_packs
from expedition33.management import ManagementError
Graph=importlib.import_module('story_packs_test.graph').ConversationGraph
StoryView=importlib.import_module('story_packs_test.view').StoryView
PackEditor=importlib.import_module('story_packs_test.authoring').PackEditor
PackLibrary=importlib.import_module('story_packs_test.storage').PackLibrary


class StoryGraphTests(unittest.TestCase):
    def test_all_branches_and_shared_destinations_remain_visible(self):
        pack=test_story_packs.sample();d=pack['dialogues']['first-meeting']
        row=d['nodes']['welcome'];target=next(k for k in d['nodes'] if k!='welcome')
        for choice in row['choices']:choice['next']=target
        model=N(live=N(choices=lambda:None,error=None),library=N(get=lambda _:copy.deepcopy(pack)),edit_pack=Mock())
        v=StoryView(N(_check=lambda:None),model);v.pack=pack['id'];v.dialogue='first-meeting';v.screen='story_graph';v.render()
        routes=copy.deepcopy(v.graph_wire_routes)
        for choice in row['choices']:
            self.assertTrue(any(a==('welcome',choice['id']) and b==(target,None) for a,b,_,_ in routes))
        v.graph.output=row['choices'][0]['id'];v.render()
        self.assertEqual(v.graph_wire_routes,routes)
        row['choices'][0]['next']=None;frame=v.render()
        self.assertTrue(any('CHOICE 1 /' in c.label and '| END' in c.label for c in frame.controls))
        self.assertTrue(any(c.label=='End conversation' for c in frame.controls))

    def test_end_uses_selected_response_not_a_previous_pending_wire(self):
        with tempfile.TemporaryDirectory() as folder:
            pack=test_story_packs.sample();editor=PackEditor(folder);editor.create(pack)
            library=PackLibrary(folder);library.refresh()
            def edit(key,operation,*args):getattr(editor.open(key),operation)(*args);library.refresh()
            model=N(live=N(choices=lambda:None,error=None),library=library,edit_pack=edit)
            v=StoryView(N(_check=lambda:None),model);v.pack=pack['id'];v.dialogue='first-meeting';v.screen='story_graph';f=v.render()
            row=pack['dialogues'][v.dialogue]['nodes']['welcome'];first,second=row['choices'][:2]
            def action(op,arg):
                nonlocal f
                token=next(t for t,c in v._commands.items() if c[:2]==(op,arg))
                f=v.activate(f.revision,token)
            end=next(c for c in f.controls if c.label=='End conversation');self.assertFalse(end.enabled)
            action('graph_output',('welcome',first['id']))
            action('graph_select',('welcome',second['id']))
            action('graph_end',None)
            saved=library.get(pack['id'])['dialogues'][v.dialogue]['nodes']['welcome']['choices']
            self.assertEqual(saved[0],first);self.assertIsNone(saved[1]['next']);self.assertIsNone(v.graph.pending)

    def test_fit_uses_tall_speech_bounds(self):
        d=copy.deepcopy(test_story_packs.sample()['dialogues']['first-meeting'])
        row=d['nodes']['welcome'];row['choices']=[dict(id=str(i),text=str(i),next=None) for i in range(12)]
        g=Graph().sync(d);g.response_positions={};g.positions={'welcome':[40.,500.]};g.choice_counts={'welcome':12};g.fit()
        self.assertLessEqual((500+78+12*22)*g.zoom,700.0001)

    def test_floating_response_can_be_edited_wired_detached_and_reassigned(self):
        Conversation=importlib.import_module('story_packs_test.dialogue').Conversation
        with tempfile.TemporaryDirectory() as folder:
            pack=test_story_packs.sample();editor=PackEditor(folder);editor.create(pack)
            library=PackLibrary(folder);library.refresh()
            def edit(key,operation,*args):getattr(editor.open(key),operation)(*args);library.refresh()
            model=N(live=N(choices=lambda:None,error=None),library=library,edit_pack=edit)
            v=StoryView(N(_check=lambda:None),model);v.pack=pack['id'];v.dialogue='first-meeting';v.screen='story_graph';f=v.render()
            def action(op,arg=None,**kwargs):
                nonlocal f
                token=next(t for t,c in v._commands.items() if c[:2]==(op,arg));f=v.activate(f.revision,token,**kwargs)
            action('graph_loose');choice=v.graph.output
            self.assertEqual(v.graph.selected,'@responses')
            action('apply',value='A floating response')
            document=library.get(pack['id']);flow=Conversation(document,v.dialogue,{})
            self.assertNotIn(choice,[c['id'] for c in flow.view()['choices']])
            action('graph_output',('welcome',None));action('graph_response_in',('@responses',choice))
            self.assertEqual(v.graph.selected,'welcome');self.assertEqual(v.graph.output,choice)
            choices=library.get(pack['id'])['dialogues'][v.dialogue]['nodes']['welcome']['choices']
            self.assertEqual(choices[-1]['text'],'A floating response')
            target=next(k for k in document['dialogues'][v.dialogue]['nodes'] if k!='welcome')
            action('graph_output',('welcome',choice));action('graph_input',target)
            action('graph_detach')
            saved=library.get(pack['id']);loose=saved['dialogues'][v.dialogue]['loose_choices'][0]
            self.assertEqual(loose['next'],target);self.assertEqual(loose['text'],'A floating response')
            action('graph_add');self.assertNotEqual(v.graph.selected,'@responses')
            action('graph_output',(v.graph.selected,None));action('graph_response_in',('@responses',choice))
            self.assertEqual(v.graph.output,choice)
            # The response survives moving to a different actor speech.
            self.assertEqual(library.get(pack['id'])['dialogues'][v.dialogue]['nodes'][v.graph.selected]['choices'][0],loose)

    def test_many_floating_responses_save_and_placement_avoids_overlap(self):
        with tempfile.TemporaryDirectory() as folder:
            editor=PackEditor(folder);pack=test_story_packs.sample();draft=editor.create(pack)
            for i in range(24):draft.loose_choice('first-meeting',f'floating-{i}',f'Response {i}')
            saved=editor.open(pack['id']).document;d=saved['dialogues']['first-meeting'];g=Graph().sync(d)
            self.assertEqual(len(d['loose_choices']),24)
            g.place_response(('@responses','floating-0'),d,40,30)
            first=g.entity_position(('@responses','floating-0'))
            self.assertNotEqual(first,g.positions['welcome'])
            # Native per-speech response count is still enforced atomically.
            for i in range(14):draft.attach_choice('first-meeting','@responses',f'floating-{i}','welcome')
            before=editor.open(pack['id']).document
            with self.assertRaises(ValueError):draft.attach_choice('first-meeting','@responses','floating-14','welcome')
            self.assertEqual(editor.open(pack['id']).document,before)

    def test_loose_response_conditions_and_delete_return_to_a_real_speech(self):
        with tempfile.TemporaryDirectory() as folder:
            pack=test_story_packs.sample();editor=PackEditor(folder);editor.create(pack)
            library=PackLibrary(folder);library.refresh()
            def edit(key,operation,*args):getattr(editor.open(key),operation)(*args);library.refresh()
            model=N(live=N(choices=lambda:None,error=None),library=library,edit_pack=edit)
            v=StoryView(N(_check=lambda:None),model);v.pack=pack['id'];v.dialogue='first-meeting';v.screen='story_graph';f=v.render()
            def action(op,arg=None):
                nonlocal f
                token=next(t for t,c in v._commands.items() if c[:2]==(op,arg));f=v.activate(f.revision,token)
            action('graph_loose');identity=(v.graph.selected,v.graph.output)
            action('graph_flags');self.assertEqual(v.screen,'story_flags')
            edit(pack['id'],'flag',v.flag_target,'visited',True);f=v.render()
            self.assertTrue(any('visited' in c.label for c in f.controls))
            v.screen='story_graph';f=v.render();self.assertEqual((v.graph.selected,v.graph.output),identity)
            action('graph_delete');action('graph_delete')
            self.assertIn(v.graph.selected,pack['dialogues'][v.dialogue]['nodes']);self.assertIsNone(v.graph.output)
            action('graph_focus',1)

    def test_crowded_graph_stays_within_native_control_and_wire_capacity(self):
        pack=test_story_packs.sample();d=pack['dialogues']['first-meeting'];target=next(k for k in d['nodes'] if k!='welcome')
        d['nodes']['welcome']['choices']=[dict(id=str(i),text=f'Response {i}',next=target,requires={},set={}) for i in range(16)]
        model=N(live=N(choices=lambda:None,error=None),library=N(get=lambda _:copy.deepcopy(pack)),edit_pack=Mock())
        v=StoryView(N(_check=lambda:None),model);v.pack=pack['id'];v.dialogue='first-meeting';v.screen='story_graph';v.render()
        for i,c in enumerate(d['nodes']['welcome']['choices']):v.graph.response_positions[('welcome',c['id'])]=[400+i%3*270,30+i//3*110]
        v.graph.positions[target]=[100,500];v.graph.zoom=.8;v.graph.selected=target;f=v.render()
        self.assertEqual(len(v.graph_entities),16)
        self.assertLessEqual(sum(bool(c.label) and c.enabled for c in f.controls),64)
        self.assertLessEqual(len(v.graph_wires),48)
        self.assertGreater(v.graph_hidden_routes,0)
        self.assertIn('links not drawn',f.status)

    def test_saved_choice_slots_are_independent_of_canvas_positions(self):
        Conversation=importlib.import_module('story_packs_test.dialogue').Conversation
        with tempfile.TemporaryDirectory() as folder:
            pack=test_story_packs.sample();editor=PackEditor(folder);editor.create(pack)
            draft=editor.open(pack['id']);row=draft.document['dialogues']['first-meeting']['nodes']['welcome']
            first=row['choices'][0]['id'];snapshot=copy.deepcopy(row['choices'][0])
            draft.choice('first-meeting','welcome','third','Third response',None)
            draft=editor.open(pack['id']);draft.reorder_choice('first-meeting','welcome',first,2)
            saved=editor.open(pack['id']).document;choices=saved['dialogues']['first-meeting']['nodes']['welcome']['choices']
            self.assertEqual(choices[2],snapshot)
            flow=Conversation(saved,'first-meeting',{})
            self.assertEqual([c['id'] for c in flow.view()['choices']],[c['id'] for c in choices])
            graph=Graph().sync(saved['dialogues']['first-meeting']);graph.set_position(('welcome',first),10,900)
            self.assertEqual(editor.open(pack['id']).document,saved)
            before=copy.deepcopy(saved)
            with self.assertRaises(ValueError):draft.reorder_choice('first-meeting','welcome',first,99)
            self.assertEqual(editor.open(pack['id']).document,before)

    def test_create_next_speech_is_an_atomic_link_and_preserves_other_routes(self):
        with tempfile.TemporaryDirectory() as folder:
            pack=test_story_packs.sample();editor=PackEditor(folder);editor.create(pack)
            draft=editor.open(pack['id']);row=draft.document['dialogues']['first-meeting']['nodes']['welcome']
            choice=row['choices'][0]['id'];speaker=row['speaker']
            draft.destination('first-meeting','welcome',choice,None)
            draft=editor.open(pack['id']);draft.append_node('first-meeting','welcome',choice,'next-speech',speaker)
            saved=editor.open(pack['id']).document;nodes=saved['dialogues']['first-meeting']['nodes']
            self.assertEqual(nodes['welcome']['choices'][0]['next'],'next-speech')
            self.assertEqual(nodes['next-speech']['speaker'],speaker)
            with self.assertRaises(ValueError):draft.append_node('first-meeting','welcome',choice,'unwanted',speaker)
            self.assertEqual(editor.open(pack['id']).document,saved)
            graph=Graph().sync(pack['dialogues']['first-meeting'])
            occupied=list(graph.positions['welcome'])
            graph.place_speech('fresh',pack['dialogues']['first-meeting'],*occupied)
            self.assertNotEqual(graph.positions['fresh'],occupied)

    def test_drag_only_updates_geometry_without_rendering_or_reading_content(self):
        from contextlib import nullcontext
        graph_view=importlib.import_module('story_packs_test.graph_view')
        pack=test_story_packs.sample();library=N(get=Mock(return_value=pack))
        model=N(live=N(choices=lambda:None,error=None),library=library,edit_pack=Mock())
        v=StoryView(N(_check=lambda:None),model);v.pack=pack['id'];v.dialogue='first-meeting';v.screen='story_graph';v.render()
        def objects(start,count):return [N(index=i,serial=1,address=i*16) for i in range(start,start+count)]
        p=N(button_slots=objects(0,48),label_slots=objects(100,48),story_skin_images=objects(200,64),
            story_skin_slots=objects(300,64),_graph_set_cache={},_slot_geometry={},_render_call=Mock(),
            set_visible=Mock(),paint_batch=nullcontext,invisible=4,collapsed=1)
        v.graph_art_indices={t:i+2 for i,t in enumerate(v.graph_rects) if t<48}
        v.graph_strips=[('border',o,s) for o,s in zip(objects(400,48),objects(500,48))]
        menu=N(panel=p,_paint=Mock(),refresh=Mock())
        graph_view.drag_paint(v,menu);p._render_call.reset_mock();library.get.reset_mock()
        v.graph.move(30,20);graph_view.drag_paint(v,menu)
        library.get.assert_not_called();menu._paint.assert_not_called();menu.refresh.assert_not_called()
        self.assertLessEqual(p._render_call.call_count,30)
        self.assertTrue(all(c.args[2] in ('SetPosition','SetSize') for c in p._render_call.call_args_list))

    def test_cycles_disconnected_nodes_and_fit_are_bounded(self):
        d=copy.deepcopy(test_story_packs.sample()['dialogues']['first-meeting'])
        d['nodes']['other']=copy.deepcopy(d['nodes'][d['entry']]);d['nodes']['other']['choices']=[];d['nodes']['other']['next']='other'
        g=Graph().sync(d);g.fit()
        self.assertEqual(set(g.positions),set(d['nodes']))
        self.assertTrue(.35<=g.zoom<=1)
        self.assertLessEqual(len(g.visible(d)),6)
        g.pending=('other',None);self.assertEqual(g.link(d,'other'),('other',None,'other'))
        with self.assertRaises(ValueError):g.link(d,'missing')

    def test_output_pagination_keeps_stable_choice_ids(self):
        d=test_story_packs.sample()['dialogues']['first-meeting'];g=Graph().sync(d);row=d['nodes'][d['entry']]
        row['choices']=[dict(id=str(i),text=str(i),next=None) for i in range(7)]
        g.response_pages[d['entry']]=2
        self.assertEqual([r[0] for r in g.outputs(d['entry'],row)],['4','5'])
        g.pending=(d['entry'],'6');self.assertEqual(g.link(d,None)[1],'6')
        row['choices'].pop();g.sync(d);self.assertIsNone(g.pending)

    def test_graph_wiring_text_entry_and_cancel_use_existing_saved_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            editor=PackEditor(folder);pack=test_story_packs.sample();editor.create(pack)
            library=PackLibrary(folder);library.refresh()
            def edit(key,operation,*args):
                getattr(editor.open(key),operation)(*args);library.refresh()
            model=N(live=N(choices=lambda:None,error=None),library=library,edit_pack=edit)
            v=StoryView(N(_check=lambda:None),model);v.pack=pack['id'];v.dialogue='first-meeting';v.screen='story_graph'
            def click(frame,label,**args):
                c=next(c for c in frame.controls if c.label.startswith(label));return v.activate(frame.revision,c.token,**args)
            f=v.render();self.assertLessEqual(sum(c.enabled for c in f.controls),64)
            choice=next(iter(pack['dialogues'][v.dialogue]['nodes']['welcome']['choices']))
            token=next(t for t,c in v._commands.items() if c[:2]==('graph_output',('welcome',choice['id'])))
            f=v.activate(f.revision,token);before=library.get(pack['id'])
            f=click(f,'Cancel wire');self.assertEqual(library.get(pack['id']),before)
            token=next(t for t,c in v._commands.items() if c[:2]==('graph_output',('welcome',choice['id'])))
            f=v.activate(f.revision,token)
            target=next(k for k in before['dialogues'][v.dialogue]['nodes'] if k!='welcome')
            token=next(t for t,c in v._commands.items() if c[:2]==('graph_input',target))
            old=f;f=v.activate(f.revision,token)
            with self.assertRaises(ManagementError):v.activate(old.revision,token)
            saved=library.get(pack['id']);actual=next(c for c in saved['dialogues'][v.dialogue]['nodes']['welcome']['choices'] if c['id']==choice['id'])
            self.assertEqual(actual['next'],target)
            f=click(f,'Apply text',value='Custom response after wiring')
            self.assertEqual(next(c for c in library.get(pack['id'])['dialogues'][v.dialogue]['nodes']['welcome']['choices'] if c['id']==choice['id'])['text'],'Custom response after wiring')
            self.assertEqual(saved['placements'],library.get(pack['id'])['placements'])

    def test_navigation_does_not_write_content_or_retire_live_actors(self):
        pack=test_story_packs.sample();model=N(live=N(choices=lambda:None,error=None),library=N(get=lambda _:copy.deepcopy(pack)),edit_pack=Mock())
        v=StoryView(N(_check=lambda:None),model);v.pack=pack['id'];v.dialogue='first-meeting';v.screen='story_graph';f=v.render()
        for prefix in ('Zoom','Fit','Next line'):
            c=next(c for c in f.controls if c.label.startswith(prefix));f=v.activate(f.revision,c.token)
        model.edit_pack.assert_not_called()

    def test_response_cards_move_independently_and_selection_does_not_wire(self):
        pack=test_story_packs.sample();d=pack['dialogues']['first-meeting'];g=Graph().sync(d)
        choice=d['nodes']['welcome']['choices'][0]['id'];before=list(g.positions['welcome'])
        g.selected='welcome';g.output=choice;old=list(g.response_positions[('welcome',choice)])
        g.move(80,40)
        self.assertEqual(g.positions['welcome'],before)
        self.assertEqual(g.response_positions[('welcome',choice)],[old[0]+80,old[1]+40])
        model=N(live=N(choices=lambda:None,error=None),library=N(get=lambda _:copy.deepcopy(pack)),edit_pack=Mock())
        v=StoryView(N(_check=lambda:None),model);v.pack=pack['id'];v.dialogue='first-meeting';v.screen='story_graph';f=v.render()
        token=next(t for t,c in v._commands.items() if c[:2]==('graph_select',('welcome',choice)))
        v.activate(f.revision,token)
        self.assertEqual(v.graph.output,choice);self.assertIsNone(v.graph.pending);model.edit_pack.assert_not_called()

    def test_delete_response_requires_confirmation_and_preserves_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            editor=PackEditor(folder);pack=test_story_packs.sample();editor.create(pack)
            library=PackLibrary(folder);library.refresh()
            def edit(key,operation,*args):getattr(editor.open(key),operation)(*args);library.refresh()
            model=N(live=N(choices=lambda:None,error=None),library=library,edit_pack=edit)
            v=StoryView(N(_check=lambda:None),model);v.pack=pack['id'];v.dialogue='first-meeting';v.screen='story_graph';f=v.render()
            choice=pack['dialogues'][v.dialogue]['nodes']['welcome']['choices'][0]['id']
            token=next(t for t,c in v._commands.items() if c[:2]==('graph_select',('welcome',choice)))
            f=v.activate(f.revision,token)
            def click(label):
                nonlocal f
                c=next(c for c in f.controls if c.label==label);f=v.activate(f.revision,c.token)
            before=library.get(pack['id']);click('Delete response');self.assertEqual(library.get(pack['id']),before)
            click('Confirm delete');after=library.get(pack['id'])
            self.assertEqual(set(after['dialogues'][v.dialogue]['nodes']),set(before['dialogues'][v.dialogue]['nodes']))
            self.assertFalse(any(c['id']==choice for c in after['dialogues'][v.dialogue]['nodes']['welcome']['choices']))

    def test_drag_threshold_zoom_pan_and_focus_loss(self):
        Gesture=importlib.import_module('story_packs_test.graph_pointer').GraphGesture
        d=test_story_packs.sample()['dialogues']['first-meeting'];g=Graph().sync(d)
        v=N(graph=g,graph_body_tokens={0:('welcome',None)},graph_rects={0:(40,30,270,130)})
        gesture=Gesture();origin=list(g.positions['welcome'])
        self.assertIsNone(gesture.sample(v,(150,280),True,False))
        self.assertIsNone(gesture.sample(v,(152,280),True,False))
        self.assertEqual(gesture.sample(v,(210,310),True,False),'paint')
        self.assertEqual(g.positions['welcome'],[origin[0]+60,origin[1]+30])
        self.assertEqual(gesture.sample(v,None,False,False),'finish')
        old=list(g.positions['welcome']);gesture.sample(v,(600,500),False,True)
        gesture.sample(v,(500,450),False,True)
        self.assertEqual(g.positions['welcome'],old);self.assertEqual(g.offset,[100,50])
        self.assertEqual(gesture.sample(v,(500,450),False,False),'finish')
        # A short native gesture may reach the owner only as down + release.
        gesture=Gesture();g.offset=[0.,0.];g.positions['welcome']=[40.,30.]
        gesture.sample(v,(150,280),True,False)
        self.assertEqual(gesture.sample(v,(230,300),False,False),'finish')
        self.assertEqual(g.positions['welcome'],[120.,50.])

    def test_content_edit_preserves_actors_and_waits_for_active_native_flow(self):
        Mod=importlib.import_module('story_packs_test.mod').Mod
        with tempfile.TemporaryDirectory() as folder:
            pack=test_story_packs.sample();PackEditor(folder).create(pack)
            m=Mod();m.library=PackLibrary(folder);m.library.refresh()
            actor=object();runtime=N(document=copy.deepcopy(pack),actors={'boy':actor})
            m.live=N(runtime=runtime,conversations=N(flow=object()),retire=Mock())
            m.edit_pack(pack['id'],'text','first-meeting','welcome','New text')
            m.live.retire.assert_not_called();self.assertIs(runtime.actors['boy'],actor)
            m._refresh_story_document()
            self.assertNotEqual(runtime.document['dialogues']['first-meeting']['nodes']['welcome']['text'],'New text')
            m.live.conversations.flow=None;m._refresh_story_document()
            self.assertEqual(runtime.document['dialogues']['first-meeting']['nodes']['welcome']['text'],'New text')
            self.assertIs(runtime.actors['boy'],actor);m.live.retire.assert_not_called()
