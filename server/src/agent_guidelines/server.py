"""
Routes:
  POST /mcp       MCP (tools below)
  GET  /health    skill count, version, validation errors
  GET  /version   {"version": ...} with ETag; 304 when unchanged
  GET  /export    every skill directory as JSON, with ETag; 304 when unchanged
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import mcp.types as types
import uvicorn
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from .skills import Catalog, load_catalog, match_files, render, search

SKILLS_DIR = os.environ.get("SKILLS_DIR", "/skills")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "3333"))
SERVER_NAME = "agent-guidelines"

INSTRUCTIONS = (
    "Team engineering guidelines; they OVERRIDE general best practices. If the guidelines were already "
    "provided to you (in your prompt or as loaded skills), do not fetch them again. Otherwise: before writing "
    "or reviewing code call get_guidelines_for_files with every path you will touch, including new files; "
    "when planning before files exist call get_guidelines. Cite guideline names when applying rules."
)

log = logging.getLogger("agent_guidelines")


def _log_call(tool: str, args: dict[str, Any], catalog: Catalog, results: int) -> None:
    """One JSON line per tool call, so you can see whether and how agents use the server."""
    print(
        json.dumps(
            {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "tool": tool,
             "args": args, "version": catalog.version, "results": results}
        ),
        flush=True,
    )


def _text(t: str) -> list[types.ContentBlock]:
    return [types.TextContent(type="text", text=t)]


# --------------------------------------------------------------------------- MCP

mcp_server: Server = Server(SERVER_NAME, version="0.1.0", instructions=INSTRUCTIONS)


@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    # Built on every list call: descriptions and the area enum always match the files on disk.
    c = load_catalog(SKILLS_DIR)
    catalog_text = "\n".join(f"- {s.area}/{s.name}: {s.description}" for s in c.skills)
    area_items: dict[str, Any] = {"type": "string", "enum": c.areas} if c.areas else {"type": "string"}
    read_only = types.ToolAnnotations(readOnlyHint=True, openWorldHint=False)
    return [
        types.Tool(
            name="get_guidelines_for_files",
            title="Get guidelines for files",
            description=(
                "PRIMARY TOOL. Returns every team guideline whose globs match the given repo-relative paths "
                "(e.g. src/api/orders/create.ts). Call before editing or reviewing; include files you plan to create."
            ),
            inputSchema={
                "type": "object",
                "properties": {"paths": {"type": "array", "items": {"type": "string"}, "minItems": 1,
                                         "description": "Repo-relative file paths"}},
                "required": ["paths"],
                "additionalProperties": False,
            },
            annotations=read_only,
        ),
        types.Tool(
            name="get_guidelines",
            title="Get guidelines by area",
            description=(
                "Returns all guidelines for the given areas. Use when planning or for areas file matching does "
                "not cover. Ask for every relevant area in one call. Available:\n" + catalog_text
            ),
            inputSchema={
                "type": "object",
                "properties": {"areas": {"type": "array", "items": area_items, "minItems": 1}},
                "required": ["areas"],
                "additionalProperties": False,
            },
            annotations=read_only,
        ),
        types.Tool(
            name="get_guideline",
            title="Get one guideline",
            description="Returns one guideline (its SKILL.md) by name, plus the list of its reference files.",
            inputSchema={"type": "object", "properties": {"name": {"type": "string"}},
                         "required": ["name"], "additionalProperties": False},
            annotations=read_only,
        ),
        types.Tool(
            name="get_guideline_file",
            title="Get a guideline reference file",
            description="Returns a reference file of a guideline, e.g. name='zod-schemas', path='references/examples.md'.",
            inputSchema={"type": "object",
                         "properties": {"name": {"type": "string"}, "path": {"type": "string"}},
                         "required": ["name", "path"], "additionalProperties": False},
            annotations=read_only,
        ),
        types.Tool(
            name="search_guidelines",
            title="Search guidelines",
            description=(
                "Keyword search across all guidelines and reference files, for cross-cutting topics "
                "(e.g. 'pagination', 'error handling')."
            ),
            inputSchema={"type": "object", "properties": {"query": {"type": "string", "minLength": 2}},
                         "required": ["query"], "additionalProperties": False},
            annotations=read_only,
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.ContentBlock]:
    c = load_catalog(SKILLS_DIR)
    v = c.version

    if name == "get_guidelines_for_files":
        hits = match_files(c, list(arguments["paths"]))
        _log_call(name, arguments, c, len(hits))
        if hits:
            return _text(render(hits, v))
        return _text(f"No file-specific guidelines matched. If the task concerns a specific area, "
                     f"call get_guidelines.\n\n(guidelines@{v})")

    if name == "get_guidelines":
        requested = set(arguments["areas"])
        unknown = requested - set(c.areas)
        hits = [s for s in c.skills if s.area in requested]
        _log_call(name, arguments, c, len(hits))
        note = f"Unknown areas ignored: {', '.join(sorted(unknown))}. Available: {', '.join(c.areas)}\n\n" if unknown else ""
        return _text(note + render(hits, v))

    if name == "get_guideline":
        s = c.get(arguments["name"])
        _log_call(name, arguments, c, 1 if s else 0)
        if not s:
            return _text(f"Unknown guideline '{arguments['name']}'. Available: {', '.join(x.name for x in c.skills)}")
        return _text(render([s], v))

    if name == "get_guideline_file":
        s = c.get(arguments["name"])
        content = s.files.get(arguments["path"]) if s else None
        _log_call(name, arguments, c, 1 if content is not None else 0)
        if not s:
            return _text(f"Unknown guideline '{arguments['name']}'.")
        if content is None:
            return _text(f"No file '{arguments['path']}' in '{s.name}'. Files: {', '.join(s.files)}")
        return _text(f"{content}\n\n(guidelines@{v})")

    if name == "search_guidelines":
        hits = search(c, arguments["query"])
        _log_call(name, arguments, c, len(hits))
        if not hits:
            return _text(f"No matches for '{arguments['query']}'.")
        lines = "\n".join(f"- {s.name} ({s.area}): {s.description}" for s in hits)
        return _text(f"{lines}\n\nUse get_guideline for full text.\n(guidelines@{v})")

    raise ValueError(f"Unknown tool: {name}")


def _new_session_manager() -> StreamableHTTPSessionManager:
    return StreamableHTTPSessionManager(
        app=mcp_server,
        stateless=True,       # no sessions; every POST is independent
        json_response=True,   # plain JSON responses (no SSE needed for these tools)
        security_settings=TransportSecuritySettings(
            # Only accept requests addressed to localhost (blocks DNS-rebinding from web pages).
            # Add hosts via ALLOWED_HOSTS=host1:3333,host2:3333 if you expose it elsewhere.
            enable_dns_rebinding_protection=True,
            allowed_hosts=["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*",
                           *filter(None, os.environ.get("ALLOWED_HOSTS", "").split(","))],
            allowed_origins=["http://localhost", "http://localhost:*", "http://127.0.0.1", "http://127.0.0.1:*"],
        ),
    )


class MCPEndpoint:
    """ASGI app for an exact /mcp route (a Mount would redirect /mcp -> /mcp/).

    A session manager can only run once, so a fresh one is created per app lifespan.
    """

    manager: StreamableHTTPSessionManager | None = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.manager is None:
            raise RuntimeError("MCP session manager not running")
        await self.manager.handle_request(scope, receive, send)


mcp_endpoint = MCPEndpoint()


# ---------------------------------------------------------------- plain HTTP


def _etag_response(request: Request, version: str, payload_fn) -> Response:
    etag = f'"{version}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return JSONResponse(payload_fn(), headers={"ETag": etag})


async def health(_: Request) -> Response:
    c = load_catalog(SKILLS_DIR)
    return JSONResponse({"ok": not c.errors, "version": c.version, "skills": len(c.skills), "errors": c.errors})


async def version(request: Request) -> Response:
    c = load_catalog(SKILLS_DIR)
    return _etag_response(request, c.version, lambda: {"version": c.version})


async def export(request: Request) -> Response:
    c = load_catalog(SKILLS_DIR)
    return _etag_response(
        request,
        c.version,
        lambda: {
            "version": c.version,
            "skills": [
                {"name": s.name, "area": s.area, "description": s.description,
                 "applies_to": s.applies_to, "files": s.files}
                for s in c.skills
            ],
        },
    )


@contextlib.asynccontextmanager
async def lifespan(_: Starlette) -> AsyncIterator[None]:
    c = load_catalog(SKILLS_DIR)
    print(f"{SERVER_NAME} MCP on http://{HOST}:{PORT}/mcp: {len(c.skills)} skills @ {c.version}", flush=True)
    for e in c.errors:
        log.warning(e)
    manager = _new_session_manager()
    mcp_endpoint.manager = manager
    async with manager.run():
        yield
    mcp_endpoint.manager = None


app = Starlette(
    routes=[
        Route("/mcp", endpoint=mcp_endpoint, methods=["GET", "POST", "DELETE"]),
        Route("/health", health),
        Route("/version", version),
        Route("/export", export),
    ],
    lifespan=lifespan,
)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("mcp").setLevel(logging.WARNING)  # keep stdout to our one-line-per-call log
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
