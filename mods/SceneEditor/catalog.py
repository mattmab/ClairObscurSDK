"""Read-only character discovery browser; runtime roles remain palette-owned."""
import json
from functools import lru_cache
from pathlib import Path
from .palette import CHARACTERS, ANIMATIONS, BODY_SKELETON, animation_owner, actor_animation_owner

DATA=json.loads(Path(__file__).with_name('catalog.json').read_text(encoding='utf8'))
CATEGORIES=('Main Characters','Nevrons','Gestrals','NPCs','Unknown/Unclassified')
SUPPORTED={e['id']:e for e in DATA['supported']}
REVIEW={e['id']:e for e in DATA['review']}

def entries(category=None,query='',review=False):
    words=query.casefold().split()
    return tuple(e for e in (REVIEW if review else SUPPORTED).values()
        if (category is None or e['category']==category)
        and all(w in (e['label']+' '+e['category']+' '+' '.join(e['body_mesh_paths']+e['blueprint_paths']+e.get('aliases',[]))).casefold() for w in words))

def entry(key):return REVIEW.get(key) or SUPPORTED[key]

def _matches(e):
    for role,a in CHARACTERS.items():
        if a['parts'][0]['path'] not in e['body_mesh_paths']:continue
        # A named class using a generic body cannot borrow another person's recipe.
        if e.get('identity_sensitive') and role not in e.get('baseline_role_ids',[]) and a['label'].casefold()!=e['label'].casefold():continue
        yield role,a

def ready_roles(e):
    return tuple(role for role,a in _matches(e) if not a.get('raw') or a.get('main_actor'))

def candidate_roles(e):
    return tuple(role for role,a in _matches(e) if a.get('library_kind')=='assembly_candidate' and role not in ready_roles(e))

def body_roles(e):
    if e.get('identity_sensitive'):return ()
    return tuple(role for role,a in _matches(e) if a.get('raw') and not a.get('main_actor') and a.get('library_kind')!='assembly_candidate')

@lru_cache(maxsize=512)
def _authored(role):
    a=CHARACTERS[role];body=a['parts'][0]['path'];skeleton=a.get('skeleton') or DATA['mesh_skeletons'].get(body) or (BODY_SKELETON if not a.get('raw') else None)
    owner=actor_animation_owner(role)
    selected={k for k,v in ANIMATIONS.items() if skeleton and v['skeleton']==skeleton and animation_owner(v['path'])==owner}
    authored=set(DATA['body_authored_animation_paths'].get(body,()))
    selected.update(k for k,v in ANIMATIONS.items() if skeleton and v['skeleton']==skeleton and v['path'] in authored)
    default=a.get('default_animation')
    if default in ANIMATIONS and ANIMATIONS[default]['skeleton']==skeleton:selected.add(default)
    return frozenset(selected)

def counts(e):
    roles=ready_roles(e)+candidate_roles(e)+body_roles(e)
    authored=set().union(*(_authored(role) for role in roles)) if roles else set()
    return len(authored),e.get('structural_animation_count',0)

def status(e):
    return 'Ready' if ready_roles(e) else 'Candidate preview' if candidate_roles(e) else 'Body only' if body_roles(e) else 'Assembly pending'

def candidate_action(role):
    return 'Preview assembled candidate' if any(p['path'] for p in CHARACTERS[role]['parts'][1:]) else 'Body only (candidate)'

def for_role(role):
    return next((e for e in SUPPORTED.values() if role in ready_roles(e)+candidate_roles(e)),None)

def label(e):
    authored,_=counts(e)
    return e['label']+' | '+status(e)+f' | {authored} preview clips'

def details(e):
    authored,structural=counts(e)
    return (e['label']+' | '+e['category']+'\n'+status(e)+'\n\n'+e['assembly_status']
        +f"\n\n{authored} authored clips in the preview catalog\n{e.get('discovered_authored_animation_count',0)} authored mesh clips discovered\n{structural} structural animation references"
        +'\nShared skeletons do not prove intended character animation ownership. Structural counts include shared rigs; they are not a verified character set.'
        +'\n\n'+e.get('identity_status','Supported internal character family')
        +'\n'+e.get('note','')+'\n\nBody: '+(e['body_mesh_paths'][0] if e['body_mesh_paths'] else 'Not bound to a mesh')
        +f"\n{len(e['body_mesh_paths'])} body references | {len(e['blueprint_paths'])} Blueprint references retained in catalog evidence.")
