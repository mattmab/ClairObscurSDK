"""Read-only save-carried story provenance. Slot numbers never bind a story."""
import json,struct
from pathlib import Path

PREFIX=0xe33c5701
STAGE=0x53335031
def _string(value):
    data=value.encode('ascii')+b'\0';return struct.pack('<i',len(data))+data
SIGNATURE=(_string('InteractedDialogues')+_string('MapProperty')+struct.pack('<I',2)
    +_string('StructProperty')+struct.pack('<I',1)+_string('Guid')+struct.pack('<I',1)
    +_string('/Script/CoreUObject')+struct.pack('<I',0)+_string('IntProperty')+struct.pack('<I',0))

def identity_from_save(data):
    """Validate the serialized UE5 Guid→Int map before reading our marker."""
    if type(data) is not bytes or not 16<=len(data)<=32*1024*1024 or data[:4]!=b'GVAS' or struct.unpack_from('<I',data,4)[0]!=3:raise ValueError('Unsupported save format')
    at=data.find(SIGNATURE)
    if at<0 or data.find(SIGNATURE,at+1)>=0:raise ValueError('Save dialogue history is missing or ambiguous')
    at+=len(SIGNATURE)
    if at+13>len(data):raise ValueError('Truncated dialogue history')
    size=struct.unpack_from('<I',data,at)[0];flags=data[at+4];start=at+5
    if flags!=8 or size<8 or start+size>len(data):raise ValueError('Unqualified dialogue map tag')
    removed,count=struct.unpack_from('<II',data,start)
    if removed or count>8192 or size!=8+count*20:raise ValueError('Dialogue history extent mismatch')
    markers=[];seen=set()
    for i in range(count):
        a,b,c,d,value=struct.unpack_from('<4Ii',data,start+8+i*20)
        key=(a,b,c,d)
        if key in seen:raise ValueError('Duplicate dialogue history key')
        seen.add(key)
        if a==PREFIX:
            if value!=STAGE:raise ValueError('Invalid SDK story identity marker')
            markers.append(''.join(f'{v:08x}' for v in key))
    if len(markers)>1:raise ValueError('Ambiguous SDK story identity')
    return markers[0] if markers else None

def label_for_save(data,playthroughs,titles):
    try:key=identity_from_save(data)
    except ValueError:return 'Story unknown'
    if key is None:return 'Vanilla'
    row=playthroughs.get(key)
    if row is None:return 'Custom story (unavailable)'
    pack=row.get('pack')
    return 'Vanilla' if pack is None else titles.get(pack,'Custom story: '+pack)

def read_label(path,playthroughs,titles):
    path=Path(path);before=path.stat();data=path.read_bytes();after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):return 'Story unknown'
    return label_for_save(data,playthroughs,titles)
