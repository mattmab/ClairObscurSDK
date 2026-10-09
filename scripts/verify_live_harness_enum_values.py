"""Typed JSON enum calls and original retained values on an owned Button.

Run on the persistent controller owner thread after loading the current adapter.
Uses the shared undisplayed widget fixture and its exact holder cleanup check.
"""
import hashlib
import json
from pathlib import Path
import runpy

from expedition33.catalog import capture
from expedition33.enums import describe_enums
from expedition33.introspection import Harness, core

ROOT = Path(__file__).resolve().parents[1]


def run(session):
    assert session.supports_enum_values
    progress = dict(pid=session.pid, passed=False, displayed=False, input_changed=False)
    def save():
        (ROOT / 'evidence/harness-enum-values-progress.json').write_text(
            json.dumps(progress, indent=2), encoding='utf-8')
    save()
    def probe(scope, slot, button, catalog):
        catalog = capture()
        target = {'$object': catalog.path_name(catalog.resolve(button))}
        enum = catalog.find_path('/Script/UMG.ESlateVisibility', 'Enum')
        descriptor = describe_enums(catalog, [enum])[enum.index]
        def spec(short):
            names = [m.name for m in descriptor.members if m.name.rsplit('::', 1)[-1] == short]
            assert len(names) == 1
            return {'$enum': {'type': catalog.path_name(enum), 'name': names[0]}}
        hidden, visible = spec('Hidden'), spec('Visible')
        with Harness(scope) as harness:
            assert '$enum' in harness.request({'op': 'status'})['argument_types']
            def invoke(member, args=None, **extra):
                return harness.request(dict(op='invoke', target=target, member=member,
                    args=args or {}, allow_mutation=True, **extra))
            invoke('SetVisibility', {'InVisibility': hidden})
            copied = invoke('GetVisibility', retain='visibility')
            assert copied == {'$enum': dict(hidden['$enum'], value=2)}, copied
            invoke('SetVisibility', {'InVisibility': visible})
            assert invoke('GetVisibility') == {'$enum': dict(visible['$enum'], value=0)}
            invoke('SetVisibility', {'InVisibility': {'$value': {'name': 'visibility'}}})
            assert invoke('GetVisibility') == copied
            invoke('SetVisibility', {'InVisibility': copied})
            assert invoke('GetVisibility') == copied
            rejected = []
            for bad in (0, {'$enum': dict(hidden['$enum'], value=0)},
                        {'$enum': dict(hidden['$enum'], name='NoSuchMember')}):
                try:
                    invoke('SetVisibility', {'InVisibility': bad})
                except ValueError:
                    rejected.append(bad)
                else:
                    raise AssertionError('Invalid enum argument accepted')
                assert invoke('GetVisibility') == copied
            assert harness.request({'op': 'release_value', 'name': 'visibility'})['retained_values'] == []
            try:
                invoke('SetVisibility', {'InVisibility': {'$value': {'name': 'visibility'}}})
            except KeyError:
                pass
            else:
                raise AssertionError('Released enum remained accessible')
            invoke('SetVisibility', {'InVisibility': visible})
            invoke('GetVisibility', retain='close_cleanup')
            progress.update(encoded_hidden=copied, rejected_arguments=rejected,
                retained_reuse_release=True, annotation_roundtrip=True)
            save()
        assert harness._explorer.values == {} and harness._explorer._owners == {}
        progress['harness_close_cleared'] = True
        progress['original_core_sha256'] = hashlib.sha256(
            Path(core.__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        save()
        return {k: v for k, v in progress.items() if k != 'passed'}
    result = runpy.run_path(str(ROOT / 'scripts/verify_live_widget_children.py'))['run'](
        session, slot_probe=probe, evidence_name='harness-enum-values-live.json')
    progress['passed'] = True
    save()
    print('Harness enum JSON, retained reuse/release, rejection and exact holder cleanup passed.')
    return result
