"""Immutable SDK-reviewed title profiles; installed definitions alone grant no replay."""
from dataclasses import dataclass
import json
from pathlib import Path
import re
from types import MappingProxyType

@dataclass(frozen=True)
class TitleProfile:
    profile_id: str
    definition: str
    saved_id: str
    sequence: str
    definition_sha256: str
    director: str
    sound_mode: str
    sound_wave: str
    required_protocols: tuple
    evidence: tuple
    validation: str

    def available(self, transport):
        admitted=getattr(transport,'cinematic_title_profiles',())
        if (type(admitted) not in (tuple,list) or len(admitted)>32 or
                any(type(x) is not str for x in admitted) or self.profile_id not in admitted):
            return False
        return all(type(getattr(transport,name,0)) is int and getattr(transport,name,0)==1
                   for name in self.required_protocols)

    def matches(self, scene):
        return (scene.get('id')==self.definition and scene.get('saved_id')==self.saved_id
            and scene.get('sequence')==self.sequence and
            scene.get('sha256',scene.get('definition_sha256'))==self.definition_sha256)


def load_profiles(document):
    if document.get('version')!=1 or document.get('category')!='owned_title':
        raise ValueError('Unsupported title manifest version/category')
    rows=document.get('profiles')
    if type(rows) is not list or not 1<=len(rows)<=32:raise ValueError('Bounded title profiles required')
    result={}; ids=set()
    for row in rows:
        if set(row)!=set(TitleProfile.__dataclass_fields__):raise ValueError('Unexpected title profile fields')
        if any(type(row[k]) is not str or not row[k] or len(row[k])>1024 for k in row if k not in ('required_protocols','evidence')):
            raise ValueError('Invalid title profile strings')
        if (not row['definition'].startswith('Sandfall/Content/Cinematics/') or not row['definition'].endswith('.uasset') or
                not row['sequence'].startswith('/Game/Cinematics/') or '..' in row['definition'] or '..' in row['sequence'] or
                not re.fullmatch('[0-9a-f]{64}',row['definition_sha256'])):
            raise ValueError('Invalid exact title identity')
        if row['sound_mode'] not in ('single_owned_sound','none_verified_empty'):raise ValueError('Unknown sound ownership mode')
        if row['sound_mode']=='none_verified_empty' and 'cinematic_empty_title_protocol' not in row['required_protocols']:raise ValueError('Empty-channel native guard required')
        if row['validation'] not in ('live_mechanism_verified','static_admitted_live_pending'):
            raise ValueError('Unaudited title profile cannot be admitted')
        requirements=row['required_protocols']; evidence=row['evidence']
        if (type(requirements) is not list or not requirements or len(requirements)>16 or
                any(type(x) is not str or not re.fullmatch('[a-z0-9_]+_protocol',x) for x in requirements) or
                type(evidence) is not list or not evidence or len(evidence)>16 or any(type(x) is not str or not x for x in evidence)):
            raise ValueError('Bounded native requirements and evidence required')
        if row['definition'] in result or row['profile_id'] in ids:raise ValueError('Duplicate title profile')
        ids.add(row['profile_id'])
        result[row['definition']]=TitleProfile(**dict(row,required_protocols=tuple(requirements),evidence=tuple(evidence)))
    return MappingProxyType(result)

TITLE_PROFILES=load_profiles(json.loads(Path(__file__).with_name('title_profiles.json').read_text(encoding='utf8')))
PROLOGUE=next(profile for profile in TITLE_PROFILES.values() if profile.profile_id=='prologue_lumiere')
