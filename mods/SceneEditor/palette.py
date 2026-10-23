"""Inspected skeleton-compatible clip/assembly catalog shared with the native build."""
import json
import re
from pathlib import Path
from .assets import ASSETS as SAMPLE_ASSETS
PALETTE=json.loads(Path(__file__).with_name('palette.json').read_text(encoding='utf8'))
CHARACTERS={row['id']:row for row in PALETTE['characters']}
CHARACTERS['monoco']['label']='Monoco'
ANIMATIONS={row['id']:row for row in PALETTE['clips']}
ROLES=tuple(CHARACTERS)
CLIPS=tuple(ANIMATIONS)
CLIP_LABELS=tuple(row['label'] for row in ANIMATIONS.values())
ASSETS=dict(SAMPLE_ASSETS)
PART_KEYS=('body','face','hair','equipment','beard','mustache')
ASSEMBLIES={}
for role,row in CHARACTERS.items():
    assembly={}
    for key,part in zip(PART_KEYS,row['parts']):
        if part['path']:
            asset_key=role+'_'+key;ASSETS[asset_key]=part['path'];assembly[key]=asset_key
    assembly['recipe']='scene-palette-v15';ASSEMBLIES[role]=assembly
ASSETS.update({key:row['path'] for key,row in ANIMATIONS.items()})

# Asset-origin sets are independent of editable actor names. Skeleton matching
# remains separate: the same character family can include body and face rigs.
BODY_SKELETON=PALETTE['skeleton']
# Folder names in cinematics identify the scene, not the actor performing a track.
# These aliases are asset identities; editable actor labels never participate.
_OWNER_ALIASES={name.casefold():name for name in ('Lune','Maelle','Sciel','Verso','Monoco','Gustave','Clea','Simon','Paintress')}
_OWNER_ALIASES.update(noah='Gustave',aline='Paintress',giantpaintress='Paintress',simonstandin='Simon')
_OWNER_OVERRIDES={
    '/Game/Characters/Enemies/Axons/Many_faces/Faces/Animations/SadnessOutro_Mask_Sadness_Idle.SadnessOutro_Mask_Sadness_Idle':'Sadness mask',
    '/Game/Characters/Enemies/ManyFaces/Masks/Anims/Sequences/Animation_Mask/Sadness_Sequence_01.Sadness_Sequence_01':'Sadness mask',
    '/Game/Cinematics/Visages/Sadness/SadnessIntro_Anim_01.SadnessIntro_Anim_01':'Sadness mask',
    '/Game/Characters/Heros/Lune/Animations/BattleTurn/Paintress_Idle_FinalSequence.Paintress_Idle_FinalSequence':'Paintress',
}

# Exact authored PreviewSkeletalMesh associations for inspected new assemblies.
_OWNER_OVERRIDES.update(PALETTE.get('audited_animation_owners',{}))

def animation_owner(path):
    override=_OWNER_OVERRIDES.get(path)
    if override:return override
    bits=path.split('/');lower=[b.casefold() for b in bits]
    name=bits[-1].rsplit('.',1)[-1].casefold()
    if '/many_faces/faces/' in path.casefold() or '/manyfaces/masks/' in path.casefold():
        for mask in ('Joy','Anger','Sadness'):
            if mask.casefold() in name:return mask+' mask'
        return None
    # Actual character folders are trustworthy, unlike cinematic scene folders.
    if '/characters/' in path.casefold():
        for hero in ('Lune','Maelle','Sciel','Verso','Monoco','Gustave','Noah'):
            if hero.casefold() in lower:return _OWNER_ALIASES[hero.casefold()]
        if 'enemies' in lower:
            tail=bits[lower.index('enemies')+1:]
            for i,value in enumerate(tail):
                if value.casefold() in ('animations','anims','animation'):
                    owner=tail[i-1] if i else None
                    return _OWNER_ALIASES.get((owner or '').casefold(), 'Clea' if owner=='Clea_v1' else owner)
        if 'npcs' in lower:
            tail=bits[lower.index('npcs')+1:]
            if tail and tail[0].casefold() not in ('animations','animation'):
                return _OWNER_ALIASES.get(tail[0].casefold(),tail[0])
    # Boundary matching avoids Clea=dataclean and Simon=FinisherSimon.
    owners={_OWNER_ALIASES[token] for token in re.split(r'[_-]+',name) if token in _OWNER_ALIASES}
    return next(iter(owners)) if len(owners)==1 else None

def actor_animation_owner(role):
    if role=='target':return 'Petank'
    path=CHARACTERS[role]['parts'][0]['path']
    return animation_owner(path) or (path.split('/')[-2] if '/Enemies/' in path else CHARACTERS[role]['label'].removesuffix(' (mesh)'))

def clip_set(clip):return animation_owner(ANIMATIONS[clip]['path']) or 'Shared / '+('Idles' if clip=='target_idle' else ANIMATIONS[clip]['group'])

def animation_choices(role,skeleton,group='character',query=''):
    if not skeleton:return ()
    compatible=tuple(k for k,v in ANIMATIONS.items() if v['skeleton']==skeleton)
    if group=='character':
        own=tuple(k for k in compatible if animation_owner(ANIMATIONS[k]['path'])==actor_animation_owner(role) or (role=='target' and k=='target_idle'))
        compatible=own or tuple(k for k in compatible if animation_owner(ANIMATIONS[k]['path']) is None)
    elif group is not None:compatible=tuple(k for k in compatible if clip_set(k)==group)
    words=query.casefold().split()
    return tuple(k for k in compatible if all(w in (ANIMATIONS[k]['label']+' '+ANIMATIONS[k]['path']+' '+clip_set(k)).casefold() for w in words))

def animation_sets(role,skeleton):return tuple(sorted({clip_set(k) for k in animation_choices(role,skeleton,None)}))


def library_roles(all_meshes=False,query=''):
    words=query.casefold().split()
    return tuple(role for role,row in CHARACTERS.items()
        if (all_meshes or not row.get('raw') or row.get('main_actor'))
        and all(word in (row['label']+' '+row['parts'][0]['path']).casefold() for word in words))

def library_label(role):
    row=CHARACTERS[role];count=row.get('animation_count')
    return row['label']+(f' | {count} animation'+('s' if count!=1 else '') if count else ' [face / part]' if '/Faces/' in row['parts'][0]['path'] else '')


def animation_inventory(role,skeleton):
    owner=actor_animation_owner(role)
    return tuple(row for row in PALETTE.get('animation_inventory',()) if row['skeleton']==skeleton and animation_owner(row['path'])==owner)

# Display counts derive from the full verified catalog, not the old one-clip audit.
for role,row in CHARACTERS.items():
    if row.get('raw') and not row.get('main_actor'):continue
    skeleton=row.get('skeleton') or (BODY_SKELETON if not row.get('raw') else None)
    own=animation_choices(role,skeleton, 'character')
    row['animation_count']=len(own)
    row['discovered_animation_count']=len(animation_inventory(role,skeleton))
