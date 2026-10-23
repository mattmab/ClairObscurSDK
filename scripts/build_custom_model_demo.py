"""Create original OBJ/PNG supply-crate demo assets (no game or BL4 assets)."""
from pathlib import Path
import struct,zlib
root=Path(__file__).resolve().parents[1]/'mods/CustomModel/assets'
root.mkdir(parents=True,exist_ok=True)
lines=['# Original Expedition SDK supply crate; centimeters, Z up. MIT.']
offset=0
def box(center,extent,metal=False):
    global offset
    x,y,z=center;a,b,c=(v/2 for v in extent)
    faces=[((1,0,0),[(a,-b,-c),(a,b,-c),(a,b,c),(a,-b,c)]),
      ((-1,0,0),[(-a,b,-c),(-a,-b,-c),(-a,-b,c),(-a,b,c)]),
      ((0,1,0),[(a,b,-c),(-a,b,-c),(-a,b,c),(a,b,c)]),
      ((0,-1,0),[(-a,-b,-c),(a,-b,-c),(a,-b,c),(-a,-b,c)]),
      ((0,0,1),[(-a,-b,c),(a,-b,c),(a,b,c),(-a,b,c)]),
      ((0,0,-1),[(-a,b,-c),(a,b,-c),(a,-b,-c),(-a,-b,-c)])]
    for n,points in faces:
        u0,u1=(.78,.98) if metal else (.02,.73)
        for p,uv in zip(points,[(u1,.98),(u0,.98),(u0,.02),(u1,.02)]):
            lines.append('v %g %g %g'%(p[0]+x,p[1]+y,p[2]+z))
            lines.append('vt %g %g'%uv);lines.append('vn %g %g %g'%n)
        ids=range(offset+1,offset+5);lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in ids));offset+=4
box((0,0,58),(128,88,100))
box((0,0,113),(136,96,10),True)
for x in (-43,43):box((x,0,60),(9,94,108),True)
for x in (-45,45):
    for y in (-28,28):box((x,y,4),(22,22,8),True)
(root/'supply-crate.obj').write_text('\n'.join(lines)+'\n')
raw=bytearray()
glyph=['111','001','001','111','001','001','111']
for y in range(128):
    raw.append(0)
    for x in range(128):
        grain=((x*17+y*3)%13)-6
        color=(95+grain,57+grain,28+grain) if x<96 else (97+grain,111+grain,121+grain)
        if x<96 and (y%24<2 or x%24<1):color=(35,23,14)
        if 15<x<81 and 30<y<95:color=(15,53,76)
        for start in (23,52):
            gx,gy=(x-start)//5,(y-43)//5
            if 0<=gx<3 and 0<=gy<7 and glyph[gy][gx]=='1':color=(244,209,116)
        raw.extend(color)
def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data))
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',128,128,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
(root/'supply-crate.png').write_bytes(png)
