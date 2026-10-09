"""Plan from live target metadata and validate wire bytes; never dispatch."""
from pathlib import Path
import json
import subprocess

from expedition33.catalog import capture
from expedition33.enums import describe_enums
from expedition33.invocation import prepare_call
from expedition33 import _enum_wire


def main():
    root = Path(__file__).resolve().parents[1]
    catalog = capture()
    enum = catalog.find_path('/Script/Engine.EMouseLockMode', 'Enum')
    descriptor = describe_enums(catalog, [enum])[enum.index]
    cls = catalog.find_class('WidgetBlueprintLibrary')
    targets = [o for o in catalog.objects if o.class_index == cls.index and o.name == 'Default__WidgetBlueprintLibrary']
    functions = [o for o in catalog.objects if o.outer_index == cls.index and o.name == 'SetInputMode_GameAndUIEx']
    assert len(targets) == len(functions) == 1
    plan = prepare_call(catalog, targets[0], functions[0], dict(PlayerController=None,
        InWidgetToFocus=None, InMouseLockMode=descriptor.value('EMouseLockMode::DoNotLock'),
        bHideCursorDuringCapture=False, bFlushInput=False), enum_values=True)
    packet = _enum_wire.encode_plan(plan)
    path = root / 'evidence/enum-live-plan.bin'
    path.write_bytes(packet)
    result = subprocess.run([str(root / 'build/enum-schema-fixture/enum_schema_fixture.exe'), str(path)],
        capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.stdout.strip() == 'Python enum packet passed native pure validation; no dispatch.', result.stdout
    evidence = dict(pid=catalog.pid, passed=True, dispatched=False, function=catalog.path_name(functions[0]),
        wire_version=plan.wire_version, packet_size=len(packet), parameter_size=plan.parameter_size,
        enum_path=catalog.path_name(enum), member='EMouseLockMode::DoNotLock', value=0,
        native_validation=result.stdout.strip(), limitation='Candidate path; session integration pending')
    (root / 'evidence/enum-live-plan.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__': main()
