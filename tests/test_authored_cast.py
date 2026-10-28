import copy, unittest
from expedition33.cinematics.authored_cast import bindings


def guid(n):return dict(struct='/Script/CoreUObject.Guid',fields=dict(A=n,B=0,C=0,D=0),complete=True,errors={})
def array(rows):return dict(array=rows,length=len(rows),complete=True)
def struct(kind,**fields):return dict(struct='/Script/MovieScene.'+kind,fields=fields,errors={},complete=True)
def fixture():
    root='/Game/Test.Test';scene=root+':MovieScene';track=scene+'.BodyTrack'
    actor=struct('MovieSceneSpawnable',Guid=guid(1),Name='Actor',ObjectTemplate=dict(object_path=scene+'.Actor',**{'class':'BP_Cine_Test_C'}))
    # Shipping spawnable ownership is not decoded; identity fields still are.
    actor.update(complete=False,errors={'Ownership':'STRUCT_MEMBER_TYPE_UNSUPPORTED'})
    component=struct('MovieScenePossessable',Guid=guid(2),Name='Body',ParentGuid=guid(1))
    binding=struct('MovieSceneBinding',ObjectGuid=guid(2),Tracks=array([dict(object_path=track,**{'class':'MovieSceneSkeletalAnimationTrack'})]))
    return dict(sequence=root,nodes={root:dict(class_name='LevelSequence',fields=dict(MovieScene=dict(object_path=scene))),
        scene:dict(class_name='MovieScene',fields=dict(Spawnables=array([actor]),Possessables=array([component]),ObjectBindings=array([binding]))),
        track:dict(class_name='MovieSceneSkeletalAnimationTrack',fields={})})


class AuthoredCastTests(unittest.TestCase):
    def test_null_cooked_spawn_template_preserves_guid_and_child_tracks(self):
        from expedition33.cinematics.authored_cast import replacement_overlap_warning
        from expedition33.cinematics.authored_timeline import create,replace_cast
        source=fixture();before=copy.deepcopy(source)
        actor=source['nodes'][source['sequence']+':MovieScene']['fields']['Spawnables']['array'][0]
        actor['fields']['ObjectTemplate']=None
        rows=bindings(source)
        self.assertIsNone(rows[0]['template'])
        self.assertEqual(rows[0]['children'],[rows[1]['guid']])
        self.assertEqual(len(rows[1]['tracks']),1)
        self.assertEqual(replacement_overlap_warning(rows,[],('other','other'),'sciel'),'')
        with self.assertRaises(ValueError):
            replace_cast(create(source,'Test'),source['sequence'],rows[0]['guid'],'sciel')
        self.assertIsNotNone(before['nodes'][source['sequence']+':MovieScene']['fields']['Spawnables']['array'][0]['fields']['ObjectTemplate'])
    def test_overlap_warning_counts_effective_cast_in_the_same_shot(self):
        from expedition33.cinematics.authored_cast import replacement_overlap_warning
        rows=[dict(sequence='shot',guid='one',kind='spawnable',name='Renoir',template={'class':'BP_Cine_Renoir_C'}),
              dict(sequence='shot',guid='two',kind='spawnable',name='Maelle',template={'class':'BP_Cine_Maelle_C'}),
              dict(sequence='other',guid='three',kind='spawnable',name='Maelle',template={'class':'BP_Cine_Maelle_C'}),
              dict(sequence='shot',guid='four',kind='possessable',name='Body',template=None)]
        selected=('shot','one')
        warning=replacement_overlap_warning(rows,[],selected,'maelle')
        self.assertIn('Maelle',warning);self.assertIn('both may appear',warning)
        self.assertEqual(replacement_overlap_warning(rows,[],selected,'sciel'),'')
        edits=[dict(sequence='shot',guid='two',profile='sciel')]
        self.assertEqual(replacement_overlap_warning(rows,edits,selected,'maelle'),'')
        self.assertIn('Maelle',replacement_overlap_warning(rows,edits,selected,'sciel'))
        self.assertEqual(replacement_overlap_warning(rows,[],selected,'unknown'),'')
    def test_projected_identity_keeps_child_tracks_and_source_immutable(self):
        source=fixture();before=copy.deepcopy(source);rows=bindings(source)
        self.assertEqual(source,before)
        self.assertEqual(rows[0]['children'],[rows[1]['guid']])
        self.assertEqual(rows[1]['parent'],rows[0]['guid'])
        self.assertEqual(len(rows[1]['tracks']),1)
        self.assertFalse(rows[1]['unread_tracks'])
        self.assertNotIn('address',str(rows))
        rows[0]['template']['class']='Modified caller copy'
        self.assertEqual(source,before)
    def test_same_guid_in_different_shots_is_not_a_duplicate(self):
        source=fixture();other=fixture();old=other['sequence'];new='/Game/Shot.Shot'
        import json
        other=json.loads(json.dumps(other).replace(old,new));source['nodes'].update(other['nodes'])
        rows=bindings(source);self.assertEqual(len(rows),4)
        self.assertEqual(rows[0]['guid'],rows[2]['guid']);self.assertNotEqual(rows[0]['sequence'],rows[2]['sequence'])
    def test_partial_identity_and_array_never_look_complete(self):
        for mutate in (
            lambda f:f['Spawnables'].update(complete=False),
            lambda f:f['Spawnables']['array'][0]['fields']['Guid'].update(complete=False),
            lambda f:f['Spawnables']['array'][0]['errors'].update(Name='unavailable'),
            lambda f:f['Possessables']['array'][0]['fields']['Guid']['fields'].update(A=True),
            lambda f:f['ObjectBindings']['array'][0]['fields']['Tracks'].update(length=2),
        ):
            source=fixture();mutate(source['nodes'][source['sequence']+':MovieScene']['fields'])
            with self.assertRaises(ValueError):bindings(source)
    def test_foreign_templates_tracks_unknown_bindings_and_cycles_rejected(self):
        for mutate in (
            lambda f:f['Spawnables']['array'][0]['fields']['ObjectTemplate'].update(object_path='/Game/Foreign.Actor'),
            lambda f:f['ObjectBindings']['array'][0]['fields']['Tracks']['array'][0].update(object_path='/Game/Foreign.Track'),
            lambda f:f['ObjectBindings']['array'][0]['fields'].update(ObjectGuid=guid(99)),
            lambda f:f['Possessables']['array'][0]['fields'].update(ParentGuid=guid(2)),
            lambda f:f['Possessables']['array'][0]['fields'].update(ParentGuid=guid(99)),
            lambda f:f['Possessables']['array'][0]['fields'].update(Guid=guid(1)),
        ):
            source=fixture();mutate(source['nodes'][source['sequence']+':MovieScene']['fields'])
            with self.assertRaises(ValueError):bindings(source)
    def test_referenced_unread_tracks_remain_explicit(self):
        source=fixture();source['nodes'].pop(source['sequence']+':MovieScene.BodyTrack')
        row=bindings(source)[1]
        self.assertEqual(row['unread_tracks'],row['tracks'])

