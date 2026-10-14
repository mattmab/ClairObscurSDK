"""Bounded 25-candidate lit comparison with numbered markers; no shared edits."""
from pathlib import Path
import json,struct,zlib
from .catalog import prepare

DIGITS=('111101101101111','010110010010111','111001111100111','111001111001111','101101111001001','111100111001111','111100111101111','111001001001001','111101111101111','111101111001111')
def label_png(path,number):
    w,h=128,64;raw=bytearray()
    text=str(number);start=(w-len(text)*24+6)//2
    for y in range(h):
        raw.append(0)
        for x in range(w):
            on=False
            if 17<=y<47:
                for i,digit in enumerate(text):
                    u=x-start-i*24
                    if 0<=u<18:on=DIGITS[int(digit)][((46-y)//6)*3+u//6]=='1';break
            raw.extend((255,255,255,255) if on else (5,5,5,255))
    def chunk(k,v):return struct.pack('>I',len(v))+k+v+struct.pack('>I',zlib.crc32(k+v)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))

def cube(path,x,y,z,sx=80,sy=80,sz=80):
    faces=(((1,0,0),((1,0,0),(1,1,0),(1,1,1),(1,0,1))),((-1,0,0),((0,1,0),(0,0,0),(0,0,1),(0,1,1))),((0,1,0),((1,1,0),(0,1,0),(0,1,1),(1,1,1))),((0,-1,0),((0,0,0),(1,0,0),(1,0,1),(0,0,1))),((0,0,1),((0,0,1),(1,0,1),(1,1,1),(0,1,1))),((0,0,-1),((0,1,0),(1,1,0),(1,0,0),(0,0,0))))
    v=[];ix=[]
    for normal,corners in faces:
        base=len(v)
        for point,uv in zip(corners,((0,1),(1,1),(1,0),(0,0))):v.append((x+point[0]*sx,y+point[1]*sy,z+point[2]*sz,*normal,*uv))
        ix.extend(base+i for i in (0,2,1,0,3,2))
    path.write_bytes(struct.pack('<8sII',b'E33MESH1',len(v),len(ix))+b''.join(struct.pack('<8d',*p) for p in v)+struct.pack('<36i',*ix))

def prepare_lit_samples(root,output,batch=1):
    if type(batch)is not int or not 1<=batch<=4:raise ValueError('Choose lit batch 1..4')
    output=Path(output);original=prepare(root,'2b',output/'source')
    texture=next(row['texture'] for row in original['sections'] if row['texture'])
    candidates=json.loads(Path(__file__).with_name('lit_candidates.json').read_text())[(batch-1)*25:batch*25]
    sections=[];mapping=[]
    for i,row in enumerate(candidates):
        x=(i%5-2)*240;y=(i//5)*240;number=row['id']
        mesh=output/f'lit-{number:03}.e33mesh';cube(mesh,x,y,30)
        sections.append(dict(mesh=str(mesh.resolve()),texture=texture,profile=row['profile'],sample=number))
        label=output/f'label-{number:03}.png';label_png(label,number)
        badge=output/f'label-{number:03}.e33mesh';cube(badge,x+10,y+30,120,60,20,30)
        sections.append(dict(mesh=str(badge.resolve()),texture=str(label.resolve()),profile=2,tint_gain=8,sample=number))
        mapping.append(dict(row,local_center=[x+40,y+40,70],row=i//5+1,column=i%5+1))
    result=dict(id=f'lit-materials-{batch}',sections=sections,vertices=24*len(sections),material_profiles=[],sample_mapping=mapping,batch=batch)
    (output/'comparison.json').write_text(json.dumps(result,indent=2))
    return result
