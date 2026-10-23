"""Camera-free, independently owned static props for gameplay map loaders."""
import secrets
import struct
from types import SimpleNamespace
from .catalog import capture_matching
from .values import read_values_with_references
from ._reader import ReadBatch
from ._scope import SessionScope

SIZE = 20984
FUNCTIONS = ('GameplayStatics.BeginDeferredActorSpawnFromClass',
             'GameplayStatics.FinishSpawningActor', 'Actor.K2_DestroyActor',
             'SceneComponent.SetMobility', 'Actor.K2_GetRootComponent',
             'SceneComponent.K2_GetComponentToWorld', 'SceneComponent.K2_SetWorldTransform',
             'Controller.K2_GetPawn', 'StaticMeshComponent.SetStaticMesh')


def validate_request(data):
    if type(data) is not bytes or len(data) != SIZE:
        raise ValueError('Map runtime packet size')
    version, op, error, state, owner = struct.unpack_from('<4IQ', data)
    if version != 3 or op not in (93, 94, 95, 96, 97) or error or state or not owner or any(data[24:88]):
        raise ValueError('Map runtime header')
    if op == 93:
        for at in range(88, 360, 16):
            i, s, a = struct.unpack_from('<iiQ', data, at)
            if i < 0 or s < 0 or not a:
                raise ValueError('Map runtime prerequisite identity')
        if any(data[360:]):
            raise ValueError('Map runtime initialization padding')
    elif op == 94:
        from .worldbuilder_maps import pose
        count = struct.unpack_from('<I', data, 2000)[0]
        if not 1 <= count <= 32 or any(data[88:2000]) or any(data[2004:4096]) or any(data[4096+128*count:]):
            raise ValueError('Map runtime batch bounds')
        for at in range(4096, 4096+128*count, 128):
            i, s, a = struct.unpack_from('<iiQ', data, at)
            if i < 0 or s < 0 or not a or any(data[at+112:at+128]):
                raise ValueError('Map runtime asset identity')
            pose(list(struct.unpack_from('<12d', data, at+16)))
    elif op == 97:
        import re
        path=data[2000:2512].split(b'\0',1)[0]
        if not re.fullmatch(rb'/Game/[A-Za-z0-9_/-]+\.[A-Za-z0-9_]+',path) or len(path)>=512 or any(data[88:2000]) or any(data[2000+len(path):]):
            raise ValueError('Map runtime static-mesh path')
    elif op == 95:
        if any(data[88:]):
            raise ValueError('Map runtime cleanup padding')
    elif any(data[88:2000]) or any(data[2004:]) or struct.unpack_from('<I', data, 2000)[0] >= 6000:
        raise ValueError('Map runtime snapshot index')


def context(scope):
    """Observe local exploration pawn and serial-checked world/visit identity."""
    with ReadBatch(scope.pid):
        c = capture_matching(scope.pid, classes=('PlayerController',))
        local = []
        for pc in c.select('PlayerController'):
            if pc.object_flags & 0x30:
                continue
            values, c = read_values_with_references(c, pc, fields=('Pawn', 'bIsLocalPlayerController'))
            values = {k[1]: v for k, v in values.values.items()}
            if values.get('bIsLocalPlayerController'):
                local.append((pc, values.get('Pawn')))
        if len(local) != 1 or local[0][1] is None:
            return None
        pc, pawn = local[0]
        obj = pawn
        for _ in range(32):
            if obj.class_name == 'World':
                return dict(world=c.path_name(obj), visit=[obj.index, obj.serial, obj.address],
                            pawn=[pawn.index, pawn.serial, pawn.address],
                            ready=pawn.class_name in ('BP_jRPG_Character_World_C', 'BP_jRPG_Character_WorldMap_pawn_C'))
            if obj.outer_index not in c.by_index:
                return None
            obj = c.by_index[obj.outer_index]
    return None


