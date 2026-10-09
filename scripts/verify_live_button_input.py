"""Bounded real-input specimen; computer-use supplies mouse/keyboard activation."""
import dataclasses
import argparse
import json
from pathlib import Path
import runpy
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33 import sdk


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--without-label',action='store_true',help='Isolate hit testing from the overlapping label')
    modes.add_argument('--noninteractive-label',action='store_true',help='Verify native HitTestInvisible on the overlapping label')
    options=parser.parse_args()
    stem=('button-input-unlabelled' if options.without_label else
          'button-input-label-hit-test' if options.noninteractive_label else 'button-input')
    progress=ROOT/f'evidence/{stem}-progress.json'
    evidence={'passed':False,'phase':'preparing','events':[]}
    def save(): progress.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    save()
    observe=runpy.run_path(str(ROOT/'scripts/inspect_slate_focus_dispatch.py'))['observe']
    before=observe()
    assert before['users'][0]['matches_game_viewport']
    with sdk.Session(button_actions=True) as session:
        class Lifecycle:
            menu=None
            action=None
            def open(self,scope,widget,button,player):
                self.menu=scope.prepare_menu(widget,button,player)
                assert self.menu.attach() and self.menu.focus()
                def callback(event):
                    evidence['events'].append(dataclasses.asdict(event))
                    save()
                    if len(evidence['events'])==2:
                        raise RuntimeError('Intentional SDK button callback exception')
                self.action=self.menu.bind_action(callback)
            def close(self):
                if self.menu is not None:
                    assert self.menu.close()
                    evidence['menu_closed']=True
                    restored=observe()
                    assert restored['users'][0]['matches_game_viewport']
                    assert restored['game_viewport']==before['game_viewport']
                    evidence['focus_restored']=True
                    save()
        lifecycle=Lifecycle()
        def interact(*_):
            evidence['phase']='awaiting_three_activations'; save()
            deadline=time.monotonic()+180
            while len(evidence['events'])<3 and time.monotonic()<deadline:
                session.poll(); time.sleep(.05)
            if len(evidence['events'])!=3:
                evidence.update(phase='input_timeout',focus_at_timeout=observe())
                save()
                raise AssertionError('Expected three real input activations')
            assert len(lifecycle.action.failures)==1
            evidence['callback_failures']=list(lifecycle.action.failures)
            assert lifecycle.action.remove()
            evidence['phase']='unbound_click_check'; save()
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                session.poll(); time.sleep(.05)
            assert len(evidence['events'])==3
            evidence['unbound_no_delivery']=True; save()
            return dict(events=evidence['events'],exceptions_contained=True,unbound_no_delivery=True)
        result=runpy.run_path(str(ROOT/'scripts/verify_live_widget_visible.py'))['run'](
            session,activatable=True,button_enabled=True,native_lifecycle=lifecycle,
            on_display=interact,hold_seconds=0,
            label_text=None if options.without_label else 'SDK ACTION TEST - click',
            label_hit_test_invisible=options.noninteractive_label,
            evidence_name=f'{stem}-live.json')
        assert result['passed'] and result['holder_baseline_restored']
        evidence['holder_baseline_restored']=True
    evidence.update(passed=True,phase='complete',normal_close=True); save()
    print('Three real activations, callback exception containment, unregistration and exact cleanup passed.')


if __name__=='__main__': main()
