"""Read-only target-build pause widget inventory. No controller or mutations."""
from pathlib import Path
import sys, json
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from expedition33.catalog import capture
from expedition33.values import read_values
from expedition33.reflection import describe
from expedition33._reader import ReadBatch

def main():
    c = capture()
    def ref(v):
        if hasattr(v, 'index') and hasattr(v, 'name'):
            return dict(index=v.index, serial=v.serial, name=v.name, cls=v.class_name, path=c.path_name(v))
        if isinstance(v, (str, int, float, bool)) or v is None: return v
        return repr(v)[:400]
    pause = [o for o in c.select('WBP_PauseMenu_C') if not o.object_flags & 0x10]
    objects = []
    for o in c.objects:
        if any(p.name in c.path_name(o) for p in pause): objects.append(o)
    functions = [o for o in c.select('Function') if c.by_index[o.outer_index].name in
        ('WBP_PauseMenu_C','WBP_BaseButton_C','CommonButtonBase','CommonButtonInternalBase','WBP_WrappingText_C','PanelWidget','VerticalBox','VerticalBoxSlot')]
    with ReadBatch(c.pid):
        values = []
        for o in objects:
            if o in pause or (o.name in ('ResumeButton','SettingsButton','PausePanel','CommonTextBlock_178') or (o.class_name == 'GridSlot' and '.GridPanel_0.GridSlot_' in c.path_name(o) and len(c.path_name(o)) < 220)):
                v=read_values(c,o)
                values.append(dict(object=ref(o), fields={f'{c.by_index[k[0]].name}.{k[1]}':ref(x) for k,x in v.values.items()},errors={str(k):str(v) for k,v in v.errors.items()}))
        desc=describe(c,functions)
    report=dict(pid=c.pid,objects=[ref(o) for o in objects],values=values,functions=[dict(object=ref(o),metadata=dict(desc[o.index].function),parameters=[dict(p) for p in desc[o.index].properties]) for o in functions])
    path=ROOT/'evidence/pause-menu-inventory.json'
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(path=str(path),objects=len(objects),functions=len(functions))))
if __name__=='__main__': main()