class MapRuntime:
    """One private native owner; scope/session shutdown also destroys its actors.

    Failed/unknown spawn dispatches are never replayed. The native owner tracks
    partial creations before finishing them, so cleanup includes failed rows.
    """
    def __init__(self, scope):
        scope._check()
        if getattr(scope._session._transport, 'map_runtime_protocol', 0) != 1:
            raise RuntimeError('Install the SDK map runtime candidate first')
        self.scope = scope
        self.owner = secrets.randbits(64) or 1
        self.started = False
        self.uncertain = False
        self.objects = {}
        self.visit = None
        scope._reference_owners.append(self)

    def _send(self, op, *, ids=(), rows=(), index=0, path=None):
        packet = bytearray(SIZE)
        struct.pack_into('<4IQ', packet, 0, 3, op, 0, 0, self.owner)
        for i, obj in enumerate(ids):
            struct.pack_into('<iiQ', packet, 88+16*i, obj.index, obj.serial, obj.address)
        if op == 94:
            struct.pack_into('<I', packet, 2000, len(rows))
            for i, (asset, transform) in enumerate(rows):
                struct.pack_into('<iiQ12d', packet, 4096+128*i, asset.index, asset.serial, asset.address, *transform)
        if op == 96:
            struct.pack_into('<I', packet, 2000, index)
        if op == 97:
            encoded=path.encode('ascii')
            if not 1<=len(encoded)<512:raise ValueError('Static-mesh path length')
            packet[2000:2000+len(encoded)]=encoded
        validate_request(bytes(packet))
        try:
            with self.scope._lease_context():
                reply = self.scope._session._transport.command('mesh', bytes(packet))
            raw = bytes.fromhex(reply['mesh_packet'])
            # Only header status, output counts and bounded per-row output may change.
            compare = bytearray(raw)
            compare[8:16] = packet[8:16]
            compare[80:84] = packet[80:84]
            compare[3560:3568] = packet[3560:3568]
            if op == 94:
                for i in range(len(rows)):
                    at = 4096+128*i+112
                    compare[at:at+16] = packet[at:at+16]
            elif op == 96:
                compare[4096:4208] = packet[4096:4208]
            elif op == 97:
                compare[4096:4112] = packet[4096:4112]
            if len(raw) != SIZE or compare != packet:
                raise RuntimeError('Map runtime acknowledgement mismatch; outcome uncertain')
        except Exception:
            self.uncertain = True
            raise
        error = struct.unpack_from('<I', raw, 8)[0]
        if error:
            if error == 2109:
                self.uncertain = True
            if op==97:
                reason={2111:'Missing registered static mesh',2112:'Asset load dispatch rejected',2113:'Missing or unsupported static mesh',2114:'Asset retention limit reached'}.get(error,'Static-mesh registry unavailable')
                raise RuntimeError(f'{reason}: {path} ({error}); not retried')
            raise RuntimeError(f'Map runtime operation {op} failed ({error}, step {struct.unpack_from("<I",raw,80)[0]}); not retried')
        return raw

    def _prepare(self, expected):
        if context(self.scope) != expected or not expected['ready']:
            raise RuntimeError('Exploration pawn or vanilla world changed')
        with ReadBatch(self.scope.pid):
            names = tuple(f.split('.')[1] for f in FUNCTIONS) + ('Default__GameplayStatics', 'StaticMeshActor','Default__StaticMesh','Default__KismetSystemLibrary','LoadAsset_Blocking')
            c = capture_matching(self.scope.pid, names=names, classes=('PlayerController',))
            def one(name):
                found = [o for o in c.objects if o.name == name]
                if len(found) != 1:
                    raise ValueError('Missing or ambiguous runtime prerequisite: '+name)
                return found[0]
            pc = next(o for o in c.select('PlayerController') if not o.object_flags & 0x30 and o.index >= 0)
            # Read the chosen controller again; native current() verifies exact pawn/world.
            v, c = read_values_with_references(c, pc, fields=('Pawn', 'bIsLocalPlayerController'))
            v = {k[1]: value for k, value in v.values.items()}
            if not v.get('bIsLocalPlayerController'):
                raise ValueError('Runtime controller is not local')
            pawn = v['Pawn']; world = c.by_index[expected['visit'][0]]
            ids = [pc, pawn, world, one('Default__GameplayStatics'), c.find_path('/Script/Engine.StaticMeshActor'), c.by_index[one('Default__StaticMesh').class_index]]
            ids += [c.find_path('/Script/Engine.'+f.replace('.', ':')) for f in FUNCTIONS]
            ids += [one('Default__KismetSystemLibrary'),c.find_path('/Script/Engine.KismetSystemLibrary:LoadAsset_Blocking')]
        self.started = True  # Also close after a partial or rejected initialization.
        self._send(93, ids=ids)
        self.visit = expected['visit']

    def load(self, data, expected):
        from .worldbuilder_maps import validate
        data = validate(data, expected['world'])
        rows = [r for r in data['objects'] if r['kind'] != 'world_edit']
        if any(r['kind'] != 'mesh' or r.get('component_edits') for r in rows):
            raise ValueError('Version 1 supports static-mesh props without component edits; unsupported actor types were not spawned')
        if self.started or self.uncertain:
            raise RuntimeError('Unload the current map before loading again')
        if not rows:
            return dict(objects=0,skipped_world_edits=len(data['objects']))
        assets = {}
        load_scope = SessionScope(self.scope)
        try:
            self._prepare(expected)
            # Resolve registered FNames natively, including numbered names.
            # Every asset is retained and validated before any actor is created.
            for path in dict.fromkeys(r['asset'] for r in rows):
                if path.startswith('/Engine/'):
                    with ReadBatch(self.scope.pid):
                        c = capture_matching(self.scope.pid,names=(path.rsplit('.',1)[-1],'Default__GameplayStatics'))
                        mesh = c.find_path(path)
                    if mesh.class_name != 'StaticMesh':raise ValueError('Unsupported engine asset: '+path)
                    load_scope.retain(mesh)
                else:
                    raw = self._send(97,path=path)
                    index,serial,address=struct.unpack_from('<iiQ',raw,4096)
                    if index<0 or serial<0 or not address:
                        self.uncertain=True
                        raise RuntimeError('Missing retained asset identity; not retried')
                    mesh=SimpleNamespace(index=index,serial=serial,address=address)
                assets[path]=mesh
                if len(assets)%16==0:
                    __import__('logging').getLogger(__name__).info('Map runtime asset preflight: %d ready',len(assets))
            at = 0
            while at < len(rows):
                # Native current() checks the exact pawn/world before every
                # spawn, including within a batch; no per-prop read subprocess.
                batch = rows[at:at+32]
                raw = self._send(94, rows=[(assets[r['asset']], r['transform']) for r in batch])
                done = struct.unpack_from('<I', raw, 3560)[0]
                if not 1 <= done <= len(batch):
                    self.uncertain = True
                    raise RuntimeError('Invalid runtime spawn progress; not retried')
                for i, r in enumerate(batch[:done]):
                    actor = struct.unpack_from('<iiQ', raw, 4096+128*i+112)
                    if not actor[2]:
                        self.uncertain = True
                        raise RuntimeError('Missing runtime actor identity')
                    self.objects[r['id']] = dict(asset=r['asset'], actor=actor, transform=r['transform'])
                at += done
            return dict(objects=len(rows), skipped_world_edits=len(data['objects'])-len(rows))
        except Exception:
            if self.started and not self.uncertain:
                self.close()
            raise
        finally:
            load_scope.close()

    def snapshot(self, index):
        raw = self._send(96, index=index)
        return dict(actor=struct.unpack_from('<iiQ', raw, 4096), transform=list(struct.unpack_from('<12d', raw, 4112)))

    def close(self):
        if self.uncertain:
            raise RuntimeError('Map runtime outcome uncertain; restart the SDK/game for native cleanup')
        if self.started:
            self._send(95)
            self.started = False
        self.objects.clear()
        self.visit = None
        return True
