"""Exact unlocked sequence imports: retained asset load and metadata only."""
import json
from pathlib import Path
from uuid import uuid4
from expedition33._scope import SessionScope
from expedition33.assets import load_asset
from expedition33.catalog import capture
from expedition33 import _query

PROFILES = (
    ('Sandfall/Content/Cinematics/MonolithInterior/Locomotive/DA_GA_CIN_Locomotive_MonocoToLumiere.uasset',
     '/Game/Cinematics/MonolithInterior/Locomotive/CS_GPE_MonolithInterior_Locomotive_MonocoToLumiere.CS_GPE_MonolithInterior_Locomotive_MonocoToLumiere',
     'f410a0ded2866855ddb290142b509831b274a6564e34cb4170bf3625a8c2e59f'),
    ('Sandfall/Content/Levels/OrangeForest/GameActions/DA_GA_CIN_MCS_ScavengerIntro.uasset',
     '/Game/Cinematics/OrangeForest/CS_OrangeForest_ScavengerIntro.CS_OrangeForest_ScavengerIntro',
     '269cd1e6ec20415ffc70b613288d7b9650faad0ea43ab7c9be8d1855d8006ea3'),
)
OWNERS = frozenset(('BP_ExternalAudioSequencerSection_C',
    'BP_ExternalAudioSequencerTrack_C','BP_ExternalAudioSequencerTrackInstance_C',
    'LensAndFilmPostProcess_GlobalCinematics_C','LensAndFilmPostProcess_C',
    'BP_GameAction_CinematicWithLightingScenario_C','BP_GameAction_Cinematic_C'))

def run(mod):
    if mod.video is not None or (mod.title_replay and mod.title_replay.status().get('active')):
        raise RuntimeError('Stop playback before importing research assets')
    mod.discover()
    scenes=mod.discovery.get('confirmed',())
    for definition,sequence,digest in PROFILES:
        matches=[s for s in scenes if s.get('id')==definition and s.get('unlocked') is True
                 and s.get('sequence')==sequence and s.get('definition_sha256')==digest]
        if len(matches)!=1:raise RuntimeError('Exact research definition is not freshly unlocked')
    scope=SessionScope(mod.session)
    report={'playback_attempted':False,'actors_spawned':False,'loaded':[],'metadata':[]}
    assets=[]
    try:
        for definition, _, _ in PROFILES:
            package = '/Game/' + definition.removeprefix('Sandfall/Content/').removesuffix('.uasset')
            path = package + '.' + package.rsplit('/', 1)[1]
            obj = load_asset(scope, path).return_value
            if obj is None or obj.class_name != 'BP_GameAction_CinematicWithLightingScenario_C':
                raise RuntimeError('Expected exact cinematic definition class')
            report['loaded'].append(path)
        for _,path,_ in PROFILES:
            result=load_asset(scope,path)
            obj=result.return_value
            if obj is None or obj.class_name!='LevelSequence':
                raise RuntimeError('Expected exact LevelSequence asset')
            assets.append(obj)
            report['loaded'].append(path)
        catalog=capture()
        if catalog.pid!=scope.pid:raise RuntimeError('Game identity changed')
        from inspect_camera_initialization import inspect_retained_camera_template
        report['camera_initialization'] = inspect_retained_camera_template(catalog, assets[0])
        from expedition33.values import read_values
        from inspect_spawned_camera_contracts import copied
        ls=catalog.find_class('LevelSequence'); ms=catalog.find_class('MovieScene')
        report['spawn_declarations']=[]
        for obj in assets:
            asset_values=read_values(catalog,catalog.resolve(obj))
            scene=asset_values.values.get((ls.index,'MovieScene'))
            if scene is None:raise RuntimeError('Retained sequence MovieScene not readable')
            scene_values=read_values(catalog,scene)
            key=(ms.index,'Spawnables')
            report['spawn_declarations'].append(dict(sequence=catalog.path_name(obj),
                value=copied(scene_values.values.get(key),catalog),
                error=str(scene_values.errors[key]) if key in scene_values.errors else None))
        owners=[o for o in catalog.objects if o.name in OWNERS and o.class_name=='BlueprintGeneratedClass']
        indexes={o.index for o in owners}
        targets=owners+[o for o in catalog.objects if o.outer_index in indexes and o.class_name=='Function']
        if len(targets)>96:raise RuntimeError('Research descriptor bound exceeded')
        for obj in targets:
            start,rows=_query(['--describe',str(scope.pid),f'{obj.index}:{obj.serial}:{obj.address:x}'])
            report['metadata'].append({'path':catalog.path_name(obj),'start':start,'rows':rows})
        report['missing_owners']=sorted(OWNERS-{o.name for o in owners})
    finally:
        scope.close()
    report['scope_closed']=True
    output = Path(__file__).resolve().parents[1] / 'evidence' / (
        'actor-cinematic-imports-' + uuid4().hex + '.json')
    output.write_text(json.dumps(report, indent=2), encoding='utf8')
    return {'artifact': str(output), 'loaded': report['loaded'],
            'metadata_count': len(report['metadata']),
            'missing_owners': report['missing_owners'], 'scope_closed': True,
            'playback_attempted': False, 'actors_spawned': False}
