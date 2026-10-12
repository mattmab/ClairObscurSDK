"""Live owned-sound check; call begin with Cinematics open, then Escape, finish.

Uses an SDK-created AudioComponent, never the original game's music component.
No sequence or story callback is executed by this test.
"""
import json
import runpy
import subprocess
from pathlib import Path
from expedition33.catalog import capture

ROOT = Path(__file__).resolve().parents[1]

def save():
    (ROOT/'evidence/owned-sound-live.json').write_text(json.dumps(report, indent=2), encoding='utf8')

def begin(mod):
    global helper, scope, owner, planner, component, report
    helper = runpy.run_path(str(ROOT/'scripts/verify_music_reference_owner.py'))
    helper['begin'](mod)
    context = helper['begin'].__globals__
    scope, owner = context['scope'], context['audio_owner']
    report = dict(context['report'])
    report['test'] = 'explicit SDK-owned title audio; no cinematic playback'
    try:
        from expedition33.assets import load_asset
        load_asset(scope, '/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere.LS_Title_PrologueLumiere')
        catalog = capture()
        sound = tuple(o for o in catalog.objects if o.name == 'Exp33_TitleCards_01_Prologue_Lumiere' and o.class_name == 'SoundWave')
        if len(sound) != 1: raise ValueError('Expected one loaded title sound')
        planner = scope.invocation_planner(catalog=catalog)
        component = owner.create_sound(planner, mod.native.menu.panel, sound[0], volume=.35)
        report['component'] = [component.index, component.serial, component.address]
        report['playing_after_create'] = call('IsPlaying')
        if report['playing_after_create']: raise RuntimeError('Factory unexpectedly started playback')
        call('Play', StartTime=0.0)
        report['playing_after_play'] = call('IsPlaying')
        report['owner_while_playing'] = owner.status()
        save()
        return {k:v for k,v in report.items() if k != 'before_hashes'}
    except BaseException as error:
        report['error'] = repr(error)
        scope.close()
        save()
        raise

def call(name, **args):
    catalog = planner._catalog
    cls = next(o for o in catalog.objects if o.name == 'AudioComponent' and o.class_name == 'Class')
    fn = next(o for o in catalog.objects if o.name == name and o.outer_index == cls.index)
    with planner.prepare(component, fn, **args).invoke(refresh_from_result=True) as result:
        return result.return_value

def finish():
    report['owner_after_escape'] = owner.status()
    # A destroyed identity is expected to be rejected. Use a separate reader;
    # a terminal read failure must not poison the menu's shared worker.
    try:
        probe = subprocess.run([str(ROOT/'build/sequence-inspector/research_probe.exe'),
            '--catalog-select', str(scope.pid), f'{component.index}:{component.serial}:{component.address:x}'],
            capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        report['component_query_after_escape'] = dict(code=probe.returncode, stdout=probe.stdout, stderr=probe.stderr)
    except Exception as error:
        report['component_read_after_escape'] = repr(error)
    try:
        result = helper['finish']()
        report.update({key:result[key] for key in ('original_restored_before_python_close', 'leases_after', 'save_hashes_unchanged')})
    finally:
        save()
    return {k:v for k,v in report.items() if k != 'before_hashes'}
