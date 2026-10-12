"""Capture selected cinematic-history Blueprint scripts without executing them."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33.catalog import capture_matching

pid = int(sys.argv[1])
names = ('HasPlayedCinematic', 'SetPlayedCinematic', 'OnSaveLoaded', 'GetIsSaveLoaded',
         'BP_jRPG_GI_Custom_C', 'Map_Find', 'Map_Add', 'BooleanAND')
catalog = capture_matching(pid, names=names)
records = []
for obj in catalog.objects:
    if obj.class_name not in ('Function', 'BlueprintGeneratedClass') or obj.name not in names:
        continue
    path = catalog.path_name(obj)
    if ('BP_jRPG_GI_Custom' not in path and 'BP_GlobalVariablesFunctionLibrary' not in path
            and obj.name not in ('Map_Find', 'Map_Add', 'BooleanAND')):
        continue
    response = subprocess.run([str(ROOT / 'build/widget-frame-inspector/research_probe.exe'),
        '--describe-script' if obj.name in ('HasPlayedCinematic', 'SetPlayedCinematic',
            'OnSaveLoaded', 'GetIsSaveLoaded') else '--describe',
        str(pid), f'{obj.index}:{obj.serial}:{obj.address:x}'],
        capture_output=True, text=True, check=True, timeout=30)
    records.append(dict(path=path, rows=[json.loads(line) for line in response.stdout.splitlines()]))
print(json.dumps(records, indent=2))
