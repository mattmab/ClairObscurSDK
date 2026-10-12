"""Exact unlocked title factory/camera capture/close; never calls Play."""
import time
from expedition33.sequences import OwnedLevelSequence
from expedition33._sequence_owner import SequenceCleanupDeferred
from expedition33.cinematics.title_profiles import TITLE_PROFILES

def run(mod):
    if mod.video is not None or (mod.title_replay and mod.title_replay.status().get('active')):
        raise RuntimeError('Stop playback before camera ownership inspection')
    if getattr(mod, '_camera_capture_retained', None) is not None:
        raise RuntimeError('Previous camera inspection remains retained; no retry')
    menu = getattr(getattr(mod, 'native', None), 'menu', None)
    if menu is None or menu.panel.state!='open' or menu.panel.uncertain:
        raise RuntimeError('A known open Cinematics menu is required')
    profile = next(p for p in TITLE_PROFILES.values() if p.profile_id=='back_at_camp')
    mod.discover()
    rows = [s for s in mod.discovery.get('confirmed', ()) if s.get('id')==profile.definition]
    if len(rows)!=1 or rows[0].get('unlocked') is not True or not profile.matches(rows[0]):
        raise RuntimeError('Exact reviewed title must be freshly unlocked')
    session = getattr(mod.session, '_session', mod.session)
    if not profile.available(session._transport):
        raise RuntimeError('Reviewed native title profile unavailable')
    sequence = OwnedLevelSequence(mod.session)
    mod._camera_capture_retained = sequence
    report = dict(playback_attempted=False, camera_change_requested=False, closed=False)
    try:
        sequence.build(menu.panel, profile.sequence, capture_camera=True)
        report['built_state'] = sequence.state
        report['owner_state'] = sequence.owner.state
    except Exception as error:
        report['build_error'] = repr(error)
    if not sequence.uncertain and sequence.owner.state!='unknown':
        for attempt in range(8):
            try:
                sequence.close()
                report['closed'] = True
                mod._camera_capture_retained = None
                break
            except SequenceCleanupDeferred:
                time.sleep(.1)
            except Exception as error:
                report['close_error'] = repr(error)
                break
    report['state'] = sequence.state
    report['owner_state_after'] = sequence.owner.state
    return report
