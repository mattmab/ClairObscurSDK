"""Use the real MCP stdio protocol; preserve responses as local research evidence.

`list` discovers the live tool schemas. `call` accepts an argument JSON file.
This client does not treat a bridge-only handshake as a working Ghidra backend.
"""
import argparse
import asyncio
from datetime import timedelta, datetime, timezone
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run(args):
    env = dict(os.environ)
    env.update(TEMP=r'D:\HobbyDevelopment\Caches\ClairObscurSDK',
               TMP=r'D:\HobbyDevelopment\Caches\ClairObscurSDK',
               PYTHONDONTWRITEBYTECODE='1',
               GHIDRA_MCP_URL='http://127.0.0.1:8089',
               GHIDRA_MCP_LOG_LEVEL='WARNING')
    server = StdioServerParameters(command=sys.executable,
                                   args=['-m', 'bridge_mcp_ghidra', '--no-lazy'],
                                   env=env)
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=300)) as session:
            async with asyncio.timeout(45):
                init = await session.initialize()
            if args.action == 'list':
                result = await session.list_tools()
            else:
                arguments = json.loads(args.arguments.read_text(encoding='utf-8-sig')) if args.arguments else {}
                result = await session.call_tool(args.tool, arguments)
            payload = {'timestamp': datetime.now(timezone.utc).isoformat(),
                       'server': init.model_dump(mode='json'),
                       'action': args.action, 'tool': args.tool,
                       'result': result.model_dump(mode='json')}
            args.output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
            if args.action == 'list':
                print(json.dumps([{'name': t.name, 'inputSchema': t.inputSchema} for t in result.tools], indent=2))
            else:
                print(result.model_dump_json(indent=2))
                if result.isError:
                    raise RuntimeError('Ghidra MCP tool returned an error; evidence preserved')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['list', 'call'])
    parser.add_argument('--tool')
    parser.add_argument('--arguments', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'call' and not args.tool:
        parser.error('call requires --tool')
    asyncio.run(run(args))
