"""Bounded copied camera observations, never a retention or restoration journal."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33.catalog import capture
from expedition33.values import read_values, StoredStruct

def run(pid):
    catalog = capture()
    if catalog.pid != pid:
        raise RuntimeError('Game PID changed')
    controllers = [o for o in catalog.select('PlayerController')
                   if not o.name.startswith('Default__') and not (o.object_flags & 0x10)]
    if len(controllers) > 8:
        raise RuntimeError('Controller observation bound exceeded')
    def identity(obj):
        return None if obj is None else dict(path=catalog.path_name(obj),
            index=obj.index, serial=obj.serial, address=hex(obj.address), pid=obj.pid)
    rows = []
    for controller in controllers:
        values = read_values(catalog, controller)
        pc = catalog.find_class('PlayerController')
        manager = values.values.get((pc.index, 'PlayerCameraManager'))
        row = dict(controller=identity(controller), manager=identity(manager),
                   observation_only=True)
        if manager is not None:
            observed = read_values(catalog, manager)
            cls = catalog.find_class('PlayerCameraManager')
            for name in ('ViewTarget', 'PendingViewTarget'):
                key = (cls.index, name)
                value = observed.values.get(key)
                if isinstance(value, StoredStruct):
                    if 'Target' in value.fields:
                        row[name] = identity(value.fields['Target'])
                    else:
                        row[name + '_error'] = 'Target not copied'
                else:
                    row[name + '_error'] = str(observed.errors.get(key, 'Not copied'))
        rows.append(row)
    output = ROOT / 'evidence/cinematic-camera-context.json'
    output.write_text(json.dumps(dict(pid=pid, controllers=rows,
        retained=False, mutated=False), indent=2), encoding='utf8')
    print(output)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, required=True)
    run(parser.parse_args().pid)
