"""User-owned converted assets live outside disposable mod caches."""
import os,json
from pathlib import Path
import expedition33

ASSET_ROOT=Path(os.environ.get('E33_ASSET_LIBRARY',str(Path(expedition33.__file__).resolve().parents[2].parent/'SDK_Assets')))

def package(model):
    if model not in ('ayane','2b'):raise ValueError('Unknown model')
    return ASSET_ROOT/model

def entries():
    result=[]
    for key,name in (('ayane','Ayane — Ninja Gaiden 2 Black'),('2b','2B — NieR:Automata')):
        row=dict(id=key,name=name,available=False,reason='Download separately and run the converter. See README.',replacement=key)
        try:
            data=json.loads((package(key)/'manifest.json').read_text())
            if data['schema']!='e33-weighted-model/1':raise ValueError('Unsupported package')
            row.update(available=True,vertices=data['vertices'],sections=len(data['sections']),reason='Local converted asset. Approximate animation; meshes may lag.')
        except (OSError,ValueError,KeyError):pass
        result.append(row)
    return result

def prepare_static(model):
    from .custom_skin import checked_package
    data,checked=checked_package(package(model))
    sections=[]
    for row in data['sections']:
        mesh,_=checked(row['mesh']);texture,_=checked(row['texture'])
        sections.append(dict(mesh=str(mesh),texture=str(texture),profile=13))
    return dict(id=model,vertices=data['vertices'],sections=sections)
