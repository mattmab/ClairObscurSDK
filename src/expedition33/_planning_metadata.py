"""Bounded descriptor observations; never authority to dispatch engine calls."""


class MetadataObservations:
    def __init__(self):
        self._entries = {}

    def clear(self):
        self._entries.clear()

    def read(self, kind, catalog, objects, reader):
        objects = tuple(catalog.resolve(obj) for obj in objects)
        result, missing = {}, []
        for obj in objects:
            key = (kind, obj.pid, obj.index, obj.serial, obj.address)
            entry = self._entries.get(key)
            if entry is None:
                missing.append(obj)
            else:
                descriptor, dependencies = entry
                for observed in dependencies:
                    catalog.resolve(observed)
                result[obj.index] = descriptor
        if missing:
            fresh = reader(catalog, tuple(missing))
            for obj in missing:
                descriptor = fresh[obj.index]
                indices = {obj.index}
                for row in (*getattr(descriptor, 'owners', ()), *getattr(descriptor, 'properties', ())):
                    for name, value in row.items():
                        if (name == 'index' or name.endswith('_index')) and type(value) is int and value >= 0:
                            indices.add(value)
                dependencies = tuple(catalog.by_index[index] for index in sorted(indices))
                key = (kind, obj.pid, obj.index, obj.serial, obj.address)
                # Bound observations without evicting an active call's owners.
                # Descriptors are copied metadata, not native resource owners.
                if len(self._entries) >= 256:
                    self._entries.clear()
                self._entries[key] = descriptor, dependencies
                result[obj.index] = descriptor
        return result
