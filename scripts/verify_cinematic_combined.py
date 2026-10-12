"""Exact Prologue adapters together, idle: no sequence or audio playback."""
import json
import runpy
from pathlib import Path
from expedition33.catalog import capture
from expedition33.sequences import OwnedLevelSequence
from expedition33._cinematic_sound_event import NativeCinematicSoundEvent
from verify_cinematic_widget_hook import prepare as prepare_widgets
from verify_music_reference_owner import hashes

ROOT=Path(__file__).resolve().parents[1]

def run(mod):
    report={'playback_attempted':False};before=hashes();sequence=None;context=None
    session=mod.session._session
    report['leases_before']=repr(session._lease_command('lease-status'))
    helper=runpy.run_path(str(ROOT/'scripts/verify_music_reference_owner.py'))
    def one(rows):
        rows=list(rows)
        if len(rows)!=1:raise ValueError('Ambiguous combined admission dependency')
        return rows[0]
    try:
        mod.pause.open()
        helper['begin'](mod)
        context=helper['begin'].__globals__
        scope,audio=context['scope'],context['audio_owner']
        sequence=OwnedLevelSequence(mod.session)
        sequence.build(mod.native.menu.panel,'/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere.LS_Title_PrologueLumiere')
        widgets=prepare_widgets(sequence)
        catalog=capture()
        planner=scope.invocation_planner(catalog=catalog)
        sound=one(o for o in catalog.objects if o.name=='Exp33_TitleCards_01_Prologue_Lumiere' and o.class_name=='SoundWave')
        director=one(o for o in catalog.objects if o.name=='LS_Title_PrologueLumiere_DirectorBP_C' and o.class_name=='BlueprintGeneratedClass')
        event=one(o for o in catalog.objects if o.outer_index==director.index and o.name=='SequenceEvent')
        component=audio.create_sound(planner,mod.native.menu.panel,sound)
        cls=one(o for o in catalog.objects if o.name=='AudioComponent' and o.class_name=='Class')
        default=one(o for o in catalog.objects if o.name=='Default__AudioComponent')
        play=one(o for o in catalog.objects if o.outer_index==cls.index and o.name=='Play')
        pause=one(o for o in catalog.objects if o.outer_index==cls.index and o.name=='SetPaused')
        sound_owner=NativeCinematicSoundEvent(scope)
        sound_owner.prepare(event,sequence.player,sound,planner.prepare(component,play,StartTime=0.0)._plan)
        audio.pause_original_audio(planner.prepare(default,pause,bPause=False)._plan)
        report['armed']={'widgets':widgets.status(),'sound':sound_owner.status(),'audio':audio.status(),
                         'sequence':sequence.status()}
        report['leases_armed']=repr(session._lease_command('lease-status'))
        if not sequence.owner.close():raise RuntimeError('Native cleanup deferred')
        report['closed']={'widgets':widgets.status(),'sound':sound_owner.status(),'audio':audio.status()}
        sequence.close()
        report['restoration']=helper['finish']()
        context=None
    except BaseException as error:report['error']=repr(error)
    finally:
        sequence_closed=True
        if sequence is not None:
            try:sequence.close()
            except BaseException as error:
                sequence_closed=False
                report['sequence_cleanup_error']=repr(error)
                # Keep adapter leases until native sequence teardown succeeds.
                # Closing the controller invokes its durable cleanup machinery.
                session._abort_ownership()
        if context is not None and sequence_closed:
            try:context['scope'].close()
            except BaseException as error:report['audio_cleanup_error']=repr(error)
        report['save_hashes_unchanged']=hashes()==before
        try:report['leases_after']=repr(session._lease_command('lease-status'))
        except BaseException as error:report['lease_error']=repr(error)
        (ROOT/'evidence/cinematic-combined-arm.json').write_text(json.dumps(report,indent=2))
    return report
