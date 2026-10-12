"""Generate per-definition support evidence without granting replay permission."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def assess(item, history):
    saved_id = item.get('saved_id')
    unlocked = history.get(saved_id) if saved_id else None
    if type(unlocked) is not bool:
        unlocked = None
    result = dict(id=item['id'], title=item['title'], sequence=item['sequence'],
                  saved_id=saved_id, recorded_unlock=unlocked,
                  full_scene_live_verified=False, status='unverified', blockers=[])
    if unlocked is not True:
        result['blockers'].append('Unlock: missing verified saved ID or no true value in the recorded history.')
    if item['id'].endswith('/DA_GA_CIN_MyFlower_P1.uasset') and saved_id == 'MyFlowerP1':
        result['status'] = 'partial'
        result['verified'] = 'Owned prerendered intro segment: visible playback, pause/resume, stop, repeat, Escape.'
        result['evidence'] = ['research/CINEMATICS_MEDIA_VALIDATION.md', 'evidence/myflower-mapping-verified.json']
        result['blockers'].append('Full scene: remaining in-engine bindings, event callbacks and segment transitions are unverified.')
    elif item['id'].endswith('/DA_GA_CIN_Title_PrologueLumiere.uasset'):
        result['status'] = 'blocked'
        result['verified'] = 'Asset load, idle player/actor creation and Escape cleanup; no playback.'
        result['evidence'] = ['evidence/sequence-creation-live.json',
            'evidence/sequence-interruption-20261011-103703.json', 'evidence/sequence-callbacks.json']
        result['blockers'].append('Audio isolation: custom music callbacks replace shared contexts without restoring them; direct PlaySound2D interruption remains unowned.')
        result['blockers'].append('Callback audit: complete widget/director flow and native restoration must be verified before Play.')
    else:
        result['verified'] = 'Definition-to-sequence mapping only; no playback claim.'
        result['evidence'] = ['mods/Cinematics/catalog.json']
        result['blockers'].append('Game adapter: sequence hierarchy, bindings, event callbacks and restoration have not been audited for this definition.')
        result['blockers'].append('Live validation: playback, controls, natural completion, interruption and travel are unverified.')
    return result

def build():
    catalog = json.loads((ROOT/'mods/Cinematics/catalog.json').read_text(encoding='utf8'))
    raw = json.loads((ROOT/'evidence/cinematics-history-map.json').read_text(encoding='utf8'))
    maps = [r['value']['$map']['items'] for r in raw
            if r.get('event') == 'stored_value' and r.get('name') == 'InteractedCinematics']
    if len(maps) != 1:
        raise ValueError('Expected one recorded history map')
    history = dict(maps[0])
    rows = [assess(item, history) for item in catalog['scenes']]
    if len(rows) != 155 or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Catalog size or unique identity changed')
    report = dict(version=1, manifest_sha256=catalog['manifest_sha256'],
        scope='Recorded evidence only. This report is not an executable replay whitelist.',
        history_source='evidence/cinematics-history-map.json', scenes=rows)
    (ROOT/'research/CINEMATICS_COMPATIBILITY.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    text = ['# Cinematics compatibility — recorded evidence, October 11', '',
        '155 definitions; **0 full in-engine scenes live verified**, 1 partial movie segment.',
        'Generic asset loading and idle sequence ownership are implemented in candidate v35.',
        'Unverified means not yet assessed; it does not mean technically impossible or unsafe.',
        'Unlock values below come from a recorded save-history snapshot and must be refreshed before playback.', '',
        '| Definition | Recorded unlock | Replay status | Remaining blocker |',
        '| --- | --- | --- | --- |']
    for row in rows:
        unlock = 'true' if row['recorded_unlock'] is True else 'false' if row['recorded_unlock'] is False else 'unknown'
        text.append('| ' + ' | '.join((row['title'], unlock, row['status'], ' '.join(row['blockers']))) + ' |')
    text += ['', 'Exact asset paths, saved IDs and evidence references are in CINEMATICS_COMPATIBILITY.json.',
        'Neither discovery nor a successful idle factory call grants playback permission.']
    (ROOT/'research/CINEMATICS_COMPATIBILITY.md').write_text('\n'.join(text)+'\n', encoding='utf8')
    print(len(rows), 'definitions;', sum(r['status']=='partial' for r in rows), 'partial;',
          sum(r['status']=='blocked' for r in rows), 'known blocked;',
          sum(r['status']=='unverified' for r in rows), 'unverified')

if __name__ == '__main__':
    build()
