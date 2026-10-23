"""Local isolated Scene Editor controller. Stop the installed SDK first."""
import argparse,dataclasses,json,logging,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33 import sdk,TargetExitedError
from expedition33.mods import ModLoader
from expedition33.mod_lock import ModRootLock
from expedition33.settings import SettingsStore
from expedition33.controller_commands import CommandServer,Command

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sdk-root',type=Path,required=True);p.add_argument('--pid',type=int,required=True)
    p.add_argument('--version',type=int,default=27);p.add_argument('--mod-root',type=Path,default=ROOT/'mods');args=p.parse_args()
    output=ROOT/'evidence/scene-editor';output.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(output/'controller.log',encoding='utf8')],format='%(asctime)s %(levelname)s %(name)s %(message)s')
    os.environ['E33_EXPECTED_GAME_PID']=str(args.pid)
    def record(event,value):
        with (output/'events.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(time=time.time(),event=event,value=value),default=str)+'\n')
        return value
    original=sdk.SessionTransport;sdk.SessionTransport=lambda **kw:original(_executable=ROOT/f'build/release/research-probe-cinematic-v{args.version}/research_probe.exe')
    lock=ModRootLock(args.sdk_root)
    try:
        with sdk.Session(multiple_pause_entries=True) as session,ModLoader(args.mod_root,settings=SettingsStore(ROOT/'settings/SceneEditor/management.json'),session=session) as loader:
            if session.pid!=args.pid:raise RuntimeError('Unexpected game process')
            for name in ('SDKManagement','SceneEditor'):loader.load(name);loader.enable(name,console=True)
            model=loader._loaded['SceneEditor'][1]
            def frame():
                menu=model.timeline if model.timeline is not None and model.timeline.panel.state=='open' else model.native.menu
                if menu is None or menu.panel.state!='open':return dict(open=False,status=model.status())
                return dict(open=True,screen=getattr(menu.view,'screen','timeline'),frame=dataclasses.asdict(menu.frame),status=model.status())
            def click(token,revision=None):
                menu=model.timeline if model.timeline is not None and model.timeline.panel.state=='open' else model.native.menu
                if menu is None or menu.panel.state!='open':raise ValueError('Scene Editor is not open')
                control=next(c for c in menu.frame.controls if c.token==token and c.enabled)
                operation=menu.view._commands[token][0] if hasattr(menu.view,'_commands') else 'timeline'
                submission={'value':menu.panel.read_field()} if operation in ('apply','search') or operation=='timeline' and token==27 else {}
                menu.submit(menu.frame.revision if revision is None else revision,token,**submission)
                return frame()
            def field(value):
                menu=model.timeline if model.timeline is not None and model.timeline.panel.state=='open' else model.native.menu
                if menu is None or not (getattr(menu.view,'picker',False)=='audio' or getattr(menu.view,'editing',False) or getattr(menu.view,'screen','') in ('scene_animation','scene_animation_groups','scene_clips')):raise ValueError('Select an editable property or animation search first')
                menu.panel.field_value=None;menu.panel.set_field(value);return frame()
            def shutdown():loader.request_stop();return 'Stopping Scene Editor controller'
            def author():return record('authoring_started',model.start_authoring())
            def audition(slot=0,play=True):
                if not model.runtime.authoring:raise ValueError('Enter authoring first')
                return record('audition',model.runtime.audition(slot,play))
            def seek(seconds=0):
                if not model.runtime.authoring:raise ValueError('Enter authoring first')
                return record('seek',model.runtime.seek(seconds))
            def reference_cast(assemblies):
                """Temporary production casting; never saves or edits catalog recipes."""
                import copy,importlib
                scene=importlib.import_module('.scene',model.__class__.__module__.rsplit('.',1)[0])
                if not isinstance(assemblies,list) or not 1<=len(assemblies)<=6 or any(a not in scene.ROLES for a in assemblies):raise ValueError('Choose one to six catalog assemblies')
                if model.runtime.scope is not None:model.stop()
                data=scene.sample(model.document['target_map'] if model.document else __import__('expedition33.cinematics.original_game_action',fromlist=['controller_context']).controller_context(session)['world_path'])
                data['name']='FOR THE NEXT - Reference cast'
                data['events']=[e for e in data['events'] if e['id']=='camera-orbit']
                data['actors']=[]
                for i,assembly in enumerate(assemblies):
                    actor=copy.deepcopy(scene.ACTOR_TEMPLATES[assembly]);actor['id']='reference-'+str(i)
                    actor['transform']['position']=[0.,float(i*450),0.];actor['transform']['rotation']=[0.,0.,0.]
                    data['actors'].append(actor);data['assemblies'][assembly]=scene.ASSEMBLIES[assembly]
                    data['events'].append(dict(id='anim-'+actor['id'],type='animation',target=actor['id'],at=0.,params=dict(asset='bind_pose',speed=1.,loop=False)))
                model.document=scene.validate(data);model.key=None;model.dirty=True
                return author()
            def reference_pose(slot=0,angle=0,distance=360,height=100,seconds=0):
                """Frame an existing temporary actor through the existing native plan API."""
                import math
                r=model.runtime
                if not r.authoring or type(slot) is not int or not 0<=slot<len(model.document['actors']):raise ValueError('Select a live reference actor')
                for value,lo,hi in ((angle,-180,180),(distance,120,2000),(height,30,350),(seconds,0,20)):
                    if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:raise ValueError('Reference camera outside bounds')
                r.editor_control(0);r.editor_control(5,0)
                data=r.sync_document(model.document);origin=r.last['anchor'];pose=data['actors'][slot]['transform']['position']
                yaw=math.radians(origin[3]);x=origin[0]+math.cos(yaw)*pose[0]-math.sin(yaw)*pose[1];y=origin[1]+math.sin(yaw)*pose[0]+math.cos(yaw)*pose[1]
                heading=math.radians(origin[3]+data['actors'][slot]['transform']['rotation'][1]+angle)
                camera=[x+math.cos(heading)*distance,y+math.sin(heading)*distance,origin[2]+pose[2]+height,0.,math.remainder(math.degrees(heading)+180,360),0.]
                r._command(76,payload=r._encode(data,camera));r.seek(seconds)
                r.editor_control(5,1);r._command(73);r.editor_control(5,0)
                if model.timeline is not None:model.timeline.close();model.timeline=None
                if model.hud is not None:model.hud.close();model.hud=None
                return r.status()
            def snapshot():
                sys.path.insert(0,str(ROOT/'scripts'))
                from run_runtime_cinematic_demo import snapshot as observe
                return observe(session)
            def animations():
                from expedition33 import RuntimeQueryError
                from expedition33.catalog import capture_matching
                from expedition33.values import read_values_with_references
                c=capture_matching(session.pid,classes=('AnimSingleNodeInstance',));rows=[]
                for obj in c.select('AnimSingleNodeInstance'):
                    if obj.object_flags&0x40000030:continue
                    path=c.path_name(obj)
                    if 'SkeletalMeshActor_' not in path:continue
                    try:values,observed=read_values_with_references(c,obj,fields=('CurrentAsset',))
                    except RuntimeQueryError as error:
                        # Rebuilding an authoring scene invalidates old animation
                        # instances. Report them rather than retrying identities.
                        if 'Object identity changed' not in str(error):raise
                        rows.append(dict(instance=path,stale=True));continue
                    rows.append(dict(instance=path,assets={k[1]:observed.path_name(v) if hasattr(v,'class_index') else v for k,v in values.values.items()},errors={k[1]:str(v) for k,v in values.errors.items()}))
                return rows
            def audio_components():
                from expedition33 import RuntimeQueryError
                from expedition33.catalog import capture_matching
                from expedition33.values import read_values_with_references
                c=capture_matching(session.pid,classes=('AudioComponent',));rows=[]
                for obj in sorted(c.select('AudioComponent'),key=lambda o:o.serial,reverse=True)[:16]:
                    if obj.object_flags&0x40000030:continue
                    try:values,observed=read_values_with_references(c,obj,fields=('Sound','VolumeMultiplier'))
                    except RuntimeQueryError:continue
                    row=dict(instance=c.path_name(obj),values={k[1]:observed.path_name(v) if hasattr(v,'class_index') else v for k,v in values.values.items()})
                    rows.append(row)
                return rows
            commands={
                'scene.audio_library':Command('inspect',lambda offset=0:dict(count=len(model.audio_paths or ()),offset=max(0,int(offset)),paths=(model.audio_paths or ())[max(0,int(offset)):max(0,int(offset))+32])),
                'scene.status':Command('inspect',lambda:record('status',model.status())),
                'scene.open':Command('editor',model.open),'scene.frame':Command('inspect',frame),
                'scene.document':Command('inspect',lambda:model.document),
                'scene.reference_cast':Command('editor',reference_cast),'scene.reference_pose':Command('editor',reference_pose),
                'scene.edit_clip':Command('editor',model.queue_timeline_edit),'scene.audio_components':Command('inspect',audio_components),
                'scene.click':Command('editor',click),'scene.field':Command('editor',field),
                'scene.stop':Command('editor',model.stop),'scene.snapshot':Command('inspect',snapshot),'scene.animations':Command('inspect',animations),
                'scene.timeline':Command('editor',model.toggle_timeline),'scene.author':Command('editor',author),'scene.audition':Command('editor',audition),'scene.seek':Command('editor',seek),
                'sdk.shutdown':Command('lifecycle',shutdown)}
            with_server=CommandServer(commands,capabilities={'inspect','editor','lifecycle'},queue_timeout=60)
            try:
                connection=with_server.write_connection(ROOT/'settings/SceneEditor/controller')
                (output/'connection-path.txt').write_text(str(connection),encoding='utf8')
                record('ready',dict(pid=session.pid,version=args.version,connection_path=str(connection)))
                model.open()
                previous=None
                while not loader.stop_requested:
                    with_server.poll()
                    try:loader.poll()
                    except BaseException:
                        logging.exception('Scene Editor poll failed');raise
                    current=model.status();key=(current['playback'].get('state'),current['playback'].get('error'),current['message'])
                    if key!=previous:record('state',current);previous=key
                    time.sleep(.01)
            except TargetExitedError:record('game_exited',True)
            finally:with_server.close();model.stop();record('closed',model.status())
    finally:sdk.SessionTransport=original;lock.close()

if __name__=='__main__':main()
