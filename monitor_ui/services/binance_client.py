"""Binance Futures API client — async, lightweight, using aiohttp + HMAC SHA256."""
import hashlib
import hmac
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)

BINANCE_FUTURES_BASE = "https://fapi.binance.com"


class BinanceClient:
    """Async Binance USDⓈ-M Futures API client."""

    def __init__(self, api_key: str, api_secret: str):
        self._api_key = api_key
        self._api_secret = api_secret
        self._session: Optional[aiohttp.ClientSession] = None
        # Cache
        self._cache: Dict[str, Any] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"X-MBX-APIKEY": self._api_key}
            )
        return self._session

    def _sign(self, params: dict) -> str:
        query = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    async def _request(self, method: str, path: str, params: dict = None) -> Any:
        """Make signed request to Binance Futures API."""
        session = await self._get_session()
        params = params or {}
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 10000
        params["signature"] = self._sign(params)

        url = f"{BINANCE_FUTURES_BASE}{path}"
        async with session.request(method, url, params=params) as resp:
            data = await resp.json()
            if resp.status != 200:
                logger.error(f"Binance API error {resp.status}: {data}")
                raise Exception(f"Binance API error: {data.get('msg', resp.status)}")
            return data

    # ─── Account ─────────────────────────────────────────────

    async def fetch_account(self) -> Dict[str, float]:
        """Fetch wallet balance, unrealized PnL, available balance."""
        data = await self._request("GET", "/fapi/v2/account")
        return {
            "wallet_balance": float(data.get("totalWalletBalance", 0)),
            "unrealized_pnl": float(data.get("totalUnrealizedProfit", 0)),
            "available_balance": float(data.get("availableBalance", 0)),
        }

    # ─── Income History (24h) ────────────────────────────────

    async def _fetch_income_page(
        self, start_ms: int, end_ms: int, income_type: str = None, limit: int = 1000
    ) -> list:
        """Fetch one page of income records."""
        params = {
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": limit,
        }
        if income_type:
            params["incomeType"] = income_type
        return await self._request("GET", "/fapi/v1/income", params)

    async def _fetch_all_income(
        self, start_ms: int, end_ms: int, income_type: str = None
    ) -> list:
        """Fetch all income records, paginating if needed (max 1000 per page)."""
        all_records = []
        current_start = start_ms
        while True:
            page = await self._fetch_income_page(
                current_start, end_ms, income_type, limit=1000
            )
            if not page:
                break
            all_records.extend(page)
            if len(page) < 1000:
                break
            # Next page starts after the last record's timestamp
            current_start = int(page[-1]["time"]) + 1
        return all_records

    async def fetch_income_24h(self) -> Dict[str, Any]:
        """Fetch and aggregate income for last 24 hours.

        Returns: gross_pnl, commission, funding, net_pnl, winners, losers, trade_count.
        """
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=24)
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(now.timestamp() * 1000)

        records = await self._fetch_all_income(start_ms, end_ms)

        gross_pnl = 0.0
        commission = 0.0
        funding = 0.0
        winners = 0
        losers = 0

        for rec in records:
            income = float(rec.get("income", 0))
            itype = rec.get("incomeType", "")

            if itype == "REALIZED_PNL":
                gross_pnl += income
                if income > 0:
                    winners += 1
                elif income < 0:
                    losers += 1
            elif itype == "COMMISSION":
                commission += income
            elif itype == "FUNDING_FEE":
                funding += income

        net_pnl = gross_pnl + commission + funding
        trade_count = winners + losers

        return {
            "gross_pnl": round(gross_pnl, 4),
            "commission": round(commission, 4),
            "funding": round(funding, 4),
            "net_pnl": round(net_pnl, 4),
            "winners": winners,
            "losers": losers,
            "trade_count": trade_count,
            "win_rate": round((winners / trade_count * 100), 1) if trade_count > 0 else 0.0,
        }

    # ─── Combined Fetch ──────────────────────────────────────

    async def fetch_stats(self) -> Dict[str, Any]:
        """Fetch all stats in one call. Returns combined dict. Uses cache on error."""
        try:
            account = await self.fetch_account()
            income = await self.fetch_income_24h()
            result = {**account, **income}
            self._cache = result
            return result
        except Exception as e:
            logger.error(f"Binance fetch_stats error: {e}")
            if self._cache:
                logger.info("Returning cached Binance stats")
                return self._cache
            # Return zeros on first failure
            return {
                "wallet_balance": 0.0,
                "unrealized_pnl": 0.0,
                "available_balance": 0.0,
                "gross_pnl": 0.0,
                "commission": 0.0,
                "funding": 0.0,
                "net_pnl": 0.0,
                "winners": 0,
                "losers": 0,
                "trade_count": 0,
                "win_rate": 0.0,
            }

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
