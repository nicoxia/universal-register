"""
OpenAI 注册适配器
从 codex_register/chatgpt.py 提取核心逻辑
包含: Sentinel 攻克 + OAuth2 PKCE Token 提取
"""
import json
import time
import secrets
import hashlib
import base64
import urllib.parse
from typing import Optional, Dict, Any

from curl_cffi import requests
from core.tls_client import TLSClient
from platforms import BasePlatform, _rand_name, _rand_birthdate

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# OpenAI OAuth 常量
AUTH_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
REDIRECT_URI = "http://localhost:1455/auth/callback"
SCOPE = "openid email profile offline_access"


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")

def _sha256_b64url(s):
    return _b64url(hashlib.sha256(s.encode()).digest())

def _pkce():
    return secrets.token_urlsafe(64)


class OpenAIPlatform(BasePlatform):
    platform_name = "openai"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.code_verifier = _pkce()
        self.state = secrets.token_urlsafe(16)
        self.sentinel_token = None

    def _build_auth_url(self):
        params = {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "state": self.state,
            "code_challenge": _sha256_b64url(self.code_verifier),
            "code_challenge_method": "S256",
            "prompt": "login",
        }
        return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    def _fetch_sentinel(self, flow: str, did: str) -> Optional[str]:
        """获取 Sentinel 防护 Token"""
        try:
            resp = requests.post(
                "https://sentinel.openai.com/backend-api/sentinel/req",
                headers={
                    "origin": "https://sentinel.openai.com",
                    "referer": "https://sentinel.openai.com/backend-api/sentinel/frame.html?sv=20260219f9f6",
                    "content-type": "text/plain;charset=UTF-8",
                    "user-agent": UA,
                },
                data=json.dumps({"p": "", "id": did, "flow": flow}),
                impersonate="chrome120",
                timeout=15,
                proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
            )
            if resp.status_code == 200:
                return resp.json().get("token")
        except:
            pass
        return None

    def _get_sentinel_header(self, did):
        if not self.sentinel_token:
            self.sentinel_token = self._fetch_sentinel("authorize_continue", did)
        if self.sentinel_token:
            return json.dumps({
                "p": "", "t": "", "c": self.sentinel_token,
                "id": did, "flow": "authorize_continue"
            })
        return None

    def _extract_token_from_redirect(self, client: TLSClient, redirect_url: str) -> Optional[str]:
        """跟随重定向链，提取 OAuth code 并换 Token"""
        current = redirect_url
        for _ in range(6):
            resp = client.get(current, allow_redirects=False, timeout=15)
            loc = resp.headers.get("Location", "")
            if resp.status_code not in [301, 302, 303, 307, 308] or not loc:
                break
            next_url = urllib.parse.urljoin(current, loc)
            if "code=" in next_url and "state=" in next_url:
                parsed = urllib.parse.urlparse(next_url)
                qs = urllib.parse.parse_qs(parsed.query)
                code = qs.get("code", [""])[0]
                st = qs.get("state", [""])[0]
                if code and st == self.state:
                    # 用 code 换 Token
                    import urllib.request
                    body = urllib.parse.urlencode({
                        "grant_type": "authorization_code",
                        "client_id": CLIENT_ID,
                        "code": code,
                        "redirect_uri": REDIRECT_URI,
                        "code_verifier": self.code_verifier,
                    }).encode()
                    req = urllib.request.Request(TOKEN_URL, data=body, method="POST",
                        headers={"Content-Type": "application/x-www-form-urlencoded"})
                    try:
                        with urllib.request.urlopen(req, timeout=30) as r:
                            return json.loads(r.read().decode())
                    except:
                        pass
            current = next_url
        return None

    def register(self, client: TLSClient, email: str, password: str, fetch_code) -> Optional[Dict]:
        s = client.session

        # 1. 进入 OAuth，获取 oai-did
        auth_url = self._build_auth_url()
        resp = s.get(auth_url, timeout=15)
        did = s.cookies.get("oai-did")
        if not did:
            print("  [!] 获取 oai-did 失败")
            return None

        sentinel = self._get_sentinel_header(did)
        headers = {"referer": "https://auth.openai.com/create-account"}
        if sentinel:
            headers["openai-sentinel-token"] = sentinel

        # 2. 提交邮箱
        r = s.post("https://auth.openai.com/api/accounts/authorize/continue",
                    json={"username": {"value": email, "kind": "email"}, "screen_hint": "signup"},
                    headers=headers)
        if r.status_code != 200:
            print(f"  [!] 提交邮箱失败: {r.status_code}")
            return None

        # 3. 设置密码
        headers["referer"] = "https://auth.openai.com/create-account/password"
        r = s.post("https://auth.openai.com/api/accounts/user/register",
                    json={"password": password, "username": email}, headers=headers)
        if r.status_code != 200:
            print(f"  [!] 设置密码失败: {r.status_code}")
            return None

        # 4. 发送验证码
        s.get("https://auth.openai.com/api/accounts/email-otp/send", headers=headers, timeout=15)
        code = fetch_code()
        if not code:
            print("  [!] 验证码获取失败")
            return None
        print(f"  [*] 验证码: {code}")

        # 5. 校验验证码
        headers["referer"] = "https://auth.openai.com/email-verification"
        r = s.post("https://auth.openai.com/api/accounts/email-otp/validate",
                    json={"code": code}, headers=headers)
        if r.status_code != 200:
            print(f"  [!] 验证码校验失败: {r.status_code}")
            return None

        # 6. 填写个人信息
        so_token = self._fetch_sentinel("oauth_create_account", did)
        headers = {"referer": "https://auth.openai.com/about-you"}
        if so_token:
            headers["openai-sentinel-so-token"] = so_token
        r = s.post("https://auth.openai.com/api/accounts/create_account",
                    json={"name": _rand_name(), "birthdate": _rand_birthdate()}, headers=headers)
        if r.status_code != 200:
            print(f"  [!] 填写信息失败: {r.status_code}")
            return None

        # 7. 选择工作区
        auth_cookie = s.cookies.get("oai-client-auth-session")
        if not auth_cookie:
            return None
        try:
            payload = auth_cookie.split(".")[0]
            pad = "=" * ((4 - len(payload) % 4) % 4)
            ws_info = json.loads(base64.urlsafe_b64decode((payload + pad).encode()).decode())
            ws_id = (ws_info.get("workspaces") or [{}])[0].get("id", "")
        except:
            ws_id = ""

        r = s.post("https://auth.openai.com/api/accounts/workspace/select",
                    json={"workspace_id": ws_id},
                    headers={"referer": "https://auth.openai.com/sign-in-with-chatgpt/codex/consent"})
        if r.status_code != 200:
            return None
        cont = r.json().get("continue_url", "")

        # 8. 拦截重定向获取 Token
        token_data = self._extract_token_from_redirect(client, cont)
        if token_data:
            return {
                "access_token": token_data.get("access_token", ""),
                "refresh_token": token_data.get("refresh_token", ""),
                "id_token": token_data.get("id_token", ""),
                "expires_in": token_data.get("expires_in", 0),
            }
        return None
