"""
TLS 指纹伪装 HTTP 客户端
从 codex_register 提取，基于 curl_cffi 伪装 Chrome 120
绕过 Cloudflare / TLS 指纹检测
"""
import json
import urllib.parse
from curl_cffi.requests import Session
from typing import Optional, Dict, Any

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class TLSClient:
    """伪装 Chrome 120 TLS 指纹的 HTTP 客户端"""

    def __init__(self, proxy: Optional[str] = None):
        proxies = {"http": proxy, "https": proxy} if proxy else None
        self.session = Session(proxies=proxies, impersonate="chrome120")
        self.session.headers.update({"user-agent": UA})

    def get(self, url, **kwargs):
        return self.session.get(url, **kwargs)

    def post_json(self, url, data: Dict, headers: Optional[Dict] = None, **kwargs):
        h = {"content-type": "application/json", "accept": "application/json"}
        if headers:
            h.update(headers)
        return self.session.post(url, json=data, headers=h, **kwargs)

    def post_form(self, url, data: Dict, headers: Optional[Dict] = None, **kwargs):
        h = {"content-type": "application/x-www-form-urlencoded"}
        if headers:
            h.update(headers)
        return self.session.post(url, data=urllib.parse.urlencode(data), headers=h, **kwargs)

    def cookies(self):
        return self.session.cookies
