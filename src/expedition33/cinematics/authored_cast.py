"""Sequence-local cast declarations from immutable imported source data.

Binding GUIDs are scoped to their sequence, including nested shots. Unrelated
unsupported spawnable fields do not invalidate independently decoded identity
fields. This is an editor projection, never a runtime actor handle.
"""


def _guid(value, *, empty=False):
    if (type(value) is not dict or value.get('struct') != '/Script/CoreUObject.Guid'
            or value.get('complete') is not True or value.get('errors')):
        raise ValueError('Complete binding GUID required')
    fields = value.get('fields', {})
    if type(fields) is not dict or set(fields) != set('ABCD') or any(type(fields[k]) is not int or
            not -(1 << 31) <= fields[k] < (1 << 31) for k in 'ABCD'):
        raise ValueError('Invalid binding GUID')
    result = ''.join(f'{fields[k] & 0xffffffff:08x}' for k in 'ABCD')
    if result == '0' * 32:
        if empty:return None
        raise ValueError('Empty binding GUID')
    return result


def _array(value):
    if (type(value) is not dict or value.get('complete') is not True or
            type(value.get('array')) is not list or type(value.get('length')) is not int
            or value['length'] != len(value['array']) or not 0 <= value['length'] <= 4096):
        raise ValueError('Complete bounded cast array required')
    return value['array']


def _fields(value, kind, names):
    if type(value) is not dict or value.get('struct') != '/Script/MovieScene.' + kind:
        raise ValueError('Invalid cast declaration type')
    fields = value.get('fields', {})
    errors=value.get('errors', {})
    if type(fields) is not dict or type(errors) is not dict or any(k not in fields or k in errors for k in names):
        raise ValueError('Cast declaration identity is incomplete')
    return fields


def bindings(graph):
    """Project each imported LevelSequence's cast and its component hierarchy."""
    if type(graph) is not dict or type(graph.get('nodes')) is not dict:raise ValueError('Imported source graph required')
    nodes = graph['nodes'];result = []
    for sequence, node in nodes.items():
        if type(sequence) is not str or type(node) is not dict:raise ValueError('Invalid imported source node')
        if node.get('class_name') != 'LevelSequence':continue
        scene_ref = node.get('fields', {}).get('MovieScene')
        if scene_ref is None:continue
        if type(scene_ref) is not dict:raise ValueError('Imported MovieScene reference required')
        scene_path = scene_ref.get('object_path')
        if type(scene_path) is not str:raise ValueError('Imported MovieScene path required')
        scene = nodes.get(scene_path)
        if (type(scene) is not dict or scene.get('class_name') != 'MovieScene' or
                not scene_path.startswith(sequence + ('.' if ':' in sequence else ':'))):
            raise ValueError('Imported sequence MovieScene is unavailable or foreign')
        fields = scene['fields'];local = {}
        if type(fields) is not dict:raise ValueError('Imported MovieScene fields required')
        for kind in ('Spawnables', 'Possessables'):
            for declaration in _array(fields.get(kind)):
                spawn = kind == 'Spawnables'
                data = _fields(declaration, 'MovieSceneSpawnable' if spawn else 'MovieScenePossessable',
                               ('Guid', 'Name', 'ObjectTemplate') if spawn else ('Guid', 'Name', 'ParentGuid'))
                guid = _guid(data['Guid'])
                if guid in local:raise ValueError('Duplicate sequence-local cast GUID')
                name = data['Name']
                if type(name) is not str or len(name) > 1024:raise ValueError('Invalid cast name')
                template = data.get('ObjectTemplate') if spawn else None
                # Cooked scenes can retain a spawn declaration whose editor-only
                # visualizer template was stripped. Keep its GUID and tracks in
                # the projection, but never offer that declaration as a replacement.
                if spawn and template is not None and (type(template) is not dict or set(template) != {'object_path', 'class'} or
                        any(type(template[k]) is not str or not template[k] for k in template) or
                        not template['object_path'].startswith(scene_path + '.')):
                    raise ValueError('Spawnable template is outside its source MovieScene')
                local[guid] = dict(sequence=sequence, scene=scene_path, guid=guid, name=name,
                    kind='spawnable' if spawn else 'possessable', template=dict(template) if template else None,
                    parent=None if spawn else _guid(data['ParentGuid'], empty=True), tracks=[], unread_tracks=[], children=[])
        seen = set()
        for binding in _array(fields.get('ObjectBindings')):
            data = _fields(binding, 'MovieSceneBinding', ('ObjectGuid', 'Tracks'))
            guid = _guid(data['ObjectGuid'])
            if guid in seen or guid not in local:raise ValueError('Unknown or duplicate cast track binding')
            seen.add(guid)
            for track in _array(data['Tracks']):
                if (type(track) is not dict or type(track.get('object_path')) is not str or
                        not track['object_path'].startswith(scene_path + '.') or
                        type(track.get('class')) is not str or not track['class'].endswith('Track')):
                    raise ValueError('Cast track is unavailable or foreign')
                local[guid]['tracks'].append(track['object_path'])
                if track['object_path'] not in nodes:local[guid]['unread_tracks'].append(track['object_path'])
        for guid, row in local.items():
            parent = row['parent']
            if parent is not None:
                if parent not in local:raise ValueError('Cast component parent is unavailable')
                local[parent]['children'].append(guid)
            visited = {guid}
            while parent is not None:
                if parent not in local:raise ValueError('Cast component parent is unavailable')
                if parent in visited:raise ValueError('Cyclic cast component hierarchy')
                visited.add(parent);parent = local[parent]['parent']
        result.extend(local.values())
        if len(result)>16384:raise ValueError('Imported cast exceeds binding limit')
    return tuple(result)


def replacement_overlap_warning(rows, edits, selected, profile):
    """Describe other bindings in the same shot using this character class.

    Spawn sections may not overlap in time, so this is a warning, never a
    claim that both actors are currently visible. Replaced peers use their
    effective replacement class rather than their original template class.
    """
    from .blueprint_actor import PROFILES
    if profile not in PROFILES:return ''
    target=PROFILES[profile].rsplit('.',1)[-1]
    chosen={ (e['sequence'],e['guid']): e['profile'] for e in edits }
    other=[]
    for row in rows:
        key=(row['sequence'],row['guid'])
        if key==selected or row['sequence']!=selected[0] or row['kind']!='spawnable' or not row['template']:continue
        changed=chosen.get(key)
        cls=PROFILES[changed].rsplit('.',1)[-1] if changed in PROFILES else row['template']['class']
        if cls==target:other.append(row['name'])
    if not other:return ''
    return f"This shot also has {', '.join(other[:3])} as {profile.title()}; both may appear together."
