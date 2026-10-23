"""Generate matching UI/native allowlists from inspected scene assets."""
import hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'evidence/scene-editor/palette-inspection.json'
BODY='/Game/Characters/Mannequins/Meshes/SK_UE5_Mannequin.SK_UE5_Mannequin'

def path(package):return package+'.'+package.rsplit('/',1)[1]
def quaternion(rotation):
    p,y,r=[math.radians(v)*.5 for v in rotation];sp,cp=math.sin(p),math.cos(p);sy,cy=math.sin(y),math.cos(y);sr,cr=math.sin(r),math.cos(r)
    return [cr*sp*sy-sr*cp*cy,-cr*sp*cy-sr*cp*sy,cr*cp*sy-sr*sp*cy,cr*cp*cy+sr*sp*sy]
def part(package,mode=0,socket='',position=(0,0,0),rotation=(0,0,0),scale=(1,1,1)):
    return dict(path=path(package) if package else '',mode=mode,socket=socket,position=list(position),quaternion=quaternion(rotation),scale=list(scale))

def main():
    source=json.loads(SOURCE.read_text());sample=json.loads((ROOT/'mods/SceneEditor/sample.scene.json').read_text());assets=sample['assets']
    def pkg(key):return assets[key].split('.')[0]
    characters=[
        dict(id='lune',label='Lune',scale=1,reference='live Lune v12',parts=[part(pkg('lune_body')),part(pkg('lune_face'),1),part(pkg('lune_hair'),2,'Head',(17.65,2.83,0),(-90,0,0),(1.055,)*3)]),
        dict(id='maelle',label='Maelle',scale=1,reference='live Maelle v12',parts=[part(pkg('maelle_body')),part(pkg('maelle_face'),1),part(pkg('maelle_hair'),1),part(pkg('sword'),3,'weapon_r',rotation=(0,180,-180))]),
        dict(id='target',label='Petank',scale=1,reference='verified sample v12',parts=[part(pkg('target_body'))]),
        dict(id='verso',label='Verso',scale=1.03,reference='BP_Cine_Verso plus live head and weapon transforms',parts=[
            part('/Game/Characters/Heros/Verso/SK_Verso'),part('/Game/MetaHumans/verso/Face/verso_FaceMesh',1),
            part('/Game/Characters/Hair/Heroes/Verso/Verso_hair_v2_skl',2,'Head',(20.379389,-.878003,.000001),(-90,0,0)),
            part('/Game/Characters/Weapons/Noah/noah_weapon_l',3,'weapon_r',(1,0,0)),
            part('/Game/Characters/Hair/Heroes/Verso/Beard_Verso_skl',4),part('/Game/Characters/Hair/Heroes/Verso/Mustache_Verso_skl',4)]),
        dict(id='sciel',label='Sciel',scale=.94,reference='BP_Cine_Sciel hair defaults; live card grip; hair needs visual feedback',parts=[
            part('/Game/Characters/Heros/Sciel/SK_Sciel_Placeholder'),part('/Game/MetaHumans/sciel/Face/sciel_FaceMesh',1),
            part('/Game/Characters/Hair/Heroes/Sciel/Hair_Sciel_MessyBun_skl',2,'Head',(9.814183,-.782583,.000003),(-90,0,.133661),(1.065,1.075,1.075)),
            part('/Game/Characters/Heros/Sciel/Weapon/Sciel_Cards',3,'weapon_l',(.624067,5.390306,3.67063),(-63.260066,86.959747,-84.900053))]),
        dict(id='monoco',label='Monoco',scale=1,reference='exact live BP_GameMenu_Monoco double-bun and weapon setup',parts=[
            part('/Game/Characters/Heros/Monoco/SK_Monoco_UE5'),part('/Game/Characters/Heros/Monoco/Head/SK_Monoco_Head',1),
            part('/Game/Characters/Hair/Heroes/Z_Hair_Variation/Monoco/Monoco_DoubleBun_sk',2,'Monoco_HeadCustom_Bone01',(.15722389985093,-14.894525808666,-5.518111061518),(0,-2.049757815325,-180),(1,1,1.0000000298023224)),
            part('/Game/Characters/Heros/Monoco/Weapon/SK_Monoco_Weapon_Original',3,'weapon_r',rotation=(90,135,-135))]),
        dict(id='braseleur',label='Braseleur',scale=1,reference='live loaded full body; no gameplay Blueprint',parts=[part('/Game/Characters/Enemies/MonocoMountain/Braseleur/SK_Braseleur_UE5')]),
        dict(id='pelerin',label='Pelerin',scale=1,reference='live loaded full body; no gameplay Blueprint',parts=[part('/Game/Characters/Enemies/MonocoMountain/Swordman/SK_Pelerin_UE5')]),
        dict(id='stalact',label='Stalact',scale=1,reference='live loaded full body; no gameplay Blueprint',parts=[part('/Game/Characters/Enemies/MonocoMountain/Stalact/SK_Stalact_UE5')])]
    clips=[dict(id=key,path=assets[key],label=label,group='Sample',skeleton=BODY) for key,label in zip(('lune_attack','maelle_attack','target_idle'),('Lune - Thunder Kick','Maelle - Dancing Fury','Idle - weight shift'))]
    seen={c['path'] for c in clips}
    for row in sorted(source['animations'],key=lambda r:r['path']):
        p=row['path'];v=row['values']
        if not row['eligible'] or v.get('Skeleton')!=BODY or v.get('AdditiveAnimType')!=0 or v.get('SequenceLength',0)<.1 or p in seen:continue
        if not re.fullmatch(r'/Game/(?:[A-Za-z0-9_-]+/)*([A-Za-z0-9_-]+)\.(?i:\1)',p):continue
        group=next((name for name in ('Verso','Sciel','Monoco','Lune','Maelle') if '/'+name+'/' in p),None)
        if group is None:
            group='Gustave' if '/Noah/' in p else 'Enemies' if '/Enemies/' in p else 'NPC gestures' if '/AnimNPC/' in p or '/NPCs/' in p else 'Locomotion' if '/ALS_UE5/' in p else 'Idles' if '/Idles/' in p else 'Movement and actions'
        clips.append(dict(id='clip-'+hashlib.sha256(p.encode()).hexdigest()[:16],path=p,label=p.rsplit('.',1)[1].replace('_',' '),group=group,skeleton=BODY,length=v['SequenceLength']))
        seen.add(p)
    # Append only this inspected mask family, preserving existing native clip slots.
    mask_source=ROOT/'evidence/scene-editor/mask-animation-inspection.json'
    if mask_source.is_file():
        mask_rows=json.loads(mask_source.read_text(encoding='utf8'))
        approved={'JoyIntro_MaskJoy_Idle','JoyOutro_mask_Joy_Idle','Mask_Anger_Idle_02','Mask_Base_Empty','Mask_Hit_2','Mask_Joy_Attack1','Mask_Joy_Idle','Mask_Joy_Scream','Anger_Sequence_01','Joy_Sequence_01'}
        for row in sorted(mask_rows['animations'],key=lambda row:row['path']):
            p=row['path'];v=row['values'];name=p.rsplit('.',1)[1]
            if name not in approved:continue
            if row['errors'] or not row['eligible'] or v.get('Skeleton')!='/Game/Animations/EmptySkeleton.EmptySkeleton' or v.get('Notifies',{}).get('length')!=0 or v.get('bEnableRootMotion') is not False or v.get('AdditiveAnimType')!=0 or not .1<=v.get('SequenceLength',0)<=120:raise ValueError('Mask animation evidence failed: '+p)
            if p in seen:continue
            clips.append(dict(id='clip-'+hashlib.sha256(p.encode()).hexdigest()[:16],path=p,label=name.replace('_',' '),group='Masks',skeleton=v['Skeleton'],length=v['SequenceLength']))
            seen.add(p)
    # Complete typed registry audit; append new clips to preserve saved slot IDs.
    inventory=[]
    baseline=json.loads((ROOT/'evidence/scene-editor/clip-baseline-v52.json').read_text())
    existing={c['path'] for c in baseline}
    clips=baseline+[c for c in clips if c['path'] not in existing]
    audit_file=ROOT/'evidence/scene-editor/animation-registry-audit.json'
    if audit_file.is_file():
        audit=json.loads(audit_file.read_text(encoding='utf8'))
        if not audit.get('complete') or len(audit['animations'])!=audit['total']:raise ValueError('Incomplete animation audit')
        for row in sorted(audit['animations'],key=lambda row:row['path']):
            p=row['path'];v=row['values'];reason=[]
            if row['errors']:reason.append('Inspection incomplete')
            if v.get('Notifies',{}).get('length',0):reason.append('Gameplay animation notifies')
            if v.get('bEnableRootMotion'):reason.append('Root motion')
            if v.get('AdditiveAnimType',0):reason.append('Additive pose needs a base animation')
            if not .1<=v.get('SequenceLength',0)<=120:reason.append('Outside preview duration range')
            if not v.get('Skeleton'):reason.append('No verified skeleton')
            eligible=row['eligible'] and not reason
            inventory.append(dict(path=p,skeleton=v.get('Skeleton'),length=v.get('SequenceLength'),previewable=eligible,reason='; '.join(reason)))
            if not eligible or p in seen:continue
            if not re.fullmatch(r'/Game/(?:[A-Za-z0-9_-]+/)*([A-Za-z0-9_-]+)\.(?i:\1)',p):continue
            clips.append(dict(id='clip-'+hashlib.sha256(p.encode()).hexdigest()[:16],path=p,label=p.rsplit('.',1)[1].replace('_',' '),group='Registry',skeleton=v['Skeleton'],length=v['SequenceLength']))
            seen.add(p)
        baseline=json.loads((ROOT/'evidence/scene-editor/clip-baseline-v52.json').read_text())
        if [c['path'] for c in clips[:len(baseline)]]!=[c['path'] for c in baseline]:raise ValueError('Existing native clip order changed')
    registry_file=ROOT/'evidence/scene-editor/game-asset-registry.json'
    if registry_file.is_file():
        registry=json.loads(registry_file.read_text());known={c['parts'][0]['path'] for c in characters}
        for p in registry['skeletal_meshes']:
            if p in known:continue
            label=p.rsplit('.',1)[1]
            if '/Paintress/' in p:label='Paintress - '+label
            characters.append(dict(id='mesh-'+hashlib.sha256(p.encode()).hexdigest()[:12],label=label+' (mesh)',scale=1,raw=True,group=p.split('/')[3] if p.startswith('/Game/Characters/') else 'Other',reference='Typed game Asset Registry; body/part mesh, assembly not inferred',parts=[part(p.split('.')[0])]))
    for c in characters:
        name=c['parts'][0]['path'].rsplit('.',1)[-1]
        if name in ('Face_Joy','Face_Anger'):
            mesh=next(row for row in mask_rows['meshes'] if row['path']==c['parts'][0]['path'])
            if mesh['errors'] or mesh['values']['Skeleton']!='/Game/Animations/EmptySkeleton.EmptySkeleton':raise ValueError('Mask mesh evidence failed')
            c['skeleton']=mesh['values']['Skeleton'];c['label']=name.removeprefix('Face_')+' (mask)'
            c['reference']='Inspected original mask Blueprint and matching Blendshape animation family; scene-owned mesh'
    for c in characters:c['parts']+=[part('') for _ in range(6-len(c['parts']))]
    library_source=ROOT/'evidence/scene-editor/actor-library-audit.json'
    if library_source.is_file():
        by_role={c['id']:c for c in characters};by_clip={c['id']:c for c in clips}
        for row in json.loads(library_source.read_text(encoding='utf8')):
            character=by_role[row['role']]
            if character['parts'][0]['path']!=row['path'] or not row['clips'] or any(by_clip[k]['skeleton']!=row['skeleton'] for k in row['clips']):raise ValueError('Animated actor audit changed')
            character.update(main_actor=True,skeleton=row['skeleton'],label=row['label'],animation_count=len(row['clips']),library_kind=row['library_kind'],library_note=row['note'])
            if row['library_kind']=='mask':
                joy='Face_Joy' in row['path']
                character.update(spawn_rotation=[0.,-90.,-90. if joy else 0.],spawn_scale=1.5 if joy else .005,spawn_height=120.)
            character['default_animation']=next((k for k in row['clips'] if 'idle' in by_clip[k]['path'].casefold()),row['clips'][0])
    # Enrich existing role slots from inspected assembly recipes; never reorder IDs.
    recipes=ROOT/'evidence/scene-editor/five-actor-assembly-recipes.json'
    if recipes.is_file():
        by_role={c['id']:c for c in characters};by_clip={c['id']:c for c in clips}
        for recipe in json.loads(recipes.read_text(encoding='utf8')):
            c=by_role[recipe['role']]
            if c['parts'][0]['path']!=recipe['body'] or len(recipe['parts'])!=6 or by_clip[recipe['default_animation']]['skeleton']!=recipe['skeleton']:raise ValueError('Assembly recipe identity changed')
            c.update(main_actor=True,label=recipe['label'],parts=recipe['parts'],skeleton=recipe['skeleton'],default_animation=recipe['default_animation'],spawn_scale=recipe['spawn_scale'],spawn_rotation=recipe['spawn_rotation'],spawn_height=recipe['spawn_height'],library_kind=recipe['library_kind'],library_note=recipe['note'],reference='five-actor-assembly-inspection.json; scene-owned assembly')
    for clip in clips:
        if clip['path'].endswith('.Mask_Anger_Idle_02'):clip['preview_scale']=100.
    palette=dict(schema=1,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),skeleton=BODY,characters=characters,clips=clips,animation_inventory=inventory)
    (ROOT/'mods/SceneEditor/palette.json').write_text(json.dumps(palette,indent=2)+'\n')
    lines=['// Generated by scripts/build_scene_palette.py from live inspection.','#pragma once','namespace e33_runtime_scene {',f'inline constexpr unsigned scene_role_count={len(characters)},scene_clip_count={len(clips)};',
           'struct PalettePart {const char* package;const char* name;unsigned mode;const char* socket;double position[3],quaternion[4],scale[3];};',
           'inline const PalettePart scene_parts[][6]={']
    q=lambda value:json.dumps(value)
    array=lambda values:'{'+','.join(format(v,'.17g') for v in values)+'}'
    for c in characters:
        lines.append('{'+','.join('{'+','.join((q(p['path'].split('.')[0]),q(p['path'].rsplit('.',1)[-1] if p['path'] else ''),str(p['mode']),q(p['socket']),array(p['position']),array(p['quaternion']),array(p['scale'])))+'}' for p in c['parts'])+'},')
    lines+=['};','struct PaletteClip {const char* package;const char* name;double preview_scale;};','inline const PaletteClip scene_clips[]={']
    lines += ['{'+q(c['path'].split('.')[0])+','+q(c['path'].rsplit('.',1)[1])+','+str(c.get('preview_scale',1.))+'},' for c in clips]
    lines+=['};','}'];(ROOT/'native/runtime_scene_palette.h').write_text('\n'.join(lines)+'\n')
    wire=ROOT/'src/expedition33/_runtime_scene_wire.py';wire_text=wire.read_text()
    wire_text=re.sub(r'^ROLE_COUNT=\d+$','ROLE_COUNT='+str(len(characters)),wire_text,flags=re.M)
    wire_text=re.sub(r'^CLIP_COUNT=\d+$','CLIP_COUNT='+str(len(clips)),wire_text,flags=re.M)
    wire.write_text(wire_text)
    print(json.dumps(dict(characters=len(characters),animations=len(clips),groups=sorted({c['group'] for c in clips}))))

if __name__=='__main__':main()
