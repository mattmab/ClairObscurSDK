"""Read-only same-build construction schema; does not spawn or invoke actors."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33.catalog import capture
from expedition33.reflection import describe
from expedition33._reader import ReadBatch

OWNERS = frozenset(('SCS_Node', 'SimpleConstructionScript',
    'InheritableComponentHandler', 'ComponentOverrideRecord', 'ComponentKey',
    'BlueprintGeneratedClass', 'Guid', 'ActorComponent', 'SceneComponent',
    'PostProcessComponent', 'BoxComponent', 'BlueprintCookedComponentInstancingData',
    'TViewTarget', 'PlayerController', 'PlayerCameraManager',
    'MovieSceneDynamicBinding', 'MovieSceneBindingOverrides', 'MovieSceneBindingOverrideData',
    'CineCameraActor', 'CameraActor', 'CineCameraComponent', 'CameraComponent',
    'CameraFilmbackSettings', 'PlateCropSettings', 'Rotator'))

def run(pid):
    catalog = capture()
    if catalog.pid != pid:
        raise RuntimeError('Game PID changed')
    targets = [o for o in catalog.objects if o.name in OWNERS and
               o.class_name in ('Class', 'ScriptStruct')]
    if len(targets) > len(OWNERS):
        raise RuntimeError('Ambiguous schema owners')
    rows = []
    with ReadBatch(pid):
        for obj in targets:
            metadata = describe(catalog, (obj,))[obj.index]
            rows.append(dict(path=catalog.path_name(obj), index=obj.index,
                serial=obj.serial, properties=[dict(p) for p in metadata.properties],
                owners=[dict(o) for o in metadata.owners]))
    output = ROOT / 'evidence/lens-construction-schemas.json'
    output.write_text(json.dumps(dict(pid=pid, schemas=rows,
        missing=sorted(OWNERS - {o.name for o in targets}),
        playback_attempted=False, actors_spawned=False), indent=2), encoding='utf8')
    print(output, len(rows))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, required=True)
    run(parser.parse_args().pid)
