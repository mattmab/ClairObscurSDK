"""Exploration prototype: reduce the local 2B rig to Verso's main body bones.

No animations or game skeleton assets are replaced. Auxiliary face/hair/cloth
bones follow their nearest mapped ancestor; this is not cloth or facial parity.
"""
import json,math,struct
from pathlib import Path
from .catalog import prepare,inside,TARGETS

def qmul(a,b):
    x,y,z,w=a;X,Y,Z,W=b
    return (w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z)

def rotate(q,v):
    t=qmul(qmul(q,(*v,0)),(-q[0],-q[1],-q[2],q[3]))
    return t[:3]

def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def norm(v):
    n=math.sqrt(sum(x*x for x in v))
    if n<1e-8:raise ValueError('Degenerate bone direction')
    return tuple(x/n for x in v)

def arc(a,b):
    a,b=norm(a),norm(b);dot=sum(x*y for x,y in zip(a,b))
    if dot<-.9999:raise ValueError('Opposite bind axes require explicit mapping')
    return norm((a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0],1+dot))

def reference_world(rows):
    result={}
    for b in rows:
        t=b['reference'];q=tuple(t[:4]);p=tuple(t[4:7])
        if b['parent']!='None':
            pq,pp=result[b['parent']];q=qmul(pq,q);p=add(pp,rotate(pq,p))
        result[b['name']]=(q,p)
    return result

def mapped_sides(source_arm_x,target_left_arm_x):
    """Match sides after source coordinates have been rotated into engine space."""
    if not all(math.isfinite(x) and abs(x)>1e-6 for x in (source_arm_x,target_left_arm_x)):
        raise ValueError('Ambiguous arm side in reference pose')
    left='l' if source_arm_x*target_left_arm_x>0 else 'r'
    return left,'r' if left=='l' else 'l'

def prepare_skin(root,output,rows,prepared=None):
    output=Path(output);data=dict(prepared) if prepared else prepare(root,'2b',output)
    root=Path(root);entry=next(r for r in json.loads((root/'catalog.json').read_text())['assets'] if r['id']==TARGETS['2b'])
    a=json.loads((inside(root,entry['path'])/'manifest.json').read_text())['asset'];bones=a['skeleton']
    target=reference_world(rows);by_name={b['name']:b for b in rows}
    spelling={name.lower():name for name in target}
    # Positions inferred from the stored inverse bind matrices, not numeric names.
    points=[]
    for b in bones:
        m=b['inverse_bind'];t=[-sum(m[j*4+k]*m[j*4+3] for j in range(3)) for k in range(3)]
        points.append((-100*t[0],-100*t[2],100*t[1]))
    left,right=mapped_sides(points[35][0],target[spelling['upperarm_l']][1][0])
    mapping={1:'Root',2:'Pelvis',3:'spine_01',4:'spine_03',5:'spine_05',6:'neck_01',7:'Head',89:'Pelvis',
        34:'clavicle_'+left,35:'upperarm_'+left,36:'lowerarm_'+left,37:'Hand_'+left.upper(),
        61:'clavicle_'+right,62:'upperarm_'+right,63:'lowerarm_'+right,64:'Hand_'+right.upper(),
        90:'thigh_'+left,91:'calf_'+left,92:'foot_l' if left=='l' else 'Foot_R',93:'ball_'+left,
        94:'thigh_'+right,95:'calf_'+right,96:'foot_l' if right=='l' else 'Foot_R',97:'ball_'+right}
    mapping={i:spelling[name.lower()] for i,name in mapping.items()}
    names=list(dict.fromkeys(mapping.values()));slot={n:i for i,n in enumerate(names)}
    raw=bytearray(struct.pack('<8sII',b'E33SKIN2',len(names),len(data['sections'])))
    for n in names:
        i=next(i for i,name in mapping.items() if name==n)
        parent=bones[i]['parent']
        while parent>=0 and (parent not in mapping or mapping[parent]==n):parent=bones[parent]['parent']
        parent_slot=slot[mapping[parent]] if parent>=0 else -1
        q,p=target[n]
        raw.extend(struct.pack('<I64si3f7d',by_name[n]['index'],n.encode('ascii'),parent_slot,*points[i],*q,*p))
    def mapped(index):
        while index not in mapping:
            index=bones[index]['parent']
            if index<0:return 1
        return index
    section=0
    for part in a['parts']:
        for s in part['sections']:
            if not s.get('visible',True):continue
            mesh=Path(data['sections'][section]['mesh']).read_bytes();_,count,_=struct.unpack_from('<8sII',mesh)
            if count!=len(part['corners']):raise ValueError('Skin corner count mismatch')
            raw.extend(struct.pack('<II',section,count))
            for k,corner in enumerate(part['corners']):
                pos=part['positions'][corner];p=(-pos[0]*100,-pos[2]*100,pos[1]*100)
                v=struct.unpack_from('<8d',mesh,16+64*k);normal=(-v[3],-v[4],v[5])
                combined={}
                for bone,weight in part['influences'][part['groups'][corner]]:
                    bone=mapped(bone);combined[bone]=combined.get(bone,0)+weight
                selected=sorted(combined.items(),key=lambda x:-x[1])[:4];total=sum(w for _,w in selected)
                if total<=0:raise ValueError('Unweighted vertex')
                for bone,weight in selected:
                    local=sub(p,points[bone]);n=normal
                    raw.extend(struct.pack('<If6f',slot[mapping[bone]],weight/total,*local,*n))
                raw.extend(bytes(32*(4-len(selected))))
            section+=1
    path=output/'verso.e33skin';path.write_bytes(raw)
    data['skin']=str(path.resolve());data['mapping']={bones[i]['name']:n for i,n in mapping.items()}
    (output/'skin-provenance.json').write_text(json.dumps(data,indent=2))
    return data
