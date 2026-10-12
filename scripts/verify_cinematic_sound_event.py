"""No-play event arming test. Never executes sequence or story callbacks."""
import json
import runpy
from pathlib import Path
from expedition33.catalog import capture
from expedition33.sequences import OwnedLevelSequence
from expedition33._cinematic_sound_event import NativeCinematicSoundEvent

ROOT = Path(__file__).resolve().parents[1]


def run(mod):
    helper = runpy.run_path(str(ROOT/'scripts/verify_music_reference_owner.py'))
    sequence = None
    report = {'sequence_playback_attempted': False, 'audio_playback_attempted': False}
    try:
        helper['begin'](mod)
        context = helper['begin'].__globals__
        scope, audio = context['scope'], context['audio_owner']
        sequence = OwnedLevelSequence(mod.session)
        sequence.build(mod.native.menu.panel,
            '/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere.LS_Title_PrologueLumiere')
        catalog = capture()
        def one(rows):
            rows = tuple(rows)
            if len(rows) != 1: raise ValueError('Ambiguous sound-event identity')
            return rows[0]
        sound = one(o for o in catalog.objects if o.name == 'Exp33_TitleCards_01_Prologue_Lumiere' and o.class_name == 'SoundWave')
        director = one(o for o in catalog.objects if o.name == 'LS_Title_PrologueLumiere_DirectorBP_C' and o.class_name == 'BlueprintGeneratedClass')
        event = one(o for o in catalog.objects if o.outer_index == director.index and o.name == 'SequenceEvent')
        planner = scope.invocation_planner(catalog=catalog)
        component = audio.create_sound(planner, mod.native.menu.panel, sound)
        cls = one(o for o in catalog.objects if o.name == 'AudioComponent' and o.class_name == 'Class')
        play = one(o for o in catalog.objects if o.outer_index == cls.index and o.name == 'Play')
        event_owner = NativeCinematicSoundEvent(scope)
        event_owner.prepare(event, sequence.player, sound, planner.prepare(component, play, StartTime=0.0)._plan)
        report['armed'] = event_owner.status()
        report['sequence_idle'] = sequence.status()
        sequence.close()
        report['after_sequence_close'] = event_owner.status()
        if not audio.close() or not context['owner'].close():
            raise RuntimeError('Native audio/reference cleanup deferred')
        report['restoration'] = helper['finish']()
    except BaseException as error:
        report['error'] = repr(error)
        if sequence is not None:
            try: sequence.close()
            except BaseException as cleanup: report['sequence_cleanup_error'] = repr(cleanup)
        context = helper['begin'].__globals__
        if 'scope' in context:
            try: context['scope'].close()
            except BaseException as cleanup: report['scope_cleanup_error'] = repr(cleanup)
    finally:
        (ROOT/'evidence/cinematic-sound-event-arm.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    return report
