#!/usr/bin/env python3
"""
Helper to call TestY MCP tools from the command line.
Keeps the MCP server process alive and sends tool calls via stdin.

Usage:
    echo '{"method":"tools/call","id":1,"params":{"name":"get_projects","arguments":{"page":1,"page_size":10}}}' | python3 call_tool.py
    echo '{"method":"tools/call","id":1,"params":{"name":"get_cases","arguments":{"project_id":22,"page":1,"page_size":20}}}' | python3 call_tool.py
"""
import json
import subprocess
import sys
import time


def call_tool(tool_name: str, arguments=None):
    if arguments is None:
        arguments = {}
    """Call a TestY MCP tool and return the result."""
    args = arguments or {}
    msg = json.dumps({
        "method": "tools/call",
        "id": 1,
        "params": {"name": tool_name, "arguments": args},
    })

    proc = subprocess.Popen(
        ["python3", "testy_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Read initial greeting
    greeting = proc.stdout.readline()
    try:
        data = json.loads(greeting)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid greeting from MCP server: {greeting}")

    # Send tool call
    proc.stdin.write(msg + "\n")
    proc.stdin.flush()

    # Read response
    resp_line = proc.stdout.readline()
    resp = json.loads(resp_line)

    proc.terminate()
    proc.wait()

    if "error" in resp.get("result", {}):
        raise RuntimeError(resp["result"]["error"])
    return resp.get("result", resp)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        tool_name = sys.argv[1]
        tool_args = json.loads(sys.argv[2]) if len(sys.argv) >= 3 else {}
        result = call_tool(tool_name, tool_args)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Read from stdin (pipe mode)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                if msg.get("method") == "tools/call":
                    name = msg["params"]["name"]
                    args = msg["params"].get("arguments", {})
                    result = call_tool(name, args)
                    resp = {
                        "jsonrpc": "2.0",
                        "id": msg.get("id", 1),
                        "result": result,
                    }
                    print(json.dumps(resp, ensure_ascii=False))
            except Exception as e:
                print(json.dumps({"error": str(e)}))
