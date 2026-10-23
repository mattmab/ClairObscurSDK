"""Experimental E33 world geometry builder. Paired native adapter required."""
import ctypes
import json
import logging
import math
from pathlib import Path
import secrets
import struct
import time
from contextlib import contextmanager
from expedition33.catalog import capture_matching
from expedition33.values import read_values_with_references
from expedition33._reader import ReadBatch, active_reader
from expedition33.management import Action, Keybind, ModDefinition

LOG = logging.getLogger('expedition33.world_builder')
FUNCTIONS = json.loads(Path(__file__).with_name('functions.json').read_text())


def input_motion(keys, dt):
    if 18 in keys and 90 in keys:
        return [0.]*8
    dt = max(0., min(.1, dt))
    forward = int(87 in keys) - int(83 in keys)
    right = int(68 in keys) - int(65 in keys)
    up = int(32 in keys or 69 in keys) - int(17 in keys or 81 in keys)
    speed = 1600. * dt * (4 if 16 in keys else 1)
    scale = speed / max(1., math.sqrt(forward**2 + right**2 + up**2))
    fine = 150. * dt * (.1 if 18 in keys else 1)
    return [forward * scale, right * scale, up * scale, int(1 in keys),
            (int(104 in keys) - int(98 in keys)) * fine,
            (int(102 in keys) - int(100 in keys)) * fine,
            (int(105 in keys) - int(99 in keys)) * fine,
            (int(103 in keys) - int(97 in keys)) * fine * .1]


def discover(pid):
    with ReadBatch(pid):
        names = tuple(f.split('.')[1] for f in FUNCTIONS) + (
            'Default__GameplayStatics', 'Default__KismetSystemLibrary',
            'CameraActor', 'Pawn','StaticMeshComponent','Default__WidgetLayoutLibrary','M_DebugEmissive1','SceneCapture2D','Default__KismetRenderingLibrary','StaticMeshActor','StaticMesh','Actor','PointLight','Cube','PrimitiveComponent')
        c = capture_matching(pid, names=tuple(dict.fromkeys(names)), classes=('PlayerController',))
        local = []
        for pc in c.select('PlayerController'):
            if pc.object_flags & 0x30:
                continue
            v, c = read_values_with_references(c, pc, fields=(
                'bIsLocalPlayerController', 'Pawn', 'PlayerCameraManager'))
            values = {k[1]: x for k, x in v.values.items()}
            if values.get('bIsLocalPlayerController') is True:
                local.append((pc, values))
        if len(local) != 1:
            raise RuntimeError('Load a save and use an exploration character first.')
        pc, values = local[0]
        pawn = values.get('Pawn')
        if pawn is None or pawn.class_name not in (
                'BP_jRPG_Character_World_C', 'BP_jRPG_Character_WorldMap_pawn_C'):
            raise RuntimeError('Builder requires an unmounted exploration character.')
        v, c = read_values_with_references(c, pawn, fields=('CharacterMovement',))
        movement = next(x for k, x in v.values.items() if k[1] == 'CharacterMovement')
        def one(name):
            rows = [o for o in c.objects if o.name == name]
            if len(rows) != 1:
                raise RuntimeError('Missing or ambiguous prerequisite: ' + name)
            return rows[0]
        ids = [pc, pawn, movement, values['PlayerCameraManager'],
               one('Default__GameplayStatics'), one('Default__KismetSystemLibrary'),
               c.by_index[c.find_class('CameraActor').index],
               c.by_index[c.find_class('Pawn').index]]
        ids += [c.find_path('/Script/' + ('UMG.' if f.split('.')[0] in ('CanvasPanelSlot','Widget','TextBlock','WidgetLayoutLibrary','Border') else 'Engine.') + f.replace('.', ':')) for f in FUNCTIONS]
        extra_functions = ids[49:]
        ids = ids[:49] + [None] * (128-49)
        ids[64:79] = extra_functions[:15]
        ids[96:96+len(extra_functions[15:])] = extra_functions[15:]
        ids[87]=c.by_index[c.find_class('PointLight').index]
        ids[88]=c.find_path('/Engine/BasicShapes/Cube.Cube')
        ids[89]=c.by_index[c.find_class('PrimitiveComponent').index]
        ids[80] = c.by_index[c.find_class('SceneCapture2D').index]
        ids[83] = one('Default__KismetRenderingLibrary')
        for slot,name in ((84,'StaticMeshActor'),(85,'StaticMesh'),(86,'Actor')):ids[slot]=c.by_index[c.find_class(name).index]
        ids[62] = ids[48]  # Deprojection function; slot 48 belongs to the HUD below.
        ids[63] = c.by_index[c.find_class('StaticMeshComponent').index]
        ids[58] = one('Default__WidgetLayoutLibrary')
        ids[59] = c.find_path('/Game/LevelTools/FreeAimTargets/M_DebugEmissive1.M_DebugEmissive1')
        return ids


