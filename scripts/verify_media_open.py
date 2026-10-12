"""Bounded decoder-only plumbing test on a new player, without story delegates."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from expedition33.catalog import capture_matching
from expedition33._scope import SessionScope


def hashes():
    base = Path('C:/Users/Matt/AppData/Local/Sandfall/Saved/SaveGames')
    return {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in base.rglob('*.sav')}


def run(model):
    session = model.session
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'pid': session.pid,
              'test': 'decoder plumbing only; no display, audio or unlock claim', 'events': []}
    scope = SessionScope(session)
    player = planner = None
    uncertain = False
    def one(rows):
        rows = tuple(rows)
        if len(rows) != 1: raise ValueError('Expected one observed identity')
        return rows[0]
    try:
        model.discover()
        report['history_before'] = model.discovery
        report['hashes_before'] = hashes()
        catalog = capture_matching(session.pid, names=('FileMediaSource','MediaPlayer','GameplayStatics',
            'Default__GameplayStatics','SpawnObject','SetFilePath','OpenSource','Close',
            'IsReady','IsPlaying','IsClosed','Pause','Play','SetRate','/Engine/Transient'))
        def cls(name):
            return one(o for o in catalog.objects if o.name == name and o.class_name == 'Class')
        def fn(owner, name):
            return one(o for o in catalog.objects if o.name == name and o.outer_index == cls(owner).index)
        default = one(o for o in catalog.objects if o.name == 'Default__GameplayStatics')
        outer = one(o for o in catalog.objects if o.name == '/Engine/Transient' and o.class_name == 'Package')
        planner = scope.invocation_planner(selected_results=True, catalog=catalog)
        def invoke(target, owner, name, **args):
            nonlocal uncertain
            prepared = planner.prepare(target, fn(owner, name), **args)
            uncertain = True
            result = prepared.invoke(refresh_from_result=True)
            uncertain = False
            return result
        source_result = invoke(default,'GameplayStatics','SpawnObject',ObjectClass=cls('FileMediaSource'),Outer=outer)
        source = source_result.return_value
        invoke(source,'FileMediaSource','SetFilePath',Path='./Movies/LoadingScreen/LoadingScreen_Loop_Petals.mp4').release()
        player_result = invoke(default,'GameplayStatics','SpawnObject',ObjectClass=cls('MediaPlayer'),Outer=outer)
        player = player_result.return_value
        report['objects'] = {name: {'index': obj.index, 'serial': obj.serial}
                             for name, obj in (('source',source),('player',player))}
        with invoke(player,'MediaPlayer','OpenSource',MediaSource=source) as result:
            report['open_accepted'] = result.return_value
        for step in range(20):
            with invoke(player,'MediaPlayer','IsReady') as ready, invoke(player,'MediaPlayer','IsPlaying') as playing:
                report['events'].append({'step':step,'ready':ready.return_value,'playing':playing.return_value})
                if ready.return_value:
                    break
            time.sleep(.1)
        for name, args in (('Pause',{}),('Play',{}),('SetRate',{'Rate':.5})):
            with invoke(player,'MediaPlayer',name,**args) as result:
                report[name] = result.return_value
        invoke(player,'MediaPlayer','Close').release()
        with invoke(player,'MediaPlayer','IsClosed') as result:
            report['closed'] = result.return_value
        if not report['closed']: raise RuntimeError('Player did not confirm closed')
        player = None
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        try:
            if player is not None and not uncertain:
                invoke(player,'MediaPlayer','Close').release()
            if planner is not None: planner.close()
            scope.close()
            report['scope_closed'] = True
            model.discover()
            report['history_after'] = model.discovery
            report['hashes_after'] = hashes()
            report['save_files_unchanged'] = report['hashes_before'] == report['hashes_after']
        finally:
            Path('evidence/media-open-live.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print({k:v for k,v in report.items() if not k.startswith(('history','hashes'))})


if 'model' in globals():
    run(model)


