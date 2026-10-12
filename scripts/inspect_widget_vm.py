"""Focused, read-only VM evidence for the Cinematics component lookup callsite."""
import asyncio,json,os,sys,time
from pathlib import Path
from datetime import timedelta
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]
async def main():
 env=dict(os.environ,GHIDRA_MCP_URL='http://127.0.0.1:8089',GHIDRA_MCP_LOG_LEVEL='WARNING',TEMP=r'D:\HobbyDevelopment\Caches\ClairObscurSDK',TMP=r'D:\HobbyDevelopment\Caches\ClairObscurSDK')
 params=StdioServerParameters(command=sys.executable,args=['-m','bridge_mcp_ghidra','--no-lazy'],env=env)
 evidence=ROOT/'evidence/widget-vm-callsite.json'
 out=json.loads(evidence.read_text(encoding='utf8')) if evidence.exists() else []
 async with stdio_client(params) as (read,write):
  async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=45)) as session:
   await session.initialize()
   for address in sys.argv[1:]:
    start=time.perf_counter()
    result=await session.call_tool('force_decompile',{'program':'/game/SandFall-Win64-Shipping.exe','function':address})
    out.append({'address':address,'duration_ms':(time.perf_counter()-start)*1000,'result':result.model_dump(mode='json')})
    print(result.model_dump_json())
 (ROOT/'evidence/widget-vm-callsite.json').write_text(json.dumps(out,indent=2),encoding='utf8')
if __name__=='__main__':asyncio.run(main())
