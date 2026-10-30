"""Reject release runtime/source drift before writing any archive."""
from pathlib import Path
import io
import zipfile


def verify_sources(root,entries,names):
    names=tuple(names)
    if len(names)!=len(set(names)) or any(not n.startswith('src/') or '..' in Path(n).parts for n in names):
        raise ValueError('Explicit distinct SDK source inventory required')
    expected={'SDK/'+n for n in names}
    actual={n for n in entries if n.startswith('SDK/src/')}
    if actual!=expected:raise ValueError('Frozen SDK source inventory differs from the release source inventory')
    for name in names:
        if entries['SDK/'+name]!=(Path(root)/name).read_bytes():
            raise ValueError('Frozen SDK source differs from release source: '+name)


def verify_mod(root,data,names):
    names=tuple(names)
    if len(names)!=len(set(names)) or any(Path(n).is_absolute() or '..' in Path(n).parts for n in names):
        raise ValueError('Explicit distinct mod source inventory required')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members=[row.filename for row in archive.infolist() if not row.is_dir()]
        if len(members)!=len(set(members)) or set(members)!=set(names):
            raise ValueError('Frozen mod inventory differs from release source inventory')
        for name in names:
            if archive.read(name)!=(Path(root)/name).read_bytes():
                raise ValueError('Frozen mod differs from release source: '+name)
