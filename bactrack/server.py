"""Generic local HTTP API for BACtrack breath tests."""

import asyncio
import copy
import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .client import BACtrackClient


logger = logging.getLogger(__name__)

TERMINAL_STATUSES = frozenset(
    {"complete", "cancelled", "blow_error", "timeout", "error"}
)

NOTIFICATION_STATUSES = {
    "countdown": "countdown",
    "start_blow": "blow",
    "keep_blowing": "blow",
    "analyzing": "analyzing",
    "finalizing": "analyzing",
    "wrapping_up": "analyzing",
    "result": "complete",
    "cancelled": "cancelled",
    "blow_error": "blow_error",
    "timeout": "timeout",
    "error": "error",
}


def utc_now() -> str:
    """Return an API timestamp with an explicit UTC offset."""
    return datetime.now(timezone.utc).isoformat()


def normalize_status(notification_type: str) -> Optional[str]:
    """Map a decoded device notification type to a public lifecycle status."""
    return NOTIFICATION_STATUSES.get(notification_type)


@dataclass
class TestState:
    test_id: str
    status: str
    message: str
    bac: Optional[float]
    raw_result_packet: Optional[str]
    latest_raw_notification: Optional[str]
    notification_history: List[Dict[str, Any]]
    error: Optional[str]
    metadata: Any
    created_at: str
    updated_at: str

    def serialize(self) -> Dict[str, Any]:
        """Create a detached, JSON-compatible state snapshot."""
        return copy.deepcopy(asdict(self))


@dataclass
class TestRecord:
    state: TestState
    subscribers: Set[asyncio.Queue] = field(default_factory=set)
    task: Optional[asyncio.Task] = None


class ActiveTestError(RuntimeError):
    """Raised when another test already owns the device."""


class TestNotFoundError(KeyError):
    """Raised when a test ID is not present in memory."""


class CreateTestRequest(BaseModel):
    metadata: Any = Field(default_factory=dict)


