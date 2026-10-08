"""Independent Expedition 33 runtime research API.

Every objects() call invokes our native reader against the running game.
Returned values are observations, not durable UObject handles. Native class
metadata, stored boolean observations, a fixed reflected invocation and a scoped
native function observer are supported. The sdk submodule exposes persistent
sessions for the validated getter. The mods submodule provides a minimal trusted
local mod lifecycle. General invocation remains unimplemented.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from ._callbacks import CallbackDispatcher, CallbackFailure, ObservedIdentity, ObserverContext


class RuntimeQueryError(RuntimeError):
    """The native runtime query failed or returned an incomplete snapshot."""


@dataclass(frozen=True)
class ObjectSnapshot:
    pid: int
    index: int
    serial: int
    address: int
    name: str
    class_name: str
    metaclass_name: str
    class_index: int


@dataclass(frozen=True)
class PropertyMetadata:
    owner: str
    name: str
    type: str
    offset: int
    element_size: int
    dimension: int
    struct_name: str | None = None
    enum_name: str | None = None
    inner_type: str | None = None
    inner_element_size: int | None = None


@dataclass(frozen=True)
class ClassMetadata:
    pid: int
    name: str
    hierarchy: tuple[str, ...]
    sizes: tuple[int, ...]
    properties: tuple[PropertyMetadata, ...]


@dataclass(frozen=True)
class StoredBool:
    owner: str
    name: str
    element: int
    value: bool
    raw_byte: int
    mask: int
    byte_offset: int


@dataclass(frozen=True)
class BoolSnapshot:
    pid: int
    object_name: str
    class_name: str
    index: int
    serial: int
    values: tuple[StoredBool, ...]


@dataclass(frozen=True)
class FunctionParameter:
    name: str
    type: str
    offset: int
    element_size: int
    dimension: int
    flags: int
    bool_encoding: int | None


@dataclass(frozen=True)
class FunctionMetadata:
    pid: int
    game_thread_id: int
    owner: str
    name: str
    index: int
    flags: int
    params_size: int
    return_offset: int | None
    entry_rva: int
    parameters: tuple[FunctionParameter, ...]


@dataclass(frozen=True)
class InvocationProof:
    pid: int
    game_thread_id: int
    object_index: int
    function_index: int
    result: bool
    hook_removed: bool
    remote_module_unloaded: bool


@dataclass(frozen=True)
class ObserverProof:
    pid: int
    contexts: tuple[ObserverContext, ...]
    callback_failures: tuple[CallbackFailure, ...]
    entry_restored: bool
    module_resident: bool


def objects(*, limit: int = 0) -> list[ObjectSnapshot]:
    """Read current objects through our native bridge (0 = all occupied slots).

