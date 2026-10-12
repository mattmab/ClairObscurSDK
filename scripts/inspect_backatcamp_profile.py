"""Fixed no-play asset/schema observation for the next audited title profile."""
import importlib.util
from pathlib import Path
from expedition33._scope import SessionScope
from expedition33.assets import load_asset


def run(session):
    path = Path(__file__).resolve().parents[1] / '.agent-work/validation/coverage_native/inspect_backatcamp_channel.py'
    spec = importlib.util.spec_from_file_location('backatcamp_channel_observation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scope = SessionScope(session)
    try:
        with load_asset(scope, '/Game/Cinematics/Titles/SequenceTitles/LS_Title_BackAtCamp.LS_Title_BackAtCamp') as loaded:
            if loaded.return_value is None or loaded.return_value.class_name != 'LevelSequence':
                raise RuntimeError('Exact BackAtCamp sequence was not loaded')
            channel = module.main(scope.pid)
            compiled_path = Path(__file__).resolve().parents[1] / '.agent-work/reverse_engineering/coverage/inspect_back_compiled_entities.py'
            compiled_spec = importlib.util.spec_from_file_location('backatcamp_compiled_observation', compiled_path)
            compiled = importlib.util.module_from_spec(compiled_spec)
            compiled_spec.loader.exec_module(compiled)
            return dict(channel=channel, compiled=compiled.main(scope.pid))
    finally:
        scope.close()
