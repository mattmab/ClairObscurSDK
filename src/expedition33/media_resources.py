"""Hash-verified, bounded local media carried in explicit sdkmod chunks."""
import hashlib,json,os,re
from pathlib import Path
from .paths import sdk_root

def install(manifest_path):
    path=Path(manifest_path);data=json.loads(path.read_text(encoding='utf8'))
    if set(data)!={'schema','id','files'} or data['schema']!=1 or not re.fullmatch(r'[a-z0-9-]{1,64}',data['id']):raise ValueError('Invalid media bundle')
    if not 1<=len(data['files'])<=16:raise ValueError('Media file count bound')
    base=sdk_root()/'media';root=base/data['id'];root.mkdir(parents=True,exist_ok=True)
    if base.is_symlink() or base.is_junction() or root.is_symlink() or root.is_junction() or root.resolve().parent!=base.resolve():raise ValueError('Redirected media destination')
    source_root=path.parent.resolve();outputs={};names=set();chunks=set();expanded=0
    for row in data['files']:
        if set(row)!={'name','size','sha256','chunks'} or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}\.mp4',row['name']):raise ValueError('Invalid media filename')
        if not 0<row['size']<=512*1024*1024 or not re.fullmatch(r'[a-f0-9]{64}',row['sha256']):raise ValueError('Invalid media bounds/hash')
        if not 1<=len(row['chunks'])<=256:raise ValueError('Media chunk count bound')
        if row['name'] in names:raise ValueError('Duplicate media name')
        names.add(row['name']);expanded+=row['size']
        if expanded>512*1024*1024:raise ValueError('Expanded media bundle bound')
        target=root/row['name']
        if target.is_symlink() or target.is_junction():raise ValueError('Redirected media file')
        if target.is_file() and target.stat().st_size==row['size'] and hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256']:
            outputs[row['name']]=target;continue
        temporary=target.with_suffix('.pending');digest=hashlib.sha256();total=0
        if temporary.is_symlink() or temporary.is_junction():raise ValueError('Redirected media staging file')
        try:
            with temporary.open('wb') as stream:
                for chunk in row['chunks']:
                    if set(chunk)!={'path','size','sha256'} or not re.fullmatch(r'media-\d{3}\.bin',chunk['path']) or not 0<chunk['size']<=4*1024*1024:raise ValueError('Invalid media chunk')
                    source=source_root/chunk['path']
                    if chunk['path'] in chunks or source.is_symlink() or source.is_junction() or source.resolve().parent!=source_root:raise ValueError('Duplicate or redirected media chunk')
                    chunks.add(chunk['path']);part=source.read_bytes()
                    if len(part)!=chunk['size'] or hashlib.sha256(part).hexdigest()!=chunk['sha256']:raise ValueError('Media chunk verification failed')
                    total+=len(part)
                    if total>row['size']:raise ValueError('Media size exceeded')
                    stream.write(part);digest.update(part)
            if total!=row['size'] or digest.hexdigest()!=row['sha256']:raise ValueError('Media file verification failed')
            os.replace(temporary,target)
        finally:
            if temporary.exists():temporary.unlink()
        outputs[row['name']]=target
    return outputs
