"""Signal WebSocket client — connects to FAS Smart signal server."""
import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Optional, Callable, Deque, List, Dict, Any

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore

logger = logging.getLogger(__name__)

BUFFER_SIZE = 50


class SignalWSClient:
    """Async WebSocket client for live trading signals."""

    def __init__(self, url: str, token: str, reconnect_interval: int = 5):
        self.url = url
        self.token = token
        self.reconnect_interval = reconnect_interval

        # State
        self._ws = None
        self._running = False
        self._connected = False
        self._authenticated = False

        # Ring buffer for signals
        self._signals: Deque[dict] = deque(maxlen=BUFFER_SIZE)
        self._signals_received = 0
        self._last_signal_time: Optional[datetime] = None
        self._connected_at: Optional[datetime] = None
        self._reconnect_count = 0

        # Broadcast callback — set by main.py
        self.on_signal: Optional[Callable] = None

    # ─── Public API ───────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self._connected and self._authenticated,
            "url": self.url,
            "signals_received": self._signals_received,
            "last_signal_time": self._last_signal_time.isoformat() if self._last_signal_time else None,
            "connected_at": self._connected_at.isoformat() if self._connected_at else None,
            "buffer_size": len(self._signals),
            "reconnect_count": self._reconnect_count,
        }

    def get_signals(self, limit: int = 50) -> List[dict]:
        return list(self._signals)[:limit]

    async def run(self):
        """Main loop — connect, auth, listen, reconnect."""
        if websockets is None:
            logger.error("websockets package not installed — signal WS disabled")
            return

        self._running = True
        logger.info(f"Signal WS client starting: {self.url}")

        while self._running:
            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Signal WS error: {e}")

            if not self._running:
                break

            self._connected = False
            self._authenticated = False
            self._reconnect_count += 1
            logger.info(f"Signal WS reconnecting in {self.reconnect_interval}s...")
            await asyncio.sleep(self.reconnect_interval)

        logger.info("Signal WS client stopped")

    def stop(self):
        self._running = False

    # ─── Internal ─────────────────────────────────────────────

    async def _connect_and_listen(self):
        async with websockets.connect(
            self.url, ping_interval=20, ping_timeout=10
        ) as ws:
            self._ws = ws
            self._connected = True
            self._connected_at = datetime.now(timezone.utc)
            logger.info("Signal WS connected")

            # Auth handshake
            if not await self._authenticate(ws):
                return

            self._authenticated = True
            logger.info("Signal WS authenticated")

            # Broadcast status update
            if self.on_signal:
                await self.on_signal("signal_status", self.get_status())

            # Listen loop
            async for raw in ws:
                if not self._running:
                    break
                await self._handle_message(raw)

    async def _authenticate(self, ws) -> bool:
        try:
            # Wait for auth_required
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(raw)
            if msg.get("type") != "auth_required":
                logger.error(f"Expected auth_required, got: {msg.get('type')}")
                return False

            # Send token
            await ws.send(json.dumps({"type": "auth", "token": self.token}))

            # Wait for response
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(raw)

            if msg.get("type") == "auth_success":
                logger.info(
                    f"Signal WS auth OK — rules={msg.get('strategy_rules_count')}, "
                    f"window={msg.get('signal_window')}min"
                )
                return True
            else:
                logger.error(f"Signal WS auth failed: {msg.get('message')}")
                return False

        except asyncio.TimeoutError:
            logger.error("Signal WS auth timeout")
            return False

    async def _handle_message(self, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        msg_type = msg.get("type")

        if msg_type == "signal":
            sig = self._normalize(msg)
            self._signals.appendleft(sig)
            self._signals_received += 1
            self._last_signal_time = datetime.now(timezone.utc)

            if self.on_signal:
                await self.on_signal("signal", sig)

        elif msg_type == "signals":
            data = msg.get("data", [])
            if data:
                for s in data:
                    sig = self._normalize(s)
                    self._signals.appendleft(sig)
                    self._signals_received += 1

                self._last_signal_time = datetime.now(timezone.utc)

                if self.on_signal:
                    await self.on_signal("signals_batch", {
                        "signals": list(self._signals),
                        "count": len(self._signals),
                    })

        elif msg_type == "pong":
            pass

        elif msg_type == "error":
            logger.warning(f"Signal server error: {msg.get('message')}")

    @staticmethod
    def _normalize(raw: dict) -> dict:
        """Normalize server signal format for the dashboard."""
        return {
            "symbol": raw.get("pair_symbol", "???"),
            "score": raw.get("total_score", 0),
            "patterns": raw.get("patterns", []),
            "rsi": raw.get("rsi"),
            "volume_zscore": raw.get("volume_zscore"),
            "oi_delta_pct": raw.get("oi_delta_pct"),
            "timestamp": raw.get("timestamp", ""),
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
