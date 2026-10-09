"""Exercise the preserved Explorer's typed structs and retained numeric values.

Run on the current persistent v11 owner thread. The specimen and all resources
belong to the shared child-lifecycle scope; no viewport or input changes occur.
"""
from pathlib import Path
import runpy
from expedition33.catalog import capture
from expedition33.introspection import Harness, UnsupportedCapability

ROOT = Path(__file__).resolve().parents[1]


def run(session):
    assert session.supports_pod_values
    def probe(scope, slot, button, catalog):
        current=capture()
        target={'$object':current.path_name(current.resolve(slot))}
        with Harness(scope) as harness:
            def invoke(member, args=None, **extra):
                return harness.request(dict(op='invoke',target=target,member=member,args=args or {},allow_mutation=True,**extra))
            vector={'$struct':'/Script/CoreUObject.Vector2D','fields':{'X':144.25,'Y':72.5}}
            invoke('SetPosition',{'InPosition':vector})
            expected={'$struct':'Vector2D','fields':vector['fields']}
            retained=invoke('GetPosition',retain='position')
            assert retained == expected, retained
            invoke('SetPosition',{'InPosition':{'$struct':'Vector2D','fields':{'X':1,'Y':2}}})
            invoke('SetPosition',{'InPosition':{'$value':{'name':'position'}}})
            restored=invoke('GetPosition')
            assert restored == expected, restored
            released=harness.request({'op':'release_value','name':'position'})
            assert released['retained_values'] == []
            try:
                invoke('SetPosition',{'InPosition':{'$value':{'name':'position'}}})
                raise AssertionError('Released numeric value was accepted')
            except KeyError:
                pass
            try:
                invoke('SetPosition',{'InPosition':{'$struct':'/Script/InputCore.Key','fields':{}}})
                raise AssertionError('Unsupported owned struct was accepted')
            except UnsupportedCapability:
                pass
            nested={'$struct':'Anchors','fields':{
                'Minimum':{'$struct':'Vector2D','fields':{'X':0,'Y':0}},
                'Maximum':{'$struct':'Vector2D','fields':{'X':0,'Y':0}}}}
            invoke('SetAnchors',{'InAnchors':nested})
            status=harness.request({'op':'status'})
            assert '$struct' in status['argument_types'] and len(status['struct_types']) == 4
            return {'typed_result':retained,'value_reuse_readback':restored,
                    'release_rejected_reuse':True,'owned_type_rejected':True,
                    'nested_anchors_dispatch_returned':True,'status':status}
    result=runpy.run_path(str(ROOT/'scripts/verify_live_widget_children.py'))['run'](
        session,slot_probe=probe,evidence_name='harness-pod-live.json')
    print('Original Harness typed struct, result, retained reuse/release and scoped cleanup passed.')
    return result
