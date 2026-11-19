"""Reviewed text-to-viseme cues for portable scenes; no audio or save mutation."""
import math,re,struct
SHAPES=('jaw_open','mouth_funnel_DL','mouth_funnel_DR','mouth_funnel_UL','mouth_funnel_UR','mouth_stretch_left','mouth_stretch_right','mouth_lowerLipBite_L','mouth_lowerLipBite_R','mouth_press_DL','mouth_press_DR','mouth_press_UL','mouth_press_UR','mouth_cornerPull_left','mouth_cornerPull_right','mouth_cornerDepress_L','mouth_cornerDepress_R','brow_raiseIn_L','brow_raiseIn_R','brow_down_L','brow_down_R','eye_blink_L','eye_blink_R','jaw_clench_L')
EMOTIONS=('neutral','relief','grief','uncertain','surprise','frustration')
KEY=struct.Struct('<ffHBBf');MAX_KEYS=768
VISEMES={p:i for i,phones in enumerate(('', 'P B M','F V','TH DH','T D S Z N L','CH JH SH ZH','R ER','AA AE AH AW AY','EH EY IH IY Y','AO OW OY','UH UW W')) for p in phones.split()}
VISEMES.update(HH=7,NG=4,K=4,G=4)

def validate(document):
 for row in document.get('captions',[]):
  if 'phonemes' not in row:continue
  if type(row['phonemes']) is not str:raise ValueError('Reviewed ARPABET phonemes required')
  tokens=row['phonemes'].split()
  if not tokens or len(tokens)>256 or any(t not in VISEMES and t not in ('|','...') for t in tokens):raise ValueError('Reviewed ARPABET phonemes required')
  if row.get('emotion','neutral') not in EMOTIONS:raise ValueError('Unknown facial emotion')
  strength=row.get('emotion_strength',.6)
  if type(strength) not in (float,int) or not math.isfinite(strength) or not 0<=strength<=1:raise ValueError('Facial emotion strength outside zero to one')

def compile_keys(document):
 validate(document);actors={a['name']:i for i,a in enumerate(document['actors'])};keys=[]
 for row in document.get('captions',[]):
  if 'phonemes' not in row:continue
  if row['speaker'] not in actors:raise ValueError('Facial caption speaker has no scene actor')
  tokens=row['phonemes'].split();weights=[1.6 if t=='...' else .45 if t=='|' else 1.25 if t in ('AA','AE','AH','AW','AY','EH','EY','IH','IY','AO','OW','OY','UH','UW') else .8 for t in tokens]
  span=row['end']-row['at'];unit=span/sum(weights);at=row['at']
  for token,weight in zip(tokens,weights):
   length=unit*weight
   if length<.02:raise ValueError('Caption too short for reviewed phonemes')
   keys.append((at,length,actors[row['speaker']],VISEMES.get(token,0),EMOTIONS.index(row.get('emotion','neutral')),row.get('emotion_strength',.6)));at+=length
 keys.sort(key=lambda k:(k[0],k[2]))
 if len(keys)>MAX_KEYS:raise ValueError('Facial timeline exceeds 768 keys')
 return keys

def encode_keys(document):
 keys=compile_keys(document)
 return len(keys),b''.join(KEY.pack(*row) for row in keys)+bytes((MAX_KEYS-len(keys))*KEY.size)

def validate_wire(data):
 if len(data)!=20984 or any(data[108:112]) or any(data[14704:]):raise ValueError('Facial timeline reserved payload')
 index,serial,address=struct.unpack_from('<iiQ',data,88);count=struct.unpack_from('<I',data,104)[0]
 if index<0 or serial<0 or not address or count>MAX_KEYS:raise ValueError('Facial timeline header')
 previous={};active=set()
 for i in range(MAX_KEYS):
  at,duration,actor,viseme,emotion,strength=KEY.unpack_from(data,2416+i*KEY.size)
  if i>=count:
   if any((at,duration,actor,viseme,emotion,strength)):raise ValueError('Unused facial key')
   continue
  if actor>=6 or viseme>10 or emotion>5 or any(not math.isfinite(v) for v in (at,duration,strength)) or at<0 or not .019999<=duration<=30 or at<previous.get(actor,-1)-.0001 or not 0<=strength<=1:raise ValueError('Invalid facial key')
  previous[actor]=at+duration;active.add(actor)
 for actor in range(6):
  for shape in range(24):
   identity=struct.unpack_from('<iiQ',data,112+(actor*24+shape)*16)
   if actor in active:
    if identity[0]<0 or identity[1]<0 or not identity[2]:raise ValueError('Missing facial morph identity')
   elif any(identity):raise ValueError('Unused facial morph identity')
