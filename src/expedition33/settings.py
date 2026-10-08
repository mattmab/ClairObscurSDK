"""Versioned settings shared by management frontends; no engine dependencies.

One controller owns a store. Saves reject concurrent/stale writers instead of
merging or replaying changes with unknown outcomes. Corrupt input is preserved.
"""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import uuid

MAX_BYTES = 1024 * 1024


class SettingsError(RuntimeError):
    pass


class SettingsVersionError(SettingsError):
    pass


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_.-]{0,95}', value):
        raise SettingsError('Expected a stable lowercase identifier, at most 96 characters')
    return value


def _json_value(value, depth=0):
    if depth > 16:
        raise SettingsError('Settings nesting exceeds 16 levels')
    if type(value) in (str, bool, int) or value is None:
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) in (list, dict):
        if len(value) > 4096:
            raise SettingsError('Settings collection exceeds 4096 entries')
        if isinstance(value, dict) and any(type(key) is not str for key in value):
            raise SettingsError('Settings keys must be strings')
        for child in value.values() if isinstance(value, dict) else value:
            _json_value(child, depth + 1)
        return
    raise SettingsError('Settings require finite JSON values')


def _validate(document):
    if type(document) is not dict or type(document.get('version')) is not int:
        raise SettingsError('Missing integer settings version')
    if document['version'] != 1:
        raise SettingsVersionError(f"Unsupported settings version {document['version']}")
    if set(document) != {'version', 'revision', 'mods'}:
        raise SettingsError('Unexpected settings document fields')
    if type(document['revision']) is not int or document['revision'] < 0:
        raise SettingsError('Invalid settings revision')
    if type(document['mods']) is not dict or len(document['mods']) > 1024:
        raise SettingsError('Expected at most 1024 mod settings records')
    for mod_id, record in document['mods'].items():
        identifier(mod_id)
        if type(record) is not dict or set(record) - {'enabled', 'options', 'keybinds'}:
            raise SettingsError('Invalid mod settings record')
        if 'enabled' in record and type(record['enabled']) is not bool:
            raise SettingsError('Enabled preference must be a boolean')
        for category in ('options', 'keybinds'):
            values = record.get(category, {})
            if type(values) is not dict:
                raise SettingsError(f'{category} must map stable IDs to values')
            for key, value in values.items():
                identifier(key)
                if category == 'keybinds' and value is not None and type(value) is not str:
                    raise SettingsError('Stored key mappings must be strings or null')
    _json_value(document)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SettingsError('Duplicate JSON setting key')
        result[key] = value
    return result


class SettingsStore:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.backup = self.path.with_suffix(self.path.suffix + '.bak')
        self.lock = self.path.with_suffix(self.path.suffix + '.lock')
        self._owner = threading.get_ident()
        self.recovery = None
        self.preserved_corrupt = None
        raw = self._read(self.path)
        self._fingerprint = self._hash(raw)
        self._corrupt = False
        try:
            self._document = self._decode(raw) if raw is not None else None
        except SettingsVersionError:
            raise  # Never overwrite a future version with an older backup.
        except SettingsError as error:
            self._corrupt = True
            self.recovery = str(error)
            self._document = None
        if self._document is None:
            backup = self._read(self.backup)
            if backup is not None:
                self._document = self._decode(backup)
                self.recovery = 'Loaded last-good backup: ' + (self.recovery or 'primary is missing')
            elif self._corrupt:
                raise SettingsError('Primary settings are invalid and no backup exists')
            else:
                self._document = {'version': 1, 'revision': 0, 'mods': {}}

    def _check(self):
        if threading.get_ident() != self._owner:
            raise SettingsError('Settings require their controller owner thread')

    @staticmethod
    def _read(path):
        try:
            with path.open('rb') as stream:
                raw = stream.read(MAX_BYTES + 1)
        except FileNotFoundError:
            return None
        if len(raw) > MAX_BYTES:
            raise SettingsError('Settings file exceeds 1 MiB')
        return raw

    @staticmethod
    def _hash(raw):
        return hashlib.sha256(raw).hexdigest() if raw is not None else None

    @staticmethod
    def _decode(raw):
        try:
            result = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs)
            _validate(result)
            return result
        except (ValueError, UnicodeError, RecursionError) as error:
            raise SettingsError('Malformed settings JSON') from error

    @staticmethod
    def _encode(document):
        _validate(document)
        raw = json.dumps(document, ensure_ascii=True, allow_nan=False, indent=2).encode('utf-8')
        if len(raw) > MAX_BYTES:
            raise SettingsError('Settings file exceeds 1 MiB')
        return raw

    @staticmethod
    def _atomic(path, raw):
        temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with temp.open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)

    def get(self, mod_id):
        self._check()
        return copy.deepcopy(self._document['mods'].get(identifier(mod_id), {}))

    @property
    def revision(self):
        self._check()
        return self._document['revision']

    def save(self, mod_id, record):
        """Replace one mod's preferences after validation; preserve all other mods.

        This does not enable a mod, apply an option or validate an engine key name.
        Those operations belong to the registry/lifecycle/input implementations.
        """
        self._check()
        updated = copy.deepcopy(self._document)
        updated['mods'][identifier(mod_id)] = copy.deepcopy(record)
        updated['revision'] += 1
        raw = self._encode(updated)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as error:
            raise SettingsError('Another settings writer or abandoned lock exists; inspect before retrying') from error
        try:
            os.close(descriptor)
            current = self._read(self.path)
            if self._hash(current) != self._fingerprint:
                raise SettingsError('Settings changed on disk; reload before saving')
            if self._corrupt and current is not None:
                quarantine = self.path.with_name(self.path.name + '.corrupt.' + uuid.uuid4().hex)
                with quarantine.open('xb') as stream:
                    stream.write(current)
                self.preserved_corrupt = quarantine
            # Backup the last accepted generation, never the damaged primary.
            self._atomic(self.backup, self._encode(self._document))
            self._atomic(self.path, raw)
            self._document = updated
            self._fingerprint = self._hash(raw)
            self._corrupt = False
        finally:
            self.lock.unlink(missing_ok=True)
