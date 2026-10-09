"""Validate argument planning against live functions. Does not invoke anything."""
import json
from pathlib import Path

from expedition33.catalog import capture
from expedition33.invocation import prepare_call, UnsupportedInvocation


def main():
    catalog = capture()
    def one(rows):
        rows = list(rows)
        assert len(rows) == 1, [obj.name for obj in rows]
        return rows[0]
    def named(name): return one(obj for obj in catalog.objects if obj.name == name)
    def function(owner, name):
        cls = catalog.find_class(owner)
        return one(obj for obj in catalog.objects if obj.outer_index == cls.index and obj.name == name)
    pc = one(obj for obj in catalog.select('PlayerController') if not obj.object_flags & 0x10)
    gi = one(obj for obj in catalog.select('GameInstance') if not obj.object_flags & 0x10)
    library = named('Default__WidgetBlueprintLibrary')
    widget_class = catalog.by_index[catalog.find_class('UserWidget').index]
    specimens = [(library, function('WidgetBlueprintLibrary','Create'),
                  {'WorldContextObject':gi,'WidgetType':widget_class,'OwningPlayer':pc}),
                 (library, function('WidgetBlueprintLibrary','SetInputMode_GameOnly'),
                  {'PlayerController':pc,'bFlushInput':False}),
                 (pc, function('Controller','IsLocalController'), {})]
    results = []
    for target, fn, arguments in specimens:
        plan = prepare_call(catalog,target,fn,arguments)
        for reference in plan.objects:
            assert plan.data[reference.offset:reference.offset+8] == bytes(8)
        results.append({'target':catalog.path_name(target), 'function':catalog.path_name(fn),
            'parameter_size':plan.parameter_size,'allocation_extent':plan.allocation_extent,
            'return_offset':plan.return_offset,'buffer_hex':plan.data.hex(),
            'parameters':[{'name':p.name,'kind':p.kind,'input':p.input,'offset':p.offset} for p in plan.parameters],
            'object_patches':[{'offset':p.offset,'object':catalog.path_name(p.object)} for p in plan.objects]})
    unsupported = function('PlayerController','IsInputKeyDown')
    try:
        prepare_call(catalog,pc,unsupported,{'Key':'Tilde'})
    except UnsupportedInvocation as error:
        rejection = str(error)
    else:
        raise AssertionError('FKey lifetime was not rejected')
    result = {'pid':catalog.pid,'plans':results,'key_call_rejection':rejection,
              'dispatched':False,'native_backend_implemented':False}
    path = Path(__file__).resolve().parents[1] / 'evidence/invocation-plans-live.json'
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__ == '__main__': main()
