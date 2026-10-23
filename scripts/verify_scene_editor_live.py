"""Exercise the first milestone through real menu controls and native fields."""
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from scene_editor_command import request
REPORT=ROOT/'evidence/scene-editor/acceptance.json'
events=[]
def record(name,value):
    events.append(dict(event=name,value=value));REPORT.write_text(json.dumps(dict(machine_checks_only=True,manual_visual_confirmation=False,events=events),indent=2)+'\n',encoding='utf8')
def click(label):
    frame=request('scene.frame')
    control=next((c for c in frame['frame']['controls'] if c['label']==label and c['enabled']),None)
    if control is None:raise ValueError('Missing enabled control '+label)
    return request('scene.click',dict(token=control['token'],revision=frame['frame']['revision']))
def edit(label,value):click(label);request('scene.field',dict(value=str(value)));return click('Apply')
def wait_state(wanted,timeout=100):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        status=request('scene.status')
        if status['playback'].get('error'):raise RuntimeError(str(status))
        if status['playback'].get('state') in wanted:return status
        if status['message'].startswith('Preview failed'):raise RuntimeError(status['message'])
        time.sleep(.2)
    raise TimeoutError('Scene state did not reach '+str(wanted))
def main():
    sample=ROOT/'mods/SceneEditor/sample.scene.json';digest=hashlib.sha256(sample.read_bytes()).hexdigest()
    record('before',request('scene.snapshot'))
    click('Load Sample Scene');click('Actors / properties');click('Lune [lune]')
    edit('Forward X: 0',30);click('Back');click('Back');click('Timeline events')
    frame=request('scene.frame');control=next(c for c in frame['frame']['controls'] if 'audio / lune' in c['label'] and c['enabled'])
    request('scene.click',dict(token=control['token'],revision=frame['frame']['revision']))
    edit('Start time: 2.5 seconds',3.25);click('Back');click('Back')
    click('Save As...');request('scene.field',dict(value='Scene Editor acceptance - edited sample'));click('Apply')
    saved=request('scene.document');state=request('scene.status');record('saved',dict(id=state['saved_id'],document=saved))
    click('Load Sample Scene');click('Load saved scene');click(saved['name'])
    restored=request('scene.document')
    if restored!=saved:raise RuntimeError('Saved document did not round-trip')
    if next(a for a in restored['actors'] if a['id']=='lune')['transform']['position'][0]!=30:raise RuntimeError('Actor transform edit missing')
    if next(e for e in restored['events'] if e['id']=='audio-0')['at']!=3.25:raise RuntimeError('Timestamp edit missing')
    if request('scene.status')['playback'].get('state') not in ('idle','finished','interrupted'):raise RuntimeError('Loading started playback')
    record('roundtrip_without_playback',True)
    click('Play modified scene');wait_state({'playing'});record('playing',True)
    finished=wait_state({'finished'},60);record('finished',finished)
    result=finished['playback']
    if result['private_leases'] or result['audio_cues_dispatched']!=9 or result['effects_spawned']!=11 or not 3.25<=result['audio_at']<3.6:raise RuntimeError('Modified timeline/native cleanup evidence incomplete')
    deadline=time.monotonic()+30
    while not request('scene.frame')['open'] and time.monotonic()<deadline:time.sleep(.2)
    record('after_full',request('scene.snapshot'))
    click('Play modified scene');wait_state({'playing'});time.sleep(2.8);request('scene.stop')
    stopped=wait_state({'interrupted'},30);record('stopped',stopped)
    if stopped['playback']['private_leases']:raise RuntimeError('Early stop leaked private references')
    record('after_stop',request('scene.snapshot'))
    if events[0]['value']!=events[-1]['value']:raise RuntimeError('Camera/input/world baseline changed')
    if hashlib.sha256(sample.read_bytes()).hexdigest()!=digest:raise RuntimeError('Bundled sample changed')
    record('sample_unchanged',True);record('machine_acceptance_passed',True)
    print(json.dumps(dict(report=str(REPORT),passed=True,manual_visual_confirmation=False)))

if __name__=='__main__':
    try:main()
    except Exception as error:record('error',repr(error));raise