class TestManager:
    """Own in-memory lifecycle state and background BACtrack work."""

    def __init__(self, client_factory: Callable[[], BACtrackClient] = BACtrackClient):
        self.client_factory = client_factory
        self.records: Dict[str, TestRecord] = {}
        self._create_lock = threading.Lock()

    async def create_test(self, metadata: Any = None) -> Dict[str, Any]:
        with self._create_lock:
            if any(
                record.state.status not in TERMINAL_STATUSES
                for record in self.records.values()
            ):
                raise ActiveTestError("Another BAC test is already active")

            now = utc_now()
            test_id = str(uuid4())
            state = TestState(
                test_id=test_id,
                status="scanning",
                message="Scanning for a BACtrack device",
                bac=None,
                raw_result_packet=None,
                latest_raw_notification=None,
                notification_history=[],
                error=None,
                metadata={} if metadata is None else copy.deepcopy(metadata),
                created_at=now,
                updated_at=now,
            )
            record = TestRecord(state=state)
            self.records[test_id] = record
            self._log_transition(record)
            record.task = asyncio.create_task(self._run_test(record))
            return state.serialize()

    def get_test(self, test_id: str) -> Dict[str, Any]:
        return self._record(test_id).state.serialize()

    def subscribe(self, test_id: str) -> asyncio.Queue:
        record = self._record(test_id)
        queue: asyncio.Queue = asyncio.Queue()
        record.subscribers.add(queue)
        queue.put_nowait(record.state.serialize())
        return queue

    def unsubscribe(self, test_id: str, queue: asyncio.Queue) -> None:
        record = self.records.get(test_id)
        if record is not None:
            record.subscribers.discard(queue)

    def handle_notification(self, record: TestRecord, notification: Dict[str, Any]) -> None:
        decoded = copy.deepcopy(notification)
        record.state.notification_history.append(decoded)

        raw_hex = decoded.get("raw_hex")
        if raw_hex is not None:
            record.state.latest_raw_notification = raw_hex

        notification_type = decoded.get("type", "unknown")
        status = normalize_status(notification_type)
        if status is not None:
            record.state.status = status
        record.state.message = decoded.get("message", record.state.message)

        if notification_type == "result":
            record.state.bac = decoded.get("value")
            record.state.raw_result_packet = raw_hex
        if status == "error":
            record.state.error = record.state.message

        record.state.updated_at = utc_now()
        if status is not None:
            self._log_transition(record)
        self._publish(record)

    async def _run_test(self, record: TestRecord) -> None:
        client = None
        try:
            client = self.client_factory()
            connected = await client.connect()
            if not connected:
                raise RuntimeError("BACtrack device did not connect")

            self._transition(record, "connected", "Connected to BACtrack device")
            result = await client.take_test(
                callback=lambda notification: self.handle_notification(record, notification)
            )

            if record.state.status not in TERMINAL_STATUSES:
                if result is not None:
                    self._transition(
                        record,
                        "complete",
                        "BAC test complete",
                        bac=result,
                    )
                else:
                    self._transition(
                        record,
                        "error",
                        "BAC test ended without a result",
                        error="BAC test ended without a result",
                    )
        except asyncio.CancelledError:
            self._transition(record, "cancelled", "BAC test cancelled")
            raise
        except asyncio.TimeoutError:
            logger.exception(
                "BACtrack test timed out",
                extra={"event": "test_timeout", "test_id": record.state.test_id},
            )
            self._transition(record, "timeout", "BAC test timed out")
        except Exception as exc:
            logger.exception(
                "BACtrack test failed",
                extra={"event": "test_exception", "test_id": record.state.test_id},
            )
            self._transition(record, "error", str(exc), error=str(exc))
        finally:
            if client is not None:
                try:
                    await client.disconnect()
                except Exception:
                    logger.exception(
                        "BACtrack disconnect failed",
                        extra={
                            "event": "disconnect_exception",
                            "test_id": record.state.test_id,
                        },
                    )

    def _transition(
        self,
        record: TestRecord,
        status: str,
        message: str,
        bac: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        record.state.status = status
        record.state.message = message
        if bac is not None:
            record.state.bac = bac
        if error is not None:
            record.state.error = error
        record.state.updated_at = utc_now()
        self._log_transition(record)
        self._publish(record)

    def _publish(self, record: TestRecord) -> None:
        for queue in tuple(record.subscribers):
            queue.put_nowait(record.state.serialize())

    def _record(self, test_id: str) -> TestRecord:
        try:
            return self.records[test_id]
        except KeyError:
            raise TestNotFoundError(test_id)

    @staticmethod
    def _log_transition(record: TestRecord) -> None:
        logger.info(
            "BACtrack lifecycle transition",
            extra={
                "event": "lifecycle_transition",
                "test_id": record.state.test_id,
                "status": record.state.status,
            },
        )


def format_sse(state: Dict[str, Any]) -> str:
    """Format one complete state snapshot as an SSE event."""
    event = "terminal" if state["status"] in TERMINAL_STATUSES else "state"
    data = json.dumps(state, separators=(",", ":"), sort_keys=True)
    return f"event: {event}\ndata: {data}\n\n"


def create_app(
    client_factory: Callable[[], BACtrackClient] = BACtrackClient,
) -> FastAPI:
    api = FastAPI(title="BACtrack local API", version="1.0.0")
    manager = TestManager(client_factory=client_factory)
    api.state.test_manager = manager

    @api.get("/health")
    async def health():
        return {"status": "ok"}

    @api.post("/tests", status_code=202)
    async def create_test(request: Optional[CreateTestRequest] = None):
        try:
            metadata = request.metadata if request is not None else {}
            return await manager.create_test(metadata=metadata)
        except ActiveTestError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    @api.get("/tests/{test_id}")
    async def get_test(test_id: str):
        try:
            return manager.get_test(test_id)
        except TestNotFoundError:
            raise HTTPException(status_code=404, detail="Test not found")

    @api.get("/tests/{test_id}/events")
    async def test_events(test_id: str):
        try:
            queue = manager.subscribe(test_id)
        except TestNotFoundError:
            raise HTTPException(status_code=404, detail="Test not found")

        async def event_stream():
            try:
                while True:
                    state = await queue.get()
                    yield format_sse(state)
                    if state["status"] in TERMINAL_STATUSES:
                        return
            finally:
                manager.unsubscribe(test_id, queue)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return api


app = create_app()
