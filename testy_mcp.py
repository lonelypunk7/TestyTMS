#!/usr/bin/env python3
"""
TestY TMS — MCP Server (JSON-RPC 2.0 over stdio)

Реализует полный MCP-протокол:
- initialize handshake (protocol version, capabilities)
- tools/list — discovery доступных инструментов
- tools/call — вызов инструментов
- notifications/progress — прогресс-нотификации
- strict JSON-RPC 2.0 error codes

Работает на Python 3.9+, без внешних зависимостей (только stdlib + httpx).
"""
import os
import sys
import json
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.dirname(os.path.abspath(__file__)) + "/.env", override=True)

BASE_URL = os.getenv("TESTY_URL", "https://testy.megapolis-it.pro")
LOGIN = os.getenv("TESTY_LOGIN", "")
PASSWORD = os.getenv("TESTY_PASSWORD", "")

_auth_state = {"token": None, "refresh": None}


# ──────────────────────────────────────────────
# TestY API client
# ──────────────────────────────────────────────

class TestYClient:
    """HTTP client for TestY API with automatic JWT auth."""

    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Accept": "application/json"},
            follow_redirects=True,
        )

    async def login(self):
        resp = await self.client.post(
            "/api/token/",
            json={"username": LOGIN, "password": PASSWORD},
        )
        resp.raise_for_status()
        data = resp.json()
        _auth_state["token"] = data.get("access")
        _auth_state["refresh"] = data.get("refresh")
        return _auth_state["token"]

    async def refresh(self):
        if not _auth_state.get("refresh"):
            return await self.login()
        resp = await self.client.post(
            "/api/token/refresh/",
            json={"refresh": _auth_state["refresh"]},
        )
        resp.raise_for_status()
        data = resp.json()
        _auth_state["token"] = data.get("access")
        return _auth_state["token"]

    async def _headers(self):
        token = _auth_state.get("token")
        return {"Authorization": f"Bearer {token}"} if token else {}

    async def get(self, path, params=None):
        h = await self._headers()
        r = await self.client.get(path, params=params or {}, headers=h)
        r.raise_for_status()
        return r.json()

    async def post(self, path, body=None):
        h = await self._headers()
        r = await self.client.post(path, json=body or {}, headers=h)
        r.raise_for_status()
        return r.json()

    async def put(self, path, body=None):
        h = await self._headers()
        r = await self.client.put(path, json=body or {}, headers=h)
        r.raise_for_status()
        return r.json()

    async def patch(self, path, body=None):
        h = await self._headers()
        r = await self.client.patch(path, json=body or {}, headers=h)
        r.raise_for_status()
        return r.json()

    async def delete(self, path):
        h = await self._headers()
        r = await self.client.delete(path, headers=h)
        r.raise_for_status()
        return r.json()

    async def close(self):
        await self.client.aclose()


# ──────────────────────────────────────────────
# MCP Protocol — Constants
# ──────────────────────────────────────────────

MCP_PROTOCOL_VERSION = "2024-11-17"
MCP_SERVER_NAME = "testy-mcp"
MCP_SERVER_VERSION = "2.0.0"

# JSON-RPC 2.0 error codes
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL = -32603
ERROR_SERVER_NOT_INITIALIZED = -32002
ERROR_PROGRESS = -32098

# Custom application error codes (>= -32000 and < -32099)
ERROR_UNKNOWN_TOOL = -32001
ERROR_AUTH_REQUIRED = -32002
ERROR_API_ERROR = -32003


# ──────────────────────────────────────────────
# MCP Server — Capabilities & Tools
# ──────────────────────────────────────────────

CAPABILITIES = {
    "tools": {"listChanged": False},
    "notifications": {
        "initialized": {"method": "notifications/initialized"},
        "progress": {"method": "notifications/progress"},
    },
}

