"""Read-only raw battle-manager observations for codec diagnosis."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33 import _query
from expedition33.catalog import capture
from expedition33._reader import ReadBatch
from expedition33.values import _decode_values, read_values

def main():
    catalog = capture()
    records = []
    with ReadBatch(catalog.pid):
        for obj in catalog.select('AC_jRPG_BattleManager_C'):
            if obj.object_flags & 0x10:
                continue
            start, rows = _query(['--read-values', str(catalog.pid), f'{obj.index}:{obj.serial}:{obj.address:x}'])
            record = {'path': catalog.path_name(obj), 'start': start, 'rows': rows}
            try:
                decoded = _decode_values(catalog, obj, start, rows)
                wanted = {'BattleSummaryStatsManager', 'TurnCount', 'BattleEndState', 'AbandonRequested'}
                record['decoded'] = {'values': len(decoded.values),
                    'statistics_fields': {name: repr(value) for (_,name),value in decoded.values.items() if name in wanted},
                    'errors': dict((str(k),v) for k,v in decoded.errors.items())}
                summaries = [value for (_,name),value in decoded.values.items()
                             if name == 'BattleSummaryStatsManager' and value is not None]
                if len(summaries) == 1:
                    summary = read_values(catalog, summaries[0])
                    record['summary'] = {'path': catalog.path_name(summaries[0]),
                        'values': {name: value for (_,name),value in summary.values.items()
                                   if type(value) in (bool,int,float,str) or value is None},
                        'errors': {str(k):v for k,v in summary.errors.items()}}
            except Exception as error:
                record['error'] = str(error)
            records.append(record)
    path = ROOT / 'evidence/statistics-reference/battle-manager-values.json'
    path.write_text(json.dumps(records, indent=2), encoding='utf-8')
    print(json.dumps([{'path': r['path'], 'error': r.get('error'),
        'decoded_values': r.get('decoded', {}).get('values'),
        'statistics_fields': r.get('decoded', {}).get('statistics_fields'),
        'unsupported_fields': len(r.get('decoded', {}).get('errors', {}))} for r in records]))

if __name__ == '__main__':
    main()
