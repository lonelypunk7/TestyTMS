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
        # Read the greeting (first line from subprocess)
        greeting_line = await self.proc.stdout.readline()
        data = json.loads(greeting_line)
        self._init_done = True
        return data

    async def call(self, tool_name, args):
        if not self._init_done:
            await self.start()
        # Send tool call as MCP JSON-RPC 2.0
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
        # MCP response format: {"jsonrpc": "2.0", "id": 1, "result": ...}
        return resp.get("result", resp)

    async def route(self, resource, args, method="GET"):
        mapping = {
            "projects": "get_projects", "project": "get_project",
            "cases": "get_cases", "case": "get_case",
            "tests": "get_tests", "test": "get_test",
            "suites": "get_suites", "suite": "get_suite",
            "testplans": "get_testplans", "testplan": "get_testplan",
            "results": "get_results", "result": "get_result",
            "users": "get_users", "user": "get_user",
            "groups": "get_groups", "group": "get_group",
            "labels": "get_labels", "label": "get_label",
            "statuses": "get_statuses", "status": "get_status",
            "attachments": "get_attachments", "attachment": "get_attachment",
            "comments": "get_comments", "notifications": "get_notifications",
        }
        if method == "GET":
            tool = mapping.get(resource, resource)
        elif method == "POST":
            tool = f"create_{resource}"
        elif method == "PUT":
            tool = f"update_{resource}"
        elif method == "DELETE":
            tool = f"delete_{resource}"

        return await self.call(tool, args)


proxy = MCPProxy()


async def handle(request):
    try:
        path = request.path.lstrip("/")
        if path == "health":
            return web.json_response({"status": "ok"})

        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(request.path)
        args = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        parts = path.split("/")
        resource = parts[0]
        resource_id = parts[1] if len(parts) > 1 else None

        if request.method == "GET":
            if resource_id:
                args[resource] = resource_id
            result = await proxy.route(resource, args, "GET")
        elif request.method == "POST":
            body = await request.json()
            if resource_id:
                body[resource] = resource_id
            result = await proxy.route(resource, body, "POST")
        elif request.method == "PUT":
            body = await request.json()
            if resource_id:
                body[resource] = resource_id
            result = await proxy.route(resource, body, "PUT")
        elif request.method == "DELETE":
            if resource_id:
                args[resource] = resource_id
            result = await proxy.route(resource, args, "DELETE")
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
