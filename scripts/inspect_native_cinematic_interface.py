"""Read-only capture of the game's own cinematic Blueprint interface."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33.catalog import capture
from expedition33.reflection import describe

FUNCTIONS = {'TriggerCinematic', 'ValidateCinematicContext', 'ValidateCinematicParameters',
    'PrepareWorldToStartCinematic', 'PlayCinematicWithLevelSequence', 'SkipCinematic',
    'CleanUpAfterCinematic', 'ExecutePostCinematicTransition', 'ResumeGameAfterCinematic',
    'ExecuteUbergraph_BP_CinematicSystem', 'StartLevelSequence', 'OnSequenceFinished',
    'FinishPreCinematicTransition'}
STRUCTS = {'S_TriggerCinematicVariables', 'S_PreCinematicParameters',
    'S_PostCinematicParameters', 'S_GameFlowTransitionRequest', 'S_GameFlowTransitionType'}

def main(pid):
    catalog = capture()
    if catalog.pid != pid:
        raise RuntimeError('Game process changed')
    owners = [o for o in catalog.objects if o.name == 'BP_CinematicSystem_C'
              and o.class_name == 'BlueprintGeneratedClass']
    if len(owners) != 1:
        raise RuntimeError('Expected one cinematic component class')
    owner = owners[0]
    targets = [o for o in catalog.objects if
        (o.class_name == 'Function' and o.outer_index == owner.index and o.name in FUNCTIONS)
        or (o.name in STRUCTS and o.class_name in ('UserDefinedStruct', 'UserDefinedEnum'))]
    if len(targets) > len(FUNCTIONS) + len(STRUCTS):
        raise RuntimeError('Ambiguous interface schemas')
    report = {'pid': pid, 'read_only': True, 'invoked': False, 'rows': [],
              'instances': [dict(path=catalog.path_name(o), index=o.index, serial=o.serial)
                  for o in catalog.objects if o.class_name == 'BP_CinematicSystem_C']}
    output = ROOT / 'evidence/native-cinematic-interface-current.json'
    for obj in targets:
        row = dict(path=catalog.path_name(obj), index=obj.index, serial=obj.serial)
        if obj.class_name == 'UserDefinedEnum':
            row['note'] = 'Enum observed; struct descriptor does not support enum members'
            report['rows'].append(row)
            continue
        metadata = describe(catalog, (obj,))[obj.index]
        row['properties'] = [dict(p) for p in metadata.properties]
        row['owners'] = [dict(p) for p in metadata.owners]
        row['function'] = dict(metadata.function) if metadata.function else None
        if obj.class_name == 'Function':
            result = subprocess.run([str(ROOT / 'build/widget-frame-inspector/research_probe.exe'),
                '--describe-script', str(pid), f'{obj.index}:{obj.serial}:{obj.address:x}'],
                text=True, capture_output=True, timeout=30, check=True)
            row['script'] = [json.loads(line) for line in result.stdout.splitlines()]
        report['rows'].append(row)
        output.write_text(json.dumps(report, indent=2), encoding='utf8')
    from expedition33.invocation import prepare_call, UnsupportedInvocation
    target = [o for o in catalog.objects if o.class_name == 'BP_CinematicSystem_C'
              and ':PersistentLevel.' in catalog.path_name(o)]
    trigger = [o for o in targets if o.name == 'TriggerCinematic']
    if len(target) == 1 and len(trigger) == 1:
        try:
            prepare_call(catalog, target[0], trigger[0], {}, pod_values=True)
            report['local_prepare'] = 'Unexpectedly prepared; NOT invoked'
        except UnsupportedInvocation as error:
            report['local_prepare'] = {'rejected': True, 'error': str(error), 'invoked': False}
    output.write_text(json.dumps(report, indent=2), encoding='utf8')
    print(output)

if __name__ == '__main__':
    main(int(sys.argv[1]))
