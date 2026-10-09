"""Close an owned menu while a separate owned UserWidget holds focus."""
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33 import sdk
from expedition33.catalog import capture


def run(session):
    observe=runpy.run_path(str(ROOT/'scripts/inspect_slate_focus_dispatch.py'))['observe']
    visible=runpy.run_path(str(ROOT/'scripts/verify_live_widget_visible.py'))['run']
    before=observe()
    assert len(before['users'])==1 and before['users'][0]['matches_game_viewport']
    result=dict(passed=False,before=before)
    path=ROOT/'evidence/menu-unrelated-focus-progress.json'
    def save(): path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    save()
    catalog=capture()
    def one(rows):
        rows=list(rows)
        assert len(rows)==1
        return rows[0]
    def fn(owner,name):
        cls=catalog.find_class(owner).index
        return one(o for o in catalog.objects if o.outer_index==cls and o.name==name)
    library=one(o for o in catalog.select('WidgetBlueprintLibrary') if o.name=='Default__WidgetBlueprintLibrary')
    set_focus=fn('Widget','SetUserFocus')
    keyboard=fn('Widget','HasKeyboardFocus')
    user=fn('Widget','HasUserFocus')
    restore=fn('WidgetBlueprintLibrary','SetFocusToGameViewport')
    class Lifecycle:
        handle=None
        def open(self,scope,widget,child,player):
            self.handle=scope.prepare_menu(widget,child,player)
            assert self.handle.attach() and self.handle.focus()
            result['menu_focused']=observe()
            assert not result['menu_focused']['users'][0]['matches_game_viewport']
            save()
        def close(self):
            if self.handle is not None: assert self.handle.close()
    lifecycle=Lifecycle()
    def other_display(scope,widget,child,player):
        acknowledged=False
        try:
            result['focus_transfer_pending']=True; save()
            scope.invoke(child,set_focus,PlayerController=player)
            acknowledged=True
            result['focus_transfer_pending']=False
            assert scope.invoke(child,keyboard).return_value is True
            assert scope.invoke(child,user,PlayerController=player).return_value is True
            other=observe()
            result['other_before_close']=other; save()
            assert not other['users'][0]['matches_game_viewport']
            assert other['users'][0]['last_widget']!=result['menu_focused']['users'][0]['last_widget']
            assert lifecycle.handle.close()
            after=observe()
            result['other_after_close']=after; save()
            assert after['users'][0]['last_widget']==other['users'][0]['last_widget']
            assert after['users'][0]['last_control']==other['users'][0]['last_control']
            assert scope.invoke(child,keyboard).return_value is True
            assert scope.invoke(child,user,PlayerController=player).return_value is True
            result['unrelated_focus_preserved']=True; save()
        finally:
            if acknowledged:
                # Cleanup of the independently owned test UI, after recording
                # whether the native menu preserved its focus. Never replay a
                # failed SetUserFocus; the restoration call has its own record.
                result['restoration_pending']=True; save()
                scope.invoke(library,restore)
                result['restoration_pending']=False
                result['restored']=observe(); save()
                assert result['restored']['users'][0]['matches_game_viewport']
                assert result['restored']['game_viewport']==before['game_viewport']
        return {'unrelated_focus_preserved':True}
    def primary_display(*_args):
        other=visible(session,activatable=False,button_enabled=True,hold_seconds=0,
                      on_display=other_display,label_text='SDK unrelated focus',
                      evidence_name='menu-unrelated-secondary-live.json')
        assert other['passed'] and other['holder_baseline_restored']
        return {'other_scope_cleaned':True}
    primary=visible(session,activatable=True,button_enabled=True,hold_seconds=0,
                    native_lifecycle=lifecycle,on_display=primary_display,label_text='SDK menu focus',
                    evidence_name='menu-unrelated-primary-live.json')
    assert primary['passed'] and primary['holder_baseline_restored']
    result['after']=observe()
    assert result['after']['users'][0]['matches_game_viewport']
    result['passed']=result['holder_baseline_restored']=True
    save()


if __name__=='__main__':
    with sdk.Session(menu_ownership=True) as session: run(session)
    print('Native menu close preserved unrelated widget focus; both scopes and viewport restored.')
