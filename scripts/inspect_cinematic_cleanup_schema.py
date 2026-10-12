"""Read-only reflected cleanup contracts for audio and sequence widgets."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from expedition33.catalog import capture_matching
from expedition33 import _query

names = ('AudioComponent', 'BP_CinematicSystem_C', 'MovieSceneTrackInstance',
         'BP_WidgetSequencerTrackInstance_C', 'GetPlayState', 'SetPaused',
         'SetPhotoModeButtonEnabled', 'RegisterSpawnedWidget', 'UnregisterSpawnedWidget')
c = capture_matching(9616, names=names)
records = []
for obj in c.objects:
    if obj.name not in names or obj.class_name not in ('Class', 'BlueprintGeneratedClass', 'Function'): continue
    record = dict(path=c.path_name(obj), identity=[obj.index, obj.serial, obj.address])
    try:
        record['start'], record['rows'] = _query(['--describe', str(c.pid),
            f'{obj.index}:{obj.serial}:{obj.address:x}'])
    except Exception as error: record['error'] = repr(error)
    records.append(record)
(ROOT/'evidence/cinematic-cleanup-schema.json').write_text(json.dumps(records, indent=2), encoding='utf8')
print(len(records), 'contracts captured')
