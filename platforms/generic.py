"""
通用平台注册适配器
适用于任意 OpenAI 兼容 API 平台的注册：
- SiliconFlow、Groq、DeepSeek、OpenRouter、通义千问等
用户只需配置 register_url 和表单字段即可
"""
import json
import re
import time
import random
from typing import Optional, Dict, List

from core.tls_client import TLSClient
from platforms import BasePlatform


class GenericPlatform(BasePlatform):
    """
    通用注册适配器
    配置示例:

        platform = GenericPlatform(
            name="siliconflow",
            register_url="https://cloud.siliconflow.cn/api/user/register",
            form_fields={
                "email": "{email}",
                "password": "{password}",
                "username": "{username}",
            },
            method="POST",          # POST / GET
            content_type="json",    # json / form
            verify_url="https://cloud.siliconflow.cn/api/user/login",
            api_key_url="https://cloud.siliconflow.cn/api/user/token",
            otp_keywords=["verification", "code", "SiliconFlow"],
        )
    """

    def __init__(
        self,
        name: str = "generic",
        register_url: str = "",
        form_fields: Optional[Dict] = None,
        method: str = "POST",
        content_type: str = "json",
        headers: Optional[Dict] = None,
        otp_keywords: Optional[List[str]] = None,
        api_key_url: str = "",
        verify_url: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = name
        self.register_url = register_url
        self.form_fields = form_fields or {}
        self.method = method.upper()
        self.content_type = content_type
        self.extra_headers = headers or {}
        self.otp_keywords = otp_keywords
        self.api_key_url = api_key_url
        self.verify_url = verify_url

    @property
    def platform_name(self):
        return self.name

    def _gen_username(self):
        first = ["alex", "elena", "marco", "sarah", "ivan", "lucia", "kevin", "nina", "david", "kate",
                 "james", "emma", "liam", "olivia", "noah", "ava", "ethan", "mia", "lucas", "chloe"]
        last = ["smith", "jones", "brown", "davis", "wilson", "moore", "taylor", "white", "harris", "martin"]
        return f"{random.choice(first)}{random.choice(last)}{random.randint(100, 999)}"

    def _render_fields(self, email: str, password: str) -> Dict:
        """渲染模板字段"""
        username = self._gen_username()
        rendered = {}
        for k, v in self.form_fields.items():
            if isinstance(v, str):
                rendered[k] = v.format(email=email, password=password, username=username)
            else:
                rendered[k] = v
        return rendered

    def register(self, client: TLSClient, email: str, password: str, fetch_code) -> Optional[Dict]:
        fields = self._render_fields(email, password)

        if self.content_type == "json":
            resp = client.post_json(self.register_url, fields, headers=self.extra_headers)
        else:
            resp = client.post_form(self.register_url, fields, headers=self.extra_headers)

        if resp and resp.status_code in [200, 201]:
            try:
                data = resp.json()
            except:
                data = {}
            print(f"  [+] 注册成功: {data}")
            return {"raw_response": data}
        else:
            print(f"  [!] 注册失败: {resp.status_code if resp else '无响应'} {resp.text[:200] if resp else ''}")
            return None

    def extract_api_key(self, client: TLSClient, email: str, password: str) -> Optional[str]:
        """尝试登录并提取 API Key"""
        if not self.api_key_url:
            return None

        # 先登录
        if self.verify_url:
            login_resp = client.post_json(self.verify_url, {"email": email, "password": password})
            if login_resp and login_resp.status_code == 200:
                print(f"  [+] 登录成功")

        # 获取 API Key
        resp = client.get(self.api_key_url)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                # 尝试常见路径
                for path in [["api_key"], ["key"], ["data", "api_key"], ["data", "key"]]:
                    val = data
                    for p in path:
                        val = val.get(p) if isinstance(val, dict) else None
                    if val:
                        return val
            except:
                pass
        return None
