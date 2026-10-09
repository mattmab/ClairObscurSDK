"""Exercise reusable scope-owned menu API against the verified live specimen."""
import json
from pathlib import Path
import runpy
import sys
import hashlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33 import sdk
from expedition33.ownership import LeaseError


def run(session, *, button_references=False, button_actions=False):
    observe=runpy.run_path(str(ROOT/'scripts/inspect_slate_focus_dispatch.py'))['observe']
    before=observe()
    assert before['users'][0]['matches_game_viewport']
    evidence=dict(passed=False,before=before)
    stem='button-action-binding' if button_actions else 'button-reference' if button_references else 'scoped-menu'
    path=ROOT/f'evidence/{stem}-progress.json'
    if button_references:
        assert session._transport.button_reference_protocol==1
        evidence['runtime_sha256']=hashlib.sha256((ROOT/f'build/runtime-session-v{16 if button_actions else 15}/runtime_session_v{16 if button_actions else 15}.dll').read_bytes()).hexdigest()
    def save(): path.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    save()
    class Lifecycle:
        handle=None
        def open(self,scope,widget,child,player):
            self.handle=scope.prepare_menu(widget,child,player)
            evidence['prepared']=True
            if button_references:
                assert self.handle._button_reference_state==0
                evidence['reference_after_prepare']=self.handle._button_reference_state
            for lease in self.handle._leases:
                try: lease.release()
                except LeaseError as error:
                    assert error.native_error==403 and error.outcome=='not_dispatched'
                else: raise AssertionError('Protected lease release unexpectedly succeeded')
                assert lease.active
            evidence['protected_handles_preserved']=True
            assert self.handle.attach() and self.handle.focus()
            if button_references:
                assert self.handle._button_reference_state==2
                evidence['reference_after_focus']=self.handle._button_reference_state
            evidence['during']=observe()
            assert not evidence['during']['users'][0]['matches_game_viewport']
            if button_actions:
                assert session.supports_button_actions
                evidence['callbacks']=[]
                callback=lambda event: evidence['callbacks'].append(event.sequence)
                first=self.handle.bind_action(callback)
                evidence['first_registration']=first._registration
                assert first._poll()==0
                assert first.remove() and not first.active
                self.action=self.handle.bind_action(callback)
                assert self.action._registration!=first._registration
                evidence['second_registration']=self.action._registration
                assert self.action._poll()==0
                evidence['bind_drain_unbind_rebind']=True
            save()
        def close(self):
            if self.handle is None: return
            assert self.handle.close() and not self.handle.active
            if button_actions:
                assert not self.action.active and self.action._state=='closed'
                evidence['menu_revoked_action']=True
            if button_references:
                assert self.handle._button_reference_state==0
                evidence['reference_after_close']=self.handle._button_reference_state
            evidence['restored']=observe()
            assert evidence['restored']['game_viewport']==before['game_viewport']
            assert evidence['restored']['users'][0]['matches_game_viewport']
            save()
    result=runpy.run_path(str(ROOT/'scripts/verify_live_widget_visible.py'))['run'](
        session,activatable=True,button_enabled=True,native_lifecycle=Lifecycle(),
        hold_seconds=0,label_text='SDK scoped menu',evidence_name=f'{stem}-live.json')
    assert result['passed'] and result['holder_baseline_restored']
    evidence['passed']=evidence['holder_baseline_restored']=True
    save()


if __name__=='__main__':
    button_actions=sys.argv[1:]==['--button-actions']
    button_references=button_actions or sys.argv[1:]==['--button-references']
    with sdk.Session(menu_ownership=True,button_references=button_references,button_actions=button_actions) as session:
        run(session,button_references=button_references,button_actions=button_actions)
    print('Scope-owned menu API lifecycle and exact cleanup passed live.')
