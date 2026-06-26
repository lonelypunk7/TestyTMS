#!/usr/bin/env python3
"""
TestY MCP HTTP Server.
Launches testy_mcp.py as subprocess, proxies HTTP → MCP JSON-RPC over stdin pipe.

Uses only stdlib + aiohttp. No external MCP SDK needed.
"""
import asyncio
import json
import sys
from aiohttp import web


class MCPProxy:
    def __init__(self):
        self.proc = None
        self._init_done = False

    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(
            sys.executable, "testy_mcp.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/Users/leonid/Projects/TestyTMS",
        )
        greeting_line = await self.proc.stdout.readline()
        data = json.loads(greeting_line)
        self._init_done = True
        return data

    async def call(self, tool_name, args):
        if not self._init_done:
            await self.start()
        msg = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
            "params": {"name": tool_name, "arguments": args}
        })
        self.proc.stdin.write((msg + "\n").encode())
        await self.proc.stdin.drain()
        line = await self.proc.stdout.readline()
        resp = json.loads(line)
        return resp.get("result", resp)

    async def route(self, tool_name, args):
        return await self.call(tool_name, args)


proxy = MCPProxy()

# Singular resource names for ID-based operations
SINGULAR = {
    "projects": "project", "cases": "case", "tests": "test",
    "suites": "suite", "testplans": "testplan", "results": "result",
    "users": "user", "groups": "group", "labels": "label",
    "statuses": "status", "attachments": "attachment", "comments": "comment",
}


async def handle(request):
    try:
        path = request.path.lstrip("/")
        if path == "health":
            return web.json_response({"status": "ok"})

        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(request.path)
        query_args = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        parts = path.split("/")
        resource = parts[0]
        has_id = len(parts) >= 2 and parts[1] and not parts[1].startswith("?")

        method = request.method
        args = dict(query_args)

        if method == "GET":
            if has_id:
                singular = SINGULAR.get(resource, resource.rstrip("s"))
                args[singular] = parts[1]
            if has_id:
                singular = SINGULAR.get(resource, resource.rstrip("s"))
                tool = f"get_{singular}"
            else:
                tool = f"get_{resource}"
            result = await proxy.route(tool, args)

        elif method == "POST":
            body = await request.json()
            if has_id:
                singular = SINGULAR.get(resource, resource.rstrip("s"))
                body[singular] = parts[1]
            singular = SINGULAR.get(resource, resource.rstrip("s"))
            tool = f"create_{singular}"
            result = await proxy.route(tool, body)

        elif method == "PUT":
            body = await request.json()
            if has_id:
                singular = SINGULAR.get(resource, resource.rstrip("s"))
                body[singular] = parts[1]
            singular = SINGULAR.get(resource, resource.rstrip("s"))
            tool = f"update_{singular}"
            result = await proxy.route(tool, body)

        elif method == "DELETE":
            if has_id:
                singular = SINGULAR.get(resource, resource.rstrip("s"))
                args[singular] = parts[1]
            singular = SINGULAR.get(resource, resource.rstrip("s"))
            tool = f"delete_{singular}"
            result = await proxy.route(tool, args)
        else:
            return web.json_response({"error": "Method not allowed"}, status=405)

        return web.json_response(result)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def main():
    await proxy.start()
    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handle)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8765)
    await site.start()
    print(f"MCP HTTP proxy running on http://0.0.0.0:8765")

    stop = asyncio.Event()
    await stop.wait()


if __name__ == "__main__":
    asyncio.run(main())
