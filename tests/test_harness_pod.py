import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from expedition33 import _pod_values as pod
from expedition33.introspection import Harness, UnsupportedCapability, _Backend, _Explorer, _Object, _adapt


class HarnessPodTests(unittest.TestCase):
    def backend(self, enabled=True):
        return _Backend(SimpleNamespace(supports_reflected_invocation=True, supports_retained_invocation=True,
                                        supports_object_assignment=True, supports_pod_values=enabled))

    def test_original_decoder_encoder_nested_structs_and_type_validation(self):
        backend=self.backend(); explorer=_Explorer(backend)
        vector={'$struct':'Vector2D','fields':{'X':0.25,'Y':0.5}}
        anchor={'$struct':pod.ANCHORS,'fields':{'Minimum':vector,'Maximum':vector}}
        value=explorer.decode(anchor)
        self.assertEqual(value.Minimum.X,0.25)
        encoded=explorer.encode(value,depth=4)
        self.assertEqual(encoded,dict(anchor, **{'$struct':'Anchors'}))
        self.assertEqual(pod.encode(pod.ANCHORS,value._value),pod.encode(pod.ANCHORS,explorer.decode(encoded)._value))
        with self.assertRaises(ValueError): pod.encode(pod.VECTOR,value._value)
        for fields in ({'X':1}, {'X':True,'Y':0}, {'X':float('inf'),'Y':0}):
            with self.assertRaises(ValueError): explorer.decode({'$struct':'Vector2D','fields':fields})
        with self.assertRaises(UnsupportedCapability): explorer.decode({'$struct':'/Script/InputCore.Key','fields':{}})
        with self.assertRaises(UnsupportedCapability): _Explorer(self.backend(False)).decode(vector)

    def test_numeric_values_copy_nested_input_and_support_mapping_use(self):
        source={'Minimum':{'X':0,'Y':0},'Maximum':{'X':1,'Y':1}}
        value=pod.NumericStructValue(pod.ANCHORS,source)
        source['Maximum']['X']=99
        self.assertEqual(value['Maximum']['X'],1)
        with self.assertRaises(TypeError): value['Minimum']['X']=1
        self.assertEqual(dict(pod.decode(pod.VECTOR,pod.encode(pod.VECTOR,{'X':1,'Y':2}))),{'X':1,'Y':2})

    def test_adapter_unwraps_typed_arguments_and_wraps_results(self):
        backend=self.backend()
        value=pod.decode(pod.VECTOR,pod.encode(pod.VECTOR,{'X':10,'Y':20}))
        fn=SimpleNamespace(name='RoundTrip')
        backend.catalog=SimpleNamespace(ancestors=lambda _: (2,))
        backend.function_children={2:[fn]}
        backend.refresh=Mock()
        result=SimpleNamespace(return_value=value,outputs={'Out':value})
        backend.session.invoke_retained=Mock(return_value=result)
        target=_Object(backend,SimpleNamespace(class_index=2))
        adapted=target.RoundTrip(Input=_adapt(backend,value))
        self.assertIs(backend.session.invoke_retained.call_args.kwargs['Input'],value)
        self.assertEqual(_Explorer(backend).encode(adapted['return']),{'$struct':'Vector2D','fields':{'X':10.0,'Y':20.0}})
        self.assertEqual(adapted['out']['Out'].Y,20)
        self.assertIs(backend.pending_owner,result)

    def test_original_retain_value_reuse_expiry_and_release(self):
        backend=self.backend(); explorer=_Explorer(backend)
        owners=[]
        value=_adapt(backend,pod.decode(pod.VECTOR,pod.encode(pod.VECTOR,{'X':12,'Y':34})))
        def invoke(**args):
            owner=SimpleNamespace(release=Mock(return_value=True)); owners.append(owner)
            backend.pending_owner=owner
            backend.pending_value=args.get('Input',value)
            return backend.pending_value
        explorer.resolve=lambda _: SimpleNamespace(Class=object(),RoundTrip=invoke)
        explorer.functions=lambda _: [SimpleNamespace(Name='RoundTrip')]
        request=dict(op='invoke',target='fixture',member='RoundTrip',allow_mutation=True)
        with patch('expedition33.introspection.core.time.monotonic',return_value=100):
            first=explorer.dispatch(dict(request,retain='position'))
            second=explorer.dispatch(dict(request,args={'Input':{'$value':{'name':'position'}}}))
        self.assertEqual(first,second)
        self.assertEqual(first['$struct'],'Vector2D')
        owners[0].release.assert_not_called(); owners[1].release.assert_called_once()
        with patch('expedition33.introspection.core.time.monotonic',return_value=161): explorer.expire()
        owners[0].release.assert_called_once()
        self.assertFalse(explorer.values)
        with self.assertRaises(KeyError): explorer.decode({'$value':{'name':'position'}})
        explorer.close()

    def test_status_exposes_only_four_typed_structs_with_capability(self):
        for enabled in (False,True):
            with Harness(self.backend(enabled).session) as harness:
                status=harness.request({'op':'status'})
                self.assertEqual('$struct' in status['argument_types'],enabled)
                self.assertEqual(status['struct_types'],list(pod.PROFILES) if enabled else [])
                self.assertFalse(status['parity_complete'])
