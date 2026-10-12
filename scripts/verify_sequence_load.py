"""Bounded load/inspect/release check. Never creates a player or evaluates tracks."""
import json
import hashlib
from pathlib import Path
from datetime import datetime,timezone
from expedition33.assets import load_asset
from expedition33.catalog import capture
from expedition33.values import read_values


def run(scope):
    root=Path(__file__).resolve().parents[1]
    saves=Path('C:/Users/Matt/AppData/Local/Sandfall/Saved/SaveGames')
    def hashes(): return {str(p.relative_to(saves)):hashlib.sha256(p.read_bytes()).hexdigest() for p in saves.rglob('*.sav')}
    path='/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere.LS_Title_PrologueLumiere'
    report={'utc':datetime.now(timezone.utc).isoformat(),'pid':scope.pid,'path':path,'playback_attempted':False}
    report['before_hashes']=hashes()
    report['leases_before']=repr(scope._session._lease_command('lease-status'))
    try:
        with load_asset(scope,path) as loaded:
            obj=loaded.return_value
            if obj is None or obj.class_name!='LevelSequence': raise ValueError('Not a LevelSequence')
            c=capture()
            if c.path_name(obj)!=path: raise ValueError('Loaded asset path mismatch')
            report['loaded']={'index':obj.index,'serial':obj.serial,'path':c.path_name(obj),'class':obj.class_name}
            report['leases_loaded']=repr(scope._session._lease_command('lease-status'))
            prefix=path.split('.')[0]
            observations=[]
            for o in c.objects:
                if not c.path_name(o).startswith(prefix): continue
                row={'path':c.path_name(o),'class':o.class_name,'index':o.index,'serial':o.serial}
                # Discovery only here. Detailed track reads run in an external
                # reader, so stale transient compiled data cannot terminate the
                # persistent controller's shared read worker.
                observations.append(row)
            report['objects']=observations
    except Exception as e:
        report['error']=repr(e)
    report['leases_after']=repr(scope._session._lease_command('lease-status'))
    report['after_hashes']=hashes()
    report['save_hashes_unchanged']=report['before_hashes']==report['after_hashes']
    (root/'evidence/sequence-load-live.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return {k:v for k,v in report.items() if k not in ('objects','before_hashes','after_hashes')}
