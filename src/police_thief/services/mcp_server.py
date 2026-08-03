"""Reference-compatible FastMCP mailbox exposed by every independent peer."""

from __future__ import annotations

import queue
import threading

import anyio
import uvicorn
from fastmcp import FastMCP

TOOL_SCHEMA_VERSION = "3.0.0"


class PeerInboxes:
    """Thread-safe inbound channels consumed by the local match runtime."""

    def __init__(self) -> None:
        self.agreements: queue.Queue[dict] = queue.Queue()
        self.turns: queue.Queue[dict] = queue.Queue()
        self.audits: queue.Queue[dict] = queue.Queue()
        self.controls: queue.Queue[dict] = queue.Queue()


def build_peer_server(role: str, inboxes: PeerInboxes) -> FastMCP:
    """Expose the four tools used by the lecturer's v3 peer protocol."""
    mcp = FastMCP(name=f"police-thief-{role}")

    @mcp.tool(version=TOOL_SCHEMA_VERSION)
    def negotiate(message: dict) -> dict:
        """Receive signed terms and the opponent's public identity."""
        inboxes.agreements.put(message)
        return {"ok": True}

    @mcp.tool(version=TOOL_SCHEMA_VERSION)
    def receive_turn(message: dict) -> dict:
        """Receive one public sealed turn; private truth remains committed."""
        inboxes.turns.put(message)
        return {"ok": True}

    @mcp.tool(version=TOOL_SCHEMA_VERSION)
    def submit_audit(payload: dict) -> dict:
        """Receive end-of-game records and nonce reveals for verification."""
        inboxes.audits.put(payload)
        return {"ok": True}

    @mcp.tool(version=TOOL_SCHEMA_VERSION)
    def receive_control(message: dict) -> dict:
        """Receive enable, status, restart, or quit lifecycle messages."""
        inboxes.controls.put(message)
        return {"ok": True}

    return mcp


def run_peer_server(
    mcp: FastMCP,
    host: str,
    port: int,
    stop_event: threading.Event | None = None,
) -> None:
    """Run a peer server and optionally release its port for GUI restarts."""
    if stop_event is None:
        mcp.run(transport="http", host=host, port=port, show_banner=False)
        return

    async def serve_until_stopped() -> None:
        app = mcp.http_app(path="/mcp", transport="http")
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            lifespan="on",
            ws="websockets-sansio",
            timeout_graceful_shutdown=2,
        )
        server = uvicorn.Server(config)

        def request_shutdown() -> None:
            stop_event.wait()
            server.should_exit = True

        threading.Thread(
            target=request_shutdown,
            daemon=True,
            name="mcp-peer-shutdown",
        ).start()
        async with mcp._lifespan_manager():
            await server.serve()

    anyio.run(serve_until_stopped)