class Mod:
    def __init__(self):
        self.session = None
        self.owner = secrets.randbits(64) or 1
        self.active = False
        self.last = {}
        self.error = None
        self.held = set()
        self.clock = time.monotonic()
        self.started = False
        self.dragging = False
        self.hud = None
        self.help_minimized = False
        self.hud_hidden = False
        self.next_status = 0.
        self.catalog_menu = None
        self.prewarm_at = time.monotonic()+3
        self.booth_pending=False
        self._catalog_selection=None
        self.pending_catalog_asset=None
        self._menu_reader=None
        self._loading_ui=None

    def prepare_loading_ui(self,session):
        from .loading_ui import LoadingUI
        self._loading_ui=LoadingUI(self,session)
        return self._loading_ui

    @contextmanager
    def menu_reads(self):
        current=active_reader()
        if current is not None:
            current._check()
            if current.pid!=self.session.pid:raise RuntimeError('Menu reader belongs to another process')
            yield current
        else:
            # A failed batch remains terminal, but must not poison every later
            # hotkey. Replace it only at an operation boundary, never replaying
            # the failed body (which may already have changed widgets).
            if self._menu_reader is not None and self._menu_reader._closed:
                self._menu_reader=None
                self._reader_recovery_pending=True
            if self._menu_reader is None:self._menu_reader=ReadBatch(self.session.pid,share=True)
            worker=self._menu_reader
            try:
                with worker.bind() as reader:yield reader
            except BaseException:
                if worker._closed:
                    self._menu_reader=None
                    self._reader_recovery_pending=True
                raise
            else:
                if getattr(self,'_reader_recovery_pending',False):
                    self._reader_recovery_pending=False
                    self.next_status=0.
                    if self.error and ('Read worker' in self.error or 'Read batch' in self.error):self.error=None

    def toggle_help(self, _=None):
        if not self.active:return
        self.help_minimized = not self.help_minimized
        if self.hud is not None:
            with self.menu_reads():self.hud.show_help(self.help_minimized)

    def toggle_hud(self, _=None):
        if not self.active or self.hud is None:return
        hidden = not self.hud_hidden
        with self.menu_reads():self.hud.set_hidden(hidden)
        self.hud_hidden = hidden

    def management(self):
        return ModDefinition('e33.world-builder', 'World Builder', version='0.32.4-experimental',
            description='F8 freecam. WASD fly, mouse look, Space/Ctrl up/down (E/Q also work), Shift faster. Hold left mouse to grab a world prop; release to place. Numpad 8/2 forward/back, 4/6 left/right, 9/3 up/down, 7/1 yaw; Alt precise; Alt+Z undo. F9 restores edits and clears spawned props. F7 opens folders, previews, spawning, galleries and saved maps.',
            actions=(Action('catalog', 'Open asset catalog', self.open_catalog),Action('toggle', 'Enter / leave builder camera', self.toggle),
                     Action('restore', 'Restore all edited geometry', self.restore),
                     Action('undo', 'Undo last prop edit', self.undo),
                     Action('status', 'Builder status', self.status),
                     Action('ai_export','Export for AI',lambda _:self.ai.export(reveal=True)),
                     Action('ai_import','Import AI Scene',lambda _:self.ai.choose_import())),
            keybinds=(Keybind('toggle_help','Minimize / expand builder help','F1',self.toggle_help),Keybind('region_point1','Region corner 1 at camera','F3',lambda _:self.templates.mark(1)),Keybind('region_point2','Region corner 2 at camera','F4',self.region_corner2),Keybind('directional','Open live duplication for selected prop','F5',self.open_directional),Keybind('catalog', 'Open asset catalog', 'F7', self.open_catalog),Keybind('toggle', 'Toggle builder camera', 'F8', self.toggle),
                      Keybind('play_from_camera', 'Play from camera', 'F6', self.play_from_camera),
                      Keybind('hide_hud', 'Hide / show World Builder HUD', 'H', self.toggle_hud),
                      Keybind('restore', 'Restore all geometry edits', 'F9', self.restore),
                      Keybind('duplicate_to_hand','Duplicate selected prop to hand','F10',self.duplicate_to_hand),
                      Keybind('delete_selection','Delete Current Selection','Delete',self.delete_selection)))

    def enable(self, session):
        self.session = session
        self._retirement_result=self._native_retirement=None
        self.active=self.started=self.booth_pending=False
        from .library import Library
        if self._loading_ui is not None:
            if self._loading_ui.bound is None:
                raise RuntimeError('World Builder loading UI has not completed its controller handoff')
            self.catalog_menu=self._loading_ui.catalog;self.hud=self._loading_ui.hud
            self.library._catalog=None;self.library.actors_indexed=False
        else:self.library = Library(self)
        from .directional import DuplicationDraft
        self.directional=DuplicationDraft(self.library)
        from .templates import Templates
        self.templates=Templates(self.library)
        from .ai_scene import AIWorkflow
        self.ai=AIWorkflow(self.library)
        self.current_selection='None'
        from .camera_settings import CameraSettings
        self.camera_settings=CameraSettings(self.library.store.root.parent)
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.GetAsyncKeyState.restype = ctypes.c_short
        self.user32.GetForegroundWindow.restype = ctypes.c_void_p
        self.user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        session.actions.register('world_builder.template_status',self.templates.status,mutates=False)
        session.actions.register('world_builder.template_corner',self.templates.mark,schema={'type':'object','properties':{'number':{'type':'integer'}},'required':['number'],'additionalProperties':False})
        session.actions.register('world_builder.template_save',self.templates.save,schema={'type':'object','properties':{'name':{'type':'string'}},'required':['name'],'additionalProperties':False})
        session.actions.register('world_builder.templates',self.templates.store.list,mutates=False)
        session.actions.register('world_builder.ai_export',self.ai.export)
        session.actions.register('world_builder.ai_status',self.ai.status,mutates=False)
        session.actions.register('world_builder.ai_import',self.ai.import_file,schema={'type':'object','properties':{'path':{'type':'string'}},'required':['path'],'additionalProperties':False})
        session.actions.register('world_builder.toggle', self.toggle)
        session.actions.register('world_builder.stop', self.stop)
        session.actions.register('world_builder.restore', self.restore)
        session.actions.register('world_builder.play_from_camera',self.play_from_camera)
        session.actions.register('world_builder.duplicate_to_hand',self.duplicate_to_hand)
        session.actions.register('world_builder.delete_selection',self.delete_selection)
        session.actions.register('world_builder.open_directional',self.open_directional)
        session.actions.register('world_builder.pick', self.pick)
        session.actions.register('world_builder.undo', self.undo)
        session.actions.register('world_builder.redo', self.redo)
        session.actions.register('world_builder.automatic', self.automatic, schema={'type':'object','properties':{'enabled':{'type':'boolean'}},'required':['enabled'],'additionalProperties':False})
        session.actions.register('world_builder.status', self.status, mutates=False)
        session.actions.register('world_builder.step', self.step,
            schema={'type': 'object', 'properties': {'values': {'type': 'array'}}, 'required': ['values'], 'additionalProperties': False})
        session.actions.register('world_builder.open_catalog', self.open_catalog)
        session.actions.register('world_builder.recapture_thumbnail',self.recapture_thumbnail,schema={'type':'object','properties':{'asset':{'type':'string'}},'required':['asset'],'additionalProperties':False})
        session.actions.register('world_builder.background_cache',self.background_cache,schema={'type':'object','properties':{'enabled':{'type':'boolean'},'mode':{'type':'string','enum':['idle','afk']}},'additionalProperties':False})
        session.actions.register('world_builder.menu_fields',self.menu_fields,schema={'type':'object','properties':{'first':{'type':'string'},'second':{'type':'string'},'search':{'type':'string'},'map_name':{'type':'string'}},'additionalProperties':False})
        session.actions.register('world_builder.menu_control',self.menu_control,schema={'type':'object','properties':{'index':{'type':'integer'}},'required':['index'],'additionalProperties':False})
        session.actions.register('world_builder.catalog', self.library.catalog, mutates=False, schema={'type':'object','properties':{'query':{'type':'string'},'kind':{'type':'string'},'offset':{'type':'integer'},'limit':{'type':'integer'}},'additionalProperties':False})
        session.actions.register('world_builder.spawn', self.library.spawn, schema={'type':'object','properties':{'asset':{'type':'string'},'transform':{'type':'array'}},'required':['asset'],'additionalProperties':False})
        session.actions.register('world_builder.save_map', self.library.save, schema={'type':'object','properties':{'name':{'type':'string'}},'additionalProperties':False})
        session.actions.register('world_builder.load_map', self.library.load, schema={'type':'object','properties':{'map_id':{'type':'string'}},'required':['map_id'],'additionalProperties':False})
        session.actions.register('world_builder.maps', self.library.store.list, mutates=False)
        session.actions.register('world_builder.clear_scene', self.library.clear)
        session.actions.register('world_builder.preview',self.start_booth,schema={'type':'object','properties':{'asset':{'type':'string'}},'required':['asset'],'additionalProperties':False})
        session.actions.register('world_builder.preview_close',self.end_booth)
        session.actions.register('world_builder.preview_motion',self.booth_motion,schema={'type':'object','properties':{'values':{'type':'array'}},'required':['values'],'additionalProperties':False})
        session.console.expose('world_builder', self)

    def command(self, op, ids=(), values=(), automatic=False, transform=None, registry_offset=0,thumbnail_key=None,thumbnail_stage=0,asset_path=None,bulk=None,region=None):
        packet = bytearray(20984)
        struct.pack_into('<4IQ', packet, 0, 3, op, 0, 0, self.owner)
        if op == 28: struct.pack_into('<I',packet,20976,int(automatic))
        for i, obj in enumerate(ids):
            if obj is None: continue
            struct.pack_into('<iiQ', packet, 88 + 16*i, obj.index, obj.serial, obj.address)
        if transform is not None:struct.pack_into('<12d',packet,2000,*transform)
        if op in (37,38,48):
            if not isinstance(thumbnail_key,str) or len(thumbnail_key)!=64 or any(c not in '0123456789abcdef' for c in thumbnail_key):raise ValueError('Invalid thumbnail key')
            struct.pack_into('<I',packet,2000,thumbnail_stage);packet[2004:2068]=thumbnail_key.encode('ascii')
        if op==47:
            encoded=asset_path.encode('ascii')
            if not 1<=len(encoded)<512:raise ValueError('Invalid thumbnail asset path')
            packet[2000:2000+len(encoded)]=encoded
        if op in (35,51):struct.pack_into('<I',packet,2000,registry_offset)
        if op==65:
            if not bulk or len(bulk)>64 or region is None:raise ValueError('Expected a bounded region batch')
            low,high,instance=region
            struct.pack_into('<II',packet,2000,len(bulk),instance)
            struct.pack_into('<6d',packet,2016,*low,*high)
            for i,obj in enumerate(bulk):struct.pack_into('<iiQ',packet,4096+16*i,obj.index,obj.serial,obj.address)
        if op==50:
            if not bulk or len(bulk)>64:raise ValueError('Expected 1â€“64 spawn rows')
            struct.pack_into('<I',packet,2000,len(bulk))
            for i,(index,flags,pose) in enumerate(bulk):struct.pack_into('<II12d',packet,4096+192*i,index,flags,*pose)
        if op==66:
            if not bulk or len(bulk)>128:raise ValueError('Expected 1-128 transform rows')
            struct.pack_into('<I',packet,2000,len(bulk))
            for i,(identity,pose) in enumerate(bulk):struct.pack_into('<iiQ12d',packet,4096+112*i,*identity,*pose)
        if op==53:
            if not bulk or len(bulk)>128:raise ValueError('Expected 1â€“128 deletion rows')
            struct.pack_into('<I',packet,2000,len(bulk))
            for i,identity in enumerate(bulk):struct.pack_into('<iiQ',packet,4096+16*i,*identity)
        if values:
            if len(values) != 8 or any(type(x) not in (int, float) or not math.isfinite(x) or abs(x) > (1e7 if op in (42,52) else 10000) for x in values):
                raise ValueError('Expected eight finite bounded motion values')
            struct.pack_into('<8d', packet, 2000, *values)
        with self.session._lease_context():
            reply = self.session._session._transport.command('mesh', bytes(packet))
        raw = bytes.fromhex(reply['mesh_packet'])
        if len(raw) != len(packet) or raw[:8] != packet[:8] or raw[16:24] != packet[16:24] or raw[88:3000] != packet[88:3000] or raw[3392:3400] != packet[3392:3400] or (raw[3544:3560] != packet[3544:3560] or raw[20480:] != packet[20480:] or (op not in (29,35,50,51,54,60,65) and raw[4096:20480] != packet[4096:20480])):
            raise RuntimeError('Builder acknowledgement mismatch; outcome uncertain')
        self.last_raw = raw
        _, _, error, state, _ = struct.unpack_from('<4IQ', raw)
        camera = struct.unpack_from('<iiQ', raw, 24)
        selected = struct.unpack_from('<iiQ', raw, 40)
        step, edits = struct.unpack_from('<II', raw, 80)
        self.last = dict(active=bool(state), camera_index=camera[0] if camera[2] else None,
                         selected_component_index=selected[0] if selected[2] else None,
                         position=list(struct.unpack_from('<3d', raw, 56)), edits=edits,
                         native_error=error, native_step=step)
        self.selected_identity=selected
        self.last['undo_revision']=struct.unpack_from('<I',raw,3388)[0]
        self.last['duplicate_requested']=bool(struct.unpack_from('<I',raw,3384)[0])
        self.last['carrying']=bool(struct.unpack_from('<I',raw,3380)[0])
        self.last['rotation']=list(struct.unpack_from('<3d',raw,3356))
        stats = struct.unpack_from('<8d',raw,3000)
        self.last.update(native_ticks=int(stats[0]), mean_tick_ms=stats[1], mean_work_ms=stats[2], max_work_ms=stats[3], tick_error=int(stats[4]), undo_count=int(stats[5]), hovered_component_index=int(stats[6]), dragging=bool(stats[7]), label=raw[3100:3356].split(b'\0')[0].decode('utf8',errors='replace'))
        axis,angle=struct.unpack_from('<2d',raw,4080)
        if axis not in (0.,1.,2.,3.,4.) or not math.isfinite(angle):raise RuntimeError('Invalid builder gesture status')
        self.last.update(rotation_axis={1:'Yaw',2:'Pitch',3:'Roll',4:'Scale'}.get(int(axis),''),rotation_angle=angle)
        self.last["ray_center_error_px"] = struct.unpack_from("<d",raw,3064)[0]
        self.last["gpu_diagnostics"] = list(struct.unpack_from("<12Q",raw,3400))
        sample_depth,latency,hits,ready_component,candidates,next_candidate = struct.unpack_from('<6d',raw,3496)
        self.last.update(gpu_sample_depth=sample_depth,gpu_latency_ms=latency,gpu_surface_hits=int(hits),gpu_result_component=int(ready_component),gpu_candidates=int(candidates),gpu_next_candidate=int(next_candidate))
        completed,pending,gpu_error = struct.unpack_from('<3d',raw,3072)
        self.last.update(gpu_completed=int(completed),gpu_pending=int(pending),gpu_error=int(gpu_error),gpu_ready=bool(struct.unpack_from('<I',raw,3096)[0]))
        booth=struct.unpack_from('<6d',raw,3600)
        self.last['selection_samples'] = [list(struct.unpack_from('<6d',raw,3696+48*i)) for i in range(8)]
        self.last['selection_diagnostics'] = dict(zip(('discovered_meshes','scan_index','collision_distance','query_limit','surface_limit','query_stale'), struct.unpack_from('<6d',raw,3648)))
        self.last.update(booth_active=bool(booth[0]),booth_distance=booth[1],booth_rotation=list(booth[2:5]),booth_lighting=int(booth[5]))
        if error:
            raise RuntimeError(f'Builder operation {op} rejected: error {error}, step {step}')
        if self.active and not state and self.catalog_menu is not None:
            self.catalog_menu.invalidate_native_images()
        self.active = bool(state)
        return self.status()

    def start_booth(self,asset):
        if not self.active:self.toggle()
        if self.booth_pending:self.end_booth(reopen=False)
        menu=self.catalog_menu
        if menu:menu.cancel_preview()
        self.library.clear_preview()
        pos=self.last['position'];result=self.library.spawn(asset,[0.,0.,0.,1.,pos[0],pos[1],pos[2]+100000.,0.,1.,1.,1.,0.])
        self.library.preview_key=result['id'];self.booth_pending=True
        try:
            with self.menu_reads():
                from expedition33.catalog import capture_selected
                row=self.library.owned[result['id']];c=capture_selected(self.session.pid,[tuple(row['actor'])]);actor=c.by_index[row['actor'][0]]
            self.scene_command(40,objects=(actor,))
            if menu and menu.state=='open':menu.hide()
            self.automatic(True)
        except Exception:
            self.end_booth(reopen=False);raise
        return self.status()
    def booth_motion(self,values):return self.command(44,values=values)
    def end_booth(self,_=None,reopen=True):
        if self.started:self.command(41)
        self.library.clear_preview();self.booth_pending=False
        if reopen and self.catalog_menu and self.catalog_menu.state=='built':
            with self.menu_reads():self.catalog_menu.paint();self.catalog_menu.open()
        return self.status()
    def play_from_camera(self,_=None):
        if self.booth_pending:raise ValueError('Exit the asset preview first')
        if not self.active:raise ValueError('Start the builder camera first')
        if self.catalog_menu and self.catalog_menu.state=='open':self.catalog_menu.hide()
        try:self.command(55)
        except RuntimeError:
            if self.last.get('native_error')==1959:raise ValueError('Character cannot fit here. Move the camera into open space and retry.') from None
            raise
        self.held.clear();self.dragging=False
        self.library.message='Playing from camera; character controls restored.'
        return self.status()

    def apply_camera_settings(self, values):
        from .camera_settings import validate
        values=validate(values)
        if self.active:self.command(56,values=[values['sensitivity'],values['fly_speed'],(2 if values['highlight']=='click' else int(values['highlight'])),int(values['duplicate_click']),0,0,0,0])
        return values

    def save_camera_settings(self, sensitivity, fly_speed, highlight, duplicate_click=None):
        if duplicate_click is None:duplicate_click=self.camera_settings.values.get('duplicate_click',False)
        values=self.apply_camera_settings(dict(sensitivity=sensitivity,fly_speed=fly_speed,highlight=highlight,duplicate_click=duplicate_click))
        self.camera_settings.save(values)
        self.library.message='Camera settings saved'
        return values

    def toggle_duplicate_click(self):
        values=dict(self.camera_settings.values)
        values['duplicate_click']=not values.get('duplicate_click',False)
        return self.save_camera_settings(**values)

    def sync_undone_copies(self):
        revision=self.last.get('undo_revision',0)
        if revision==getattr(self,'_undo_revision',0):return
        self.command(60)
        count=struct.unpack_from('<I',self.last_raw,3560)[0]
        if count>64:raise RuntimeError('Invalid duplicate undo history')
        if not hasattr(self,'_undone_records'):self._undone_records={}
        removed=set()
        for i in range(count):
            at=4096+i*56;event=struct.unpack_from('<Q',self.last_raw,at)[0]
            if event<=getattr(self,'_undo_revision',0):continue
            before=struct.unpack_from('<iiQ',self.last_raw,at+8)
            actor=struct.unpack_from('<iiQ',self.last_raw,at+24)
            component=struct.unpack_from('<iiQ',self.last_raw,at+40)
            if not actor[2]:
                for key,row in list(self.library.owned.items()):
                    if tuple(row['actor'])==before:
                        self._undone_records[before]=self.library.owned.pop(key);removed.add(key)
            else:
                row=self._undone_records.pop(before,None)
                if row is None:raise RuntimeError('Restored duplicate has no tracking record')
                row=dict(row,actor=actor,component=component)
                self.library.owned[row['id']]=row
                removed.discard(row['id'])
                self.library.selected=row['id']
                self.current_selection=row.get('asset','Prop').rsplit('.',1)[-1]
                self._catalog_selection=None
            self._undo_revision=event
        if self.library.selected in removed:
            self.library.selected=None
            self.current_selection='None'
            self._catalog_selection=None
            self.pending_catalog_asset=None
        menu=self.catalog_menu
        if menu:
            if menu.selected and menu.selected.get('id') in removed:menu.selected=None
            menu.signature=None
        # Match the bounded native history, retaining only recently undone records.
        while len(self._undone_records)>64:self._undone_records.pop(next(iter(self._undone_records)))

    def process_duplicate_click(self):
        if not self.last.get('duplicate_requested'):return
        try:self.duplicate_to_hand()
        except Exception as exc:
            self.library.message='Could not duplicate: '+str(exc)
            LOG.exception('Click duplication failed')
        finally:self.command(59)

    def open_directional(self,_=None):
        if not self.catalog_menu or self.catalog_menu.state!='open':self.open_catalog()
        with self.menu_reads():
            self.catalog_menu.open_directional()
            self.catalog_menu.paint()

    def sync_catalog_selection(self):
        identity=getattr(self,'selected_identity',None)
        if not identity or not identity[2] or identity==self._catalog_selection:return
        self._catalog_selection=identity
        from .camera_settings import selected_owned
        row=selected_owned(self.library.owned,identity)
        if row and row['id']!=self.library.preview_key:
            self.library.selected=row['id'];self.pending_catalog_asset=row['asset']
            self.current_selection=row['asset'].rsplit('.',1)[-1]
        else:
            from expedition33.catalog import capture_selected
            try:
                observed=capture_selected(self.session.pid,[identity])
                self.current_selection=observed.by_index[identity[0]].name
            except Exception:
                LOG.debug('Selected prop expired before its name could be read',exc_info=True)

    def refresh_menu_owner(self):
        menu=self.catalog_menu
        if menu is None:return
        # Discovery can race level streaming before construction has acquired
        # a player or any widgets. Release that empty owner and rebuild.
        if not hasattr(menu,'player') and menu.widget is None:
            if not menu.close():raise RuntimeError('Previous menu cleanup is still pending')
            self.catalog_menu=None
            return
        with self.menu_reads():
            current=capture_matching(self.session.pid,classes=('PlayerController',))
            player=next(o for o in current.select('PlayerController') if not o.object_flags&0x30)
        identity=lambda o:(o.index,o.serial,o.address)
        if identity(player)==identity(menu.player):return
        # The leased widget tree survives travel, but its owning controller
        # does not. Dispose only through the normal acknowledged cleanup path.
        LOG.info('World Builder menu owner changed after travel; rebuilding')
        if not menu.close():raise RuntimeError('Previous menu cleanup is still pending')
        self.catalog_menu=None
        self.library._catalog=None;self.library.rows=[];self.library.known={}
        self.library.registry_names_ready=False;self.library.loader_metadata=[]
        self.library.actors_indexed=False
        if not self.last.get('edits'):
            self.library.owned.clear();self.library.selected=None;self.library.preview_key=None
            self.library.active_map=None;self.library.world=None

    def region_corner2(self, _=None):
        if self.active:return self.templates.mark(2)
        overlay=self.session._session.console.dispatcher.namespace.get('map_overlays')
        if overlay is not None and overlay.session is not None:return overlay.open_menu()
        raise ValueError('Enter the builder camera with F8 to mark corners')

    def open_catalog(self,_=None):
        escape=False
        if self.started:
            self.command(64)
            escape=bool(struct.unpack_from('<I',self.last_raw,3560)[0])
        if self.booth_pending:self.end_booth();return {'open':True}
        if not self.active:self.toggle()
        self.refresh_menu_owner()
        from .catalog_menu import CatalogMenu
        building = self.catalog_menu is None and self.hud is not None
        if building:
            with self.menu_reads():self.hud.show_building(True)
        try:
            if self.catalog_menu is None:
                self.catalog_menu=CatalogMenu(self)
                with self.menu_reads():self.catalog_menu.build()
            if self.catalog_menu.state=='open' and (escape or self.catalog_menu.workspace=='Build'):self.catalog_menu.hide()
            else:
                self.command(26);self.sync_catalog_selection()
                with self.menu_reads():
                    if self.catalog_menu.workspace!='Build':
                        self.directional.cancel()
                        self.catalog_menu.click(24)
                    if self.pending_catalog_asset:
                        self.catalog_menu.focus_asset(self.pending_catalog_asset);self.pending_catalog_asset=None
                    self.catalog_menu.paint()
                    if self.catalog_menu.state!='open':self.catalog_menu.open()
        finally:
            if building:
                with self.menu_reads():self.hud.show_building(False)
        return {'open':self.catalog_menu.state=='open'}

    def menu_fields(self,first=None,second=None,search=None,map_name=None):
        menu=self.catalog_menu
        if menu is None or menu.state!='open':raise ValueError('Open the catalog first')
        with self.menu_reads():
            for widget,value in ((menu.field1,first),(menu.field2,second),(menu.search,search),(menu.map_name,map_name)):
                if value is not None:
                    if len(value)>512:raise ValueError('Field is too long')
                    menu._render_call(widget,'EditableTextBox','SetText',InText=value)
            if search is not None:menu.query=search;menu.offset=0;menu.selected=None;menu.paint()
        return self.menu_control(-1)
    def menu_control(self,index):
        menu=self.catalog_menu
        if menu is None or menu.state!='open':raise ValueError('Open the asset catalog first')
        if type(index) is not int or not -1<=index<len(menu.buttons):raise ValueError('Invalid menu control index')
        with self.menu_reads():
            if index>=0:menu.click(index)
        return dict(state=menu.state,workspace=menu.workspace,folder=menu.folder,rows=menu.rows,selected=menu.selected,message=self.library.message,thumbnails=len(menu.thumbnails),queued=len(menu.pending),gallery=dict(summary=menu.batch_gallery.summary(),owned=list(menu.batch_gallery.owned[:128]),owned_count=len(menu.batch_gallery.owned),queued=len(menu.batch_gallery.queue),paused=menu.batch_gallery.paused,failures=menu.batch_gallery.failures[:64],failure_count=len(menu.batch_gallery.failures)),library_assets=menu.library_assets,map_pending=menu.map_job is not None,capture_queued=len(menu.capture_queue),capture_paused=menu.capture_paused,cache_stats=dict(menu.cache_stats),background=menu.background.status())

    def scene_command(self,op,objects=(),transform=None):
        self.command(op,ids=objects,transform=transform)
        return self.last_raw

    def overlay_context(self):
        from .overlays import context
        return context(self)

    def load_overlay(self,map_id,expected):
        from .overlays import load
        return load(self,map_id,expected,discover)

    def toggle(self, _=None):
        if self.active:
            return self.stop()
        if self.catalog_menu is not None:self.catalog_menu.invalidate_native_images()
        with self.menu_reads():ids = discover(self.session.pid)
        from .hud import BuilderHUD
        same_player=self.hud is not None and self.hud.state=='built' and all(getattr(self.hud.player,k)==getattr(ids[0],k) for k in ('index','serial','address'))
        if not same_player:
            if self.hud is not None:self.hud.close()
            self.hud = BuilderHUD(self.session, self.help_minimized)
            with self.menu_reads():self.hud.build()
        self.hud.set_hidden(self.hud_hidden)
        self.hud._render_call(self.hud.widget,'UserWidget','AddToViewport',ZOrder=10000)
        ids[48:58] = [self.hud.widget,self.hud.title,*self.hud.slots,*self.hud.lines]
        ids[60:62] = self.hud.crosshair
        self.started = True
        try:
            result = self.command(20, ids=ids)
            self.apply_camera_settings(self.camera_settings.values)
        except Exception:
            # Adapter records each completed mutation for bounded cleanup.
            self.command(22)
            raise
        self.error = None
        self.next_status = 0.
        self.held = set()
        self.dragging = False
        self.clock = time.monotonic()
        LOG.info('Builder camera enabled: %s', result)
        return result

    def stop(self, _=None):
        if self.booth_pending:self.end_booth(reopen=False)
        if self.started:
            try:
                if self.catalog_menu is not None and self.catalog_menu.state in ("built","open"):
                    if self.catalog_menu.state=='open':self.catalog_menu.hide()
                    self.catalog_menu.clear_images(purge=True);self.catalog_menu.signature=None
            finally:
                # A failed image operation must not trap the player in freecam.
                self.command(22)
        self.active = False
        self.dragging = False
        self.held.clear()
        return self.status()

    def restore(self, _=None):
        if self.started:
            result=self.command(25)
            if hasattr(self,'library'):self.library.owned.clear()
            return result
        return self.status()

    def duplicate_to_hand(self,_=None):
        if not self.active or self.booth_pending:raise ValueError('Use the builder camera outside the asset preview')
        self.command(26)
        if self.last.get('carrying'):raise ValueError('Click to place the current copy first')
        from .camera_settings import selected_owned
        row=selected_owned(self.library.owned,getattr(self,'selected_identity',()))
        menu=self.catalog_menu
        if menu and menu.state=='open' and menu.workspace=='Library' and menu.selected:
            row=self.library.owned.get(menu.selected.get('id'))
        if not row or row['id']==self.library.preview_key:raise ValueError('Select a spawned scene or gallery prop first')
        from expedition33.catalog import capture_selected
        if row['kind']=='mesh':
            c=capture_selected(self.session.pid,[tuple(row['component'])]);source=c.by_index[row['component'][0]]
            raw=self.scene_command(57,objects=(source,))
            actor=struct.unpack_from('<iiQ',raw,3568);component=struct.unpack_from('<iiQ',raw,3584)
            if not actor[2] or not component[2]:raise RuntimeError('Duplicate identity missing; outcome uncertain')
            from .bulk import register
            result=register(self.library,row['asset'],actor,component)
        else:
            result=self.library.duplicate(row['id'])
            try:
                record=self.library.owned[result['id']]
                c=capture_selected(self.session.pid,[tuple(record['component'])])
                self.scene_command(58,objects=(c.by_index[record['component'][0]],))
            except Exception:
                self.library.delete(result['id']);raise
        if menu and menu.state=='open':menu.hide()
        self.library.message='Copy in hand. Fly to position, then click to place. F10 duplicates again.'
        return dict(result,carrying=True)

    def delete_selection(self,_=None):
        if not self.active or self.booth_pending:
            raise ValueError('Use the builder camera outside the asset preview')
        self.command(26)
        from .camera_settings import selected_owned
        row=selected_owned(self.library.owned,getattr(self,'selected_identity',()) or ())
        if not row or row['id']==self.library.preview_key or row.get('duplication_preview'):
            raise ValueError('Select a spawned scene or gallery prop first')
        key=row['id']
        draft=getattr(self,'directional',None)
        if draft and draft.source and draft.source['id']==key: draft.cancel()
        from types import SimpleNamespace
        actor=SimpleNamespace(**dict(zip(('index','serial','address'),row['actor'])))
        self.command(63,ids=(actor,))
        self.sync_undone_copies()
        if self.library.selected==key:self.library.selected=None
        menu=self.catalog_menu
        if menu:
            if menu.selected and menu.selected.get('id')==key:menu.selected=None
            menu.signature=None
        self.current_selection='None'
        self._catalog_selection=None
        self.pending_catalog_asset=None
        self.selected_identity=()
        self.dragging=False
        self.library.message='Deleted selected prop. Alt+Z restores it; Alt+Y deletes it again.'
        return dict(deleted=key)

    def pick(self, _=None):
        return self.command(23)

    def step(self, values):
        return self.command(21, values=values)

    def undo(self, _=None):
        self.command(27)
        self.sync_undone_copies()
        return self.status()

    def redo(self, _=None):
        self.command(61)
        self.sync_undone_copies()
        return self.status()

    def automatic(self, enabled):
        return self.command(28, automatic=enabled)

    def status(self, _=None):
        return dict(self.last, active=self.active, error=self.error)

    def recapture_thumbnail(self,asset):
        if not self.active or not self.catalog_menu or self.booth_pending:raise ValueError('Open the builder catalog first')
        menu=self.catalog_menu;menu.cancel_preview();menu.collect_processing(wait=True)
        with self.menu_reads():self.library.thumbnail_preview(asset)
        menu.background.set_enabled(True);menu.background.current=asset
        from . import thumbnail_cache as cache
        menu.preview_job=dict(asset=asset,key=cache.thumbnail_key(asset),stage=0,ready=time.monotonic()+.05,background=True,created=time.monotonic())
        return dict(asset=asset,key=menu.preview_job['key'])

    def background_cache(self,enabled=None,mode=None):
        if self.catalog_menu is None:raise ValueError('Wait for catalog initialization')
        bg=self.catalog_menu.background
        if mode is not None:bg.set_mode(mode)
        if enabled is not None:
            bg.set_enabled(enabled)
            if not enabled and (not self.catalog_menu.preview_job or self.catalog_menu.preview_job.get('background')):self.catalog_menu.cancel_preview()
        return dict(bg.status(),readback=dict(self.catalog_menu.cache_stats),profile=self.library.profile,input=getattr(self,'_thumbnail_busy',{}))

    def thumbnail_input_busy(self):
        cursor=(ctypes.c_long*2)()
        self.user32.GetCursorPos(ctypes.byref(cursor))
        foreground_pid=ctypes.c_ulong()
        self.user32.GetWindowThreadProcessId(self.user32.GetForegroundWindow(),ctypes.byref(foreground_pid))
        foreground=foreground_pid.value==self.session.pid
        if not foreground:cursor=(0,0)
        sample=(*cursor,*self.last.get('position',()))
        prior=getattr(self,'_thumbnail_input',None)
        moved=prior is None or len(prior)!=len(sample) or any(abs(a-b)>(3 if i<2 else .5) for i,(a,b) in enumerate(zip(sample,prior)))
        if moved:self._thumbnail_input=sample
        keys=(1,2,4,16,17,18,27,*range(32,91),*range(96,124))
        held=[k for k in keys if self.user32.GetAsyncKeyState(k)&0x8000] if foreground else []
        self._thumbnail_busy=dict(moved=moved,held=held,foreground=foreground,dragging=self.last.get('dragging',False))
        return moved or self.last.get('dragging',False) or bool(held)

    def poll(self):
        # Flight, picking, dragging and HUD all run natively once per game frame.
        # Python only reads diagnostics twice a second; other mods cannot throttle flight.
        now = time.monotonic()
        self.templates.poll()
        self.ai.poll()
        # Enabling from Mods leaves that menu focused. Wait until it closes;
        # preparing a second menu's focus plan while it owns input is rejected.
        menu_busy = any(menu.active for menu in self.session._session._menus)
        overlay=self.session._session.console.dispatcher.namespace.get('map_overlays')
        overlay_pending=bool(overlay and getattr(overlay,'startup_pending',lambda:False)())
        if self.catalog_menu is None and now>=self.prewarm_at and not menu_busy and not overlay_pending:
            self.prewarm_at=float('inf')
            try:
                from .catalog_menu import CatalogMenu
                self.catalog_menu=CatalogMenu(self)
                with self.menu_reads():
                    self.catalog_menu.build()
                    self.catalog_menu.prime_menu_plan()
                if self.hud is None:
                    from .hud import BuilderHUD
                    self.hud=BuilderHUD(self.session, self.help_minimized)
                    with self.menu_reads():self.hud.build()
            except Exception:
                LOG.exception('Catalog prewarm failed')
        if not self.started or now < self.next_status:
            return
        self.next_status = now + (.02 if self.catalog_menu and self.catalog_menu.state=='open' and self.catalog_menu.batch_gallery.queue and not self.catalog_menu.batch_gallery.paused else self.catalog_menu.background.poll_interval() if self.active and self.catalog_menu and not self.booth_pending else .5)
        if self.catalog_menu and self.catalog_menu.state=='open' and self.catalog_menu.image_queue:self.next_status=min(self.next_status,now+.02)
        if self.catalog_menu and self.catalog_menu.state=='open' and self.catalog_menu.workspace=='Bounds':self.next_status=min(self.next_status,now+.04)
        if self.active and self.camera_settings.values.get('duplicate_click',False):self.next_status=min(self.next_status,now+.05)
        if self.last.get('rotation_axis'):self.next_status=min(self.next_status,now+.05)
        try:
            self.command(26)
            self.sync_undone_copies()
            self.process_duplicate_click()
            self.sync_catalog_selection()
            if self.active and not self.booth_pending:
                self.directional.poll()
                if self.hud:self.hud.show_selection(self.current_selection,self.last.get('rotation_axis',''),self.last.get('rotation_angle',0.))
            if self.booth_pending and not self.last.get('booth_active'):self.end_booth()
            if self.catalog_menu is not None:
                with self.menu_reads():
                    self.catalog_menu.poll()
                    # AFK-only bounded burst avoids waiting through all SDK/menu
                    # polling between every capture stage. Game ticks continue.
                    deadline=time.monotonic()+.6
                    for _ in range(8):
                        bg=self.catalog_menu.background
                        if bg.mode!='afk' or not bg.enabled or self.booth_pending:break
                        if not bg.input(self.thumbnail_input_busy()):break
                        if time.monotonic()-bg.last_input<5. or time.monotonic()>=deadline:break
                        job=self.catalog_menu.preview_job
                        time.sleep(.01 if job and job.get('background') else .05)
                        self.catalog_menu.poll()
            if self.last.get('tick_error'):
                self.error = 'Native builder stopped: ' + str(self.last['tick_error'])
        except Exception as exc:
            self.error = str(exc)
            LOG.exception('Builder status failed')
            self.next_status = float('inf')

    def revoke_world(self,context):
        from .retirement import revoke
        revoke(self,context)

    def begin_world_retirement(self,context):
        return self.poll_world_retirement(context)

    def poll_world_retirement(self,context):
        from .retirement import poll
        return poll(self,context)

    def disable(self):
        failures=[]
        try:self.ai.close()
        except Exception as exc:failures.append(str(exc))
        try:self.templates.close()
        except Exception as exc:failures.append(str(exc))
        if self.catalog_menu is not None:
            try:self.catalog_menu.close()
            except Exception as exc:failures.append(str(exc))
            self.catalog_menu=None
        if self.started:
            try:self.stop();self.restore()
            except Exception as exc:failures.append(str(exc))
        if self.hud is not None:
            try:self.hud.close()
            except Exception as exc:failures.append(str(exc))
            self.hud=None
        self.session=None
        if self._menu_reader is not None:
            self._menu_reader.close();self._menu_reader=None
        if failures:raise RuntimeError('; '.join(failures))
