"""Record read-only SDK state after a manually driven cinematic menu test."""
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

def run(model):
    root = Path(__file__).resolve().parents[1]
    saves = Path('C:/Users/Matt/AppData/Local/Sandfall/Saved/SaveGames')
    hashes = {'\\'+str(p.relative_to(saves)):hashlib.sha256(p.read_bytes()).hexdigest().upper()
              for p in saves.rglob('*.sav')}
    before = json.loads((root/'evidence/myflower-menu-before.json').read_text(encoding='utf-8-sig'))
    prior = model.discovery
    model.discover()
    report = dict(utc=datetime.now(timezone.utc).isoformat(),pid=model.session.pid,
        status=model.status(),video_released=model.video is None,
        history_unchanged=prior.get('confirmed')==model.discovery.get('confirmed'),
        save_hashes_unchanged=before['hashes']==hashes,hashes=hashes)
    (root/'evidence/myflower-menu-after.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {k:report[k] for k in ('video_released','history_unchanged','save_hashes_unchanged')}
