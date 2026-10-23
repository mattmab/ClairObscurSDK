"""Exercise expanded assemblies, animation search, native selection and cleanup."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from scene_editor_command import request
import verify_scene_editor_live as base
from verify_scene_characters_live import choose
base.REPORT=ROOT/'evidence/scene-editor/palette-acceptance.json'
click=base.click;record=base.record
palette=json.loads((ROOT/'mods/SceneEditor/palette.json').read_text());clips=palette['clips']

def prefix(label):
    frame=request('scene.frame');c=next(c for c in frame['frame']['controls'] if c['enabled'] and c['label'].startswith(label))
    return request('scene.click',dict(token=c['token'],revision=frame['frame']['revision']))

def select_animation(key,needle):
    clip=next(c for c in clips if needle in c['path'])
    actor=next(a for a in request('scene.document')['actors'] if a['id']==key)
    choose(actor['name']+' ['+key+']');prefix('Animation: ')
    request('scene.field',dict(value=needle));click('Search');choose(clip['label']);click('Back')
    return clip

def add(label):
    choose('Add character...');choose('Add '+label)
    actor=request('scene.document')['actors'][-1];click('Back');return actor['id']

def remove_all():
    for actor in request('scene.document')['actors']:
        choose(actor['name']+' ['+actor['id']+']');choose('Remove character...');click('Remove this character')

def preview(name,expected):
    click('Back');click('Play modified scene');base.wait_state({'playing'},180);time.sleep(1.2)
    observed=request('scene.animations');record(name+'_native_animations',observed)
    actual=[r['assets'].get('CurrentAsset') for r in observed if not r['errors']]
    for path in expected:
        if path not in actual:raise RuntimeError('Selected animation was not observed on a native body: '+path)
    finished=base.wait_state({'finished'},60);record(name+'_finished',finished)
    if finished['playback']['private_leases']:raise RuntimeError('Native scene references remain')
    deadline=time.monotonic()+30
    while not request('scene.frame')['open'] and time.monotonic()<deadline:time.sleep(.2)
    snapshot=request('scene.snapshot');record(name+'_after',snapshot)
    if snapshot!=base.events[0]['value']:raise RuntimeError('Camera/input/world changed')
    click('Actors / properties')

def main():
    record('before',request('scene.snapshot'));click('Load Sample Scene');click('Actors / properties')
    keys=[add(label) for label in ('Verso','Sciel','Monoco (double bun)')]
    selected=[select_animation(key,needle) for key,needle in zip(keys,('A_RD_ArmsCrossed_Idle_Verso_V2','Sciel_Idle_Skill','Monoco_Idle_Base'))]
    record('hero_document',request('scene.document'))
    # Keep original sample animation choices too, verifying mixed legacy/new slots.
    await_paths=[c['path'] for c in selected]+[c['path'] for c in clips[:3]]
    preview('heroes',await_paths)
    remove_all()
    keys=[add(label) for label in ('Braseleur','Pelerin','Stalact')]
    selected=[select_animation(key,needle) for key,needle in zip(keys,('Braseleur_Stun','Pelerin_Idle_2','Stalac_Idle'))]
    click('Back');click('Save As...');request('scene.field',dict(value='Scene Editor - expanded enemy palette'));click('Apply')
    saved=request('scene.document');click('Load Sample Scene');click('Load saved scene');choose(saved['name'])
    if request('scene.document')!=saved:raise RuntimeError('Expanded choices did not save/reload exactly')
    record('enemy_roundtrip',saved);click('Actors / properties');preview('enemies',[c['path'] for c in selected])
    click('Back');click('Load Sample Scene');record('machine_acceptance_passed',True)
    print(json.dumps(dict(passed=True,report=str(base.REPORT),manual_visual_confirmation=False)))

if __name__=='__main__':
    try:main()
    except Exception as error:record('error',repr(error));raise
