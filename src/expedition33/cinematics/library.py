"""File-only catalog preparation and explicit, immutable replay admission.

Catalog membership, current-save history, available mechanisms and live visual
qualification are separate facts. Nothing in this module touches the game or
turns a past development-session permission into a persistent playback policy.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .title_profiles import TITLE_PROFILES, PROLOGUE
from .media_profiles import MEDIA_PROFILES
from .original_game_action import profiles as original_profiles, profile_matches


@dataclass(frozen=True)
class PreviewProfile:
    definition: str
    saved_id: str
    sequence: str
    sha256: str

    def matches(self, scene):
        return (scene.get('id'), scene.get('saved_id'), scene.get('sequence'),
                scene.get('sha256', scene.get('definition_sha256'))) == (
                    self.definition, self.saved_id, self.sequence, self.sha256)


PREVIEW_PROFILES = {
    p.definition: p for p in (
        PreviewProfile('Sandfall/Content/Cinematics/Simon/SimonIntro/DA_GA_CIN_SimonIntro.uasset',
            'SimonIntro', '/Game/Cinematics/Simon/SimonIntro/MCS_SimonIntro.MCS_SimonIntro',
            '1071b0c1f16347a3cba2f93f1a59ff5fcd25405b1464bba41f09a5ee615c18b0'),
        PreviewProfile('Sandfall/Content/Cinematics/Simon/SimonIntro/DA_GA_CIN_SimonPhaseTransition.uasset',
            'SimonPhaseTransition', '/Game/Characters/Enemies/HumanEnnemies/Simon/Sequences/SEQ_Simon_Skill_10_PhaseSwitch.SEQ_Simon_Skill_10_PhaseSwitch',
            '73be8bb373c64c80ad8ed66615028ed9da4eefa9f5cb77ff1e8f5ed376ff8a0f'),
        PreviewProfile('Sandfall/Content/Cinematics/Simon/SimonOutro/DA_GA_CIN_SimonOutro.uasset',
            'SimonOutro', '/Game/Cinematics/Simon/SimonOutro/MCS_SimonOutro.MCS_SimonOutro',
            '714c88af61f43b6ae5be8dd952002fd57e0d8887769014f2476a34e32bba5f1c'),
    )
}


def protocol(transport, name, version=1):
    value = getattr(transport, name, 0)
    return type(value) is int and value == version


def preview_available(transport):
    return all(protocol(transport, name) for name in (
        'sequence_player_protocol', 'sequence_camera_protocol', 'sequence_origin_protocol',
        'frame_time_values_protocol', 'menu_protocol', 'sequence_retirement_protocol'))


def title_available(transport, definition):
    profile = TITLE_PROFILES.get(definition)
    return profile is not None and profile.available(transport)


def exact_title(scene):
    profile = TITLE_PROFILES.get(scene.get('id'))
    return profile is not None and profile.matches(scene)


def catalog_scenes(history, media_available, catalog, manifest_bytes, *, title_profile_ids=(),
                   original_action_available=False, allow_original_actions=False,
                   owned_preview_available=False, portable_scene_available=False, gameplay_world_available=True,
                   current_world_path=None):
    if (type(catalog.get('version')) is not int or catalog['version'] != 1 or type(catalog.get('scenes')) is not list or
            len(catalog['scenes']) > 1024 or type(manifest_bytes) is not bytes or
            catalog.get('manifest_sha256') != hashlib.sha256(manifest_bytes).hexdigest()):
        raise ValueError('Cinematic catalog does not match the installed manifest')
    scenes, identities = [], set()
    originals = original_profiles() if original_action_available else {}
    from .portable import PROFILES as portable_profiles
    for item in catalog['scenes']:
        identity = item['id']
        if type(identity) is not str or not identity or identity in identities:
            raise ValueError('Duplicate or invalid cinematic definition')
        identities.add(identity)
        saved_id = item.get('saved_id')
        title_text = item.get('title')
        if (type(title_text) is not str or not 1 <= len(title_text) <= 512 or
                any(c in title_text or c in identity for c in ('\0', '\r', '\n')) or
                (saved_id is not None and (type(saved_id) is not str or not 1 <= len(saved_id) <= 256))):
            raise ValueError('Invalid cinematic catalog display or saved identity')
        unlocked = history.get(saved_id) if saved_id else None
        if type(unlocked) is not bool:
            unlocked = None
        title = TITLE_PROFILES.get(identity)
        media = MEDIA_PROFILES.get(identity)
        preview = PREVIEW_PROFILES.get(identity)
        original = originals.get(identity)
        portable=portable_profiles.get(identity)
        portable=portable if portable is not None and portable.matches(item) else None
        title = title if title is not None and title.matches(item) else None
        media = media if media is not None and media.matches(item) else None
        preview = preview if preview is not None and preview.matches(item) else None
        original = original if original is not None and profile_matches(original, item) else None
        kind, supported, controls = None, False, ()
        validation, reason = 'unsupported', 'No reviewed playback adapter is available for this scene.'
        preview_supported = bool(preview and owned_preview_available is True and gameplay_world_available is True and unlocked is True and
            current_world_path == '/Game/Levels/WorldMap/Level_WorldMap_Main_V2.Level_WorldMap_Main_V2')
        original_supported = bool(original and allow_original_actions is True and gameplay_world_available is True and
            current_world_path == original['world_path'])
        portable_supported=bool(portable and portable_scene_available is True and gameplay_world_available is True and
                                unlocked is True and current_world_path)
        if portable:
            kind,supported,controls='portable',portable_supported,(14,4)
            validation='live_partial'
            reason=('Full in-engine playback here with sequence-spawned actors, authored audio and owned camera restoration. '
                    'Uses a raised staging area in the current world; original scenery and lighting are not reconstructed. '
                    'Natural completion and Stop return control without running the original campaign action.')
        elif title:
            kind = 'title'
            supported = unlocked is True and title.profile_id in title_profile_ids
            controls, validation = (1, 4), title.validation
            reason = ('Reviewed title route with owned camera/audio cleanup and Play/Stop controls. '
                      'Integrated natural-end, Stop, repeat and world-transition behavior in this rebuilt candidate '
                      'remain under live validation.')
        elif media:
            kind, supported = 'movie', unlocked is True and media_available is True
            controls, validation = (1, 4), media.validation
            reason = media.limitation
        elif preview:
            kind, supported, controls = 'preview', preview_supported, (11, 4)
            validation = 'live_partial'
            reason = ('Continent current-location preview of the original sequence using owned actors and camera restoration. '
                      'Use open terrain. Earlier standalone scene previews showed the core actors and camera cuts; '
                      'integrated repeat and interruption behavior, original lighting, HUD hiding '
                      'and automatic camera-clearance placement are not fully qualified.')
        elif original:
            kind, supported, controls = 'original_action', original_supported, (1,)
            validation = 'original_action_live_pending'
            reason = ('Original-level story playback requires ' + original['exact_map'] +
                      '. Travel there separately with Map Travel. Original campaign callbacks can change progression, party state and saves. '
                      'The game owns this playback; SDK Stop is unavailable.')
        if original and current_world_path != original['world_path']:
            reason += ' The original action is unavailable in the current map.'
        if unlocked is not True and kind != 'original_action':
            reason += ' A verified current-save unlock is required.'
        if original and not allow_original_actions:
            reason += ' Original-level story playback is disabled in Cinematics settings.'
        if not gameplay_world_available and kind in ('preview', 'original_action'):
            reason += ' Load a save before using this route.'
        if title and title.profile_id not in title_profile_ids:
            reason += ' Required title/audio capabilities are unavailable.'
        scenes.append(dict(id=identity, saved_id=saved_id, title=item['title'],
            sequence=item.get('sequence'), definition_sha256=item.get('sha256'),
            unlocked=unlocked, supported=bool(supported), replay_kind=kind, controls=controls,
            validation=validation, reason=reason, full_scene=False if media else None,
            preview_supported=preview_supported, original_supported=original_supported,
            portable_supported=portable_supported,
            title_profile=title.profile_id if title else None, media_profile=identity if media else None,
            original_destination=original['world_path'] if original else None,
            original_action_path=original['action_path'] if original else None))
    return scenes


class CatalogStore:
    """Cache checked files, never current world objects or save history."""
    def __init__(self, catalog_path, manifest_path):
        self.catalog_path, self.manifest_path = Path(catalog_path), Path(manifest_path)
        self._cached = None

    def read(self):
        paths = (self.catalog_path, self.manifest_path)
        signature = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in paths)
        if self._cached is None or signature != self._cached[0]:
            if signature[0][2] > 4 * 1024 * 1024 or signature[1][2] > 128 * 1024 * 1024:
                raise ValueError('Cinematic catalog inputs exceed supported bounds')
            catalog = json.loads(self.catalog_path.read_text(encoding='utf-8'))
            manifest = self.manifest_path.read_bytes()
            catalog_scenes({}, False, catalog, manifest)
            self._cached = (signature, catalog, manifest)
        return self._cached[1:]


def installed_cinematics(lines):
    found = {}
    for line in lines:
        path = line.split('\t', 1)[0].replace('\\', '/')
        name = Path(path).stem
        if path.startswith('Sandfall/Content/Movies/CS_') and path.endswith('.mp4'):
            kind, prefix = 'Video', 'CS_'
        elif path.startswith('Sandfall/Content/') and name.startswith('DA_GA_CIN_') and path.endswith('.uasset'):
            kind, prefix = 'Cinematic entry', 'DA_GA_CIN_'
        else:
            continue
        found.setdefault(path.casefold(), dict(id=path,
            title=name.removeprefix(prefix).replace('_', ' ') + f' [{kind}; unlock unknown]',
            supported=False, unlocked=None,
            reason='Installed asset only; unlock and isolated playback have not been qualified.'))
    return sorted(found.values(), key=lambda s: (s['title'].casefold(), s['id']))
