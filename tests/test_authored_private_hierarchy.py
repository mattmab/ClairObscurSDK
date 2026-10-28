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


class ReconcileHierarchyTests(unittest.TestCase):
    def run_tree(self,deep=False,foreign=False,conflict=False):
        from expedition33.cinematics.authored_private_hierarchy import reconcile_tree
        edges={'source':[('s','shot')],'shot':[('t','leaf')],
               'private:root':[('s','private:shot' if deep else 'shot')],
               'private:shot':[('t','private:leaf')],'private:leaf':[],
               'leaf':[]}
        if foreign:edges['private:root']=[('s','foreign')];edges['foreign']=[]
        if conflict:edges['private:root'].append(('other','private:shot'));edges['source'].append(('other','different'));edges['different']=[]
        effects=[]
        def clone(child):
            effects.append(('clone',child));edges['private:'+child]=[(s,'private:'+c) for s,c in edges[child]]
            return 'private:'+child
        def adopt(a,b):effects.append(('adopt',a,b))
        try:
            reconcile_tree('source','private:root',{'source','shot','leaf'},key=lambda x:x,
                           links=lambda p:edges[p],section_key=lambda s:s,
                           is_private=lambda p:p.startswith('private:'),adopt=adopt,clone=clone,
                           relink=lambda *args:effects.append(('link',)+args))
        except Exception as e:return effects,e
        return effects,None
    def test_engine_deep_copy_is_adopted_without_extra_clone_or_relink(self):
        effects,error=self.run_tree(deep=True)
        self.assertIsNone(error)
        self.assertEqual(effects,[('adopt','source','private:root'),('adopt','shot','private:shot'),('adopt','leaf','private:leaf')])
    def test_shallow_root_with_deep_child_clone_is_supported(self):
        effects,error=self.run_tree()
        self.assertIsNone(error)
        self.assertEqual([r for r in effects if r[0]=='clone'],[('clone','shot')])
        self.assertEqual(len([r for r in effects if r[0]=='link']),1)
        self.assertIn(('adopt','leaf','private:leaf'),effects)
    def test_foreign_child_is_rejected_before_effects(self):
        effects,error=self.run_tree(foreign=True)
        self.assertIsInstance(error,RuntimeError);self.assertEqual(effects,[])
    def test_conflicting_private_provenance_is_rejected_before_effects(self):
        effects,error=self.run_tree(deep=True,conflict=True)
        self.assertIsInstance(error,RuntimeError);self.assertEqual(effects,[])
    def test_ambiguous_signature_is_rejected(self):
        from expedition33.cinematics.authored_private_hierarchy import match_children
        with self.assertRaisesRegex(RuntimeError,'Ambiguous'):
            match_children([('a','child'),('a','child')],[('a','private')],section_key=lambda x:x)
