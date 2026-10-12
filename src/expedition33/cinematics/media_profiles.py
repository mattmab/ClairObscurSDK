from dataclasses import dataclass
from types import MappingProxyType
from pathlib import Path
import json,re

@dataclass(frozen=True)
class MediaProfile:
    definition: str
    saved_id: str
    sequence: str
    definition_sha256: str
    movie_path: str
    label: str
    limitation: str
    validation: str
    evidence: tuple
    full_scene: bool = False
    def matches(self,scene):
        return (scene.get('id')==self.definition and scene.get('saved_id')==self.saved_id
            and scene.get('sequence')==self.sequence and scene.get('sha256',scene.get('definition_sha256'))==self.definition_sha256)

def load_media_profiles(document):
    if document.get('version')!=1:raise ValueError('Unknown media profile version')
    rows=document.get('profiles');result={}
    if type(rows) is not list or not 1<=len(rows)<=32:raise ValueError('Bounded media profiles required')
    for row in rows:
        if set(row)!=set(MediaProfile.__dataclass_fields__) or row['full_scene'] is not False:raise ValueError('Media segment cannot claim full-scene playback')
        if any(type(row[k]) is not str or not row[k] or len(row[k])>1024 for k in row if k not in ('full_scene','evidence')):raise ValueError('Invalid media profile')
        if (not row['definition'].startswith('Sandfall/Content/Cinematics/') or not row['sequence'].startswith('/Game/Cinematics/') or
            not re.fullmatch('[0-9a-f]{64}',row['definition_sha256']) or not row['movie_path'].startswith('./Movies/') or not row['movie_path'].endswith('.mp4') or
            '..' in row['movie_path'] or '\\' in row['movie_path'] or row['definition'] in result):raise ValueError('Invalid exact media mapping')
        if type(row['evidence']) is not list or not 1<=len(row['evidence'])<=16 or any(type(x) is not str or not x for x in row['evidence']):raise ValueError('Media mapping evidence required')
        result[row['definition']]=MediaProfile(**dict(row,evidence=tuple(row['evidence'])))
    return MappingProxyType(result)

MEDIA_PROFILES=load_media_profiles(json.loads(Path(__file__).with_name('media_profiles.json').read_text(encoding='utf8')))
