"""Bounded detached media construction diagnostic; never attaches or plays."""
from dataclasses import asdict, is_dataclass
from expedition33.media import OwnedVideoWidget
from expedition33.cinematics.media_profiles import MEDIA_PROFILES
from expedition33.cinematics.media_audio_adapter import admitted_audio_profile

ALICIA = 'Sandfall/Content/Cinematics/Lumiere/Act03/AliciaBirth/DA_GA_CIN_AliciaBirth_P3_PreRender.uasset'


def _snapshot(video):
    def copied(value):
        return asdict(value) if is_dataclass(value) else None
    return dict(state=video.state, uncertain=video.uncertain,
        widget=copied(video.widget), source=copied(video.source), player=copied(video.player),
        native_owner_state=getattr(video.native_owner, 'state', None),
        leases=[dict(active=lease.active, object=copied(lease.object))
                for lease in video.scope._leases])


def run(mod, count=6):
    if type(count) is not int or not 1 <= count <= 6:
        raise ValueError('Expected media rebuild count 1..6')
    menu = getattr(getattr(mod, 'native', None), 'menu', None)
    title = getattr(mod, 'title_replay', None)
    if (mod.video is not None or (title is not None and
            (getattr(title, 'sequence', None) is not None or
             getattr(title, 'state', None) not in ('ended','stopped','closed')))):
        raise RuntimeError('Stop active replay before detached media diagnostic')
    if menu is None or menu.panel.state != 'open' or menu.panel.uncertain:
        raise RuntimeError('A known open Cinematics menu is required')
    if getattr(mod, '_media_rebuild_retained', None) is not None:
        raise RuntimeError('Earlier diagnostic resources remain retained; no retry')
    profile = MEDIA_PROFILES[ALICIA]
    if admitted_audio_profile(profile) is None:
        raise RuntimeError('Exact reviewed Alicia profile is not admitted')
    report = dict(playback_attempted=False, attached=False, requested=count, iterations=[])
    for index in range(count):
        mod.discover()
        scenes = [s for s in mod.discovery.get('confirmed', ()) if s.get('id') == ALICIA]
        if len(scenes) != 1 or not scenes[0].get('unlocked') or not profile.matches(scenes[0]):
            raise RuntimeError('Exact Alicia definition is not freshly unlocked')
        video = OwnedVideoWidget(mod.session)
        mod._media_rebuild_retained = video
        row = dict(iteration=index+1, build_error=None, close_error=None, closed=False)
        report['iterations'].append(row)
        try:
            video.build(menu.panel, profile.movie_path)
        except Exception as error:
            row['build_error'] = repr(error)
        finally:
            row['before_close'] = _snapshot(video)
            if video.uncertain or getattr(video.native_owner, 'state', None) == 'unknown':
                row['close_error'] = 'Unknown native outcome; retained without retry'
            else:
                try:
                    video.close()
                    row['closed'] = video.state == 'closed'
                    if row['closed']:
                        mod._media_rebuild_retained = None
                except Exception as error:
                    row['close_error'] = repr(error)
            row['after_close'] = _snapshot(video)
        if row['build_error'] or not row['closed']:
            break
    report['complete'] = len(report['iterations']) == count and all(
        row['closed'] and row['build_error'] is None for row in report['iterations'])
    return report
