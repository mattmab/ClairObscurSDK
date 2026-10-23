"""One-to-three member encounter authoring. No runtime mutation or promotion."""
import json
from pathlib import Path


def load_group_catalog(path=None):
    path=Path(path) if path is not None else Path(__file__).with_name('_enemy_groups.json')
    data=json.loads(path.read_text(encoding='utf8'))
    if data.get('schema')!=1:raise ValueError('Unsupported enemy group catalog')
    choices=data['choices']
    if len({c['id'] for c in choices})!=len(choices):raise ValueError('Duplicate enemy choice')
    return data


def compose_group(catalog,member_ids,*,policy='isolated',experimental=False):
    if policy not in ('isolated','original_campaign_actions'):raise ValueError('Unknown encounter policy')
    if type(experimental) is not bool:raise ValueError('Experimental choice must be bool')
    maximum=10 if experimental else 3
    if type(member_ids) not in (list,tuple) or not 1<=len(member_ids)<=maximum:
        raise ValueError('Choose one to '+str(maximum)+' enemies')
    choices={c['id']:c for c in catalog['choices']};members=[]
    for slot,key in enumerate(member_ids):
        if type(key) is not str or key not in choices:raise ValueError('Unknown enemy definition')
        source=choices[key]
        if not source['available'] or not source['battle_class']:raise ValueError('Enemy definition has no original battle class')
        members.append({'slot':slot,'definition_id':key,'table':source['table'],
            'row':source['row'],'battle_class':source['battle_class']})
    return {'format':'e33.enemy-group','version':1,'policy':policy,'experimental':experimental,'members':members}


def group_plan(catalog,group):
    canonical=compose_group(catalog,[m['definition_id'] for m in group['members']],policy=group['policy'],experimental=group['experimental'])
    if group!=canonical:raise ValueError('Group member references or slots differ from catalog')
    wanted=[(m['slot'],m['table'],m['row']) for m in group['members']]
    matches=[]
    for encounter in catalog['encounters']:
        observed=sorted((m['slot'],m['table'],m['row']) for m in encounter['enemies'])
        if observed==wanted:
            routes=[r for r in catalog['single_authored_world_routes'] if r['encounter_row']==encounter['name']]
            matches.append({'table':catalog['encounter_table'],'row':encounter['name'],
                'narrative':encounter['narrative'],'world_routes':routes})
    return {'group':canonical,'matching_authored_encounters':matches,
        'required_enemy_slot_mask':(1<<len(group['members']))-1,
        'runtime_group_spawn_available':False,
        'required_native_work':['Owned original world members and BP_EnemyGroup lifecycle',
            'One shared encounter roster, using an exact authored row or an engine-owned temporary row',
            'Single battle trigger; group retirement deferred during combat'],
        'note':'Authored matches do not prove grouped world assembly or runtime encounter verification.'}


def arena_capacity(group,observed_enemy_mask):
    if type(observed_enemy_mask) is not int or not 0<=observed_enemy_mask<1<<64:
        raise ValueError('Expected an observed unsigned64 enemy slot mask')
    count=len(group['members'])
    if not 1<=count<=10:raise ValueError('Unsupported test group size')
    missing=[slot for slot in range(count) if not observed_enemy_mask&(1<<slot)]
    return {'required_count':count,'observed_slot_count':observed_enemy_mask.bit_count(),
        'missing_slots':missing,'all_required_slots_observed':not missing,
        'limitation':'Slot evidence does not establish battle-manager, targeting or UI capacity.'}
