"""Launch the explicitly requested continent-flight demonstration."""
from pathlib import Path
import logging
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33.sdk import Session
from expedition33.mods import ModLoader
from expedition33.settings import SettingsStore
from expedition33 import TargetExitedError

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / 'logs/continent-flight.log', encoding='utf-8')])

def main():
    with Session(vector_values=True) as session, ModLoader(ROOT / 'mods',
            settings=SettingsStore(ROOT / 'settings/management.json'), session=session) as loader:
        for name in ('SDKManagement', 'IntrospectionHarness', 'ContinentFlight'):
            loader.load(name)
            loader.enable(name, console=True)
        logging.info('CONTINENT FLIGHT READY: double-tap Space; hold E/Q to ascend/descend')
        try:
            while not loader.stop_requested:
                loader.poll()
                time.sleep(.02)
        except TargetExitedError as exc:
            if exc.exit_code != 0:
                raise

if __name__ == '__main__':
    main()