# Full tool list — matches the TestY API endpoints
TOOLS = [
    {"name": "login", "description": "Login with credentials and get JWT tokens", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "logout", "description": "Logout and invalidate tokens", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_me", "description": "Get current user info", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_system_stats", "description": "Get system statistics", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_plugins", "description": "List installed plugins", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_custom_attr_content_types", "description": "Get content types for custom attributes", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_projects", "description": "List all projects (page, page_size)", "inputSchema": {"type": "object", "properties": {"page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "get_project", "description": "Get a project by ID", "inputSchema": {"type": "object", "properties": {"project_id": {"type": "integer"}}}},
    {"name": "create_project", "description": "Create a new project", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "update_project", "description": "Update a project", "inputSchema": {"type": "object", "properties": {"project_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "delete_project", "description": "Delete a project by ID", "inputSchema": {"type": "object", "properties": {"project_id": {"type": "integer"}}}},
    {"name": "get_project_members", "description": "Get project members", "inputSchema": {"type": "object", "properties": {"project_id": {"type": "integer"}}}},
    {"name": "get_project_progress", "description": "Get project progress stats", "inputSchema": {"type": "object", "properties": {"project_id": {"type": "integer"}}}},
    {"name": "get_cases", "description": "List test cases with filters (project_id, suite_id, status, label_id, assignee_id, page, page_size)", "inputSchema": {"type": "object", "properties": {"project_id": {"type": "integer"}, "suite_id": {"type": "integer"}, "status": {"type": "string"}, "page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "get_case", "description": "Get a single test case by ID", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "integer"}}}},
    {"name": "create_case", "description": "Create a test case", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "update_case", "description": "Update a test case", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "delete_case", "description": " Delete a test case by ID", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "integer"}}}},
    {"name": "search_cases", "description": "Search test cases (query)", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}},
    {"name": "get_case_history", "description": "Get case history", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "integer"}}}},
    {"name": "get_case_tests", "description": "Get linked tests for a case", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "integer"}}}},
    {"name": "copy_case", "description": "Copy a test case", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "archive_case", "description": "Archive a test case", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "integer"}}}},
    {"name": "get_tests", "description": "List tests", "inputSchema": {"type": "object", "properties": {"project_id": {"type": "integer"}, "suite_id": {"type": "integer"}, "page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "get_test", "description": " Get a test by ID", "inputSchema": {"type": "object", "properties": {"test_id": {"type": "integer"}}}},
    {"name": "create_test", "description": "Create a test", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "update_test", "description": "Update a test", "inputSchema": {"type": "object", "properties": {"test_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "delete_test", "description": "Delete a test by ID", "inputSchema": {"type": "object", "properties": {"test_id": {"type": "integer"}}}},
    {"name": "get_suites", "description": "List test suites", "inputSchema": {"type": "object", "properties": {"project_id": {"type": "integer"}, "page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "get_suite", "description": "Get a suite by ID", "inputSchema": {"type": "object", "properties": {"suite_id": {"type": "integer"}}}},
    {"name": "create_suite", "description": "Create a suite", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "update_suite", "description": "Update a suite", "inputSchema": {"type": "object", "properties": {"suite_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "delete_suite", "description": "Delete a suite by ID", "inputSchema": {"type": "object", "properties": {"suite_id": {"type": "integer"}}}},
    {"name": "get_suite_cases", "description": "Get cases in a suite", "inputSchema": {"type": "object", "properties": {"suite_id": {"type": "integer"}}}},
    {"name": "get_suite_descendants", "description": "Get descendant suites", "inputSchema": {"type": "object", "properties": {"suite_id": {"type": "integer"}}}},
    {"name": "get_testplans", "description": "List test plans", "inputSchema": {"type": "object", "properties": {"page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "get_testplan", "description": "Get a test plan by ID", "inputSchema": {"type": "object", "properties": {"plan_id": {"type": "integer"}}}},
    {"name": "create_testplan", "description": "Create a test plan", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "update_testplan", "description": "Update a test plan", "inputSchema": {"type": "object", "properties": {"plan_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "delete_testplan", "description": "Delete a test plan by ID", "inputSchema": {"type": "object", "properties": {"plan_id": {"type": "integer"}}}},
    {"name": "get_results", "description": "List test results", "inputSchema": {"type": "object", "properties": {"page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "get_result", "description": "Get a result by ID", "inputSchema": {"type": "object", "properties": {"result_id": {"type": "integer"}}}},
    {"name": "create_result", "description": "Create a test result", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "update_result", "description": "Update a result", "inputSchema": {"type": "object", "properties": {"result_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "delete_result", "description": "Delete a result by ID", "inputSchema": {"type": "object", "properties": {"result_id": {"type": "integer"}}}},
    {"name": "get_comments", "description": "List comments", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "integer"}, "test_id": {"type": "integer"}, "page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "create_comment", "description": "Create a comment", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "update_comment", "description": "Update a comment", "inputSchema": {"type": "object", "properties": {"comment_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "delete_comment", "description": "Delete a comment by ID", "inputSchema": {"type": "object", "properties": {"comment_id": {"type": "integer"}}}},
    {"name": "get_users", "description": "List users", "inputSchema": {"type": "object", "properties": {"page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "get_user", "description": "Get a user by ID", "inputSchema": {"type": "object", "properties": {"user_id": {"type": "integer"}}}},
    {"name": "create_user", "description": "Create a user", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "update_user", "description": "Update a user", "inputSchema": {"type": "object", "properties": {"user_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "delete_user", "description": "Delete a user by ID", "inputSchema": {"type": "object", "properties": {"user_id": {"type": "integer"}}}},
    {"name": "get_groups", "description": "List groups", "inputSchema": {"type": "object", "properties": {"page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "get_group", "description": "Get a group by ID", "inputSchema": {"type": "object", "properties": {"group_id": {"type": "integer"}}}},
    {"name": "create_group", "description": "Create a group", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "update_group", "description": "Update a group", "inputSchema": {"type": "object", "properties": {"group_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "delete_group", "description": "Delete a group by ID", "inputSchema": {"type": "object", "properties": {"group_id": {"type": "integer"}}}},
    {"name": "get_labels", "description": "List labels", "inputSchema": {"type": "object", "properties": {"page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "create_label", "description": "Create a label", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "update_label", "description": "Update a label", "inputSchema": {"type": "object", "properties": {"label_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "delete_label", "description": "Delete a label by ID", "inputSchema": {"type": "object", "properties": {"label_id": {"type": "integer"}}}},
    {"name": "get_statuses", "description": "List statuses", "InputSchema": {"type": "object", "properties": {"page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "create_status", "description": "Create a status", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "update_status", "description": "Update a status", "inputSchema": {"type": "object", "properties": {"status_id": {"type": "integer"}, "body": {"type": "object"}}}},
    {"name": "delete_status", "description": "Delete a status by ID", "inputSchema": {"type": "object", "properties": {"status_id": {"type": "integer"}}}},
    {"name": "get_attachments", "description": "List attachments", "inputSchema": {"type": "object", "properties": {"page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "get_attachment", "description": "Get an attachment by ID", "inputSchema": {"type": "object", "properties": {"attachment_id": {"type": "integer"}}}},
    {"name": "create_attachment", "description": "Create an attachment", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "delete_attachment", "description": "Delete an attachment by ID", "inputSchema": {"type": "object", "properties": {"attachment_id": {"type": "integer"}}}},
    {"name": "get_notifications", "description": "List notifications", "inputSchema": {"type": "object", "properties": {"page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "mark_notification_read", "description": "Mark notification as read", "inputSchema": {"type": "object", "properties": {"notification_id": {"type": "integer"}}}},
    {"name": "get_custom_attributes", "description": "List custom attributes", "inputSchema": {"type": "object", "properties": {"page": {"type": "integer"}, "page_size": {"type": "integer"}}}},
    {"name": "bulk_update_cases", "description": "Bulk update multiple test cases", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "bulk_update_results", "description": "Bulk update multiple results", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
    {"name": "bulk_update_tests", "description": "Bulk update multiple tests", "inputSchema": {"type": "object", "properties": {"body": {"type": "object"}}}},
]


# ──────────────────────────────────────────────
# JSON-RPC 2.0 helpers
# ──────────────────────────────────────────────

def make_response(id, result):
    """Create a JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": id, "result": result}


def make_error(id, code, message, data=None):
    """Create a JSON-RPC 2.0 error response."""
    obj = {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}
    if data:
        obj["error"]["data"] = data
    return obj


def make_notification(method, params=None):
    """Create a JSON-RPC 2.0 notification (no 'id' field)."""
    obj = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        obj["params"] = params
    else:
        obj["params"] = {}
    return obj


# ──────────────────────────────────────────────
# Tool routing
# ──────────────────────────────────────────────

async def handle_tool_call(name: str, args: dict, client: TestYClient) -> dict:
    """Route tool calls to TestY API endpoints."""
    try:
        # --- Special endpoints (no simple mapping) ---
        if name == "login":
            return await client.login()
        if name == "logout":
            if _auth_state.get("refresh"):
                await client.post("/auth/logout/", body={"refresh": _auth_state["refresh"]})
            _auth_state.clear()
            return {"status": "ok"}
        if name == "get_me":
            return await client.get("/api/v2/users/me/")
        if name == "get_system_stats":
            return await client.get("/api/v2/system/statistics/")
        if name == "get_plugins":
            return await client.get("/plugins/")
        if name == "get_custom_attr_content_types":
            return await client.get("/api/v2/custom-attributes/content-types/")
        if name == "mark_notification_read":
            return await client.post(
                "/api/v2/notifications/mark-as/",
                body={"id": args.get("notification_id"), "read": True},
            )

        # --- List endpoints with pagination ---
        list_resources = [
            "get_projects", "get_users", "get_groups", "get_labels", "get_statuses",
            "get_cases", "get_tests", "get_suites", "get_testplans", "get_results",
            "get_comments", "get_notifications", "get_attachments", "get_custom_attributes",
        ]
        if name in list_resources:
            resource = name.replace("get_", "")
            page = args.get("page", 1)
            page_size = args.get("page_size", 20)
            extra = {k: v for k, v in args.items() if k not in ("page", "page_size")}
            path = f"/api/v2/{resource}/"
            params = {"page": page, "page_size": page_size}
            if extra:
                params.update(extra)
            return await client.get(path, params=params)

        # --- Get-by-ID endpoints ---
        get_by_id = [
            "get_project", "get_case", "get_test", "get_suite", "get_testplan",
            "get_result", "get_user", "get_group", "get_attachment",
        ]
        if name in get_by_id:
            id_key = name.replace("get_", "").rstrip("s")
            id_val = args.get(id_key) or args.get(f"{id_key}_id")
            if not id_val:
                return {"error": f"Missing {id_key} ID"}
            return await client.get(f"/api/v2/{id_key}/{id_val}/")

        # --- Special get endpoints ---
        if name == "get_case_history":
            return await client.get(f"/api/v2/cases/{args['case_id']}/history/")
        if name == "get_case_tests":
            return await client.get(f"/api/v2/cases/{args['case_id']}/tests/")
        if name == "get_suite_cases":
            return await client.get(f"/api/v2/suites/{args['suite_id']}/cases/")
        if name == "get_suite_descendants":
            return await client.get(f"/api/v2/suites/{args['suite_id']}/descendants-tree/")
        if name == "get_project_members":
            return await client.get(f"/api/v2/projects/{args['project_id']}/members/")
        if name == "get_project_progress":
            return await client.get(f"/api/v2/projects/{args['project_id']}/progress/")
        if name == "get_label":
            return await client.get(f"/api/v2/labels/{args['label_id']}/")
        if name == "get_status":
            return await client.get(f"/api/v2/statuses/{args['_status_id']}/")
        if name == "get_testplan":
            return await client.get(f"/api/v2/testplans/{args['plan_id']}/")
        if name == "get_result":
            return await client.get(f"/api/v2/results/{args['result_id']}/")
        if name == "get_user":
            return await client.get(f"/api/v2/users/{args['user_id']}/")
        if name == "get_group":
            return await client.get(f"/api/v2/groups/{args['group_id']}/")
        if name == "get_attachment":
            return await client.get(f"/api/v2/attachments/{args['attachment_id']}/")

        # --- Create endpoints ---
        create_paths = {
            "create_project": "/api/v2/projects/",
            "create_case": "/api/v2/cases/",
            "create_test": "/api/v2/tests/",
            "create_suite": "/api/v2/suites/",
            "create_testplan": "/api/v2/testplans/",
            "create_result": "/api/v2/results/",
            "create_user": "/api/v2/users/",
            "create_group": "/api/v2/groups/",
            "create_label": "/api/v2/labels/",
            "create_status": "/api/v2/statuses/",
            "create_attachment": "/api/v2/attachments/",
            "create_comment": "/api/v2/comments/",
        }
        if name in create_paths:
            return await client.post(create_paths[name], body=args.get("body", {}))

        # --- Update endpoints ---
        update_paths = {
            "update_project": "/api/v2/projects/",
            "update_case": "/api/v2/cases/",
            "update_test": "/api/v2/tests/",
            "update_suite": "/api/v2/suites/",
            "update_testplan": "/api/v2/testplans/",
            "update_result": "/api/v2/results/",
            "update_user": "/api/v2/users/",
            "update_group": "/api/v2/groups/",
            "update_label": "/api/v2/labels/",
            "update_status": "/api/v2/statuses/",
            "update_comment": "/api/v2/comments/",
        }
        if name in update_paths:
            resource = name.replace("update_", "").rstrip("s")
            id_val = args.get(resource) or args.get(f"{resource}_id")
            return await client.put(f"{update_paths[name]}{id_val}/", body=args.get("body", {}))

        # --- Delete endpoints ---
        delete_paths = {
            "delete_project": "/api/v2/projects/",
            "delete_case": "/api/v2/cases/",
            "delete_test": "/api/v2/tests/",
            "delete_suite": "/api/v2/suites/",
            "delete_testplan": "/api/v2/testplans/",
            "delete_result": "/api/v2/results/",
            "delete_user": "/api/v2/users/",
            "delete_group": "/api/v2/groups/",
            "delete_label": "/api/v2/labels/",
            "delete_status": "/api/v2/statuses/",
            "delete_attachment": "/api/v2/attachments/",
            "delete_comment": "/api/v2/comments/",
        }
        if name in delete_paths:
            resource = name.replace("delete_", "").rstrip("s")
            id_val = args.get(resource) or args.get(f"{resource}_id")
            return await client.delete(f"{delete_paths[name]}{id_val}/")

        # --- Bulk operations ---
        if name == "bulk_update_cases":
            return await client.put("/api/v2/cases/bulk-update/", body=args.get("body", {}))
        if name == "bulk_update_results":
            return await client.put("/api/v2/results/", body=args.get("body", {}))
        if name == "bulk_update_tests":
            return await client.put("/api/v2/tests/bulk-update/", body=args.get("body", {}))

        # --- Misc special endpoints ---
        if name == "copy_case":
            return await client.post(
                f"/api/v2/cases/{args['case_id']}/copy/",
                body=args.get("body", {}),
            )
        if name == "archive_case":
            return await client.post((
                f"/api/v2/cases/{args['case_id']}/archive/"
            ))

        return {"error": f"Unknown tool: {name}"}

    except httpx.HTTPError as e:
        return {
            "error": str(e),
            "status_code": e.response.status_code if e.response else None,
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# MCP Server — main loop
# ──────────────────────────────────────────────

async def main():
    """MCP JSON-RPC 2.0 over stdio."""
    client = TestYClient()
    await client.login()

    # ── initialize handshake ──
    # The spec says: server sends ServerInfo on first initialize request.
    # We proactively send it as the first line (the spec also allows
    # sending it as a response to initialize).
    sys.stdout.write(
        json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": CAPABILITIES,
                "serverInfo": {
                    "name": MCP_SERVER_NAME,
                    "version": MCP_SERVER_VERSION,
                },
            },
        }) + "\n"
    )
    sys.stdout.flush()

    try:
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                break
            msg = json.loads(line.strip())

            msg_id = msg.get("id")
            method = msg.get("method")

            # ── initialize (already handled above, but accept re-init) ──
            if method == "initialize":
                resp = make_response(
                    msg_id,
                    {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": CAPABILITIES,
                        "serverInfo": {
                            "name": MCP_SERVER_NAME,
                            "version": MCP_SERVER_VERSION,
                        },
                    },
                )
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
                # After initialize, send initialized notification
                sys.stdout.write(
                    json.dumps(make_notification("notifications/initialized")) + "\n"
                )
                sys.stdout.flush()
                continue

            # ── initialized notification (no response needed) ──
            if method == "notifications/initialized":
                continue

            # ── ping ──
            if method == "ping":
                sys.stdout.write(
                    json.dumps(make_response(msg_id, {})) + "\n"
                )
                sys.stdout.flush()
                continue

            # ── tools/list ──
            if method == "tools/list":
                sys.stdout.write(
                    json.dumps(make_response(msg_id, {"tools": TOOLS})) + "\n"
                )
                sys.stdout.flush()
                continue

            # ── tools/get ──
            if method == "tools/get":
                tool_name = msg.get("params", {}).get("name")
                tool = next((t for t in TOOLS if t["name"] == tool_name), None)
                if tool:
                    sys.stdout.write(
                        json.dumps(make_response(msg_id, {"tool": tool})) + "\n"
                    )
                else:
                    sys.stdout.write(
                        json.dumps(make_error(msg_id, ERROR_UNKNOWN_TOOL, f"Tool not found: {tool_name}")) + "\n"
                    )
                sys.stdout.flush()
                continue

            # ── tools/call ──
            if method == "tools/call":
                name = msg["params"]["name"]
                args = msg["params"].get("arguments", {})
                result = await handle_tool_call(name, args, client)
                sys.stdout.write(json.dumps(make_response(msg_id, result)) + "\n")
                sys.stdout.flush()
                continue

            # ── notifications/progress ──
            if method == "notifications/progress":
                continue

            # ── Default: unknown method ──
            sys.stdout.write(
                json.dumps(make_error(msg_id, ERROR_METHOD_NOT_FOUND, f"Method not found: {method}")) + "\n"
            )
            sys.stdout.flush()

    except (json.JSONDecodeError, asyncio.CancelledError):
        pass
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
