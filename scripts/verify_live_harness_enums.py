"""Read-only enum schema through the unchanged original Harness request path."""
import hashlib
import json
from pathlib import Path

from expedition33.catalog import capture
from expedition33.introspection import Harness, core


def main():
    catalog = capture()
    owner = catalog.find_class('WidgetBlueprintLibrary')
    matches = [obj for obj in catalog.objects if obj.outer_index == owner.index
               and obj.name == 'SetInputMode_GameAndUIEx' and obj.class_name == 'Function']
    assert len(matches) == 1
    path = catalog.path_name(matches[0])
    with Harness() as harness:
        schema = harness.request({'op': 'schema', 'struct': path})
        parameter = next(p for p in schema['properties'] if p['name'] == 'InMouseLockMode')
        enum = parameter['Enum']
        assert enum['path'] == '/Script/Engine.EMouseLockMode'
        assert not enum['members_truncated'] and enum['member_count'] == 5
        assert {m['name']: m['value'] for m in enum['members']} == {
            'EMouseLockMode::DoNotLock': 0, 'EMouseLockMode::LockOnCapture': 1,
            'EMouseLockMode::LockAlways': 2, 'EMouseLockMode::LockInFullscreen': 3,
            'EMouseLockMode::EMouseLockMode_MAX': 4}
        assert harness._backend.catalog is None and not harness._backend.enum_descriptors
        assert not harness.request({'op': 'status'})['parity_complete']
    result = dict(pid=catalog.pid, schema=schema, passed=True, read_only=True,
                  original_core_sha256=hashlib.sha256(Path(core.__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
                  request_cache_cleared=True, enum_invocation_supported=False)
    output = Path(__file__).resolve().parents[1] / 'evidence/harness-enum-live.json'
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
