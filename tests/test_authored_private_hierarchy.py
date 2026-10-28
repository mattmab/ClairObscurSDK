import unittest
from expedition33.cinematics.authored_private_hierarchy import required_paths,copy_required,edited_sequence_paths

class PrivateHierarchyTests(unittest.TestCase):
    def test_edit_owners_include_nested_sequence_without_similar_asset_prefix(self):
        root='/Game/Root.Root';child='/Game/Root.RootShot'
        a=root+':MovieScene.Track.Section';b=child+':MovieScene.Track.Section'
        nodes={root:dict(class_name='LevelSequence'),child:dict(class_name='LevelSequence'),
               a:dict(class_name='MovieSceneBoolSection'),b:dict(class_name='MovieSceneBoolSection')}
        document=dict(source=dict(sequence=root,nodes=nodes,pending=[]),
                      key_edits=[dict(section=b)],section_edits={a:dict(start=0,end=1)})
        self.assertEqual(edited_sequence_paths(document),frozenset((root,child)))
        document['source']['pending']=['unread']
        with self.assertRaisesRegex(ValueError,'Complete source hierarchy'):edited_sequence_paths(document)
    def test_unknown_incomplete_and_non_level_sequence_owners_are_rejected(self):
        root='/Game/Root.Root';section=root+':MovieScene.Track.Section'
        for nodes in ({root:dict(class_name='LevelSequence')},
                      {root:dict(class_name='LevelSequence'),section:dict(class_name='MovieSceneBoolSection',errors={'x':'unread'})},
                      {root:dict(class_name='CameraAnimationSequence'),section:dict(class_name='MovieSceneBoolSection')}):
            with self.assertRaises(ValueError):
                edited_sequence_paths(dict(source=dict(sequence=root,nodes=nodes),key_edits=[dict(section=section)]))
    def run_copy(self,edges,targets,fail=None):
        journal=[];writes=[]
        initial=[(parent,section,child) for parent,rows in edges.items() for section,child in rows]
        def links(parent):return edges.get(parent.removeprefix('private:'),())
        def clone(child):
            journal.append('private:'+child)
            if fail=='clone':raise RuntimeError('construction failed')
            return journal[-1]
        def relink(parent,section,child,copied):
            writes.append((parent,section,child,copied))
            if fail=='link':raise RuntimeError('dispatch failed')
        try:result=copy_required('root',targets,initial,key=lambda x:x,links=links,clone=clone,relink=relink)
        except Exception as e:return journal,writes,e
        return journal,writes,result
    def test_only_edited_branch_is_copied_and_nested_links_are_replaced_first(self):
        edges={'root':[('a','shot'),('b','untouched')],'shot':[('c','edited')]}
        journal,writes,result=self.run_copy(edges,{'edited'})
        self.assertEqual(journal,['private:shot','private:edited'])
        self.assertEqual(writes,[('private:shot','c','edited','private:edited'),('root','a','shot','private:shot')])
        self.assertEqual(result,tuple(journal))
    def test_shared_child_is_copied_once_and_each_occurrence_relinked(self):
        journal,writes,result=self.run_copy({'root':[('a','shot'),('b','shot')]},{'shot'})
        self.assertEqual(journal,['private:shot']);self.assertEqual(len(writes),2)
    def test_cycle_or_unreachable_edit_is_rejected_before_any_copy_or_write(self):
        for edges,targets in (({'root':[('a','shot')],'shot':[('b','root')]},{'shot'}),({'root':[]},{'missing'})):
            journal,writes,error=self.run_copy(edges,targets)
            self.assertEqual(journal,[]);self.assertEqual(writes,[]);self.assertIsInstance(error,ValueError)
    def test_failures_keep_constructed_journal_and_never_replay(self):
        for failure in ('clone','link'):
            journal,writes,error=self.run_copy({'root':[('a','shot'),('b','shot')]},{'shot'},failure)
            self.assertEqual(journal,['private:shot']);self.assertIsInstance(error,RuntimeError)
            self.assertEqual(len(writes),0 if failure=='clone' else 1)
    def test_root_only_edit_does_not_duplicate_unedited_children(self):
        journal,writes,result=self.run_copy({'root':[('a','shot')]},{'root'})
        self.assertEqual((journal,writes,result),([],[],()))
    def test_changed_references_fail_before_cloning_or_linking(self):
        for observed in ([],[('a','other')],[('a','shot'),('b','shot')]):
            effects=[]
            with self.assertRaisesRegex(RuntimeError,'references changed'):
                copy_required('root',{'shot'},[('root','a','shot')],key=lambda x:x,
                    links=lambda parent:observed,clone=lambda child:effects.append(child),
                    relink=lambda *args:effects.append(args))
            self.assertEqual(effects,[])
    def test_repeated_subsection_is_not_dispatched_twice(self):
        with self.assertRaisesRegex(RuntimeError,'Duplicate private subsection'):
            copy_required('root',{'shot'},[('root','a','shot'),('root','b','shot')],
                key=lambda x:x,links=lambda parent:[('a','shot'),('a','shot')],
                clone=lambda child:self.fail('unexpected clone'),
                relink=lambda *args:self.fail('unexpected write'))
