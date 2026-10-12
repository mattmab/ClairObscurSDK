"""Read-only callback evidence; pointer matches are not proof of execution."""
import json, struct, subprocess, sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.catalog import capture
from expedition33 import _query
c=capture()
addresses={o.address:o for o in c.objects}
needles=('WidgetSequencer','InteractiveMusicSequencer','SequencerTitleWidget')
helper_names={'GetCinematicsSystem','RegisterSpawnedWidget','UnregisterSpawnedWidget',
    'PushInteractiveMusicContext','ResumeInteractiveMusicSystemWithContext',
    'PauseInteractiveMusicCurrentContext','UnpauseInteractiveMusicCurrentContext','GetInteractiveMusicSystem','GetCustomGI',
    'UpdateCinematicControlsWidget','ValidateInteractiveMusicParameters','SwitchInteractiveMusicContext',
    'ReplaceInteractiveMusicContext','PlayInteractiveMusicContext','SetInteractiveMusicPaused','AdjustVolumeByContext',
    'IsCurrentLevelProductionLevel','InterruptInteractiveMusic','ApplyInteractiveMusicParameters',
    'GetInteractiveMusicByContext','ExecuteAudioTriggerByContext','AdjustVolumeCurrentContext',
    'IsNameValid','SetPhotoModeButtonEnabled','CreateInteractiveMusicWithContextIfNeeded',
    'AdjustVolumeInteractiveMusicByContext','ProcessMusicInterruption','PrintInteractiveMusicParameters',
    'PrintAudioTriggerName','GetAudioTriggerNameWhenInterrupted','ShouldPauseMusic',
    'GetCurrentInteractiveMusic','MarkAudioComponentForUnspawn','GetSoundByContext',
    'Create New Audio Component','GetAudioTriggerNameWhenInterrupting','AdjustVolumeInteractiveMusicByContext',
    'GetAudioComponentByContext','GetAudioTriggerNameWhenInterrupted',
    'DestroyAllInteractiveMusicContexts','StopInteractiveMusicSystem','Initialize',
    'RestorePreviousInteractiveMusicParameters','SaveCurrentInteractiveMusicParameters'}
rows=[]
for o in c.objects:
    path=c.path_name(o)
    if o.name=='Initialize' and 'BP_InteractiveMusicSystem.' not in path: continue
    if not any(n in path for n in needles) and o.name not in helper_names: continue
    if o.class_name!='Function' and not o.name.startswith('Default__'): continue
    record={'path':path,'identity':[o.index,o.serial,o.address]}
    try:
        if o.class_name=='Function':
            proc=subprocess.run([str(ROOT/'build/sequence-inspector/research_probe.exe'),'--describe-script',str(c.pid),
                f'{o.index}:{o.serial}:{o.address:x}'],capture_output=True,text=True,timeout=30)
            record['rows']=[json.loads(x) for x in proc.stdout.splitlines()]
            if proc.returncode: record['error']=proc.stderr
            code=next((bytes.fromhex(r['hex']) for r in record['rows'] if r['event']=='blueprint_script'),b'')
            record['pointer_matches']=[{'offset':i,'path':c.path_name(addresses[struct.unpack_from('<Q',code,i)[0]])}
                for i in range(max(0,len(code)-7)) if struct.unpack_from('<Q',code,i)[0] in addresses]
        else:
            record['start'],record['rows']=_query(['--read-values',str(c.pid),f'{o.index}:{o.serial}:{o.address:x}'])
    except Exception as error: record['error']=str(error)
    rows.append(record)
encoded=json.dumps(rows,indent=2)
(ROOT/'evidence/sequence-callbacks.json').write_text(encoded,encoding='utf8')
(ROOT/('evidence/sequence-callbacks-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.json')).write_text(encoded,encoding='utf8')
print(len(rows),'callback/default objects;',sum('error' in r for r in rows),'failed')
