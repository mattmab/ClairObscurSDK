"""Bounded offline checks of extracted asset references; never loads game actions.

This intentionally supports only the observed retoc UE5.4 legacy summaries.
It is research verification, not a general cooked-asset parser.
"""
import hashlib, json, struct
from pathlib import Path

ROOT = Path('evidence/myflower-assets')
def file(name):
    matches = list(ROOT.rglob(name))
    assert len(matches) == 1, name
    return matches[0]
def string(data, at):
    count, = struct.unpack_from('<i', data, at)
    assert 0 < count < 4096
    raw = data[at+4:at+4+count]
    assert len(raw) == count and raw[-1] == 0
    return raw[:-1].decode('utf8'), at+4+count
def names(name):
    data = file(name+'.uasset').read_bytes()
    assert data[:8] == bytes.fromhex('c1832a9ef8ffffff')
    _, at = string(data,32)
    count, offset = struct.unpack_from('<II',data,at+4)
    assert 0 < count < 4096 and offset < len(data)
    rows = []
    for _ in range(count):
        value, offset = string(data,offset)
        rows.append(value)
        offset += 4 # serialized name hashes
    return rows
def fname(data, at, table):
    index, number = struct.unpack_from('<II',data,at)
    assert index < len(table) and number == 0
    return table[index]

table = names('DA_GA_CIN_MyFlower_P1')
data = file('DA_GA_CIN_MyFlower_P1.uexp').read_bytes()
# No object GUID; one nonzero top-level struct. Nested fragments select fields
# 0,1,16,19; field 16 has a zero mask. First two fields verified by live reflection:
# SoftObjectProperty SequenceToPlay, NameProperty LevelSequence_ID.
assert data[:13] == bytes.fromhex('00000000000300048e02020301')
schema = json.loads(Path('evidence/cinematic-definition-schema.json').read_text())
fields = next(r['properties'] for r in schema if r['path'].endswith('.S_TriggerCinematicVariables'))
assert fields[0]['type'] == 'SoftObjectProperty' and 'SequenceToPlay' in fields[0]['name']
assert fields[1]['type'] == 'NameProperty' and 'LevelSequence_ID' in fields[1]['name']
sequence_package = fname(data,13,table)
sequence_asset = fname(data,21,table)
assert struct.unpack_from('<i',data,29)[0] == 0 # empty subobject path
saved_id = fname(data,33,table)
assert saved_id == 'MyFlowerP1' and sequence_package.endswith('/MCS_MyFlower_P1')
assert sequence_asset == 'MCS_MyFlower_P1'
master = names(sequence_asset)
intro = '/Game/Cinematics/Lumiere/Act01/MyFlower/CS_MyFlower_P1_PreRenderIntro'
assert intro in master
source = '/Game/Cinematics/Lumiere/Act01/MyFlower/Prerender/MyFlowerP1Intro_MediaSource'
assert source in names('CS_MyFlower_P1_PreRenderIntro')
media = file('MyFlowerP1Intro_MediaSource.uexp').read_bytes()
assert media[:6] == bytes.fromhex('000000000003')
path, _ = string(media,6)
assert path == './Movies/CS_MyFlower_P1_Intro.mp4'
assert 'FileMediaSource' in names('MyFlowerP1Intro_MediaSource')
report = dict(saved_id=saved_id, sequence=sequence_package+'.'+sequence_asset,
    intro_reference=intro, source_reference=source, file_path=path,
    label='MyFlowerP1 — prerendered intro segment',
    scope='Offline saved-ID/property decode and packaged reference chain; no story action execution',
    full_scene=False, hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in ROOT.rglob('*') if p.is_file() and 'Animation' not in p.parts})
Path('evidence/myflower-mapping-verified.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k != 'hashes'},indent=2))
