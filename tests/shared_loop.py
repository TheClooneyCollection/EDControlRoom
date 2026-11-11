"""A Starlette TestClient that runs every app on one event loop thread for the whole test run.

Starlette's own client starts a thread and a new event loop for each `with TestClient(app)` (and each
`asyncio.to_thread` executor with it), which costs more than most of the requests the tests make. This one
reuses a single loop, like the real server does; each client still runs its app's lifespan on enter and exit.
"""
from __future__ import annotations

import queue
import threading
from contextlib import nullcontext

import anyio
import anyio.from_thread
from anyio.from_thread import BlockingPortal
from starlette import testclient

_portal: BlockingPortal | None = None


def _shared_portal() -> BlockingPortal:
    global _portal
    if _portal is None:
        ready: queue.Queue[BlockingPortal] = queue.Queue()

        async def serve() -> None:
            async with BlockingPortal() as portal:
                ready.put(portal)
                await portal.sleep_until_stopped()

        # A daemon thread, so the run ends without anyone stopping the loop.
        threading.Thread(target=anyio.run, args=(serve,), name="test-asgi-loop", daemon=True).start()
        _portal = ready.get()
    return _portal


class TestClient(testclient.TestClient):
    __test__ = False

    def __enter__(self) -> TestClient:
        start = anyio.from_thread.start_blocking_portal
        anyio.from_thread.start_blocking_portal = lambda **_: nullcontext(_shared_portal())  # type: ignore[assignment]
        try:
            return super().__enter__()
        finally:
            anyio.from_thread.start_blocking_portal = start
