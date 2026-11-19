"""Install hash-checked, additive cooked resources carried by a trusted sdkmod.

The game loads these containers on its next launch. This is resource staging,
not a live mount or a Python sandbox. Only /Game/SDK package declarations and
SDK-prefixed container names are admitted; ordinary game files are untouched.
"""
import hashlib,json,os,re,tempfile
from pathlib import Path

LIMIT=128*1024*1024
CHUNK_LIMIT=4*1024*1024

def inspect(manifest_path):
    path=Path(manifest_path).resolve();root=path.parent
    document=json.loads(path.read_text(encoding='utf8'))
    if type(document) is not dict or set(document)!={'schema','id','packages','containers'} or document['schema']!=1:
        raise ValueError('Unsupported SDK asset-resource manifest')
    if type(document['id']) is not str or re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,79}',document['id']) is None:raise ValueError('Asset-resource ID')
    packages=document['packages']
    if type(packages) is not list or not 1<=len(packages)<=256 or len(set(packages))!=len(packages) or any(type(p) is not str or re.fullmatch(r'/Game/SDK/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+',p) is None for p in packages):raise ValueError('Asset resources must use additive /Game/SDK package names')
    containers=document['containers']
    if type(containers) is not list or len(containers)!=3:raise ValueError('One bounded pak/utoc/ucas resource set required')
    seen=set();chunks_seen=set();total=0;validated=[]
    for entry in containers:
        if type(entry) is not dict or set(entry)!={'name','size','sha256','chunks'}:raise ValueError('Asset container fields')
        name=entry['name']
        if type(name) is not str or re.fullmatch(r'sdk_[A-Za-z0-9_]{1,96}_P\.(pak|utoc|ucas)',name) is None or name in seen:raise ValueError('SDK asset container filename')
        seen.add(name);size=entry['size'];digest=entry['sha256']
        if type(size) is not int or not 0<size<=LIMIT or type(digest) is not str or re.fullmatch('[0-9a-f]{64}',digest) is None:raise ValueError('Asset container bounds/hash')
        total+=size
        if total>LIMIT:raise ValueError('Expanded asset resources exceed 128 MiB')
        if type(entry['chunks']) is not list or not 1<=len(entry['chunks'])<=64:raise ValueError('Asset chunk count')
        aggregate=hashlib.sha256();count=0;paths=[]
        for chunk in entry['chunks']:
            if type(chunk) is not dict or set(chunk)!={'path','size','sha256'}:raise ValueError('Asset chunk fields')
            relative=chunk['path']
            if type(relative) is not str or re.fullmatch(r'chunk-[0-9]{3}\.bin',relative) is None or relative in chunks_seen:raise ValueError('Asset chunk path')
            chunks_seen.add(relative);source=root/relative
            if source.is_symlink() or source.is_junction() or source.resolve().parent!=root:raise ValueError('Redirected asset chunk')
            if type(chunk['size']) is not int or not 0<chunk['size']<=CHUNK_LIMIT or source.stat().st_size!=chunk['size']:raise ValueError('Asset chunk size')
            data=source.read_bytes()
            if hashlib.sha256(data).hexdigest()!=chunk['sha256']:raise ValueError('Asset chunk digest mismatch')
            aggregate.update(data);count+=len(data);paths.append(source)
        if count!=size or aggregate.hexdigest()!=digest:raise ValueError('Reassembled asset container digest mismatch')
        validated.append((entry,tuple(paths)))
    stems={Path(name).stem for name in seen}
    if len(stems)!=1 or {Path(name).suffix for name in seen}!={'.pak','.utoc','.ucas'}:raise ValueError('Asset container set differs')
    return document,tuple(validated)

def install(manifest_path,*,game_root=None):
    """Stage resources once. Return True only when a new game launch is needed.

    Existing matching files are never rewritten. A different existing resource
    container is retained and rejected, rather than replaced while mapped.
    All input is verified before writing the first container.
    """
    document,entries=inspect(manifest_path)
    if game_root is None:
        from .paths import sdk_root
        game_root=sdk_root().parent
    destination=Path(game_root).resolve()/'Sandfall/Content/Paks'
    if not destination.is_dir() or destination.is_symlink() or destination.is_junction():raise ValueError('Plain game Paks directory required')
    pending=[]
    for entry,paths in entries:
        target=destination/entry['name']
        if target.exists():
            if target.is_symlink() or target.is_junction() or not target.is_file() or target.stat().st_size!=entry['size'] or hashlib.sha256(target.read_bytes()).hexdigest()!=entry['sha256']:
                raise ValueError('Existing SDK asset container differs; retained unchanged: '+entry['name'])
        else:pending.append((entry,paths,target))
    temporary=[]
    try:
        for entry,paths,target in pending:
            fd,name=tempfile.mkstemp(prefix='sdk_resource_',suffix='.staging',dir=destination)
            staged=Path(name);temporary.append(staged)
            with os.fdopen(fd,'wb') as stream:
                for source in paths:
                    with source.open('rb') as chunk:
                        while data:=chunk.read(1024*1024):stream.write(data)
                stream.flush();os.fsync(stream.fileno())
            if staged.stat().st_size!=entry['size'] or hashlib.sha256(staged.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Staged asset resource readback differs')
        # Publish the .utoc last: partial staging cannot expose its package store.
        ordered=sorted(zip(pending,temporary),key=lambda row:row[0][2].suffix=='.utoc')
        for (_,_,target),staged in ordered:
            if target.exists():raise ValueError('Asset resource destination changed during staging')
            os.replace(staged,target)
        return bool(pending)
    finally:
        for staged in temporary:
            if staged.exists():staged.unlink()
