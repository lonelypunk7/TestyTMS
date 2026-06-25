#!/usr/bin/env python3
"""
TestY TMS MCP Server
Full-featured MCP server for TestY Test Management System
Runs on Python 3.9+ using stdlib + httpx
"""
import os
import sys
import json
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("TESTY_URL")
LOGIN = os.getenv("TESTY_LOGIN")
PASSWORD = os.getenv("TESTY_PASSWORD")

_auth_state = {"token": None, "refresh": None}


class TestYClient:
    """HTTP client for TestY API with automatic auth."""

    def __init__(self):
        self.base_url = BASE_URL
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


# ── MCP Tools ──────────────────────────────────────────────────

TOOLS = [
    {"name": "login", "description": "Login with credentials and get JWT tokens"},
    {"name": "logout", "description": "Logout and invalidate tokens"},
    {"name": "get_me", "description": "Get current user info"},
    {"name": "get_projects", "description": "List all projects (page, page_size)"},
    {"name": "get_project", "description": "Get a project by ID"},
    {"name": "create_project", "description": "Create a new project (body: name, description, etc.)"},
    {"name": "update_project", "description": "Update a project (id, body)"},
    {"name": "delete_project", "description": "Delete a project by ID"},
    {"name": "get_project_members", "description": "Get project members (project_id)"},
    {"name": "get_project_progress", "description": "Get project progress stats (project_id)"},
    {"name": "get_cases", "description": "List test cases with filters (project_id, suite_id, status, label_id, assignee_id, page, page_size)"},
    {"name": "get_case", "description": "Get a single test case by ID"},
    {"name": "create_case", "description": "Create a test case (body)"},
    {"name": "update_case", "description": "Update a test case (case_id, body)"},
    {"name": "delete_case", "description": "Delete a test case by ID"},
    {"name": "search_cases", "description": "Search test cases (query)"},
    {"name": "get_case_history", "description": "Get case history (case_id)"},
    {"name": "get_case_tests", "description": "Get linked tests for a case (case_id)"},
    {"name": "copy_case", "description": "Copy a test case (case_id, body)"},
    {"name": "archive_case", "description": "Archive a test case (case_id)"},
    {"name": "get_tests", "description": "List tests (project_id, suite_id, page, page_size)"},
    {"name": "get_test", "description": "Get a test by ID"},
    {"name": "create_test", "description": "Create a test (body)"},
    {"name": "update_test", "description": "Update a test (test_id, body)"},
    {"name": "delete_test", "description": "Delete a test by ID"},
    {"name": "get_suites", "description": "List test suites (project_id, page, page_size)"},
    {"name": "get_suite", "description": "Get a suite by ID"},
    {"name": "create_suite", "description": "Create a suite (body)"},
    {"name": "update_suite", "description": "Update a suite (suite_id, body)"},
    {"name": "delete_suite", "description": "Delete a suite by ID"},
    {"name": "get_suite_cases", "description": "Get cases in a suite (suite_id)"},
    {"name": "get_suite_descendants", "description": "Get descendant suites (suite_id)"},
    {"name": "get_testplans", "description": "List test plans (page, page_size)"},
    {"name": "get_testplan", "description": "Get a test plan by ID"},
    {"name": "create_testplan", "description": "Create a test plan (body)"},
    {"name": "update_testplan", "description": "Update a test plan (plan_id, body)"},
    {"name": "delete_testplan", "description": "Delete a test plan by ID"},
    {"name": "get_results", "description": "List test results (page, page_size)"},
    {"name": "get_result", "description": "Get a result by ID"},
    {"name": "create_result", "description": "Create a test result (body)"},
    {"name": "update_result", "description": "Update a result (result_id, body)"},
    {"name": "delete_result", "description": "Delete a result by ID"},
    {"name": "get_comments", "description": "List comments (case_id, test_id, page, page_size)"},
    {"name": "create_comment", "description": "Create a comment (body)"},
    {"name": "update_comment", "description": "Update a comment (comment_id, body)"},
    {"name": "delete_comment", "description": "Delete a comment by ID"},
    {"name": "get_users", "description": "List users (page, page_size)"},
    {"name": "get_user", "description": "Get a user by ID"},
    {"name": "create_user", "description": "Create a user (body)"},
    {"name": "update_user", "description": "Update a user (user_id, body)"},
    {"name": "delete_user", "description": "Delete a user by ID"},
    {"name": "get_groups", "description": "List groups (page, page_size)"},
    {"name": "get_group", "description": "Get a group by ID"},
    {"name": "create_group", "description": "Create a group (body)"},
    {"name": "update_group", "description": "Update a group (group_id, body)"},
    {"name": "delete_group", "description": "Delete a group by ID"},
    {"name": "get_labels", "description": "List labels (page, page_size)"},
    {"name": "create_label", "description": "Create a label (body)"},
    {"name": "update_label", "description": "Update a label (label_id, body)"},
    {"name": "delete_label", "description": "Delete a label by ID"},
    {"name": "get_statuses", "description": "List statuses (page, page_size)"},
    {"name": "create_status", "description": "Create a status (body)"},
    {"name": "update_status", "description": "Update a status (status_id, body)"},
    {"name": "delete_status", "description": "Delete a status by ID"},
    {"name": "get_attachments", "description": "List attachments (page, page_size)"},
    {"name": "get_attachment", "description": "Get an attachment by ID"},
    {"name": "create_attachment", "description": "Create an attachment (body)"},
    {"name": "delete_attachment", "description": "Delete an attachment by ID"},
    {"name": "get_notifications", "description": "List notifications (page, page_size)"},
    {"name": "mark_notification_read", "description": "Mark notification as read (notification_id)"},
    {"name": "get_custom_attributes", "description": "List custom attributes (page, page_size)"},
    {"name": "get_custom_attr_content_types", "description": "Get content types for custom attributes"},
    {"name": "bulk_update_cases", "description": "Bulk update multiple test cases (body)"},
    {"name": "bulk_update_results", "description": "Bulk update multiple results (body)"},
    {"name": "bulk_update_tests", "description": "Bulk update multiple tests (body)"},
    {"name": "get_system_stats", "description": "Get system statistics"},
    {"name": "get_plugins", "description": "List installed plugins"},
]


