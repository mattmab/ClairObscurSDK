"""Isolated, captured Python dependency trees for trusted local mods."""
import hashlib
import importlib.abc
import importlib.util
from pathlib import Path
import sys
from .mod_archive import python_source_digest


class PackageSources:
    def __init__(self, entry_path, entry_code, entry_digest):
        self.root = Path(entry_path).parent.resolve(strict=True)
        self.modules = {}
        self.directories = set()
        inventory = {'mod.py': entry_digest}
        size = 0
        for path in self.root.rglob('*.py'):
            relative = path.relative_to(self.root)
            if relative.as_posix() == 'mod.py' or any(p in ('.git', '__pycache__') for p in relative.parts):
                continue
            if path.is_symlink() or not path.resolve(strict=True).is_relative_to(self.root):
                raise ValueError('Package source escapes its mod directory')
            if any((self.root.joinpath(*relative.parts[:i])).is_junction()
                   for i in range(1, len(relative.parts))):
                raise ValueError('Package junctions are unsupported')
            parts = relative.with_suffix('').parts
            if not all(p.isidentifier() for p in parts):
                raise ValueError('Package Python paths must be valid identifiers')
            package = parts[-1] == '__init__'
            name = '.'.join(parts[:-1] if package else parts)
            if not name:
                raise ValueError('mod.py is the entry point; root __init__.py is unsupported')
            if name in self.modules:
                raise ValueError('Ambiguous module and package: ' + name)
            with path.open('rb') as stream:
                source = stream.read(4 * 1024 * 1024 + 1)
            size += len(source)
            if len(source) > 4 * 1024 * 1024 or size > 64 * 1024 * 1024 or len(self.modules) >= 511:
                raise ValueError('Package Python source exceeds limits')
            self.modules[name] = (path, compile(source, str(path), 'exec', dont_inherit=True), package)
            inventory[relative.as_posix()] = hashlib.sha256(source).hexdigest()
            for i in range(1, len(parts)):
                self.directories.add('.'.join(parts[:i]))
        for name in self.directories:
            if name in self.modules and not self.modules[name][2]:
                raise ValueError('Module is also a package directory: ' + name)
        self.modules[''] = (Path(entry_path), entry_code, True)
        self.sha256 = python_source_digest(inventory)
        self.has_dependencies = len(inventory) > 1


class OwnedImports(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, key, sources):
        self.key, self.sources = key, sources
        self.closed = False

    def install(self):
        sys.meta_path.insert(0, self)

    def find_spec(self, fullname, path=None, target=None):
        if fullname != self.key and not fullname.startswith(self.key + '.'):
            return None
        if self.closed:
            raise ModuleNotFoundError('Mod import owner is closed: ' + fullname)
        name = fullname[len(self.key):].lstrip('.')
        entry = self.sources.modules.get(name)
        if entry is None:
            if name not in self.sources.directories:
                raise ModuleNotFoundError('No captured mod source: ' + fullname)
            origin, package = self.sources.root.joinpath(*name.split('.')), True
        else:
            origin, _, package = entry
        spec = importlib.util.spec_from_loader(fullname, self, origin=str(origin), is_package=package)
        spec.has_location = True
        if package:
            spec.submodule_search_locations = []  # Never fall through to disk/pyc.
        return spec

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        if self.closed:
            raise ImportError('Mod import owner is closed')
        name = module.__name__[len(self.key):].lstrip('.')
        entry = self.sources.modules.get(name)
        if entry is not None:
            exec(entry[1], module.__dict__)

    def close(self):
        self.closed = True
        if self in sys.meta_path:
            sys.meta_path.remove(self)
        for name in tuple(sys.modules):
            if name == self.key or name.startswith(self.key + '.'):
                sys.modules.pop(name, None)
        self.sources = None
