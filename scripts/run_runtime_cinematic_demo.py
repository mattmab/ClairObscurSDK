"""Run only RuntimeCinematicDemo in its isolated native candidate controller.

The installed SDK must first stop cleanly (`mods shutdown`). Its mod-root lock
is acquired before any attachment. No installed SDK file or settings is changed.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import expedition33.sdk as sdk
from expedition33.mod_lock import ModRootLock
from expedition33.mods import ModLoader
from expedition33.catalog import capture_matching, capture_selected
from expedition33.cinematics.original_game_action import controller_context


def snapshot(session):
    context=controller_context(session)
    names=('GetViewTarget','IsMoveInputIgnored','IsLookInputIgnored')
    c=capture_matching(session.pid,names=names)
    c=c.with_observations(capture_selected(session.pid,(context['controller'][1:],)))
    player=c.by_index[context['controller'][1]]
    owner=c.find_class('Controller').index
    planner=session.invocation_planner(catalog=c,selected_results=True)
    result=dict(world=context['world_path'],controller=context['controller'][1:3])
    try:
        for name in names:
            fn=next(o for o in c.objects if o.name==name and o.class_name=='Function' and o.outer_index==owner)
            with planner.prepare(player,fn).invoke(refresh_from_result=True) as reply:
                value=reply.return_value
                result[name]=[value.index,value.serial] if name=='GetViewTarget' and value is not None else value
    finally:planner.close()
    return result


def audio_snapshot(session):
    from expedition33.catalog import capture
    from expedition33.values import read_values_with_references
    c=capture()
    rows=[]
    for obj in sorted(c.select('AudioComponent'),key=lambda o:o.serial,reverse=True)[:12]:
        if obj.object_flags&0x40000030:continue
        values,observed=read_values_with_references(c,obj,fields=('Sound','VolumeMultiplier','PitchMultiplier','bIsUISound','bIsActive','SoundClassOverride'))
        row=dict(component=c.path_name(obj),values={k[1]:observed.path_name(v) if hasattr(v,'class_index') else v for k,v in values.values.items()},errors={k[1]:str(v) for k,v in values.errors.items()})
        if 'Paint_Whoosh_04' not in str(row):continue
        planner=session.invocation_planner(catalog=c,selected_results=True)
        try:
            for name in ('GetPlayState','IsPlaying'):
                fn=next(o for o in c.objects if o.class_name=='Function' and o.name==name and c.by_index[o.outer_index].name=='AudioComponent')
                with planner.prepare(obj,fn).invoke(refresh_from_result=True) as reply:
                    row[name]=str(reply.return_value)
        finally:planner.close()
        rows.append(row)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-root',type=Path,required=True)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--mode',choices=('inspect','play','interrupt','bones','action-assets','effects-assets'),default='inspect')
    parser.add_argument('--candidate-version',type=int,default=12)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mod-root',type=Path,default=ROOT/'mods')
    parser.add_argument('--audio-diagnostics',action='store_true')
    args=parser.parse_args()
    os.environ['E33_EXPECTED_GAME_PID']=str(args.pid)
    events=[]
    def record(event,result):
        events.append(dict(event=event,time_monotonic=time.monotonic(),result=result))
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(dict(schema=1,mode=args.mode,events=events,
            visual_audio_confirmation=False),indent=2)+'\n',encoding='utf8')
    # Acquisition fails immediately if the installed controller still owns it.
    lock=ModRootLock(args.sdk_root)
    original=sdk.SessionTransport
    sdk.SessionTransport=lambda **kwargs:original(_executable=ROOT/f'build/release/research-probe-cinematic-v{args.candidate_version}/research_probe.exe')
    try:
        with sdk.Session(pod_values=True,enum_values=True) as session,ModLoader(args.mod_root,session=session) as loader:
            if session.pid!=args.pid:raise RuntimeError('Unexpected game PID')
            session.console.enable()
            loader.load('RuntimeCinematicDemo');loader.enable('RuntimeCinematicDemo',console=True)
            model=loader._loaded['RuntimeCinematicDemo'][1]
            record('before',snapshot(session))
            if args.mode in ('action-assets','effects-assets'):
                from expedition33._scope import SessionScope
                from expedition33.assets import load_asset
                from expedition33.catalog import capture
                from expedition33.values import read_values_with_references,StoredArray
                paths=(
                    '/Game/Characters/Heros/Lune/Animations/Skills/Lune_Thunder_Kick_IP.Lune_Thunder_Kick_IP',
                    '/Game/Characters/Heros/Maelle/Animations/Skills/Maelle_Skill_DancingFury_B_Inplace.Maelle_Skill_DancingFury_B_Inplace',
                    '/Game/Characters/Enemies/Petank/SK_Petank.SK_Petank',
                    '/Game/Characters/Heros/Maelle/Sword/SK_Sword_Maelle.SK_Sword_Maelle',
                    '/Game/Audio/WAV/SFX/Characters/Foley/MC_Foley_Leather/F_CHAR_LightLeather_Soft_Short_Main/F_CHAR_LightLeather_Soft_Short_Main_02.F_CHAR_LightLeather_Soft_Short_Main_02')
                if args.mode=='effects-assets':
                    paths=tuple(package+'.'+package.rsplit('/',1)[1] for package in (
                        '/Game/FX/FX_Leo/Fx/Lune/Thunder_Fall/Systems/NS_Impact_Electric1',
                        '/Game/FX/FX_Leo/Fx/Maelle/FX_FlowerPetalsBurst',
                        '/Game/FX/FX_Leo/Fx/Maelle/FX_MaelleSword',
                        '/Game/FX/FX_Leo/Fx/Lune/FX_LuneTrail'))
                scope=SessionScope(model.session)
                try:
                    objects=[load_asset(scope,path).return_value for path in paths]
                    c=capture()
                    for obj in objects:
                        obj=c.resolve(obj)
                        fields=('Skeleton','SequenceLength','Notifies','bEnableRootMotion') if obj.class_name=='AnimSequence' else ('Skeleton',) if obj.class_name=='SkeletalMesh' else ()
                        values,observed=read_values_with_references(c,obj,fields=fields) if fields else (None,c)
                        def copied(v):
                            if hasattr(v,'class_index'):return observed.path_name(v)
                            if isinstance(v,StoredArray):return dict(length=v.length,copied_count=len(v.items))
                            return v
                        record('asset',dict(path=c.path_name(obj),class_name=obj.class_name,
                            values={key[1]:copied(value) for key,value in values.values.items()} if values else {},
                            errors={key[1]:str(value) for key,value in values.errors.items()} if values else {}))
                finally:scope.close()
            elif args.mode=='bones':
                from expedition33._scope import SessionScope
                from expedition33.procedural_mesh import capture_bones
                from expedition33.values import read_values_with_references
                before=capture_matching(session.pid,classes=('SkeletalMeshComponent',))
                known={(o.index,o.serial) for o in before.select('SkeletalMeshComponent')}
                model.scope=SessionScope(model.session)
                model._command(70,model._inputs())
                c=capture_matching(session.pid,classes=('SkeletalMeshComponent',))
                for obj in c.select('SkeletalMeshComponent'):
                    if (obj.index,obj.serial) in known:continue
                    values,observed=read_values_with_references(c,obj,fields=('SkinnedAsset',))
                    asset=next(iter(values.values.values()))
                    bones=capture_bones(model.scope,obj.index)
                    record('bones',dict(asset=observed.path_name(asset),component=obj.index,
                        total=bones['total'],bones=[b for b in bones['bones'] if b['name'].lower() in ('root','head','neck_01','neck_02') or b['index']<4]))
                record('stop',model.stop())
            elif args.mode!='inspect':
                record('start',model.start())
                deadline=time.monotonic()+30
                interrupt_at=time.monotonic()+2.5
                previous=None
                audio_observed=False
                while model.scope is not None and time.monotonic()<deadline:
                    loader.poll()
                    status=model.status()
                    key=(status['state'],status.get('animation_dispatched'),status.get('audio_dispatched'))
                    if key!=previous:record('state',status);previous=key
                    if args.audio_diagnostics and status.get('audio_dispatched') and not audio_observed:
                        audio_observed=True;record('audio_diagnostics',audio_snapshot(session))
                    if args.mode=='interrupt' and time.monotonic()>=interrupt_at and model.scope is not None:
                        record('interrupt',model.stop())
                    time.sleep(.01)
                if model.scope is not None:raise RuntimeError('Demo did not clean up within thirty seconds')
                status=model.status();record('final',status)
                if status['private_leases'] or status['error']:raise RuntimeError('Native cleanup failed')
                if args.mode=='play' and (status['state']!='finished' or not status['animation_dispatched'] or not status['audio_dispatched'] or status['camera_updates']<2 or (args.candidate_version>=11 and status.get('audio_cues_dispatched')!=9)):
                    raise RuntimeError('Native orchestration evidence incomplete')
                if args.mode=='play' and args.candidate_version>=12 and status.get('effects_spawned')!=11:
                    raise RuntimeError('Expected two attached effects and nine impact effects')
            after=snapshot(session);record('after',after)
            if after!=events[0]['result']:raise RuntimeError('Camera/input/world baseline was not restored')
            record('restoration_verified',True)
    except BaseException as error:
        record('error',repr(error));raise
    finally:
        sdk.SessionTransport=original;lock.close()
    print(json.dumps(dict(output=str(args.output),mode=args.mode,native_checks_passed=True,
        visual_audio_confirmation=False)))


if __name__=='__main__':main()
