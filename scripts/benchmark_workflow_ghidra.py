"""Bounded Ghidra benchmark: one explicit function, persistent MCP, saved evidence."""
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import statistics
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]
async def main():
    samples=[]
    env=dict(os.environ,GHIDRA_MCP_URL='http://127.0.0.1:8089',GHIDRA_MCP_LOG_LEVEL='WARNING',
             TEMP=r'D:\HobbyDevelopment\Caches\ClairObscurSDK',TMP=r'D:\HobbyDevelopment\Caches\ClairObscurSDK')
    start=time.perf_counter()
    params=StdioServerParameters(command=sys.executable,args=['-m','bridge_mcp_ghidra','--no-lazy'],env=env)
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=45)) as session:
            await session.initialize()
            startup=(time.perf_counter()-start)*1000
            for _ in range(3):
                clock=time.perf_counter()
                result=await session.call_tool('force_decompile',{'program':'/game/SandFall-Win64-Shipping.exe','function':'0x14333a230'})
                samples.append({'ms':(time.perf_counter()-clock)*1000,'success':not result.isError})
                if result.isError: break
            (ROOT/'evidence/workflow-ghidra-wrapper.json').write_text(result.model_dump_json(indent=2))
    cache=[]
    for _ in range(10):
        clock=time.perf_counter()
        json.loads((ROOT/'evidence/workflow-ghidra-wrapper.json').read_text())
        cache.append((time.perf_counter()-clock)*1000)
    report={'startup_ms':startup,'mcp_samples':samples,'cached_read_ms':cache,
            'target':'0x14333a230','program':'/game/SandFall-Win64-Shipping.exe',
            'note':'Saved evidence reuse is valid only for the same executable and unchanged analysis; it is not fresh analysis.'}
    (ROOT/'evidence/workflow-ghidra-benchmark.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':asyncio.run(main())
