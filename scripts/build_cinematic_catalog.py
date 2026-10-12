"""Build a conservative scene catalog from installed cooked definitions.

Only the verified first fields of S_TriggerCinematicVariables are decoded.
Unrecognized serialization remains unavailable, never guessed from filenames.
"""
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'evidence/cinematic-assets'
MANIFEST = Path('S:/SteamLibrary/steamapps/common/Expedition 33/Manifest_UFSFiles_Win64.txt')

def string(data, at):
    count, = struct.unpack_from('<i',data,at)
    if not 0 < count < 4096: raise ValueError('Unsupported FString length')
    end = at+4+count
    raw = data[at+4:end]
    if len(raw)!=count or raw[-1]!=0: raise ValueError('Truncated FString')
    return raw[:-1].decode('utf8'),end

def names(path):
    data=path.read_bytes()
    if data[:8]!=bytes.fromhex('c1832a9ef8ffffff'): raise ValueError('Unknown package summary')
    _,at=string(data,32)
    count,at=struct.unpack_from('<II',data,at+4)
    if not 0<count<4096: raise ValueError('Name table bound')
    result=[]
    for _ in range(count):
        name,at=string(data,at); result.append(name); at+=4
    return result

def header(data,at):
    fields=[]; index=0; zero_count=0
    for _ in range(128):
        fragment,=struct.unpack_from('<H',data,at); at+=2
        index+=fragment&127
        count=fragment>>9
        zero=bool(fragment&128)
        for _ in range(count):
            fields.append((index,zero_count if zero else None))
            zero_count+=int(zero); index+=1
        if fragment&256: break
    else: raise ValueError('Unterminated unversioned header')
    size=0 if not zero_count else 1 if zero_count<=8 else 2 if zero_count<=16 else ((zero_count+31)//32)*4
    mask=data[at:at+size]
    if len(mask)!=size: raise ValueError('Truncated zero mask')
    bits=int.from_bytes(mask,'little')
    return {i: n is None or not (bits>>n)&1 for i,n in fields},at+size

def fname(data,at,table):
    index,number=struct.unpack_from('<II',data,at)
    if index>=len(table) or number>1000000: raise ValueError('Unsupported FName')
    return table[index]+(f'_{number-1}' if number else ''),at+8

def mapping(path):
    table=names(path)
    if 'BP_GameAction_CinematicWithLightingScenario_C' not in table: raise ValueError('Unverified definition class')
    data=path.with_suffix('.uexp').read_bytes()
    if data[:4]!=bytes(4): raise ValueError('Unexpected object GUID')
    top,at=header(data,4)
    if not top.get(0): raise ValueError('Missing cinematic parameter struct')
    fields,at=header(data,at)
    if not fields.get(0): raise ValueError('No serialized sequence reference')
    package,at=fname(data,at,table); asset,at=fname(data,at,table)
    length,=struct.unpack_from('<i',data,at); at+=4
    if length or not package.startswith('/Game/') or package.rsplit('/',1)[-1]!=asset:
        raise ValueError('Unsupported sequence soft reference')
    saved_id=None
    if fields.get(1): saved_id,at=fname(data,at,table)
    if saved_id=='None': saved_id=None
    return dict(sequence=package+'.'+asset,saved_id=saved_id,
                mapping='decoded' if saved_id else 'no_explicit_saved_id')

def build():
    files={p.stem:p for p in ASSETS.rglob('DA_GA_CIN_*.uasset')}
    rows=[]
    for line in MANIFEST.read_text(encoding='utf-8-sig').splitlines():
        path=line.split('\t')[0]
        name=Path(path).stem
        if not name.startswith('DA_GA_CIN_') or not path.endswith('.uasset'): continue
        row=dict(id=path,title=name.removeprefix('DA_GA_CIN_').replace('_',' '),
                 saved_id=None,sequence=None,mapping='unverified')
        try:
            file=files[name]
            row.update(mapping(file))
            row['sha256']=hashlib.sha256(file.read_bytes()+file.with_suffix('.uexp').read_bytes()).hexdigest()
        except (KeyError,ValueError,IndexError,struct.error,UnicodeError) as error:
            row['mapping_error']=str(error)
        rows.append(row)
    rows.sort(key=lambda r:(r['title'].casefold(),r['id']))
    report=dict(version=1,scope='Installed cinematic definitions; playback availability is separate',
                manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),scenes=rows)
    (ROOT/'mods/Cinematics/catalog.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    from collections import Counter
    print(len(rows),dict(Counter(r['mapping'] for r in rows)))

if __name__=='__main__': build()
