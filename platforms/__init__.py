"""
平台注册适配器
每个平台继承 BasePlatform，实现 register() 方法即可
"""

import json
import time
import secrets
import hashlib
import base64
import random
import string
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from core.tls_client import TLSClient
from core.mail_tm import create_temp_mail

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class BasePlatform:
    """
    平台基类
    子类需要实现:
      - platform_name: 平台名称
      - register(client, email, password, fetch_code): 注册流程
      - extract_api_key(client, email, password): 注册后提取 API Key
    """

    platform_name = "unknown"

    def __init__(self, proxy: Optional[str] = None, out_dir: Optional[Path] = None):
        self.proxy = proxy
        self.out_dir = out_dir or Path(__file__).parent / "output"

    def register(self, client: TLSClient, email: str, password: str, fetch_code) -> Optional[Dict]:
        """子类实现：完成注册，返回账号信息 dict"""
        raise NotImplementedError

    def extract_api_key(self, client: TLSClient, email: str, password: str) -> Optional[str]:
        """子类实现：登录后提取 API Key（可选）"""
        return None

    def run(self) -> Optional[Dict]:
        """完整流程：创建邮箱 → 注册 → 保存"""
        self.out_dir.mkdir(parents=True, exist_ok=True)

        # 创建临时邮箱
        mail = create_temp_mail(proxy=self.proxy)
        if not mail:
            print(f"[{self.platform_name}] 创建邮箱失败")
            return None

        email, password, fetch_code = mail
        print(f"[{self.platform_name}] 邮箱: {email}")

        client = TLSClient(proxy=self.proxy)
        result = self.register(client, email, password, fetch_code)

        if result:
            result["email"] = email
            result["password"] = password
            result["platform"] = self.platform_name
            result["time"] = datetime.now().isoformat()

            # 保存
            fname = email.replace("@", "_")
            out_file = self.out_dir / f"{self.platform_name}_{fname}.json"
            out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{self.platform_name}] ✅ 保存至: {out_file}")

            # 追加到汇总
            summary = self.out_dir / "accounts.txt"
            with open(summary, "a", encoding="utf-8") as f:
                api_key = result.get("api_key", "")
                f.write(f"{self.platform_name}----{email}----{password}----{api_key}\n")

        return result


def _rand_name():
    first = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "David", "Elizabeth",
             "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
    last = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
            "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    return f"{random.choice(first)} {random.choice(last)}"


def _rand_birthdate():
    start = datetime(1970, 1, 1)
    end = datetime(1999, 12, 31)
    d = start + timedelta(days=random.randrange((end - start).days + 1))
    return d.strftime("%Y-%m-%d")