The reader validates this supported build, unique anchors, names and registry
relationships. It does not pin Unreal objects or provide a GC-atomic snapshot.
Do not retain addresses for later memory access.
"""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 100000000:
        raise ValueError('limit must be an integer from 0 to 100000000')
    start, samples = _query(['--limit', str(limit)])
    try:
        if any(row['event'] != 'object' for row in samples):
            raise ValueError('Unexpected metadata event')
        return [ObjectSnapshot(pid=start['pid'], index=row['index'], serial=row['serial'],
                               address=int(row['address'], 16), name=row['name'],
                               class_name=row['class_name'], metaclass_name=row['metaclass_name'],
                               class_index=row['class_index']) for row in samples]
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid object response: {error}') from error


def reflect_class(name: str) -> ClassMetadata:
    """Read a uniquely named native Class and inherited property metadata.

    This initial research path excludes BlueprintGeneratedClass and does not
    read property values, pin objects, or return callable engine handles.
    """
    if not isinstance(name, str) or not name or len(name) > 1023 or '\x00' in name:
        raise ValueError('name must be a nonempty native class name')
    start, samples = _query(['--reflect-class', name])
    try:
        objects_seen = [row for row in samples if row['event'] == 'object']
        classes = [row for row in samples if row['event'] == 'class_metadata']
        properties = [row for row in samples if row['event'] == 'property_metadata']
        if (len(objects_seen) != 1 or not classes or classes[0]['name'] != name or
                len(samples) != len(objects_seen) + len(classes) + len(properties)):
            raise ValueError('Incomplete reflection response')
        return ClassMetadata(start['pid'], name, tuple(row['name'] for row in classes),
                             tuple(row['size'] for row in classes),
                             tuple(PropertyMetadata(**{k: row[k] for k in
                                   ('owner', 'name', 'type', 'offset', 'element_size', 'dimension')},
                                   **{k: row.get(k) for k in
                                   ('struct_name', 'enum_name', 'inner_type', 'inner_element_size')})
                                   for row in properties))
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid reflection response: {error}') from error


def stored_bools(object_name: str) -> BoolSnapshot:
    """Observe stored BoolProperty values on a uniquely named native object.

    Reads backing storage, without calling custom getters or pinning objects.
    Values are individually checked observations, not an atomic object snapshot.
    """
    if not isinstance(object_name, str) or not object_name or len(object_name) > 1023 or '\x00' in object_name:
        raise ValueError('object_name must be a nonempty object name')
    start, samples = _query(['--read-bools', object_name])
    try:
        targets = [row for row in samples if row['event'] == 'object']
        if len(targets) != 1 or targets[0]['name'] != object_name:
            raise ValueError('Expected one matching native object')
        values = []
        keys = set()
        for row in samples:
            if row['event'] in ('object', 'class_metadata', 'property_metadata'):
                continue
            if row['event'] != 'stored_bool' or type(row['value']) is not bool:
                raise ValueError('Invalid stored boolean event')
            key = (row['owner'], row['name'], row['element'])
            if key in keys or not 0 < row['mask'] <= 255 or not 0 <= row['raw_byte'] <= 255:
                raise ValueError('Invalid boolean identity or encoding')
            if bool(row['raw_byte'] & row['mask']) != row['value']:
                raise ValueError('Boolean value disagrees with raw mask')
            keys.add(key)
            values.append(StoredBool(**{k: row[k] for k in
                          ('owner', 'name', 'element', 'value', 'raw_byte', 'mask', 'byte_offset')}))
        target = targets[0]
        return BoolSnapshot(start['pid'], object_name, target['class_name'], target['index'],
                            target['serial'], tuple(values))
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid stored boolean response: {error}') from error


def reflect_function(qualified_name: str) -> FunctionMetadata:
    """Inspect a live Function by owner and name, for example Actor.IsActorBeingDestroyed.

    Returns build-scoped metadata only. This API does not invoke game code.
    Duplicate owner/name matches fail rather than selecting an arbitrary object.
    """
    if (not isinstance(qualified_name, str) or '\x00' in qualified_name or
            len(qualified_name) > 2047 or '.' not in qualified_name):
        raise ValueError('qualified_name must have the form Owner.Function')
    owner, name = qualified_name.rsplit('.', 1)
    if not owner or not name:
        raise ValueError('qualified_name must have the form Owner.Function')
    start, samples = _query(['--reflect-function', qualified_name])
    try:
        objects_seen = [row for row in samples if row['event'] == 'object']
        functions = [row for row in samples if row['event'] == 'function_metadata']
        structs = [row for row in samples if row['event'] == 'struct_metadata']
        properties = [row for row in samples if row['event'] == 'property_metadata']
        if (len(objects_seen) != 1 or len(functions) != 1 or not structs or
                len(samples) != 1 + len(functions) + len(structs) + len(properties)):
            raise ValueError('Incomplete function response')
        target, fn = objects_seen[0], functions[0]
        if target['name'] != name or target['class_name'] != 'Function' or fn['owner'] != owner:
            raise ValueError('Function identity mismatch')
        if not 0 <= fn['params_size'] <= structs[0]['size']:
            raise ValueError('Parameter buffer exceeds struct size')
        return_offset = None if fn['return_offset'] == 65535 else fn['return_offset']
        if return_offset is not None and not 0 <= return_offset < fn['params_size']:
            raise ValueError('Return offset outside parameter buffer')
        parameters = []
        for p in properties:
            flags = int(p['flags'], 16)
            # Dispatcher iterates the initial fields while the low-byte sign bit
            # is set (141393330): this distinguishes parameter fields from locals.
            if not flags & 0x80:
                continue
            if not 0 <= p['offset'] < p['offset'] + p['element_size'] * p['dimension'] <= fn['params_size']:
                raise ValueError('Parameter extent outside parameter buffer')
            parameters.append(FunctionParameter(p['name'], p['type'], p['offset'],
                              p['element_size'], p['dimension'], flags,
                              int(p['bool_encoding'], 16) if 'bool_encoding' in p else None))
        return FunctionMetadata(start['pid'], start['game_thread_id'], owner, name, target['index'],
                                int(fn['flags'], 16), fn['params_size'], return_offset,
                                int(fn['entry_rva'], 16), tuple(parameters))
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid function metadata response: {error}') from error


def invoke_proof() -> InvocationProof:
    """Call Default__Actor.IsActorBeingDestroyed through reflected dispatch.

    This deliberately fixed research experiment temporarily attaches our native
    DLL to the verified game thread, validates the target and its parameter
    layout, invokes the reflected dispatcher, removes the scheduling hook and
    verifies DLL unload. It is not a general arbitrary function-call API.
    """
    start, samples = _query(['--invoke-proof'])
    try:
        objects_seen = [row for row in samples if row['event'] == 'object']
        invocations = [row for row in samples if row['event'] == 'fixed_invocation']
        if len(objects_seen) != 2 or len(invocations) != 1 or len(samples) != 3:
            raise ValueError('Incomplete invocation proof')
        targets = {row['name']: row for row in objects_seen}
        obj, fn = targets['Default__Actor'], targets['IsActorBeingDestroyed']
        result = invocations[0]
        if (obj['class_name'] != 'Actor' or fn['class_name'] != 'Function' or
                result['observed_pid'] != start['pid'] or result['observed_tid'] != start['game_thread_id'] or
                result['callbacks'] != 1 or type(result['result']) is not int or result['result'] not in (0, 1) or
                result['hook_removed'] is not True or result['remote_module_unloaded'] is not True):
            raise ValueError('Invocation identity, return or cleanup mismatch')
        return InvocationProof(start['pid'], start['game_thread_id'], obj['index'], fn['index'],
                               bool(result['result']), True, True)
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid invocation proof response: {error}') from error


def observe_proof(callback) -> ObserverProof:
    """Observe two real Default__Actor.IsActorBeingDestroyed calls.

    Native observation is scoped to this experiment and removed before Python
    delivery. The callback receives copied context on the caller's Python
    thread. A failing callback is disabled and recorded, not raised into game
    code. The native observer DLL remains inert until game exit for late-entry
    safety. This is not yet the persistent sdk.hook API.
    """
    if not callable(callback):
        raise TypeError('callback must be callable')
    start, samples = _query(['--observe-proof'])
    try:
        objects_seen = [row for row in samples if row['event'] == 'object']
        observed = [row for row in samples if row['event'] == 'observed_getter']
        proofs = [row for row in samples if row['event'] == 'observer_proof']
        if len(objects_seen) != 2 or len(observed) != 2 or len(proofs) != 1 or len(samples) != 5:
            raise ValueError('Incomplete observer response')
        targets = {row['name']: row for row in objects_seen}
        obj, fn = targets['Default__Actor'], targets['IsActorBeingDestroyed']
        proof = proofs[0]
        if (obj['class_name'] != 'Actor' or fn['class_name'] != 'Function' or
                any(proof[k] is not True for k in ('entry_restored', 'scheduling_hook_removed', 'module_resident')) or
                proof['events'] != 2 or proof['after_remove_count'] != 2 or proof['dropped'] != 0):
            raise ValueError('Observer identity or restoration mismatch')
        contexts = []
        identity = ObservedIdentity(start['pid'], obj['index'], obj['serial'], obj['name'], obj['class_name'])
        for sequence, row in enumerate(observed, 1):
            if (row['sequence'] != sequence or row['object_index'] != obj['index'] or
                    row['object_serial'] != obj['serial'] or int(row['object_address'], 16) != int(obj['address'], 16) or
                    row['thread'] != start['game_thread_id'] or type(row['result']) is not int or row['result'] not in (0, 1)):
                raise ValueError('Observer event does not match the validated object')
            contexts.append(ObserverContext(sequence, 'Actor.IsActorBeingDestroyed', identity,
                                            row['thread'], bool(row['result'])))
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid observer proof response: {error}') from error
    dispatcher = CallbackDispatcher()
    dispatcher.subscribe('Actor.IsActorBeingDestroyed', callback)
    try:
        for context in contexts:
            dispatcher.deliver(context)
        return ObserverProof(start['pid'], tuple(contexts), dispatcher.failures(), True, True)
    finally:
        dispatcher.close()


def _query(arguments: list[str]) -> tuple[dict, list[dict]]:
    root = Path(__file__).resolve().parents[2]
    executable = root / 'build' / 'research-probe' / 'research_probe.exe'
    if not executable.is_file():
        raise RuntimeQueryError(f'Native bridge missing: run {root / "scripts" / "build-research-probe.cmd"}')
    try:
        result = subprocess.run([str(executable), *arguments],
                                capture_output=True, encoding='utf-8', errors='strict',
                                timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
        raise RuntimeQueryError(f'Native bridge execution failed: {error}') from error
    if result.returncode:
        raise RuntimeQueryError(f'Native bridge rejected query: {result.stderr.strip()}')
    try:
        records = [json.loads(line) for line in result.stdout.splitlines()]
        start, end = records[0], records[-1]
        if start['event'] != 'snapshot_start' or end['event'] != 'snapshot_end':
            raise ValueError('Missing snapshot boundary')
        samples = records[1:-1]
        object_rows = [row for row in samples if row['event'] == 'object']
        if end['emitted'] != len(object_rows):
            raise ValueError('Invalid object count or event')
        if len({row['index'] for row in object_rows}) != len(object_rows):
            raise ValueError('Duplicate object indices')
        return start, samples
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid native bridge response: {error}') from error


__all__ = ['objects', 'reflect_class', 'stored_bools', 'reflect_function', 'invoke_proof', 'observe_proof', 'ObserverProof', 'ObserverContext', 'ObjectSnapshot', 'ClassMetadata',
           'PropertyMetadata', 'StoredBool', 'BoolSnapshot', 'FunctionParameter', 'FunctionMetadata', 'InvocationProof', 'RuntimeQueryError']
