"""Character milestone acceptance through actual Scene Editor menu controls."""
import copy,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from scene_editor_command import request
import verify_scene_editor_live as base

base.REPORT=ROOT/'evidence/scene-editor/characters-acceptance.json'
click=base.click
record=base.record

def choose(label):
    """Use ordinary Next page controls for long actor/property lists."""
    for _ in range(8):
        frame=request('scene.frame');controls=frame['frame']['controls']
        control=next((c for c in controls if c['label']==label and c['enabled']),None)
        if control:return request('scene.click',dict(token=control['token'],revision=frame['frame']['revision']))
        next_page=next((c for c in controls if c['enabled'] and c['label'].lower().startswith('next')),None)
        if next_page is None:break
        request('scene.click',dict(token=next_page['token'],revision=frame['frame']['revision']))
    raise ValueError('Missing menu control '+label)

def current_actor():
    frame=request('scene.frame')
    # Added actor is the newest instance; it was selected by the Add action.
    return request('scene.document')['actors'][-1]['id']

def main():
    sample=ROOT/'mods/SceneEditor/sample.scene.json';digest=hashlib.sha256(sample.read_bytes()).hexdigest()
    record('before',request('scene.snapshot'))
    click('Load Sample Scene');click('Actors / properties')
    # Leave original attackers idle to verify suppression of their authored cues.
    for key,name in (('lune','Lune'),('maelle','Maelle')):
        choose(name+' ['+key+']');choose('Animation: '+('Lune - Thunder Kick' if key=='lune' else 'Maelle - Dancing Fury'))
        click('Idle - weight shift');click('Back')
    added=[]
    for label,animation in (('Lune','Lune - Thunder Kick'),('Maelle','Maelle - Dancing Fury'),('Petank','Idle - weight shift')):
        choose('Add character...');click('Add '+label);key=current_actor();added.append(key)
        choose('Animation: Idle - weight shift');click(animation)
        choose('Loop: On');choose('Animation start: 1s');request('scene.field',dict(value='0.5'));click('Apply');click('Back')
    doc=request('scene.document');assert len(doc['actors'])==6
    record('six_instances',doc)
    # Remove the sample target, then add another duplicate Lune. This deletes
    # sample contact events but preserves the two original trail documents.
    choose('Petank target [target]');choose('Remove character...');click('Remove this character')
    doc=request('scene.document');assert all(a['id']!='target' for a in doc['actors'])
    assert not any(e['id'].startswith(('audio-','impact-','recoil-')) for e in doc['events'])
    choose('Add character...');click('Add Lune');added.append(current_actor());click('Back');click('Back')
    click('Save As...');request('scene.field',dict(value='Scene Editor - six character animation test'));click('Apply')
    saved=request('scene.document');saved_id=request('scene.status')['saved_id'];record('saved',dict(id=saved_id,document=saved))
    click('Load Sample Scene');click('Load saved scene');choose(saved['name'])
    assert request('scene.document')==saved
    record('roundtrip_without_playback',request('scene.status')['playback'].get('state') in ('idle','finished','interrupted'))
    click('Play modified scene');base.wait_state({'playing'},150);record('playing',True)
    finished=base.wait_state({'finished'},60);record('finished',finished)
    p=finished['playback'];assert p['private_leases']==0 and p['effects_spawned']==0 and p['audio_cues_dispatched']==0
    deadline=time.monotonic()+30
    while not request('scene.frame')['open'] and time.monotonic()<deadline:time.sleep(.2)
    record('after_six',request('scene.snapshot'))
    assert base.events[0]['value']==base.events[-1]['value']
    # Exercise removing every instance, including the last one, then camera-only
    # preview and early stop. Keep the saved six-instance scene for user feedback.
    click('Actors / properties')
    for actor in saved['actors']:
        choose(actor['name']+' ['+actor['id']+']');choose('Remove character...');click('Remove this character')
    assert request('scene.document')['actors']==[];click('Back')
    click('Play modified scene');base.wait_state({'playing'},150);time.sleep(1.5);request('scene.stop')
    stopped=base.wait_state({'interrupted'},30);record('empty_scene_stopped',stopped)
    assert stopped['playback']['private_leases']==0
    record('after_stop',request('scene.snapshot'));assert base.events[0]['value']==base.events[-1]['value']
    deadline=time.monotonic()+30
    while not request('scene.frame')['open'] and time.monotonic()<deadline:time.sleep(.2)
    click('Load saved scene');choose(saved['name']);assert request('scene.document')==saved
    assert hashlib.sha256(sample.read_bytes()).hexdigest()==digest
    record('sample_unchanged',True);record('machine_acceptance_passed',True)
    print(json.dumps(dict(report=str(base.REPORT),passed=True,manual_visual_confirmation=False)))

if __name__=='__main__':
    try:main()
    except Exception as error:record('error',repr(error));raise
