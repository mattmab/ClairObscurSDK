"""Bounded native v14 menu lifecycle specimen, with external readback."""
import json
import os
from pathlib import Path
import runpy
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from expedition33 import sdk, _menu_wire, _lease_wire
from expedition33._invocation_wire import encode_plan
from expedition33.catalog import capture
from expedition33.invocation import prepare_call


def run(session, *, disconnect=False):
    observe = runpy.run_path(str(ROOT/'scripts/inspect_slate_focus_dispatch.py'))['observe']
    before = observe()
    assert before['pid'] == session.pid and len(before['users']) == 1
    assert before['users'][0]['matches_game_viewport']
    progress = dict(pid=session.pid, before=before, passed=False, operations=[])
    stem = 'native-menu-disconnect' if disconnect else 'native-menu'
    path = ROOT/f'evidence/{stem}-progress.json'
    def save(): path.write_text(json.dumps(progress, indent=2), encoding='utf-8')
    save()
    class Lifecycle:
        owner = secrets.randbits(64) or 1
        attempted = False
        def command(self, operation, **kwargs):
            sent = _menu_wire.request(operation, self.owner, **kwargs)
            progress['pending'] = operation
            save()
            response = session._transport.command('menu', sent)
            reply = _menu_wire.decode(sent, response['menu_packet'])
            progress['operations'].append(dict(operation=operation, error=reply.error,
                                               outcome=reply.outcome, active=reply.active))
            progress.pop('pending', None)
            save()
            assert reply.error == 0 and reply.outcome == 'returned', repr(reply)
            return reply
        def open(self, scope, widget, child, player):
            catalog = capture()
            def one(rows):
                rows = list(rows)
                assert len(rows) == 1, len(rows)
                return rows[0]
            def function(owner, name):
                index = catalog.find_class(owner).index
                return one(o for o in catalog.objects if o.outer_index == index and o.name == name)
            library = one(o for o in catalog.select('WidgetBlueprintLibrary')
                          if o.name == 'Default__WidgetBlueprintLibrary')
            engine = one(o for o in catalog.select('GameEngine') if not o.object_flags & 0x10)
            def token(obj):
                return one(lease._token for lease in scope._leases if lease.active and
                           (lease.object.index,lease.object.serial,lease.object.address)==(obj.index,obj.serial,obj.address))
            tokens = token(widget), token(child)
            specs = (
                (widget,'UserWidget','AddToViewport',{'ZOrder':1000}),
                (widget,'Widget','IsInViewport',{}),
                (widget,'CommonActivatableWidget','ActivateWidget',{}),
                (widget,'CommonActivatableWidget','IsActivated',{}),
                (child,'Widget','SetUserFocus',{'PlayerController':player}),
                (child,'Widget','HasKeyboardFocus',{}),
                (child,'Widget','HasUserFocus',{'PlayerController':player}),
                (widget,'CommonActivatableWidget','DeactivateWidget',{}),
                (widget,'Widget','RemoveFromParent',{}),
                (library,'WidgetBlueprintLibrary','SetFocusToGameViewport',{}))
            plans = tuple(encode_plan(prepare_call(catalog,target,function(owner,name),args))
                          for target,owner,name,args in specs)
            self.attempted = True
            assert self.command('prepare', leases=tokens, identities=(engine,widget,child,player,library), plans=plans).active
            # Use the raw transport so deliberate Busy rejection does not revoke
            # the Python ObjectLease handle used for later cleanup.
            progress['protected_releases'] = []
            for token_value in tokens:
                sent = _lease_wire.request('lease-release', token=token_value)
                response = session._transport.command('lease-release', sent)
                result = _lease_wire.decode('lease-release', sent, response['lease_packet'])
                assert result.error == 403 and result.outcome == 'completed'
                progress['protected_releases'].append(dict(token=token_value,error=result.error))
            save()
            assert self.command('attach').active
            assert self.command('focus').active
            progress['during'] = observe()
            assert not progress['during']['users'][0]['matches_game_viewport']
            save()
        def close(self):
            if not self.attempted: return
            self.attempted = False  # Explicit close is attempted only once.
            assert not self.command('close').active
            progress['restored'] = observe()
            assert progress['restored']['game_viewport'] == before['game_viewport']
            assert progress['restored']['users'][0]['matches_game_viewport']
            save()
    lifecycle = Lifecycle()
    def disconnect_controller(*_args):
        progress['controller_pid'] = session._transport._process.pid
        progress['disconnect_requested'] = True
        save()
        # Only this specimen's native controller. No Python scope/session
        # finally handlers run; the game's owner watcher must do all cleanup.
        session._transport._process.kill()
        session._transport._process.wait(timeout=10)
        os._exit(23)
    result = runpy.run_path(str(ROOT/'scripts/verify_live_widget_visible.py'))['run'](
        session, activatable=True, button_enabled=True, native_lifecycle=lifecycle,
        hold_seconds=0, label_text='SDK native menu test', evidence_name=f'{stem}-live.json',
        on_display=disconnect_controller if disconnect else None)
    progress['after'] = observe()
    assert progress['after']['users'][0]['matches_game_viewport']
    assert result['passed'] and result['holder_baseline_restored']
    progress['holder_baseline_restored'] = progress['passed'] = True
    save()
    return progress


if __name__ == '__main__':
    with sdk.Session(menu_ownership=True) as session:
        run(session, disconnect=sys.argv[1:]==['--disconnect-worker'])
    print('Native v14 menu prepare/attach/focus/protected release/close and exact holder cleanup passed.')
