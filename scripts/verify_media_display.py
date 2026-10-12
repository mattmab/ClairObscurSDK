"""Bounded visible loading-clip probe, using the existing Cinematics panel."""
import json
import time
import runpy
from pathlib import Path
import importlib
import expedition33.media
OwnedVideoWidget = importlib.reload(expedition33.media).OwnedVideoWidget


def run(model, *, controls=False):
    helpers = runpy.run_path(str(Path(__file__).with_name('verify_media_open.py')))
    hashes = helpers['hashes']
    report = {'kind':'loading clip plumbing, not cinematic replay','events':[],'hashes_before':hashes()}
    model.discover()
    report['history_before'] = model.discovery
    video = OwnedVideoWidget(model.session)
    try:
        if model.native.menu is None or model.native.menu.panel.state != 'open':
            model.native.open()
        panel = model.native.menu.panel
        video.build(panel,'./Movies/LoadingScreen/LoadingScreen_Loop_Petals.mp4')
        video.attach(panel)
        video.play()
        for step in range(12):
            report['events'].append(video.status())
            if report['events'][-1]['IsReady']: break
            time.sleep(.1)
        report['initial_play_accepted'] = video.resume()
        time.sleep(.3 if controls else 20)
        report['pause_accepted'] = video.pause()
        time.sleep(.15)
        report['paused'] = video.status()
        report['resume_accepted'] = video.resume()
        video.restart()
        report['half_speed_accepted'] = video.set_rate(.5)
        time.sleep(.5)
        report['after_controls'] = video.status()
        if controls:
            # A second early pause avoids confusing an ended short clip with
            # a paused one. Preserve observed states, not just accepted calls.
            report['second_pause_accepted'] = video.pause()
            time.sleep(.15)
            report['second_paused'] = video.status()
            report['second_resume_accepted'] = video.resume()
            video.restart()
            report['normal_speed_accepted'] = video.set_rate(1.)
            report['end_observations'] = []
            for _ in range(50):
                time.sleep(.2)
                state = video.status()
                report['end_observations'].append(state)
                if not state['IsPlaying']: break
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        try:
            video.close()
            report['closed'] = video.state
            model.native.close_menu()
            report['panel_restored'] = True
        finally:
            report['hashes_after'] = hashes()
            report['save_files_unchanged'] = report['hashes_before'] == report['hashes_after']
            model.discover()
            report['history_after'] = model.discovery
            report['history_unchanged'] = report['history_before'] == report['history_after']
            output = 'media-controls-live.json' if controls else 'media-display-live.json'
            Path('evidence',output).write_text(json.dumps(report,indent=2),encoding='utf8')
    print({k:v for k,v in report.items() if not k.startswith('hashes')})


if 'model' in globals():
    run(model)
