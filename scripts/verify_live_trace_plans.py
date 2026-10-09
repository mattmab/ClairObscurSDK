"""Read live reflection and plan trace storage; never installs hooks or invokes."""
from dataclasses import asdict
import json
from pathlib import Path

from expedition33.catalog import capture
from expedition33.tracing import prepare_trace


def main():
    catalog = capture()
    records = []
    for owner, name in [('Actor', 'IsActorBeingDestroyed'), ('Actor', 'SetActorTickEnabled'),
                        ('PlayerController', 'GetViewportSize')]:
        cls = catalog.find_class(owner)
        matches = [obj for obj in catalog.objects if obj.outer_index == cls.index and obj.name == name]
        assert len(matches) == 1, (owner, name, len(matches))
        function = matches[0]
        plan = prepare_trace(catalog, function)
        records.append(dict(function=catalog.path_name(function), index=function.index,
                            serial=function.serial, entry_rva=hex(plan.entry_rva),
                            parameter_size=plan.parameter_size, capture_size=plan.capture_size,
                            fields=[dict(asdict(field), name=plan.parameters[field.parameter].name)
                                    for field in plan.fields]))
    assert [f['source'] for f in records[0]['fields']] == ['return']
    assert [f['source'] for f in records[1]['fields']] == ['locals']
    assert [f['source'] for f in records[2]['fields']] == ['out', 'out']
    result = dict(pid=catalog.pid, plans=records, hooks_installed=False, dispatched=False)
    path = Path(__file__).resolve().parents[1] / 'evidence/trace-plans-live.json'
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
