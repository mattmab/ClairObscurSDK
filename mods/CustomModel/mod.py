"""Original textured OBJ demo using independent E33 SDK APIs. MIT."""
from pathlib import Path
import time
from expedition33.management import ModDefinition,Action
from expedition33._scope import SessionScope
from expedition33.procedural_mesh import Tetrahedron,discover
from expedition33.catalog import capture_matching
from .asset import load_obj

class Mod:
    def __init__(self):
        self.session=None;self.scope=None;self.model=None;self.last={};self.next_poll=0
    def management(self):
        return ModDefinition('sdk.custom-model','Custom Model — Supply Crate',version='0.1.0-experimental',
            description='Original textured OBJ supply crate. Requires mesh-v7 SDK candidate; not RC5. Spawn on foot; zone travel removes it.',
            actions=(Action('spawn','Spawn supply crate',lambda _:self.spawn()),
                     Action('destroy','Destroy supply crate',lambda _:self.destroy()),
                     Action('status','Model status',lambda _:self.status())))
    def enable(self,session):
        if getattr(session._session._transport,'mesh_protocol',0)!=3:
            raise RuntimeError('CustomModel requires the mesh-v7 SDK candidate; RC5 does not support imported geometry')
        self.session=session
        session.console.register('model',self.command,owner=self)
    def command(self,args):
        name=args.strip().lower()
        if name=='spawn':return self.spawn()
        if name=='destroy':return self.destroy()
        if name in ('','status'):return self.status()
        raise ValueError('model spawn | destroy | status')
    def spawn(self):
        if self.model and not self.model.closed:raise RuntimeError('Destroy the current crate first')
        root=Path(__file__).resolve().parent/'assets'
        geometry=load_obj(root/'supply-crate.obj')
        texture_path=(root/'supply-crate.png').resolve()
        png=texture_path.read_bytes()
        if len(png)>1024*1024 or png[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Texture format/size')
        self.scope=SessionScope(self.session,lease_owner='CustomModel')
        self.model=Tetrahedron(self.scope)
        try:
            self.model.spawn(geometry)
            names=('DefaultImagePlateMaterial','Default__KismetStringLibrary','Default__KismetRenderingLibrary',
                'ImportFileAsTexture2D','CreateDynamicMaterialInstance','SetTextureParameterValue','K2_GetTextureParameterValue','Conv_StringToName',
                'Texture2D','Texture','MaterialInterface','MaterialInstanceDynamic')
            c=capture_matching(self.session.pid,names=names,classes=('PlayerController','BP_jRPG_Character_WorldMap_pawn_C','BP_jRPG_Character_World_C'))
            self.model.set_image_plate_texture(c,texture_path)
            self.last=dict(state='spawned',vertices=len(geometry[0]),triangles=len(geometry[1])//3,textured=True,native=self.model.status())
            return self.last
        except BaseException as error:
            self.scope.close();self.scope=None;self.model=None
            self.last=dict(state='spawn-failed',error=str(error));raise
    def destroy(self):
        if self.scope:self.scope.close()
        self.scope=None;self.model=None;self.last=dict(state='destroyed')
        return self.last
    def status(self):
        return dict(self.last,native=self.model.status() if self.model else None)
    def poll(self):
        if not self.model or time.monotonic()<self.next_poll:return
        self.next_poll=time.monotonic()+.5
        if self.model.status()['state']==0:
            self.destroy();self.last=dict(state='retired-on-travel')
    def disable(self):
        self.destroy();self.session=None
