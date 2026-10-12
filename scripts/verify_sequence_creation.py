"""Bounded no-play factory test; retain raw outcome and always request cleanup."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
from expedition33.sequences import OwnedLevelSequence

def run(mod):
    root=Path(__file__).resolve().parents[1]
    saves=Path('C:/Users/Matt/AppData/Local/Sandfall/Saved/SaveGames')
    def hashes(): return {str(p.relative_to(saves)):hashlib.sha256(p.read_bytes()).hexdigest() for p in saves.rglob('*.sav')}
    scope=mod.session
    report={'utc':datetime.now(timezone.utc).isoformat(),'pid':scope.pid,'playback_attempted':False}
    report['before_hashes']=hashes()
    report['leases_before']=repr(scope._session._lease_command('lease-status'))
    sequence=OwnedLevelSequence(scope)
    try:
        sequence.build(mod.native.menu.panel,'/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere.LS_Title_PrologueLumiere')
        report['actor']=repr(sequence.actor)
        report['player']=repr(sequence.player)
        report['status']=sequence.status()
        report['leases_created']=repr(scope._session._lease_command('lease-status'))
    except Exception as error:
        report['error']=repr(error)
    finally:
        try:
            sequence.close()
            report['cleanup']='confirmed'
        except Exception as error: report['cleanup_error']=repr(error)
    try: report['leases_after']=repr(scope._session._lease_command('lease-status'))
    except Exception as error: report['lease_status_error']=repr(error)
    report['after_hashes']=hashes()
    report['save_hashes_unchanged']=report['before_hashes']==report['after_hashes']
    (root/'evidence/sequence-creation-live.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    (root/('evidence/sequence-creation-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.json')).write_text(json.dumps(report,indent=2),encoding='utf8')
    return {k:v for k,v in report.items() if k not in ('before_hashes','after_hashes')}
