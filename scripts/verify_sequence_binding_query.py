"""Exact freshly unlocked actor sequence factory/query/close; never calls Play."""
import time
import json
from pathlib import Path
from uuid import uuid4
from expedition33.catalog import capture_matching, capture
from expedition33.sequences import OwnedLevelSequence
from expedition33._sequence_owner import SequenceCleanupDeferred
from inspect_actor_cinematic_imports import PROFILES


def binding_context(sequence, session):
    from expedition33.values import read_values
    from inspect_spawned_camera_contracts import copied
    observed=capture()
    if observed.pid!=session.pid:raise RuntimeError('Game identity changed')
    actor_values=read_values(observed,observed.resolve(sequence.actor))
    key=(observed.find_class('LevelSequenceActor').index,'BindingOverrides')
    result={'binding_overrides':copied(actor_values.values.get(key),observed)}
    if key in actor_values.errors:result['binding_overrides_error']=str(actor_values.errors[key])
    return result


def run(mod, profile=1):
    if type(profile) is not int or profile not in (1,2):
        raise ValueError('Expected reviewed binding profile 1 or 2')
    if mod.video is not None or (mod.title_replay and mod.title_replay.status().get('active')):
        raise RuntimeError('Stop playback before binding inspection')
    if getattr(mod,'_binding_query_retained',None) is not None:
        raise RuntimeError('Previous binding inspection retained; no retry')
    menu=getattr(getattr(mod,'native',None),'menu',None)
    if menu is None or menu.panel.state!='open' or menu.panel.uncertain:
        raise RuntimeError('A known open Cinematics menu is required')
    session=getattr(mod.session,'_session',mod.session)
    if getattr(session._transport,'sequence_binding_query_protocol',0)!=1:
        raise RuntimeError('Native binding query capability required')
    definition,path,digest=PROFILES[profile-1]
    mod.discover()
    rows=[s for s in mod.discovery.get('confirmed',()) if s.get('id')==definition
          and s.get('unlocked') is True and s.get('sequence')==path
          and s.get('definition_sha256')==digest]
    if len(rows)!=1:
        raise RuntimeError('Exact research definition is not freshly unlocked')
    catalog=capture_matching(session.pid,names=('MovieSceneSequencePlayer','GetBoundObjects'))
    cls=OwnedLevelSequence._one(o for o in catalog.objects
        if o.name=='MovieSceneSequencePlayer' and o.class_name=='Class')
    function=OwnedLevelSequence._one(o for o in catalog.objects
        if o.name=='GetBoundObjects' and o.class_name=='Function' and o.outer_index==cls.index)
    sequence=OwnedLevelSequence(mod.session)
    mod._binding_query_retained=sequence
    report=dict(profile=profile,playback_attempted=False,closed=False)
    try:
        sequence.build(menu.panel,path,capture_camera=True)
        # Read-only context evidence, never used as native admission authority.
        report.update(binding_context(sequence,session))
        report['query']=sequence.owner.query_authored_bindings(profile,function)
    except Exception as error:
        report['error']=repr(error)
    if not sequence.uncertain and sequence.owner.state!='unknown':
        for _ in range(8):
            try:
                sequence.close()
                report['closed']=True
                mod._binding_query_retained=None
                break
            except SequenceCleanupDeferred:
                time.sleep(.1)
            except Exception as error:
                report['close_error']=repr(error)
                break
    report['state']=sequence.state
    report['owner_state_after']=sequence.owner.state
    report['diagnostics']=getattr(sequence.owner,'binding_diagnostics',None)
    report['native_error']=getattr(sequence.owner,'binding_error',None)
    output=Path(__file__).resolve().parents[1]/'evidence'/('binding-query-'+uuid4().hex+'.json')
    output.write_text(json.dumps(report,indent=2),encoding='utf8')
    report['artifact']=str(output)
    return report
