"""
Coinone SDK (同步版)
支持常用 Public V2 接口 和 Private V2.1 签名接口
依赖: requests
pip install requests
"""
from typing import Optional, Dict, Tuple
import requests
import base64
import json
import hmac
import hashlib
import uuid


class CoinoneAPIError(Exception):
    """Coinone API 通用错误"""
    def __init__(self, message, code=None, http_status=None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class CoinoneRateLimitError(CoinoneAPIError):
    """请求频率限制错误"""
    pass


class CoinoneClient:
    PUBLIC_BASE_URL = "https://api.coinone.co.kr/public/v2"
    PRIVATE_BASE_URL = "https://api.coinone.co.kr"

    def __init__(self,
                 access_token: Optional[str] = None,
                 secret_key: Optional[str] = None,
                 session: Optional[requests.Session] = None,
                 timeout: int = 10):
        """
        初始化 Coinone 客户端
        - access_token, secret_key 如果不传，仅能访问 Public API
        - session 可选，复用 HTTP 连接
        """
        self.access_token = access_token
        self.secret_key = secret_key
        self.session = session or requests.Session()
        self.timeout = timeout

    # ================== 公共 API 方法 ==================
    def _get(self, path: str, params: Optional[Dict] = None) -> Tuple[Dict, Dict]:
        """GET 请求公共 API"""
        url = f"{self.PUBLIC_BASE_URL}{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout, headers={"Accept": "application/json"})
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise CoinoneAPIError(f"HTTP 错误: {e}", http_status=resp.status_code)

        try:
            j = resp.json()
        except ValueError:
            raise CoinoneAPIError("API 返回了无效的 JSON", http_status=resp.status_code)

        if isinstance(j, dict) and j.get("result") == "error":
            raise CoinoneAPIError(j.get("error_msg", "API 错误"), code=j.get("error_code"))

        return j, dict(resp.headers)

    def get_range_units(self, quote_currency: str, target_currency: str):
        """获取交易区间单位 GET /range_units/{quote}/{target}"""
        return self._get(f"/range_units/{quote_currency}/{target_currency}")

    def get_markets(self, quote_currency: str = "KRW"):
        """获取市场列表 GET /markets/{quote_currency}"""
        return self._get(f"/markets/{quote_currency}")

    def get_market(self, quote_currency: str, target_currency: str):
        """获取单个市场信息 GET /market/{quote}/{target}"""
        return self._get(f"/market/{quote_currency}/{target_currency}")

    def get_orderbook(self, quote_currency: str, target_currency: str, size: int = 15, order_book_unit: Optional[float] = None):
        """获取盘口数据 GET /orderbook/{quote}/{target}"""
        params = {"size": size}
        if order_book_unit is not None:
            params["order_book_unit"] = order_book_unit
        return self._get(f"/orderbook/{quote_currency}/{target_currency}", params=params)

    def get_trades(self, quote_currency: str, target_currency: str, size: int = 200):
        """获取成交记录 GET /trades/{quote}/{target}"""
        params = {"size": size}
        return self._get(f"/trades/{quote_currency}/{target_currency}", params=params)

    def get_tickers(self, quote_currency: str = "KRW", additional_data: bool = False):
        """获取所有币种行情 GET /ticker_new/{quote_currency}"""
        params = {"additional_data": "true"} if additional_data else None
        return self._get(f"/ticker_new/{quote_currency}", params=params)

    def get_ticker(self, quote_currency: str, target_currency: str, additional_data: bool = False):
        """获取单个币种行情 GET /ticker_new/{quote}/{target}"""
        params = {"additional_data": "true"} if additional_data else None
        return self._get(f"/ticker_new/{quote_currency}/{target_currency}", params=params)

    def get_chart(self, quote_currency: str, target_currency: str, interval: str, timestamp: Optional[int] = None, size: Optional[int] = None):
        """
        获取K线数据 GET /chart/{quote}/{target}
        interval 支持: 1m,3m,5m,10m,15m,30m,1h,2h,4h,6h,1d,1w,1mon
        """
        params = {"interval": interval}
        if timestamp is not None:
            params["timestamp"] = timestamp
        if size is not None:
            params["size"] = size
        return self._get(f"/chart/{quote_currency}/{target_currency}", params=params)

    # ================== 私有 API 方法 ==================
    def _encode_payload_v21(self, params: Dict) -> bytes:
        """
        V2.1 签名：nonce 使用 UUID v4，添加 access_token，然后 JSON 压缩 -> base64
        """
        body = dict(params)
        body["access_token"] = self.access_token
        body["nonce"] = str(uuid.uuid4())
        json_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        encoded = base64.b64encode(json_str.encode("utf-8"))
        return encoded

    def _sign(self, encoded_payload: bytes) -> str:
        """使用 HMAC-SHA512 签名"""
        return hmac.new(self.secret_key.encode("utf-8"), encoded_payload, hashlib.sha512).hexdigest()

    def _post_v21(self, path: str, params: Dict) -> Tuple[Dict, Dict]:
        """POST 请求私有 API (V2.1)"""
        if not self.access_token or not self.secret_key:
            raise CoinoneAPIError("调用私有 API 需要提供 access_token 和 secret_key")

        url = f"{self.PRIVATE_BASE_URL}{path}"
        encoded = self._encode_payload_v21(params)
        signature = self._sign(encoded)
        headers = {
            "Content-type": "application/json",
            "X-COINONE-PAYLOAD": encoded.decode("utf-8"),
            "X-COINONE-SIGNATURE": signature
        }
        resp = self.session.post(url, data=encoded, headers=headers, timeout=self.timeout)

        try:
            resp.raise_for_status()
        except requests.HTTPError:
            try:
                j = resp.json()
                raise CoinoneAPIError(j.get("error_msg", "HTTP 错误"), code=j.get("error_code"), http_status=resp.status_code)
            except ValueError:
                raise CoinoneAPIError("HTTP 错误", http_status=resp.status_code)

        try:
            j = resp.json()
        except ValueError:
            raise CoinoneAPIError("API 返回了无效的 JSON", http_status=resp.status_code)

        if isinstance(j, dict) and j.get("result") == "error":
            if str(j.get("error_code")) == "4":
                raise CoinoneRateLimitError(j.get("error_msg", "请求频率过高"), code=j.get("error_code"))
            raise CoinoneAPIError(j.get("error_msg", "API 错误"), code=j.get("error_code"))

        return j, dict(resp.headers)

    def place_order(self, quote_currency: str, target_currency: str, side: str, type_: str,
                    price: Optional[str] = None, qty: Optional[str] = None, amount: Optional[str] = None,
                    post_only: Optional[bool] = None, limit_price: Optional[str] = None,
                    trigger_price: Optional[str] = None, user_order_id: Optional[str] = None):
        """
        下单 POST /v2.1/order
        side: "BUY" 或 "SELL"
        type_: "LIMIT", "MARKET", "STOP_LIMIT"
        """
        payload = {
            "quote_currency": quote_currency,
            "target_currency": target_currency,
            "side": side,
            "type": type_
        }
        if price is not None:
            payload["price"] = price
        if qty is not None:
            payload["qty"] = qty
        if amount is not None:
            payload["amount"] = amount
        if post_only is not None:
            payload["post_only"] = bool(post_only)
        if limit_price is not None:
            payload["limit_price"] = limit_price
        if trigger_price is not None:
            payload["trigger_price"] = trigger_price
        if user_order_id is not None:
            payload["user_order_id"] = user_order_id
        return self._post_v21("/v2.1/order", payload)

    def get_balance_all(self):
        """获取账户全部余额 POST /v2.1/account/balance/all"""
        return self._post_v21("/v2.1/account/balance/all", {})

    def cancel_all_orders(self, quote_currency: str, target_currency: str):
        """取消某个交易对的所有挂单 POST /v2.1/order/cancel/all"""
        return self._post_v21("/v2.1/order/cancel/all", {
            "quote_currency": quote_currency,
            "target_currency": target_currency
        })
