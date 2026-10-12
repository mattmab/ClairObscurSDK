"""Repeat process-startup and targeted-test timings without touching the game."""
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
import os
ROOT=Path(__file__).resolve().parents[1]
env=dict(os.environ,TEMP=str(ROOT/'.test-tmp'),TMP=str(ROOT/'.test-tmp'))
cases={
 'python_startup':[sys.executable,'-c','pass'],
 'powershell_no_profile':['powershell.exe','-NoProfile','-Command','exit 0'],
 'targeted_transport_tests':[sys.executable,'-m','unittest','discover','-s','tests','-p','test_controller_commands.py'],
}
report={}
for name,command in cases.items():
 samples=[]
 for _ in range(5):
  start=time.perf_counter()
  result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=30)
  samples.append({'ms':(time.perf_counter()-start)*1000,'success':result.returncode==0})
 values=sorted(row['ms'] for row in samples)
 report[name]={'samples':samples,'count':5,'median_ms':statistics.median(values),'p95_ms':values[-1],
               'total_ms':sum(values),'failures':sum(not row['success'] for row in samples)}
(ROOT/'evidence/workflow-local-benchmark.json').write_text(json.dumps(report,indent=2))
print(json.dumps({key:{k:v for k,v in value.items() if k!='samples'} for key,value in report.items()},indent=2))
