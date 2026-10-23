"""Point-in-time verification of original split-body battle-component links.

Reads existing reflected object references only. Does not create, retarget,
initialize or promote actors, or claim encounter/animation success.
"""
from .catalog import capture_matching,capture_selected
from ._reader import ReadBatch
from .cinematics.original_game_action import controller_context

COMPONENT='/Game/Gameplay/Battle/DummyBattleCharacter/BP_Component_BattleDummyCharacter.BP_Component_BattleDummyCharacter_C'
HELPER_BASE='/Game/Characters/Enemies/Blueprints/BP_Battle_DummyEnemy.BP_Battle_DummyEnemy_C'
FIELDS=('LinkedDummyCharacterClass','LinkedCharacterDummyActor','As BP J RPG Character Battle Base')
BAD_FLAGS=0x40018030


def _identity(obj):return (obj.index,obj.serial,obj.address)


def _argument(value):
    if (type(value) not in (tuple,list) or len(value)!=3 or any(type(v) is not int for v in value)
        or value[0]<0 or value[1]<0 or not 0x10000<=value[2]<=0x7fffffffffff):
        raise ValueError('Expected an exact observed object identity')
    return tuple(value)


def validate_link(observation):
    """Validate copied relationships without converting metadata into spawn proof."""
    if observation['component_count']!=1:raise RuntimeError('Missing or ambiguous original dummy component')
    if observation['field_errors']:raise RuntimeError('Original dummy link fields unreadable')
    if observation['component_owner']!=observation['battle_actor']:raise RuntimeError('Dummy component owner differs')
    if observation['back_reference']!=observation['battle_actor']:raise RuntimeError('Dummy component battle back-reference differs')
    if observation['linked_actor']!=observation['helper']:raise RuntimeError('Original component selected another helper or no helper')
    if observation['lookup_class']!=observation['helper_class']:raise RuntimeError('Original helper lookup class differs')
    if observation['matching_current_world_helpers']!=[observation['helper']]:raise RuntimeError('Original class/subclass helper lookup is ambiguous')
    if not observation['same_current_world']:raise RuntimeError('Battle actor and helper are not in the current world')
    if not observation['context_unchanged']:raise RuntimeError('Travel during helper link observation')
    return dict(observation,link_verified=True,read_only=True,actor_spawned=False,
        encounter_verified=False,animation_verified=False,
        limitation='Point-in-time original object references and class uniqueness; no future streaming guarantee')


def inspect_original_helper_link(scope,battle_actor_identity,helper_identity):
    """Verify an existing original battle component links to the specified helper.

    The caller must separately establish encounter ownership and admission.
    This query never authorizes entry or changes helper lifetime state.
    """
    from .values import read_values_with_references
    scope._check();battle_id=_argument(battle_actor_identity);helper_id=_argument(helper_identity)
    if battle_id==helper_id:raise ValueError('Battle actor and helper must be distinct')
    with ReadBatch(scope.pid):
        context=controller_context(scope._session)
        c=capture_matching(scope.pid,classes=('BP_Component_BattleDummyCharacter_C','BP_Battle_DummyEnemy_C'))
        c=c.with_observations(capture_selected(scope.pid,(battle_id,helper_id)))
        battle=c.by_index[battle_id[0]];helper=c.by_index[helper_id[0]]
        if _identity(battle)!=battle_id or _identity(helper)!=helper_id:raise RuntimeError('Battle/helper identity changed')
        if battle.object_flags&BAD_FLAGS or helper.object_flags&BAD_FLAGS:raise RuntimeError('Battle/helper is a template or retired object')
        def lineage(obj):return {c.path_name(c.by_index[i]) for i in c.ancestors(obj.class_index)}
        if HELPER_BASE not in lineage(helper):raise ValueError('Expected an original dummy-helper actor')
        components=[o for o in c.objects if o.outer_index==battle.index and not o.object_flags&BAD_FLAGS and COMPONENT in lineage(o)]
        if len(components)!=1:raise RuntimeError('Missing or ambiguous original dummy component')
        component=components[0]
        values,c=read_values_with_references(c,component,fields=FIELDS)
        fields={key[1]:value for key,value in values.values.items()}
        def ref(name):
            obj=fields.get(name);return _identity(obj) if obj is not None else None
        lookup=fields.get('LinkedDummyCharacterClass')
        world_id=tuple(context['world'][1:])
        def current_world(obj):return any(_identity(o)==world_id for o in c.outer_chain(obj) if o.class_name=='World')
        matches=[]
        if lookup is not None:
            matches=[_identity(o) for o in c.objects if not o.object_flags&BAD_FLAGS and
                lookup.index in set(c.ancestors(o.class_index)) and current_world(o)]
        observation=dict(battle_actor=battle_id,helper=helper_id,helper_class=_identity(c.by_index[helper.class_index]),
            component=_identity(component),component_count=len(components),component_owner=battle_id,
            back_reference=ref(FIELDS[2]),linked_actor=ref(FIELDS[1]),lookup_class=ref(FIELDS[0]),
            matching_current_world_helpers=matches,field_errors={key[1]:str(value) for key,value in values.errors.items()},
            same_current_world=current_world(battle) and current_world(helper),
            context_unchanged=controller_context(scope._session)==context)
        return validate_link(observation)
