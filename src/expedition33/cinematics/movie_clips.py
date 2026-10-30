"""Installed prerendered clips, independent of story definitions/save unlocks.

Only direct CS_*.mp4 entries in the validated installed manifest are offered.
These are movie segments, not reconstructed scenes or campaign actions.
"""
import hashlib
import re

PREFIX = 'installed-movie:'
PATH = re.compile(r'Sandfall/Content/Movies/(CS_[A-Za-z0-9_ .-]+\.mp4)')


def clip_path(scene):
    identity = scene.get('id', '')
    match = PATH.fullmatch(identity.removeprefix(PREFIX)) if identity.startswith(PREFIX) else None
    if match is None or '..' in match[1] or scene.get('replay_kind') != 'movie_clip':
        raise ValueError('An exact installed movie clip identity is required')
    return './Movies/' + match[1]


def installed_movie_clips(manifest, *, available=False, gameplay=False):
    rows, seen = [], set()
    for line in manifest.decode('utf-8-sig').splitlines():
        path = line.split('\t', 1)[0].replace('\\', '/')
        match = PATH.fullmatch(path)
        if match is None or '..' in match[1]:
            continue
        if path.casefold() in seen:
            raise ValueError('Duplicate installed movie identity')
        seen.add(path.casefold())
        if len(seen) > 64:
            raise ValueError('Installed movie inventory exceeds supported bound')
        rows.append(dict(id=PREFIX + path, title=match[1][3:-4].replace('_', ' ') + ' [Movie clip]',
            saved_id=None, unlocked=None, supported=available is True and gameplay is True,
            replay_kind='movie_clip', controls=(1, 4), validation='mechanism_unverified',
            definition_sha256=hashlib.sha256(line.encode('utf-8')).hexdigest(), sequence=None,
            original_supported=False, preview_supported=False, full_scene=False,
            reason='Installed prerendered segment; may contain spoilers. No campaign effects or save-unlock claim. '
                   'Only embedded movie audio is played; authored dialogue/music, subtitles and in-engine portions are not reconstructed.'
                   + ('' if gameplay else ' Load a save before playback.')))
    return sorted(rows, key=lambda row: row['title'].casefold())
