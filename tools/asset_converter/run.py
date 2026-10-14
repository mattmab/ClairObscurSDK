"""One-pass local converter setup and execution; no model downloads."""
from pathlib import Path
import subprocess,sys,venv,os

def main():
    if sys.version_info[:2]!=(3,13):raise SystemExit('Run with Python 3.13: py -3.13 run.py <arguments>')
    root=Path(__file__).resolve().parent
    if len(sys.argv)<2 or '--help' in sys.argv:
        print('Usage: py -3.13 run.py ayane|2b <downloaded FBX or BLEND> --game <game directory>');return
    environment=root/'.converter-env';python=environment/'Scripts/python.exe'
    if not python.exists():venv.EnvBuilder(with_pip=True).create(environment)
    marker=environment/'dependencies-v1.ready'
    if not marker.exists():
        env=dict(os.environ,PIP_CACHE_DIR=str(root/'.pip-cache'))
        subprocess.run([str(python),'-m','pip','install','bpy==5.2.2','numpy==2.5.4','pillow==12.3.0'],check=True,env=env)
        marker.write_text('bpy5.2.2 numpy2.5.4 pillow12.3.0\n')
    subprocess.run([str(python),str(root/'convert.py'),*sys.argv[1:]],check=True)

if __name__=='__main__':main()
