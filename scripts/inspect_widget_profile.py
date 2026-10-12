"""Capture exact widget script bindings while the audited title asset is retained."""
import json,subprocess
from pathlib import Path
from expedition33._scope import SessionScope
from expedition33.assets import load_asset
from expedition33.catalog import capture_matching
ROOT=Path(__file__).resolve().parents[1]
def run(mod):
    scope=SessionScope(mod.session);records=[]
    try:
        load_asset(scope,'/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere.LS_Title_PrologueLumiere')
        names=('ExecuteUbergraph_BP_WidgetSequencerTrackInstance','BP_WidgetSequencerSection_C',
               'MovieSceneTrackInstanceInput','BP_WidgetSequencerTrackInstance_C')
        catalog=capture_matching(scope.pid,names=names)
        for obj in catalog.objects:
            if obj.name not in names:continue
            mode='--describe-script' if obj.class_name=='Function' else '--describe'
            result=subprocess.run([str(ROOT/'build/widget-frame-inspector/research_probe.exe'),mode,
                str(scope.pid),f'{obj.index}:{obj.serial}:{obj.address:x}'],capture_output=True,text=True,check=True,timeout=15)
            records.extend(json.loads(line) for line in result.stdout.splitlines())
        found={r['name'] for r in records if r['event']=='object'}
        if set(names)!=found:raise RuntimeError('Missing widget profile dependency')
    finally:
        scope.close()
        (ROOT/'evidence/widget-track-profile-current.json').write_text(json.dumps(records,indent=2),encoding='utf8')
    return {'objects':sorted(found),'playback_attempted':False}
