"""Explicit live v20 UI/flight candidate host, one persistent controller.

Requires the independently built UI/flight combination, not the standard bundle.
Stop through the normal management shutdown command. Never starts a second owner.
"""
from pathlib import Path
import logging
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33 import sdk, TargetExitedError
from expedition33.mods import ModLoader
from expedition33.settings import SettingsStore

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / 'logs/menu-latency.log', encoding='utf-8')])

def main():
    session = sdk.Session(vector_values=True, ui_batch=True)
    with session, ModLoader(ROOT / 'mods', settings=SettingsStore(ROOT / 'settings/management.json'),
                            session=session) as loader:
        for name in ('SDKManagement', 'IntrospectionHarness', 'ContinentFlight'):
            loader.load(name)
            loader.enable(name, console=True)
        loader._loaded['SDKManagement'][1].native.prepare()
        logging.info('MENU LATENCY CANDIDATE READY')
        try:
            while not loader.stop_requested:
                loader.poll()
                time.sleep(.005)
        except TargetExitedError as error:
            if error.exit_code != 0:
                raise
    logging.info('MENU LATENCY CANDIDATE CLOSED')

if __name__ == '__main__':
    main()
