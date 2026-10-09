"""Read-only live UEnum observations; never invokes or writes enum values."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
from pathlib import Path

from expedition33 import RuntimeQueryError, _query
from expedition33.catalog import capture
from expedition33.enums import describe_enums


def main():
    catalog = capture()
    targets = [catalog.find_path(path, 'Enum') for path in (
        '/Script/Engine.EMouseLockMode', '/Script/Engine.ENetRole')]
    descriptors = describe_enums(catalog, targets)
    mouse = descriptors[targets[0].index]
    assert mouse.members and any('DoNotLock' in m.name for m in mouse.members)
    # Exercise native rejection, bypassing only the Python catalog's own check.
    stale = replace(targets[0], serial=targets[0].serial + 1)
    rejected = {}
    for label, obj, expected in (
        ('stale_serial', stale, 'DESCRIPTOR_IDENTITY_CHANGED'),
        ('wrong_type', catalog.by_index[catalog.find_class('Actor').index], 'ENUM_TARGET_TYPE_UNSUPPORTED')):
        try:
            _query(['--describe-enums', str(catalog.pid), f'{obj.index}:{obj.serial}:{obj.address:x}'])
        except RuntimeQueryError as error:
            assert expected in str(error), str(error)
            rejected[label] = expected
        else:
            raise AssertionError(f'Native reader accepted {label}')
    result = dict(timestamp=datetime.now(timezone.utc).isoformat(), pid=catalog.pid,
                  read_only=True, gc_atomic=False, enum_invocation_supported=False,
                  descriptors=[asdict(d) for d in descriptors.values()], rejected=rejected)
    path = Path(__file__).resolve().parents[1] / 'evidence/enum-members-live.json'
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
