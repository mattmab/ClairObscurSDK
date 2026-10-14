"""Read static sections from the user's normalized catalog; never load clips."""
from pathlib import Path
import hashlib,json,math,struct,zlib,os

TARGETS={'bird':'BIRD__0x1472D392F4386DA1','2b':'BLEND_2B_ANIMATION_INSPECTOR'}
DEFAULT_ROOT=Path(os.environ.get('E33_NORMALIZED_CATALOG','__no_optional_catalog__'))

def entries(root):
    root=Path(root).resolve()
    if not (root/'catalog.json').is_file():return []
    rows=json.loads((root/'catalog.json').read_text(encoding='utf8'))['assets']
    result=[]
    for row in rows:
        if row.get('state') not in ('READY','READY_WITH_WARNINGS'):continue
        item=dict(id=row['id'],name=row.get('displayName',row['id']),available=True,reason='Static package; live playback unverified')
        try:
            folder=inside(root,row['path']);m=json.loads((folder/'manifest.json').read_text(encoding='utf8'))
            if m['schema']!='normalized-asset/1':raise ValueError('Unsupported normalized schema')
            sections=[s for p in m['asset']['parts'] for s in p['sections'] if s.get('visible',True)]
            if not 0<len(sections)<=64:raise ValueError('Section budget exceeded')
            count=sum(m['buffers'][s['positions']['buffer']]['shape'][0] for s in sections)
            if count>1000000:raise ValueError('Vertex budget exceeded')
            item.update(sections=len(sections),vertices=count)
            if row['id'] in TARGETS.values():item['reason']='Static spawn and cleanup tested in-game'
        except (KeyError,TypeError,ValueError,OSError) as error:item.update(available=False,reason=str(error))
        result.append(item)
    return sorted(result,key=lambda r:(r['name'].casefold(),r['id']))

def inside(root,name):
    path=(root/name).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Catalog path escapes root')
    return path

def prepare(root,selection,output):
    root=Path(root).resolve();output=Path(output);output.mkdir(parents=True,exist_ok=True)
    catalog=json.loads((root/'catalog.json').read_text(encoding='utf8'))
    identity=TARGETS.get(selection,selection)
    rows=[r for r in catalog['assets'] if r['id']==identity]
    if len(rows)!=1 or rows[0]['state'] not in ('READY','READY_WITH_WARNINGS'):raise ValueError('Catalog entry unavailable')
    folder=inside(root,rows[0]['path']);m=json.loads((folder/'manifest.json').read_text(encoding='utf8'))
    if m['schema']!='normalized-asset/1':raise ValueError('Catalog schema')
    a=m['asset']
    if a['uvConvention']!='prepared-runtime-v1':raise ValueError('UV convention')
    source=inside(folder,m['payload']['path'])
    if source.stat().st_size!=m['payload']['bytes'] or source.stat().st_size>512*1024*1024:raise ValueError('Payload size')
    with source.open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=m['payload']['sha256']:raise ValueError('Payload hash')
    def array(value,width,limit):
        if not isinstance(value,dict) or set(value)!={'buffer'}:raise ValueError('Expected numeric buffer')
        b=m['buffers'][value['buffer']];shape=b['shape'];dtype=b['dtype']
        formats={'<f4':('f',4),'<f8':('d',8),'<i4':('i',4),'<i8':('q',8),'<u4':('I',4)}
        if dtype not in formats or len(shape) not in (1,2) or not 0<shape[0]<=limit:raise ValueError('Numeric buffer type/size')
        if (shape[1] if len(shape)==2 else 1)!=width:raise ValueError('Numeric buffer width')
        fmt,size=formats[dtype];expected=shape[0]*width*size
        if b['bytes']!=expected or b['offset']<0 or not 0<b['compressed_bytes']<=32*1024*1024 or b['offset']+b['compressed_bytes']>source.stat().st_size:raise ValueError('Buffer bounds')
        with source.open('rb') as stream:
            stream.seek(b['offset']);compressed=stream.read(b['compressed_bytes'])
        decoder=zlib.decompressobj();raw=decoder.decompress(compressed,expected+1)
        if len(raw)!=expected or not decoder.eof or decoder.unused_data or hashlib.sha256(raw).hexdigest()!=b['sha256']:raise ValueError('Buffer integrity')
        values=list(struct.iter_unpack('<'+fmt*width,raw))
        if any(not math.isfinite(v) for row in values for v in row):raise ValueError('Nonfinite geometry')
        return values
    sections=[];total=0
    for part in a['parts']:
        for s in part['sections']:
            if s.get('visible',True) is False:continue
            p=array(s['positions'],3,200000);n=array(s['normals'],3,200000);uv=array(s['uv'],2,200000)
            indices=[r[0] for r in array(s['indices'],1,600000)]
            if len(n)!=len(p) or len(uv)!=len(p) or len(indices)%3 or any(type(i)!=int or i<0 or i>=len(p) for i in indices):raise ValueError('Section topology')
            total+=len(p)
            if total>1000000 or len(sections)>=64:raise ValueError('Catalog model budget')
            sections.append((p,n,uv,indices,a['materials'][s['material']]))
    if not sections:raise ValueError('No visible sections')
    minimum=[min(v[k] for p,_,_,_,_ in sections for v in p) for k in range(3)]
    maximum=[max(v[k] for p,_,_,_,_ in sections for v in p) for k in range(3)]
    extent=max(maximum[k]-minimum[k] for k in range(3))
    if extent<=0:raise ValueError('Degenerate bounds')
    scale=(250 if identity.startswith('BIRD__') else 180)/extent
    center=((minimum[0]+maximum[0])/2,(minimum[1]+maximum[1])/2,minimum[2])
    result=[]
    for index,(p,n,uv,indices,material) in enumerate(sections):
        raw=bytearray(struct.pack('<8sII',b'E33MESH1',len(p),len(indices)))
        for position,normal,texcoord in zip(p,n,uv):
            length=math.sqrt(sum(v*v for v in normal))
            if length<1e-8:raise ValueError('Zero normal')
            vertex=tuple((position[k]-center[k])*scale for k in range(3))+tuple(v/length for v in normal)+tuple(texcoord)
            if any(abs(v)>100 for v in texcoord):raise ValueError('UV range')
            raw.extend(struct.pack('<8d',*vertex))
        raw.extend(struct.pack('<'+str(len(indices))+'i',*indices))
        mesh=output/f'{index:02}.e33mesh';mesh.write_bytes(raw)
        texture=None;name=material.get('albedo')
        if name:
            relative=name if name in m['resources'] else 'textures/'+name
            resource=m['resources'][relative];path=inside(folder,relative);data=path.read_bytes()
            if len(data)>16777216 or len(data)!=resource['bytes'] or hashlib.sha256(data).hexdigest()!=resource['sha256']:raise ValueError('Texture integrity')
            if data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('PNG required')
            width,height=struct.unpack_from('>II',data,16)
            if not 0<width<=4096 or not 0<height<=4096:raise ValueError('Texture dimensions')
            texture=output/f'{index:02}.png';texture.write_bytes(data)
        result.append(dict(mesh=str(mesh.resolve()),texture=str(texture.resolve()) if texture else None,vertices=len(p),triangles=len(indices)//3))
    evidence=dict(id=identity,source_manifest_sha256=hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest(),source_payload_sha256=digest,
                  sections=result,vertices=total,scale=scale,mode='static catalog sections; no animation',source_bounds=[minimum,maximum])
    (output/'provenance.json').write_text(json.dumps(evidence,indent=2))
    return evidence
