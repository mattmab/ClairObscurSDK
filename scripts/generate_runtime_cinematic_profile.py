"""Generate the isolated demo's exact native contracts from its live report."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = (
    'Actor:GetComponentByClass', 'SkeletalMeshComponent:SetSkeletalMeshAsset',
    'SkeletalMeshComponent:PlayAnimation', 'SkeletalMeshComponent:Stop',
    'GameplayStatics:CreateSound2D', 'AudioComponent:Play', 'AudioComponent:Stop',
    'ActorComponent:K2_DestroyComponent', 'Controller:SetIgnoreLookInput',
    'CameraComponent:SetFieldOfView',
    'SkinnedMeshComponent:SetLeaderPoseComponent',
    'SceneComponent:K2_AttachToComponent', 'SkinnedMeshComponent:GetNumBones',
    'SkinnedMeshComponent:GetBoneName',
)
ANIMATION = '/Game/Characters/Heros/Lune/Animations/Skills/Lune_Thunder_Kick_IP.Lune_Thunder_Kick_IP'
MAELLE_ANIMATION = '/Game/Characters/Heros/Maelle/Animations/Skills/Maelle_Skill_DancingFury_B_Inplace.Maelle_Skill_DancingFury_B_Inplace'
TARGET_ANIMATION = '/Game/Animations/AnimPacks/Idles/MC_Idles_Pack/Shift/Pack_MCIdlesPack_am_Stand_Idle_ShiftL_Loop_01_UE5.Pack_MCIdlesPack_am_Stand_Idle_ShiftL_Loop_01_UE5'
MESH = '/Game/Characters/Heros/Lune/SK_Lune_Placeholder.SK_Lune_Placeholder'
CHARACTER_MESHES = (
    MESH,
    '/Game/MetaHumans/Lune/Face/Lune_FaceMesh.Lune_FaceMesh',
    '/Game/Characters/Hair/Heroes/Lune/Hair_Lune_2_skl.Hair_Lune_2_skl',
    '/Game/Characters/Heros/Maelle/Customization/Skin/SK_Maelle_ActeIII.SK_Maelle_ActeIII',
    '/Game/MetaHumans/Maelle_v2/Face/Maelle_v2_FaceMesh.Maelle_v2_FaceMesh',
    '/Game/Characters/Hair/Heroes/Maelle/Maelle_Hair_V3_Metahumanskl.Maelle_Hair_V3_Metahumanskl',
    '/Game/Characters/Enemies/Petank/SK_Petank.SK_Petank',
    '/Game/Characters/Heros/Maelle/Sword/SK_Sword_Maelle.SK_Sword_Maelle',
)
SOUND = '/Game/Audio/WAV/00_Placeholders/UI/Menu/Smart_UI_Interface_Click_An_Ants_Whip_1_Whoosh_Crack_Short_Menu.Smart_UI_Interface_Click_An_Ants_Whip_1_Whoosh_Crack_Short_Menu'


def generate(report_path,characters_path,actions_path,assets_path):
    raw = report_path.read_bytes()
    report = json.loads(raw)
    if not report['read_only'] or report['dispatched'] or not report['context_consistent']:
        raise ValueError('A consistent read-only live report is required')
    rows = {r['path'].split('.')[-1]: r for r in report['interfaces']}
    characters=json.loads(characters_path.read_bytes())
    if not characters['read_only'] or characters['dispatched']:raise ValueError('Read-only character report required')
    rows['SkinnedMeshComponent:SetLeaderPoseComponent']=characters['leader_pose']
    actions=json.loads(actions_path.read_bytes())
    if not actions['read_only'] or actions['dispatched']:raise ValueError('Read-only action contracts required')
    rows.update({r['path'].split('.')[-1]:r for r in actions['interfaces']})
    if not any(r['name']=='EAttachmentRule::SnapToTarget' and r['value']==2 for r in actions['attachment_rules']):
        raise ValueError('Attachment rule changed')
    asset_rows=[e['result'] for e in json.loads(assets_path.read_bytes())['events'] if e['event']=='asset']
    for path in (ANIMATION,MAELLE_ANIMATION):
        asset=next(r for r in asset_rows if r['path']==path)
        if asset['class_name']!='AnimSequence' or asset['errors'] or asset['values']['bEnableRootMotion'] is not False or asset['values']['Notifies']['length']!=0:
            raise ValueError('Attack clips must be verified in-place and notify-free')
    out = ['// Generated from live runtime-cinematic-feasibility-20261017.json.',
           '// Evidence SHA256: ' + hashlib.sha256(raw).hexdigest(), '#pragma once',
           'namespace e33_runtime_cinematic {']
    for i, name in enumerate(FUNCTIONS):
        row = rows[name]
        native_only=name in ('SceneComponent:K2_AttachToComponent','SkinnedMeshComponent:GetBoneName')
        if row.get('inspection_error') or (row['python_codec'] != 'accepted_schema_only' and not native_only):
            raise ValueError('Unsupported demo function: ' + name)
        fields = []
        for p in row['parameters']:
            fields.append('{' + ','.join((json.dumps(p['name']), json.dumps(p['type']),
                str(p['offset']), str(p['element_size']), str(p['flags'])+'ULL',
                p['vtable_rva']+'ULL', json.dumps(p.get('struct_name', '')), json.dumps(p.get('inner_type','')),
                str(p.get('inner_element_size',0)), json.dumps(p.get('inner_struct_name','')),
                p.get('bool_encoding', '0')+'U',
                json.dumps(p.get('property_class_name', p.get('meta_class_name', ''))))) + '}')
        if fields:
            out.append(f'inline const MeshField demo_fields_{i}[]={{' + ',\n'.join(fields) + '};')
    out.append('inline const MeshFunction demo_functions[]={')
    for i, name in enumerate(FUNCTIONS):
        row = rows[name]; f = row['function']; owner, function = name.split(':')
        out.append('{' + ','.join((json.dumps(owner), json.dumps(function), str(f['flags']),
            str(f['params_size']), str(row['allocation_extent']), str(f['return_offset']), f['entry_rva'],
            f'demo_fields_{i}' if row['parameters'] else 'nullptr', str(len(row['parameters'])))) + '},')
    out.append('};')
    mesh = next(r for r in report['demo_assets'] if r['class_name'] == 'SkeletalMesh')
    anim = next(r for r in report['demo_assets'] if r['path'] == TARGET_ANIMATION)
    if mesh['errors'] or anim['errors'] or anim['values']['bEnableRootMotion'] is not False or anim['values']['Notifies']['length'] != 0:
        raise ValueError('Demo requires a notify-free, non-root-motion animation')
    if mesh['values']['Skeleton']['path'] != anim['values']['Skeleton']['path']:
        raise ValueError('Demo skeletons must match exactly')
    maelle_anim=anim
    if maelle_anim['errors'] or maelle_anim['values']['bEnableRootMotion'] is not False or maelle_anim['values']['Notifies']['length']!=0:
        raise ValueError('Maelle animation must also be notify-free and in-place')
    out.append('struct FieldProof {const char* owner; const char* name; const char* type; uint32_t offset,width; uint64_t flags,table; uint32_t boolean;};')
    properties = [('player_controller', report['player_controller_field'])]
    properties += [('mesh_skeleton', next(p for p in mesh['field_schema'] if p['name']=='Skeleton'))]
    properties += [('animation_skeleton', next(p for p in anim['field_schema'] if p['name']=='Skeleton')),
        ('notifies', next(p for p in anim['field_schema'] if p['name']=='Notifies')),
        ('root_motion', next(p for p in anim['field_schema'] if p['name']=='bEnableRootMotion'))]
    for name, p in properties:
        out.append('inline constexpr FieldProof '+name+'={' + ','.join((
            json.dumps(p['owner']), json.dumps(p['name']), json.dumps(p['type']), str(p['offset']),
            str(p['element_size']), str(p['flags'])+'ULL', p['vtable_rva']+'ULL', p.get('bool_encoding','0')+'U')) + '};')
    for name, path in (('mesh', MESH), ('animation', ANIMATION), ('sound', SOUND)):
        package, obj = path.split('.')
        out.append(f'inline constexpr const char* {name}_package={json.dumps(package)};')
        out.append(f'inline constexpr const char* {name}_name={json.dumps(obj)};')
    out.append('inline constexpr const char* character_packages[]={'+','.join(json.dumps(p.split('.')[0]) for p in CHARACTER_MESHES)+'};')
    out.append('inline constexpr const char* character_names[]={'+','.join(json.dumps(p.split('.')[1]) for p in CHARACTER_MESHES)+'};')
    out.append('inline constexpr const char* maelle_animation_package='+json.dumps(MAELLE_ANIMATION.split('.')[0])+';')
    out.append('inline constexpr const char* maelle_animation_name='+json.dumps(MAELLE_ANIMATION.split('.')[1])+';')
    out.append('inline constexpr const char* target_animation_package='+json.dumps(TARGET_ANIMATION.split('.')[0])+';')
    out.append('inline constexpr const char* target_animation_name='+json.dumps(TARGET_ANIMATION.split('.')[1])+';')
    out.append('}')
    target = ROOT/'native/runtime_cinematic_profile.h'
    target.write_text('\n'.join(out)+'\n', encoding='utf8')
    print(target)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('characters',type=Path)
    parser.add_argument('actions',type=Path);parser.add_argument('assets',type=Path)
    args=parser.parse_args();generate(args.report,args.characters,args.actions,args.assets)
