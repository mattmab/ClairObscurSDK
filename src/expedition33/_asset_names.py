"""Fresh bounded name-pool lookup, borrowing qualified read-only IO when present."""
import json,subprocess
from ._reader import active_reader


def resolve(scope,path,*,export=False):
    if type(export) is not bool:raise ValueError('Boolean export-name mode required')
    command='--resolve-export-names' if export else '--resolve-asset-names'
    args=[command,str(scope.pid),path];reader=active_reader()
    if reader is not None and reader.pid!=scope.pid:raise ValueError('Asset resolver belongs to another read process')
    if reader is not None and getattr(reader,'supports_asset_names',False) is True:
        # This response contains asset_names rather than object rows and uses
        # its own exact snapshot shape. Reader framing/sequence checks still run.
        output=reader.query(args)
    else:
        query=subprocess.run([str(scope._session._transport._executable),*args],
            capture_output=True,text=True,encoding='utf8',timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        if query.returncode:raise ValueError('Asset name resolution failed: '+query.stderr.strip())
        output=query.stdout
    try:
        rows=[json.loads(line) for line in output.splitlines()]
        if (len(rows)!=3 or any(type(row) is not dict for row in rows) or rows[0].get('event')!='snapshot_start' or
                type(rows[0].get('pid')) is not int or rows[0]['pid']!=scope.pid or
                type(rows[-1].get('emitted')) is not int or
                rows[-1]!={'event':'snapshot_end','emitted':1}):raise ValueError('Incomplete asset name observation')
        result=rows[1]
        original={'event','package','asset','package_id','asset_id'}
        numbered={'package_number','asset_number'}
        if (set(result) not in (original,original|numbered) or result['event']!='asset_names' or
                result['package']+'.'+result['asset']!=path or
                any(type(result[key]) is not int or not 0<result[key]<0x20000000 for key in ('package_id','asset_id'))):
            raise ValueError('Asset-name observation changed')
        if numbered<=set(result):
            for key in ('package','asset'):
                number=result[key+'_number']
                if type(number) is not int or not 0<=number<=0x7fffffff:
                    raise ValueError('Asset-name number is invalid')
                if number and not result[key].endswith('_'+str(number-1)):
                    raise ValueError('Asset-name number differs from requested path')
        return result
    except (ValueError,KeyError,TypeError,IndexError):
        if reader is not None and getattr(reader,'supports_asset_names',False) is True:reader.close()
        raise
