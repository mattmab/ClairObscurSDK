"""Bounded owned-text probe on an existing persistent v12 owner thread.

Uses an SDK-created TextBlock with no viewport, focus or input change. The shared
child lifecycle probe closes every scope and checks the exact holder baseline.
Call run(sdk) from the native Python console; never start a second controller.
"""
import json
from pathlib import Path
import runpy
from expedition33.catalog import capture
from expedition33.introspection import Harness

ROOT = Path(__file__).resolve().parents[1]


def run(session):
    assert session.supports_text_values and session.supports_stable_returns
    progress = {'pid':session.pid, 'round_trips':[], 'passed':False, 'displayed':False}
    def record():
        (ROOT/'evidence/widget-text-progress.json').write_text(
            json.dumps(progress,indent=2,ensure_ascii=True),encoding='utf-8')
    record()
    def probe(scope, slot, button, catalog):
        def one(rows):
            rows=list(rows); assert len(rows)==1, len(rows); return rows[0]
        def cls(name): return catalog.by_index[catalog.find_class(name).index]
        def cdo(name): return one(o for o in catalog.objects if o.name=='Default__'+name and o.class_index==cls(name).index)
        def fn(owner,name): return one(o for o in catalog.objects if o.outer_index==cls(owner).index and o.name==name)
        current=capture()
        tree=current.by_index[current.resolve(button).outer_index]
        label_owner=scope.invoke_retained(cdo('GameplayStatics'),fn('GameplayStatics','SpawnObject'),
                                          ObjectClass=cls('TextBlock'),Outer=tree)
        label=label_owner.return_value
        assert label.class_index==cls('TextBlock').index and label.outer_index==tree.index
        setter,getter=fn('TextBlock','SetText'),fn('TextBlock','GetText')
        for value in ('SDK text', 'Expedition 33 — café 🚀', ''):
            with scope.invoke_retained(label,setter,InText=value):
                pass
            with scope.invoke_retained(label,getter) as returned:
                copied=returned.return_value
            assert type(copied) is str and copied==value, (value,copied)
            progress['round_trips'].append(copied); record()
        for invalid in ('embedded\0NUL','\ud800','x'*4096):
            try:
                scope.invoke_retained(label,setter,InText=invalid)
            except ValueError:
                pass
            else:
                raise AssertionError('Invalid text reached dispatch')
        progress['invalid_inputs_rejected']=True; record()
        current=capture()
        target={'$object':current.path_name(current.resolve(label))}
        with Harness(scope) as harness:
            def invoke(member,args=None,**extra):
                return harness.request(dict(op='invoke',target=target,member=member,
                                            args=args or {},allow_mutation=True,**extra))
            invoke('SetText',{'InText':'Harness text 🚀'})
            copied=invoke('GetText',retain='text_value')
            assert copied=='Harness text 🚀', copied
            invoke('SetText',{'InText':'changed'})
            invoke('SetText',{'InText':{'$value':{'name':'text_value'}}})
            assert invoke('GetText')==copied
            released=harness.request({'op':'release_value','name':'text_value'})
            assert released['retained_values']==[]
            try:
                invoke('SetText',{'InText':{'$value':{'name':'text_value'}}})
            except KeyError:
                pass
            else:
                raise AssertionError('Released Harness text value remained accessible')
        progress['harness_text_retain_reuse_release']=True; record()
        # The outer lifecycle sets passed only after holder cleanup. Avoid an
        # ambiguous nested copy of its still-pending overall completion flag.
        return {key:value for key,value in progress.items() if key!='passed'}
    result=runpy.run_path(str(ROOT/'scripts/verify_live_widget_children.py'))['run'](
        session,slot_probe=probe,evidence_name='widget-text-live.json')
    progress['passed']=True; record()
    print('Owned TextBlock text and original Harness copied-text round trips passed.')
    return result