async def handle_tool_call(name: str, args: dict, client: TestYClient) -> dict:
    """Route tool calls to endpoints based on tool name."""
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
            return await client.post("/api/v2/notifications/mark-as/", body={"id": args["notification_id"], "read": True})

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
            return await client.get(f"/api/v2/statuses/{args['status_id']}/")
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
            return await client.post(f"/api/v2/cases/{args['case_id']}/copy/", body=args.get("body", {}))
        if name == "archive_case":
            return await client.post(f"/api/v2/cases/{args['case_id']}/archive/")

        return {"error": f"Unknown tool: {name}"}

    except httpx.HTTPError as e:
        return {"error": str(e), "status_code": e.response.status_code if e.response else None}
    except Exception as e:
        return {"error": str(e)}


async def main():
    """MCP JSON-RPC over stdin/stdout."""
    client = TestYClient()
    await client.login()

    sys.stdout.write(json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"tools": TOOLS, "auth": "logged_in"}
    }) + "\n")
    sys.stdout.flush()

    try:
        while True:
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line:
                break
            msg = json.loads(line.strip())
            if msg.get("method") == "tools/call":
                name = msg["params"]["name"]
                args = msg["params"].get("arguments", {})
                result = await handle_tool_call(name, args, client)
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg["id"],
                    "result": result
                }
            elif msg.get("method") == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg["id"],
                    "result": {"protocolVersion": "2024-11-17", "serverInfo": {"name": "testy-mcp", "version": "1.0.0"}}
                }
            else:
                resp = {"jsonrpc": "2.0", "id": msg.get("id"), "result": {}}

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
    except (json.JSONDecodeError, asyncio.CancelledError):
        pass
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
